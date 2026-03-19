"""CLI entry point for sitemap downloader."""

import argparse
import sys
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
    parser.add_argument("url", help="URL to the sitemap or sitemap index")
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
    return parser.parse_args(argv)


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


def run(argv: list[str] | None = None) -> None:
    """Main entry point — download, merge, analyze."""
    args = parse_args(argv)
    paths = build_paths(args.url, args.output, args.date)

    print(f"Downloading sitemaps from {args.url}...")
    print(f"Output: {paths['base']}")

    # Step 1: Download
    downloaded = download_sitemaps(args.url, paths["originals"])
    print(f"Downloaded {len(downloaded)} sitemap file(s)")

    # Step 2: Merge
    total = merge_sitemaps(downloaded, paths["merged_file"])
    print(f"Merged into {paths['merged_file']} ({total:,} URLs)")

    # Step 3: Analyze (read from merged file so counts match the deduplicated sitemap)
    all_urls = extract_urls_from_file(paths["merged_file"])
    report = generate_report(all_urls, paths["site_name"])
    paths["report"].write_text(report, encoding="utf-8")
    print(f"Analysis saved to {paths['report']}")

    print("Done!")


if __name__ == "__main__":
    run()
