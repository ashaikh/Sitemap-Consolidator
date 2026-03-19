"""CLI entry point for sitemap downloader."""

import argparse
import shutil
import tarfile
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from sitemap_downloader.downloader import download_sitemaps
from sitemap_downloader.merger import merge_sitemaps, extract_urls_from_file
from sitemap_downloader.analyzer import generate_report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Download, merge, and analyze website sitemaps."
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=None,
        help="URL to the sitemap or sitemap index",
    )
    parser.add_argument(
        "--sites", "-s",
        help="Path to sites.txt file (one sitemap URL per line)",
        default=None,
    )
    parser.add_argument(
        "--output", "-o",
        help="Base output directory (default: current directory)",
        default=None,
    )
    parser.add_argument(
        "--date", "-d",
        help="Date for folder naming (default: today, format: YYYY-MM-DD)",
        default=None,
    )
    args = parser.parse_args(argv)
    if not args.url and not args.sites:
        parser.error("Provide a URL or --sites file")
    return args


def build_paths(sitemap_url: str, output_base: str | None, date_str: str | None) -> dict[str, Path]:
    """Build the output directory structure paths.

    Structure: <output>/<sitename>/<date>/OriginalFiles/
                                         /MergedSitemap/<sitename>-<date>.xml
    """
    parsed = urlparse(sitemap_url)
    site_name = parsed.netloc.replace("www.", "")
    date_str = date_str or date.today().isoformat()
    base = Path(output_base or ".") / site_name / date_str

    return {
        "site_name": site_name,
        "base": base,
        "originals": base / "OriginalFiles",
        "merged_dir": base / "MergedSitemap",
        "merged_file": base / "MergedSitemap" / f"{site_name}-{date_str}.xml",
        "report": base / "MergedSitemap" / f"{site_name}-{date_str}.md",
    }


def compress_originals(originals_dir: Path) -> Path:
    """Tar.gz the OriginalFiles directory and delete the XML files."""
    archive_path = originals_dir.parent / "OriginalFiles.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        for f in sorted(originals_dir.glob("*.xml")):
            tar.add(f, arcname=f.name)
    # Remove the original XML files
    shutil.rmtree(originals_dir)
    return archive_path


def load_sites(sites_path: str) -> list[str]:
    """Load sitemap URLs from a sites.txt file (one per line, # comments ok)."""
    urls = []
    with open(sites_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def process_site(sitemap_url: str, output_base: str | None, date_str: str | None) -> None:
    """Run the full pipeline for a single site."""
    paths = build_paths(sitemap_url, output_base, date_str)

    print(f"\nDownloading sitemaps from {sitemap_url}...")
    print(f"Output: {paths['base']}")

    # Step 1: Download
    downloaded = download_sitemaps(sitemap_url, paths["originals"])
    print(f"Downloaded {len(downloaded)} sitemap file(s)")

    # Step 2: Merge
    total = merge_sitemaps(downloaded, paths["merged_file"])
    print(f"Merged into {paths['merged_file']} ({total:,} URLs)")

    # Step 3: Analyze (read from merged file so counts match the deduplicated sitemap)
    all_urls = extract_urls_from_file(paths["merged_file"])
    report = generate_report(all_urls, paths["site_name"])
    paths["report"].write_text(report, encoding="utf-8")
    print(f"Analysis saved to {paths['report']}")

    # Step 4: Compress originals and clean up
    archive = compress_originals(paths["originals"])
    print(f"Compressed originals to {archive}")

    print("Done!")


def run(argv: list[str] | None = None) -> None:
    """Main entry point — download, merge, analyze."""
    args = parse_args(argv)

    urls = []
    if args.sites:
        urls = load_sites(args.sites)
        print(f"Loaded {len(urls)} site(s) from {args.sites}")
    if args.url:
        urls.append(args.url)

    for url in urls:
        process_site(url, args.output, args.date)


if __name__ == "__main__":
    run()
