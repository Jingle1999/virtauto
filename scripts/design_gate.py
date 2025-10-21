#!/usr/bin/env python3
import sys, re, yaml, pathlib, math

TOKENS_PATH = sys.argv[1] if len(sys.argv) > 1 else "rules/design_tokens.yaml"
CHECKS_PATH = sys.argv[2] if len(sys.argv) > 2 else "rules/design_checks.yaml"
root = pathlib.Path(".")

def load_yaml(p):
    p = pathlib.Path(p)
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}

tokens = load_yaml(TOKENS_PATH)
checks = load_yaml(CHECKS_PATH)

# ---- helpers ---------------------------------------------------------------
def hex_to_rgb(h):
    h = h.strip().lstrip("#")
    if len(h)==3: h = "".join([c*2 for c in h])
    return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))

def rel_lum(c):
    def f(v): 
        return v/12.92 if v<=0.03928 else ((v+0.055)/1.055)**2.4
    r,g,b = [f(v) for v in c]
    return 0.2126*r + 0.7152*g + 0.0722*b

def contrast_ratio(fg, bg):
    L1, L2 = rel_lum(hex_to_rgb(fg)), rel_lum(hex_to_rgb(bg))
    L1, L2 = max(L1,L2), min(L1,L2)
    return (L1+0.05)/(L2+0.05)

def token_color(name):
    if name.startswith("$"):
        key = name[1:]
        return tokens.get("colors",{}).get(key)
    return name

VIOLATIONS = []
def note(msg, path=None):
    prefix = f"[DESIGN] {path} - " if path else "[DESIGN] "
    VIOLATIONS.append(prefix + msg)

# ---- 1) Contrast checks on token pairs ------------------------------------
pairs = checks.get("contrast",{}).get("pairs_to_test", [])
normal_min = float(checks.get("contrast",{}).get("normal_text_min",4.5))
large_min  = float(checks.get("contrast",{}).get("large_text_min",3.0))

for a,b in pairs:
    ca, cb = token_color(a), token_color(b)
    if not ca or not cb: 
        note(f"Token color unresolved: {a}/{b}")
        continue
    cr = contrast_ratio(ca,cb)
    if cr < large_min:
        note(f"Contrast too low ({cr:.2f}) for pair {a} on {b}")

# ---- 2) Typography & spacing scales presence --------------------------------
typo = tokens.get("typography",{})
if not typo.get("scale_steps"): note("No typography scale defined in tokens.")
if not tokens.get("spacing",{}).get("scale_px"): note("No spacing scale defined in tokens.")

# ---- 3) Enforce token usage in CSS/HTML -------------------------------------
enforce = checks.get("consistency",{}).get("enforce_tokens", True)
allow_inline_hex = checks.get("consistency",{}).get("allow_inline_hex", False)

allowed_hex = set(v.lower() for v in tokens.get("colors",{}).values())
hex_re = re.compile(r"#[0-9A-Fa-f]{3,6}")

def scan_paths(paths_glob, exts):
    files=[]
    for p in paths_glob:
        base = root / p
        if base.exists():
            for f in base.rglob("*"):
                if f.suffix.lower() in exts and f.is_file():
                    files.append(f)
    return files

css_files  = scan_paths(checks.get("css_search_paths",["src","public","styles"]), {".css",".astro",".html",".mdx",".tsx",".ts",".js"})
html_files = scan_paths(checks.get("html_search_paths",["src","public"]), {".astro",".html"})

def is_data_uri(line): 
    return "data:image" in line

if enforce:
    for f in css_files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        for m in hex_re.finditer(text):
            hx = m.group(0).lower()
            if is_data_uri(text[max(0,m.start()-24):m.end()+24]): 
                continue
            if hx not in allowed_hex and not allow_inline_hex:
                note(f"Non-token color used: {hx}", f)

# ---- 4) Page brand-color budget heuristic -----------------------------------
budget = int(tokens.get("budgets",{}).get("max_brand_colors_per_page",3))
brand_keys = ["primary","secondary","accent"]
brand_hex  = [tokens.get("colors",{}).get(k,"").lower() for k in brand_keys]
for f in html_files:
    text = f.read_text(encoding="utf-8", errors="ignore").lower()
    used = set([hx for hx in brand_hex if hx and hx in text])
    if len(used) > budget:
        note(f"Brand color overuse: {len(used)} > budget {budget}", f)

# ---- 5) Output ---------------------------------------------------------------
report = "\n".join(VIOLATIONS) if VIOLATIONS else "Design gate passed with no issues."
print(report)
pathlib.Path("design_gate_report.txt").write_text(report, encoding="utf-8")
# Nicht failen – nur berichten (Governance, kein Hard-Block):
sys.exit(0)
