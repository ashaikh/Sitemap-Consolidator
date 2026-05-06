"""Tests for robots.txt sitemap discovery."""
from unittest.mock import patch

from sitemap_downloader.robots import parse_sitemaps, discover_sitemaps


ROBOTS_SAMPLE = """\
User-agent: *
Disallow: /search

# Sitemaps below
Sitemap: https://www.walmart.com/sitemap_category.xml
sitemap: https://www.walmart.com/sitemap_store_main.xml
SITEMAP:   https://www.walmart.com/help/sitemap_gm.xml
"""


def test_parse_sitemaps_extracts_all_case_insensitive():
    out = parse_sitemaps(ROBOTS_SAMPLE)
    assert out == [
        "https://www.walmart.com/sitemap_category.xml",
        "https://www.walmart.com/sitemap_store_main.xml",
        "https://www.walmart.com/help/sitemap_gm.xml",
    ]


def test_parse_sitemaps_skips_comments_and_blank():
    text = "# comment\n\nSitemap: https://x.com/a.xml\n# Sitemap: https://nope.com/b.xml\n"
    assert parse_sitemaps(text) == ["https://x.com/a.xml"]


def test_discover_sitemaps_fetches_robots_and_returns_urls():
    with patch("sitemap_downloader.robots.fetch_url", return_value=ROBOTS_SAMPLE.encode()) as m:
        urls = discover_sitemaps("https://www.walmart.com")
    m.assert_called_once_with("https://www.walmart.com/robots.txt")
    assert len(urls) == 3
    assert urls[0] == "https://www.walmart.com/sitemap_category.xml"


def test_discover_sitemaps_normalizes_origin():
    with patch("sitemap_downloader.robots.fetch_url", return_value=b"Sitemap: https://x.com/a.xml") as m:
        # trailing slash, path, query — all should be stripped
        discover_sitemaps("https://x.com/some/path?q=1")
    m.assert_called_once_with("https://x.com/robots.txt")
