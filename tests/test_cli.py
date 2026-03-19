import tarfile

from sitemap_downloader.cli import parse_args, build_paths, load_sites, compress_originals, write_errors


def test_parse_args_basic():
    args = parse_args(["https://www.example.com/sitemap.xml"])
    assert args.url == "https://www.example.com/sitemap.xml"
    assert args.output is None  # defaults to current dir


def test_parse_args_with_sites_file():
    args = parse_args(["--sites", "sites.txt", "--output", "/tmp/out"])
    assert args.sites == "sites.txt"
    assert args.url is None


def test_parse_args_with_options():
    args = parse_args([
        "https://www.example.com/sitemap.xml",
        "--output", "/tmp/sitemaps",
        "--date", "2026-01-15",
    ])
    assert args.output == "/tmp/sitemaps"
    assert args.date == "2026-01-15"


def test_build_paths_structure():
    paths = build_paths("https://www.example.com/sitemap.xml", "/tmp/out", "2026-01-01")
    assert str(paths["base"]).endswith("example.com/2026-01-01")
    assert str(paths["originals"]).endswith("OriginalFiles")
    assert str(paths["merged_dir"]).endswith("MergedSitemap")
    assert str(paths["merged_file"]).endswith("example.com-2026-01-01.xml")
    assert str(paths["report"]).endswith("example.com-2026-01-01.md")
    assert str(paths["errors"]).endswith("errors.txt")


def test_load_sites(tmp_path):
    sites_file = tmp_path / "sites.txt"
    sites_file.write_text("# comment\nhttps://a.com/sitemap.xml\n\nhttps://b.com/sitemap.xml\n")
    urls = load_sites(str(sites_file))
    assert urls == ["https://a.com/sitemap.xml", "https://b.com/sitemap.xml"]


def test_compress_originals(tmp_path):
    originals = tmp_path / "OriginalFiles"
    originals.mkdir()
    (originals / "sitemap1.xml").write_text("<urlset/>")
    (originals / "sitemap2.xml").write_text("<urlset/>")

    archive = compress_originals(originals)
    assert archive.exists()
    assert archive.name == "OriginalFiles.tar.gz"
    assert not originals.exists()  # originals deleted

    # Verify archive contents
    with tarfile.open(archive) as tar:
        names = tar.getnames()
    assert "sitemap1.xml" in names
    assert "sitemap2.xml" in names


def test_write_errors(tmp_path):
    errors = [
        {
            "timestamp": "2026-03-18T12:00:00+00:00",
            "url": "https://example.com/sitemap-broken.xml",
            "error_type": "ConnectionError",
            "error": "Connection refused",
            "parent_index": "https://example.com/sitemap.xml",
        },
        {
            "timestamp": "2026-03-18T12:00:01+00:00",
            "url": "https://example.com/sitemap-bad.xml",
            "error_type": "ValueError",
            "error": "Not a sitemap — root element is <html>",
            "parent_index": "https://example.com/sitemap.xml",
        },
    ]
    error_path = tmp_path / "errors.txt"
    write_errors(errors, error_path)

    content = error_path.read_text()
    assert "2 error(s)" in content
    assert "sitemap-broken.xml" in content
    assert "Connection refused" in content
    assert "Not a sitemap" in content
    assert "Parent Index" in content
