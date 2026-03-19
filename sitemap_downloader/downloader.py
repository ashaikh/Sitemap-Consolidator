"""Download sitemaps from websites, handling sitemap indexes and gzip."""

import gzip
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
USER_AGENT = "SitemapDownloader/0.1 (+https://github.com/sitemap-downloader)"


def is_sitemap_index(xml_content: str) -> bool:
    """Check if XML content is a sitemap index (vs a regular urlset sitemap)."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return False
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    return tag == "sitemapindex"


def parse_sitemap_index_urls(xml_content: str) -> list[str]:
    """Extract sitemap URLs from a sitemap index XML string."""
    root = ET.fromstring(xml_content)
    ns = {"sm": SITEMAP_NS}
    return [loc.text for loc in root.findall(".//sm:sitemap/sm:loc", ns) if loc.text]
