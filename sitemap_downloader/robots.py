"""Discover sitemaps from a site's /robots.txt."""

import re
from urllib.parse import urlparse

from sitemap_downloader.downloader import fetch_url

_SITEMAP_RE = re.compile(r"^\s*sitemap\s*:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)


def parse_sitemaps(robots_text: str) -> list[str]:
    """Extract Sitemap: URLs from robots.txt content (case-insensitive, skips comments)."""
    out: list[str] = []
    for line in robots_text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = _SITEMAP_RE.match(s)
        if m:
            out.append(m.group(1))
    return out


def _origin(url: str) -> str:
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        raise ValueError(f"Cannot derive origin from: {url}")
    return f"{p.scheme}://{p.netloc}"


def discover_sitemaps(site_url: str) -> list[str]:
    """Fetch <origin>/robots.txt and return all Sitemap: URLs."""
    robots_url = f"{_origin(site_url)}/robots.txt"
    content = fetch_url(robots_url)
    return parse_sitemaps(content.decode("utf-8", errors="replace"))
