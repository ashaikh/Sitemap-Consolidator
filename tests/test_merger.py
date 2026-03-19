from sitemap_downloader.merger import extract_urls_from_file, merge_sitemaps


def test_extract_urls_from_file(sample_original_files):
    urls = extract_urls_from_file(sample_original_files / "sitemap-products.xml")
    assert len(urls) == 3
    assert "https://www.example.com/products/shoes" in urls


def test_merge_sitemaps_creates_valid_xml(sample_original_files, tmp_path):
    output = tmp_path / "merged.xml"
    files = list(sample_original_files.glob("*.xml"))
    total = merge_sitemaps(files, output)
    assert output.exists()
    assert total == 6  # 3 from each sitemap
    content = output.read_text()
    assert '<?xml version=' in content
    assert "<urlset" in content
    assert content.count("<url>") == 6
