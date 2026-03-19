from sitemap_downloader.cli import parse_args, build_paths


def test_parse_args_basic():
    args = parse_args(["https://www.example.com/sitemap.xml"])
    assert args.url == "https://www.example.com/sitemap.xml"
    assert args.output is None  # defaults to current dir


def test_parse_args_with_options():
    args = parse_args([
        "https://www.example.com/sitemap.xml",
        "--output", "/tmp/sitemaps",
        "--date", "2026-01-15",
    ])
    assert args.output == "/tmp/sitemaps"
    assert args.date == "2026-01-15"


def test_build_paths_structure():
    paths = build_paths("https://www.finditparts.com/sitemap.xml", "/tmp/out", "2026-01-01")
    assert str(paths["base"]).endswith("finditparts.com/2026-01-01")
    assert str(paths["originals"]).endswith("OriginalFiles")
    assert str(paths["merged_dir"]).endswith("MergedSitemap")
    assert str(paths["merged_file"]).endswith("finditparts.com-2026-01-01.xml")
    assert str(paths["report"]).endswith("finditparts.com-2026-01-01.md")
