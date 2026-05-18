@echo off
setlocal
set RULES=rules.yaml

echo === virtauto Auto-Fix (Batch) ===
for %%F in (*.txt) do (
  echo Fixing %%F ...
  python autofix.py "%%F" --rules %RULES% --out "%%~nF_fixed.txt"
)
echo === Done. All fixed files and reports created. ===
endlocal
