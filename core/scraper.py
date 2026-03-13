"""
core/scraper.py
Scrapes a clinic's website and returns clean text for the AI knowledge base.
Fetches homepage + key sub-pages (about, services, contact, hours).
"""

import re
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# Pages worth scraping (matched against href)
_KEY_SLUGS = (
    "about", "services", "treatment", "contact", "hours",
    "team", "staff", "faq", "insurance", "appointment",
)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DentalBot/1.0)"
}


def _fetch(url: str, timeout: int = 8) -> str | None:
    """Fetch a URL and return HTML, or None on failure."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


def _extract_text(html: str) -> str:
    """Strip tags and return clean readable text."""
    soup = BeautifulSoup(html, "html.parser")
    # Remove noise
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "noscript", "iframe", "form", "svg"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _find_key_links(html: str, base_url: str) -> list[str]:
    """Find internal links that look like key info pages."""
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc
    found = []
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        full = urljoin(base_url, a["href"])
        if urlparse(full).netloc != base_domain:
            continue  # skip external links
        if any(slug in href for slug in _KEY_SLUGS):
            if full not in found:
                found.append(full)
    return found[:5]  # cap at 5 sub-pages


def scrape_website(url: str, max_chars: int = 6000) -> str:
    """
    Scrape the clinic's website and return a text summary.
    Returns empty string if the site can't be reached.
    """
    if not url:
        return ""

    # Normalize URL
    if not url.startswith("http"):
        url = "https://" + url

    homepage_html = _fetch(url)
    if not homepage_html:
        return ""

    pages_text = [_extract_text(homepage_html)]

    # Scrape key sub-pages
    for link in _find_key_links(homepage_html, url):
        html = _fetch(link)
        if html:
            pages_text.append(_extract_text(html))

    combined = "\n\n".join(pages_text)
    return combined[:max_chars]
