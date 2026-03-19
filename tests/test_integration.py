"""Integration tests — require network access. Run with: pytest -m integration

Update the URLs below to test with real sites.
"""
import pytest
from sitemap_downloader.cli import process_site

pytestmark = pytest.mark.integration

# Replace with real sitemap URLs to test
TEST_SITES = [
    "https://www.example.com/sitemap.xml",
]


@pytest.mark.integration
@pytest.mark.parametrize("sitemap_url", TEST_SITES)
def test_full_pipeline(tmp_path, sitemap_url):
    from urllib.parse import urlparse

    site_name = urlparse(sitemap_url).netloc.replace("www.", "")
    process_site(sitemap_url, str(tmp_path), "2026-01-01")

    base = tmp_path / site_name / "2026-01-01"
    assert (base / "OriginalFiles.tar.gz").exists()
    assert (base / "MergedSitemap" / f"{site_name}-2026-01-01.xml").exists()
    assert (base / "MergedSitemap" / f"{site_name}-2026-01-01.md").exists()

    report = (base / "MergedSitemap" / f"{site_name}-2026-01-01.md").read_text()
    assert "Total URLs" in report
