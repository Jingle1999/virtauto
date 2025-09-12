{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "c8cef168",
   "metadata": {},
   "outputs": [],
   "source": [
    "def check_meta_charset(soup):\n",
    "    \"\"\"Ensure UTF-8 meta tag exists\"\"\"\n",
    "    meta = soup.find(\"meta\", {\"charset\": \"utf-8\"})\n",
    "    return bool(meta), \"Missing <meta charset='utf-8'>\"\n",
    "\n",
    "def check_title(soup):\n",
    "    \"\"\"Ensure page has a <title>\"\"\"\n",
    "    title = soup.find(\"title\")\n",
    "    return bool(title and title.text.strip()), \"Missing <title> tag\"\n",
    "\n",
    "POLICIES = [check_meta_charset, check_title]"
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
