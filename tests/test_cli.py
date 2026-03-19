import tarfile

from sitemap_downloader.cli import parse_args, build_paths, load_sites, compress_originals


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
    paths = build_paths("https://www.finditparts.com/sitemap.xml", "/tmp/out", "2026-01-01")
    assert str(paths["base"]).endswith("finditparts.com/2026-01-01")
    assert str(paths["originals"]).endswith("OriginalFiles")
    assert str(paths["merged_dir"]).endswith("MergedSitemap")
    assert str(paths["merged_file"]).endswith("finditparts.com-2026-01-01.xml")
    assert str(paths["report"]).endswith("finditparts.com-2026-01-01.md")


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
