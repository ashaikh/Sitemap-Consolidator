from sitemap_downloader.downloader import is_sitemap_index, parse_sitemap_index_urls


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
