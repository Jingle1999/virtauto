{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "410c87c6",
   "metadata": {},
   "outputs": [],
   "source": [
    "from bs4 import BeautifulSoup\n",
    "from agents.common.fs import list_html_files\n",
    "from agents.consistency_agent.policies import POLICIES\n",
    "\n",
    "def run():\n",
    "    errors = []\n",
    "    for filepath in list_html_files():\n",
    "        with open(filepath, encoding=\"utf-8\") as f:\n",
    "            soup = BeautifulSoup(f, \"lxml\")\n",
    "\n",
    "        for policy in POLICIES:\n",
    "            ok, msg = policy(soup)\n",
    "            if not ok:\n",
    "                errors.append(f\"{filepath}: {msg}\")\n",
    "\n",
    "    if errors:\n",
    "        print(\"❌ Consistency check failed:\")\n",
    "        for e in errors:\n",
    "            print(\" -\", e)\n",
    "        exit(1)\n",
    "    else:\n",
    "        print(\"✅ All consistency checks passed\")\n",
    "\n",
    "if __name__ == \"__main__\":\n",
    "    run()"
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
