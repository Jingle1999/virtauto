# virtauto Consistency Agent (MVP)

This is the MVP version of the virtauto Consistency Agent.  
It checks documents for consistency, applies auto-fixes, and generates reports (JSON + Markdown).

## 🚀 Usage

### 1. Install dependencies
```bash
pip install pyyaml tqdm
```

### 2. Lint a file (check only)
```bash
python consistency_agent.py lint demo_input.txt --rules rules.yaml --glossary glossary.md --out report.json
```

Outputs:
- `report.json` (machine-readable)
- `report.md` (human-readable table)

### 3. Auto-fix a file
```bash
python autofix.py demo_input.txt --rules rules.yaml --out demo_output.txt
```

Outputs:
- `demo_output.txt` (fixed text)
- `demo_output.txt.report.json` (applied fixes)

### 4. Batch auto-fix
Run all `.txt` files in the folder:
```bash
run_fix_all.bat
```

---
## 📂 Files

- `consistency_agent.py` → Linting + Reports (JSON + Markdown)
- `autofix.py` → Standalone auto-fix tool
- `rules.yaml` → Consistency rules (regex patterns)
- `glossary.md` → Glossary with canonical terminology
- `demo_input.txt` → Example input with inconsistencies
- `demo_input_fixed.txt` → Example fixed output
- `demo_input_fixed.txt.report.json` → Example report for fixed file
- `report.md` → Example Markdown report
- `run_fix_all.bat` → Batch script to auto-fix all text files
