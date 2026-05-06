"""Walmart smoke test — exercises the full stealth-fallback path against a
real bot-walled site. Skipped by default.

Walmart uses PerimeterX + Akamai Bot Manager, which gates XML sitemap
endpoints behind a "press and hold" CAPTCHA. Headless Playwright cannot
solve it. The full flow requires headful + a human:

    pip install -e .[stealth]
    playwright install chromium
    python run.py --from-robots https://www.walmart.com --stealth --stealth-headful

When the browser pops up showing the CAPTCHA, hold the button until it
clears. The downloader resumes and reuses cookies for all sub-sitemaps.

Automated tests below cover only what is verifiable without a human:
robots.txt discovery and confirmation that plain requests get blocked.
"""
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def test_walmart_robots_discovery():
    """Walmart's /robots.txt is open — robots discovery must succeed without stealth."""
    from sitemap_downloader.robots import discover_sitemaps

    urls = discover_sitemaps("https://www.walmart.com")
    assert len(urls) >= 5, f"expected several sitemaps, got {len(urls)}"
    assert any("sitemap_category" in u for u in urls)


def test_walmart_blocks_plain_requests():
    """Sanity: confirm plain requests still get blocked. If Walmart drops PerimeterX
    this test fails and we know to revisit the stealth path."""
    from sitemap_downloader.downloader import fetch_url, BlockedError

    with pytest.raises(BlockedError):
        fetch_url("https://www.walmart.com/sitemap_category.xml")


@pytest.mark.skip(reason="Walmart requires a human to solve press-and-hold CAPTCHA — see module docstring")
def test_walmart_stealth_fallback_downloads_one_sitemap(tmp_path):
    """Full path: requests blocked → AutoFallback → Playwright headful → human solves CAPTCHA → fetches.

    Unskip + run manually to verify end-to-end:
        pytest tests/test_walmart_smoke.py::test_walmart_stealth_fallback_downloads_one_sitemap -v -s
    """
    pytest.importorskip("playwright.sync_api")

    from sitemap_downloader.downloader import download_sitemaps
    from sitemap_downloader.fetchers import build_default_fetcher

    fetcher = build_default_fetcher(stealth=True, headless=False)
    try:
        files = download_sitemaps(
            "https://www.walmart.com/sitemap_category.xml",
            tmp_path,
            errors=[],
            fetcher=fetcher,
        )
    finally:
        fetcher.close()

    assert len(files) >= 1
    assert all(f.exists() and f.stat().st_size > 0 for f in files)
