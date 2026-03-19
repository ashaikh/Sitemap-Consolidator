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

    files = download_sitemaps("https://www.example.com/sitemap.xml", tmp_path)
    assert len(files) == 2
    assert all(f.exists() for f in files)
    # Verify XML content was saved
    content = files[0].read_text()
    assert "<urlset" in content
