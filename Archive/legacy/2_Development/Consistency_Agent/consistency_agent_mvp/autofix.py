# autofix.py
import argparse, json, re, sys
try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML not installed. Run: pip install pyyaml\n")
    sys.exit(1)

def read_text(path): return open(path, "r", encoding="utf-8").read()
def write_text(path, content): open(path, "w", encoding="utf-8").write(content)
def write_json(path, data): open(path, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=2))

def apply_auto_fixes(text, rules):
    fixed, applied = text, []
    def do_block(name):
        nonlocal fixed, applied
        for rule in rules.get(name, []):
            pat, repl = rule.get("pattern"), rule.get("replace_with")
            if not pat or not repl: continue
            new_text, count = re.subn(pat, repl, fixed)
            if count > 0:
                applied.append({"block": name, "pattern": pat, "replace_with": repl, "count": count, "message": rule.get("message", ""), "severity": rule.get("severity", "info")})
                fixed = new_text
    for block in ["terminology", "forbidden", "style"]: do_block(block)
    return fixed, applied

def main():
    p = argparse.ArgumentParser()
    p.add_argument("input"); p.add_argument("--rules", default="rules.yaml"); p.add_argument("--out", default="fixed_output.txt")
    args = p.parse_args()
    rules = yaml.safe_load(read_text(args.rules)) or {}
    original = read_text(args.input)
    fixed, applied = apply_auto_fixes(original, rules)
    write_text(args.out, fixed)
    write_json(args.out + ".report.json", {"file": args.input, "out": args.out, "total_replacements": sum(x["count"] for x in applied), "applied": applied})
    print("[OK] Auto-fix done -> %s" % args.out)
if __name__ == "__main__": main()
