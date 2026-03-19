import gzip
from unittest.mock import patch

from sitemap_downloader.downloader import is_sitemap_index, parse_sitemap_index_urls
from tests.conftest import SAMPLE_SITEMAP_INDEX, SAMPLE_SITEMAP_1, SAMPLE_SITEMAP_2


def test_is_sitemap_index_returns_true_for_index(sample_sitemap_index):
    assert is_sitemap_index(sample_sitemap_index) is True


def test_is_sitemap_index_returns_false_for_urlset(sample_sitemap_1):
    assert is_sitemap_index(sample_sitemap_1) is False


def test_parse_sitemap_index_extracts_urls(sample_sitemap_index):
    urls = parse_sitemap_index_urls(sample_sitemap_index)
    assert urls == [
        "https://www.example.com/sitemap-products.xml",
        "https://www.example.com/sitemap-pages.xml.gz",
    ]


def test_decompress_gzip_content(sample_sitemap_1):
    from sitemap_downloader.downloader import decompress_if_gzip

    compressed = gzip.compress(sample_sitemap_1.encode("utf-8"))
    result = decompress_if_gzip(compressed)
    assert "<urlset" in result


def test_decompress_plain_xml(sample_sitemap_1):
    from sitemap_downloader.downloader import decompress_if_gzip

    result = decompress_if_gzip(sample_sitemap_1.encode("utf-8"))
    assert "<urlset" in result


def _mock_fetch_url(url: str) -> bytes:
    """Return mock content based on URL — patches fetch_url directly."""
    if "sitemap.xml" in url and "products" not in url and "pages" not in url:
        return SAMPLE_SITEMAP_INDEX.encode()
    elif "products" in url:
        return SAMPLE_SITEMAP_1.encode()
    elif "pages" in url:
        return SAMPLE_SITEMAP_2.encode()
    raise ValueError(f"Unexpected URL in mock: {url}")


@patch("sitemap_downloader.downloader.fetch_url", side_effect=_mock_fetch_url)
def test_download_sitemaps_creates_files(mock_fetch, tmp_path):
    from sitemap_downloader.downloader import download_sitemaps

    errors = []
    files = download_sitemaps("https://www.example.com/sitemap.xml", tmp_path, errors)
    assert len(files) == 2
    assert all(f.exists() for f in files)
    assert len(errors) == 0
    # Verify XML content was saved
    content = files[0].read_text()
    assert "<urlset" in content


@patch("sitemap_downloader.downloader.fetch_url", side_effect=_mock_fetch_url)
def test_download_sitemaps_collects_errors_on_failure(mock_fetch, tmp_path):
    from sitemap_downloader.downloader import download_sitemaps

    def _fail_on_pages(url: str) -> bytes:
        if "pages" in url:
            raise ConnectionError("Connection refused")
        return _mock_fetch_url(url)

    mock_fetch.side_effect = _fail_on_pages
    errors = []
    files = download_sitemaps("https://www.example.com/sitemap.xml", tmp_path, errors)
    assert len(files) == 1  # only products succeeded
    assert len(errors) == 1
    assert errors[0]["error_type"] == "ConnectionError"
    assert "Connection refused" in errors[0]["error"]
    assert errors[0]["url"] == "https://www.example.com/sitemap-pages.xml.gz"


def test_validate_xml_rejects_non_sitemap():
    from sitemap_downloader.downloader import _validate_xml
    import pytest

    with pytest.raises(ValueError, match="Not a sitemap"):
        _validate_xml("<html><body>Not a sitemap</body></html>", "http://example.com")


def test_unique_filename_avoids_collisions():
    from sitemap_downloader.downloader import _unique_filename

    used = {}
    assert _unique_filename("https://example.com/sitemap.xml", used) == "sitemap.xml"
    assert _unique_filename("https://example.com/en-gb/sitemap.xml", used) == "sitemap-1.xml"
    assert _unique_filename("https://example.com/en-ca/sitemap.xml", used) == "sitemap-2.xml"
    assert _unique_filename("https://example.com/products.xml", used) == "products.xml"
