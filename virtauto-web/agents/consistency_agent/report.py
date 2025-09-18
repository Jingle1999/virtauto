{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "1461274a",
   "metadata": {},
   "outputs": [],
   "source": [
    "from datetime import datetim\n",
    "from pathlib import Path\n",
    "\n",
    "def write_markdown(report_path: str, ok: bool, items: list[str]):
       p = Path(report_path)
       p.parent.mkdir(parents=True, exist_ok=True)
       stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
       status = "✅ PASSED" if ok else "❌ FAILED"
       lines = [
           "# Web Agents Consistency Report",
           f"- Status: **{status}**",
           f"- Generated: {stamp}",
           "",
       ]
       if ok:
           lines.append("All checks passed.")
       else:
           lines.append("## Details")
           lines += [f"- {x}" for x in items]
           p.write_text("\n".join(lines), encoding="utf-8")
"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.6.8"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import markdown as md

def write_markdown(report_path: str, ok: bool, items: list[str]):
    p = Path(report_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    status = "✅ PASSED" if ok else "❌ FAILED"
    lines = [
        f"# Web Agents Consistency Report",
        f"- Status: **{status}**",
        f"- Generated: {stamp}",
        "",
        "## Details" if not ok else "All checks passed.",
    ]
    if not ok:
        lines += [*(f"- {x}" for x in items)]
    p.write_text("\n".join(lines), encoding="utf-8")

def write_html(template_dir: str, template_name: str, out_path: str, ok: bool, items: list[str]):
    env = Environment(loader=FileSystemLoader(template_dir))
    tpl = env.get_template(template_name)
    html = tpl.render(ok=ok, items=items, generated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
