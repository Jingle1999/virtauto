import argparse
import json
import os
import re
from typing import List, Dict, Any

import yaml

# --- Simple file helpers -----------------------------------------------------

def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_json(path: str, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- Rule-based linter -------------------------------------------------------

def apply_regex_checks(text: str, rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings = []

    # Terminology patterns
    for rule in rules.get("terminology", []):
        pat = rule.get("pattern")
        msg = rule.get("message", "Rule violation")
        sev = rule.get("severity", "info")
        repl = rule.get("replace_with")
        for m in re.finditer(pat, text):
            snippet = text[max(0, m.start()-30): m.end()+30]
            finding = {
                "type": "terminology",
                "severity": sev,
                "message": msg,
                "span": [m.start(), m.end()],
                "snippet": snippet,
            }
            if repl:
                finding["suggestion"] = f"Replace with '{repl}'"
            findings.append(finding)

    # Optional: basic doc structure checks can be added here for .md/.txt

    return findings

# --- Optional LLM review -----------------------------------------------------

def llm_review(content: str, cfg: Dict[str, Any], glossary_snip: str, rules_snip: str) -> Dict[str, Any]:
    provider = cfg.get("provider", "openai")
    if provider == "openai":
        try:
            import openai
            api_key_env = cfg.get("openai", {}).get("api_key_env", "OPENAI_API_KEY")
            openai.api_key = os.getenv(api_key_env)
            if not openai.api_key:
                return {"error": f"Missing {api_key_env} env var for OpenAI."}

            system = read_text(cfg["paths"]["prompts"]["system"])
            user_tmpl = read_text(cfg["paths"]["prompts"]["user_template"])
            prompt = user_tmpl.replace("{{GLOSSARY_SNIPPET}}", glossary_snip[:1200])\
                              .replace("{{RULES_SNIPPET}}", rules_snip[:1200])\
                              .replace("{{CONTENT}}", content[:12000])

            # Using ChatCompletion-style for portability; adjust for SDK version as needed
            from openai import OpenAI
            client = OpenAI()
            resp = client.chat.completions.create(
                model=cfg.get("model", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            text = resp.choices[0].message.content
            # If model returns JSON in text, try to parse; otherwise wrap
            try:
                data = json.loads(text)
            except Exception:
                data = {"summary": text, "issues": [], "alignment_score": None, "decisions": []}
            return data
        except Exception as e:
            return {"error": f"OpenAI review failed: {e}"}

    elif provider == "bedrock":
        try:
            import boto3, botocore
            # left as an exercise to wire Anthropic/Bedrock response format
            return {"error": "Bedrock path not implemented in MVP."}
        except Exception as e:
            return {"error": f"Bedrock review failed: {e}"}

    return {"error": "Unknown provider"}

# --- CLI ---------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="virtauto Consistency Agent (MVP)")
    sub = p.add_subparsers(dest="cmd")

    p_lint = sub.add_parser("lint", help="Rule-based lint (no AI)")
    p_lint.add_argument("input", help="Path to .txt/.md file")
    p_lint.add_argument("--rules", default="rules.yaml")
    p_lint.add_argument("--glossary", default="glossary.md")
    p_lint.add_argument("--out", default="report.json")

    p_review = sub.add_parser("review", help="Optional LLM review (needs config.yaml)")
    p_review.add_argument("input", help="Path to .txt/.md file")
    p_review.add_argument("--config", default="config.yaml")
    p_review.add_argument("--out", default="review.json")

    args = p.parse_args()
    
    if not args.cmd:
        p.print_help()
        return

    if args.cmd == "lint":
        rules = yaml.safe_load(read_text(args.rules))
        text = read_text(args.input)
        findings = apply_regex_checks(text, rules)
        out = {
            "file": args.input,
            "total_findings": len(findings),
            "findings": findings,
            "advice": "Fix 'error' first, then 'warn'. 'info' is best-practice."
        }
        write_json(args.out, out)
        print(f"[OK] Lint done -> {args.out} (findings: {len(findings)})")

    elif args.cmd == "review":
        cfg = yaml.safe_load(read_text(args.config))
        text = read_text(args.input)
        glossary_snip = read_text(cfg["paths"]["glossary"]) if "paths" in cfg and "glossary" in cfg["paths"] else ""
        rules_snip = read_text(cfg["paths"]["rules"]) if "paths" in cfg and "rules" in cfg["paths"] else ""
        result = llm_review(text, cfg, glossary_snip, rules_snip)
        write_json(args.out, result)
        if "error" in result:
            print(f"[ERR] {result['error']}")
        else:
            print(f"[OK] Review done -> {args.out}")
    else:
        p.print_help()

if __name__ == "__main__":
    main()
