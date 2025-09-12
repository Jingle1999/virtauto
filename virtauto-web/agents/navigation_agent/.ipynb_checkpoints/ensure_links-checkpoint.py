{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "2151829e",
   "metadata": {},
   "outputs": [],
   "source": [
    "import os\n",
    "from bs4 import BeautifulSoup\n",
    "from agents.common.fs import list_html_files\n",
    "\n",
    "NAV_TEMPLATE = \"\"\"\n",
    "<nav>\n",
    "  <a href=\"/index.html\">Home</a>\n",
    "  <a href=\"/agents.html\">Agents</a>\n",
    "  <a href=\"/architecture.html\">Architecture</a>\n",
    "  <a href=\"/solutions.html\">Solutions</a>\n",
    "  <a href=\"/use-cases.html\">Use Cases</a>\n",
    "  <a href=\"/blog.html\">Blog</a>\n",
    "  <a href=\"/contact.html\">Contact</a>\n",
    "</nav>\n",
    "\"\"\"\n",
    "\n",
    "def ensure_nav(filepath):\n",
    "    with open(filepath, encoding=\"utf-8\") as f:\n",
    "        soup = BeautifulSoup(f, \"lxml\")\n",
    "\n",
    "    if not soup.find(\"nav\"):\n",
    "        soup.body.insert(0, BeautifulSoup(NAV_TEMPLATE, \"lxml\"))\n",
    "\n",
    "    with open(filepath, \"w\", encoding=\"utf-8\") as f:\n",
    "        f.write(str(soup))\n",
    "\n",
    "def run():\n",
    "    for filepath in list_html_files():\n",
    "        ensure_nav(filepath)\n",
    "        print(f\"✅ Navigation ensured in {filepath}\")\n",
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
