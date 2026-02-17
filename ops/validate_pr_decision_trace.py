# ops/validate_pr_decision_trace.py
from pathlib import PurePosixPath

ALLOWED_DECISION_TRACE_PATTERNS = [
    "decision_trace.md",
    "decision_trace.jsonl",
    "decision_traces/*.decision_trace.md",
    "decision_traces/*.decision_trace.json",
    "decision_traces/**/*.decision_trace.md",
    "decision_traces/**/*.decision_trace.json",
]

def matches_any(path: str, patterns: list[str]) -> bool:
    p = PurePosixPath(path)
    return any(p.match(pattern) for pattern in patterns)

# ... dort wo du changed files prüfst:
# if not any(fnmatch(f, pattern) ...):
# -> ersetzen durch:
if not any(matches_any(f, ALLOWED_DECISION_TRACE_PATTERNS) for f in changed_files):
    # fail wie bisher
