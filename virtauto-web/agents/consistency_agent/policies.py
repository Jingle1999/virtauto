# virtauto-web/agents/consistency_agent/policies.py
from __future__ import annotations

from typing import Callable, List
from bs4 import BeautifulSoup


# Jede Policy ist eine Funktion, die einen BeautifulSoup-DOM bekommt
# und True (bestanden) bzw. False (nicht bestanden) zurückgibt.

def check_meta_charset(soup: BeautifulSoup) -> bool:
    """UTF-8-Metatags vorhanden?"""
    tag = soup.find("meta", attrs={"charset": True})
    return bool(tag and str(tag.get("charset")).lower() == "utf-8")


def check_title(soup: BeautifulSoup) -> bool:
    """<title> vorhanden und nicht leer?"""
    return bool(soup.title and soup.title.get_text(strip=True))


def check_meta_description(soup: BeautifulSoup) -> bool:
    """Meta-Description vorhanden und nicht leer?"""
    tag = soup.find("meta", attrs={"name": "description"})
    return bool(tag and tag.get("content") and tag.get("content").strip())


def check_h1_exists(soup: BeautifulSoup) -> bool:
    """Mindestens eine <h1>-Überschrift mit Text?"""
    h1 = soup.find("h1")
    return bool(h1 and h1.get_text(strip=True))


def check_html_lang(soup: BeautifulSoup) -> bool:
    """html[lang] gesetzt? (z. B. 'de' / 'en')"""
    html = soup.find("html")
    return bool(html and html.get("lang"))


# Die Liste der aktiven Prüfregeln:
POLICIES: List[Callable[[BeautifulSoup], bool]] = [
    check_meta_charset,
    check_title,
    check_meta_description,
    check_h1_exists,
    check_html_lang,
]
