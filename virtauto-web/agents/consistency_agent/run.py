# virtauto-web/agents/consistency_agent/run.py

from bs4 import BeautifulSoup
from agents.common.fs import list_html_files
from agents.consistency_agent.policies import POLICIES
from agents.consistency_agent.report import write_markdown, write_html

with open(filepath, "rb") as f:
    soup = BeautifulSoup(f.read(), "html.parser")  # <— Standard-Parser, kein lxml

from pathlib import Path
import sys
# fügt <repo-root>\virtauto-web zum Suchpfad hinzu
sys.path.append(str(Path(__file__).resolve().parents[2]))


def run() -> None:
    """
    Läuft über alle HTML-Dateien (aus list_html_files),
    wendet die POLICIES an, erzeugt Markdown- und HTML-Report
    und beendet den Prozess mit passendem Exit-Code (0/1).
    """
    errors: list[str] = []

    # --- Checks ausführen ---
    for filepath in list_html_files():
        with open(filepath, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "lxml")

        for policy in POLICIES:
            ok, msg = policy(soup)
            if not ok:
                errors.append(f"{filepath}: {msg}")

    ok = len(errors) == 0

    # --- Reports erzeugen ---
    # 1) Markdown (für GitHub Actions Artifact)
    md_path = "agents-reports/web-consistency.md"
    write_markdown(md_path, ok=ok, items=errors)

    # 2) HTML (wird in die Website gelegt und per Pages veröffentlicht)
    html_path = "virtauto-web/site/src/reports/consistency.html"
    write_html(
        template_dir="virtauto-web/agents/consistency_agent/templates",
        template_name="report.html",
        out_path=html_path,
        ok=ok,
        items=errors,
    )

    # --- Exit-Code / Ausgabe ---
    if not ok:
        print("❌ Consistency check failed! Details:")
        for e in errors:
            print(" -", e)
        # Non-zero Exit damit CI fehlschlägt
        exit(1)

    print("✅ All consistency checks passed")


if __name__ == "__main__":
    run()