#!/usr/bin/env python3
import sys, yaml, frontmatter, pathlib, re

rules_path = sys.argv[1] if len(sys.argv) > 1 else "rules/style_guide.yaml"
rules = yaml.safe_load(open(rules_path, encoding="utf-8")) if pathlib.Path(rules_path).exists() else {}
root = pathlib.Path(".")
violations = []

def note(msg, path=None):
    prefix = f"[VIOLATION] {path} - " if path else "[VIOLATION] "
    violations.append(prefix + msg)

for md in root.rglob("content/**/*.md"):
    post = frontmatter.load(md)
    for k in rules.get("frontmatter_required", []):
        if k not in post.metadata or not post.metadata.get(k):
            note(f"Missing frontmatter '{k}'", md)

    h1 = re.findall(r"^# (.+)$", post.content, flags=re.M)
    if h1 and len(h1[0]) > rules.get("h1",{}).get("max_length", 70):
        note(f"H1 too long ({len(h1[0])} chars > limit)", md)

    text_lower = (post.content + " " + " ".join([str(v) for v in post.metadata.values()])).lower()
    for p in rules.get("forbidden_phrases", []):
        if p.lower() in text_lower:
            note(f"Forbidden phrase found: '{p}'", md)

    if rules.get("links",{}).get("require_canonical_if_external", False):
        src = post.metadata.get("source","")
        canon = post.metadata.get("canonical","")
        if src.startswith("http") and not canon:
            note("External 'source' without 'canonical' url", md)

allowed_ext = set(rules.get("files",{}).get("allowed_extensions", []))
if allowed_ext:
    for p in root.rglob("content/**/*"):
        if p.is_file() and p.suffix and p.parent.name != "ingest":
            if p.suffix not in allowed_ext:
                note(f"Disallowed file extension '{p.suffix}'", p)

if violations:
    print("\n".join(violations))
else:
    print("Review gate passed with no violations.")
