# virtauto-web/agents/common/fs.py
from pathlib import Path
from typing import Iterable, List, Sequence

EXCLUDE_DIRS: Sequence[str] = (".git", ".github", "__pycache__", "node_modules")

def list_html_files(root: Path | str = ".", patterns: Iterable[str] = ("*.html", "*.htm")) -> List[Path]:
    """
    Liefert alle HTML/HTM-Dateien unterhalb von `root`, rekursiv,
    und überspringt typische Ausschlussordner.
    """
    root = Path(root)
    files: List[Path] = []
    for pat in patterns:
        for p in root.rglob(pat):
            if not any(part in EXCLUDE_DIRS for part in p.parts):
                files.append(p)
    return sorted(files)
