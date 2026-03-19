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


def decompress_if_gzip(content: bytes) -> str:
    """Decompress gzip content if applicable, otherwise decode as UTF-8."""
    if content[:2] == b"\x1f\x8b":  # gzip magic number
        return gzip.decompress(content).decode("utf-8")
    return content.decode("utf-8")


def fetch_url(url: str) -> bytes:
    """Fetch a URL and return raw bytes."""
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.content


def download_sitemaps(sitemap_url: str, output_dir: Path) -> list[Path]:
    """Download all sitemaps from a URL. Handles sitemap indexes recursively.

    Args:
        sitemap_url: URL to the sitemap or sitemap index
        output_dir: Directory to save downloaded files (OriginalFiles/)

    Returns:
        List of paths to downloaded sitemap files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    content = fetch_url(sitemap_url)
    xml_str = decompress_if_gzip(content)

    if is_sitemap_index(xml_str):
        sub_urls = parse_sitemap_index_urls(xml_str)
        # Save the index file itself
        index_path = output_dir / _filename_from_url(sitemap_url)
        index_path.write_text(xml_str, encoding="utf-8")

        downloaded = []
        for url in sub_urls:
            try:
                downloaded.extend(download_sitemaps(url, output_dir))
            except Exception as e:
                print(f"  Warning: failed to download {url}: {e}")
        return downloaded
    else:
        # Regular sitemap — save it
        filename = _filename_from_url(sitemap_url)
        filepath = output_dir / filename
        filepath.write_text(xml_str, encoding="utf-8")
        return [filepath]


def _filename_from_url(url: str) -> str:
    """Extract a clean filename from a sitemap URL."""
    parsed = urlparse(url)
    name = Path(parsed.path).name
    # Strip .gz extension since we decompress
    if name.endswith(".gz"):
        name = name[:-3]
    return name or "sitemap.xml"
