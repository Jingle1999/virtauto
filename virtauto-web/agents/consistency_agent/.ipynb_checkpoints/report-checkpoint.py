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
    "def write_markdown(report_path: str, ok: bool, items: list[str]):\n",
    "    p = Path(report_path)\n",
    "    p.parent.mkdir(parents=True, exist_ok=True)\n",
    "    stamp = datetime.utcnow().strftime(\"%Y-%m-%d %H:%M:%S UTC\")\n",
    "    status = \"✅ PASSED\" if ok else \"❌ FAILED\"\n",
    "    lines = [\n",
    "        f\"# Web Agents Consistency Report\",\n",
    "        f\"- Status: **{status}**\",\n",
    "        f\"- Generated: {stamp}\",\n",
    "        \"\",\n",
    "        \"## Details\" if not ok else \"All checks passed.\",\n",
    "    ]\n",
    "    if not ok:\n",
    "        lines += [*(f\"- {x}\" for x in items)]\n",
    "    p.write_text(\"\\n\".join(lines), encoding=\"utf-8\")"
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
