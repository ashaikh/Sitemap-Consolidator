from sitemap_downloader.analyzer import count_sections, count_subdomains, generate_report

SAMPLE_URLS = [
    "https://www.example.com/products/shoes",
    "https://www.example.com/products/shoes/running",
    "https://www.example.com/products/shoes/casual",
    "https://www.example.com/products/hats",
    "https://www.example.com/about",
    "https://www.example.com/blog/2024/post-1",
    "https://www.example.com/blog/2024/post-2",
    "https://www.example.com/",
]


def test_count_sections_level_1():
    counts = count_sections(SAMPLE_URLS, max_depth=1)
    assert counts["/products"] == 4
    assert counts["/about"] == 1
    assert counts["/blog"] == 2
    assert counts["/"] == 1  # homepage


def test_count_sections_level_4():
    urls = SAMPLE_URLS + ["https://www.example.com/products/shoes/running/trail"]
    counts = count_sections(urls, max_depth=4)
    assert counts["/products/shoes/running"] == 2  # running + trail
    assert counts["/products/shoes/running/trail"] == 1
    assert counts["/products/shoes/casual"] == 1
    assert counts["/products/shoes"] == 4  # shoes + running + casual + trail
    assert counts["/blog/2024"] == 2


def test_count_subdomains():
    urls = [
        "https://www.example.com/page1",
        "https://www.example.com/page2",
        "https://blog.example.com/post1",
        "https://shop.example.com/item1",
        "https://shop.example.com/item2",
        "https://shop.example.com/item3",
    ]
    counts = count_subdomains(urls)
    assert counts["shop.example.com"] == 3
    assert counts["www.example.com"] == 2
    assert counts["blog.example.com"] == 1


def test_generate_report_contains_total():
    report = generate_report(SAMPLE_URLS, "example.com")
    assert "8" in report  # total URLs
    assert "example.com" in report
    assert "/products" in report
    assert "up to 4 levels" in report


def test_generate_report_shows_subdomains_when_multiple():
    urls = [
        "https://www.example.com/page1",
        "https://blog.example.com/post1",
    ]
    report = generate_report(urls, "example.com")
    assert "Subdomains" in report
    assert "www.example.com" in report
    assert "blog.example.com" in report


def test_generate_report_hides_subdomains_when_single():
    report = generate_report(SAMPLE_URLS, "example.com")
    assert "Subdomains" not in report
