from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .filters import normalize


def extract_links(html: str, base_url: str) -> list:
    """Pull all <a href> targets out of HTML, resolved to absolute and normalized."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        absolute = normalize(urljoin(base_url, href))
        if absolute in seen:
            continue
        seen.add(absolute)
        out.append(absolute)
    return out
