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
from sitemap_downloader.fetchers import build_default_fetcher
from sitemap_downloader.robots import discover_sitemaps


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
    parser.add_argument(
        "--from-robots",
        help="Discover sitemaps from <site>/robots.txt instead of supplying sitemap URL directly",
        default=None,
    )
    parser.add_argument(
        "--stealth",
        action="store_true",
        help="Force Playwright stealth fetcher from start (skip requests). Slower, for bot-walled sites.",
    )
    parser.add_argument(
        "--stealth-headful",
        action="store_true",
        help="Run stealth Playwright with visible browser (helps bypass tougher challenges).",
    )
    args = parser.parse_args(argv)
    if not args.url and not args.sites and not args.from_robots:
        parser.error("Provide a URL, --sites file, or --from-robots URL")
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
        "errors": base / "errors.txt",
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


def write_errors(errors: list[dict], error_path: Path) -> None:
    """Write download errors to errors.txt."""
    error_path.parent.mkdir(parents=True, exist_ok=True)
    with open(error_path, "w") as f:
        f.write(f"Sitemap Download Errors — {len(errors)} error(s)\n")
        f.write("=" * 60 + "\n\n")
        for i, err in enumerate(errors, 1):
            f.write(f"[{i}] {err['timestamp']}\n")
            f.write(f"    URL: {err['url']}\n")
            f.write(f"    Error Type: {err['error_type']}\n")
            f.write(f"    Error: {err['error']}\n")
            if err.get("parent_index"):
                f.write(f"    Parent Index: {err['parent_index']}\n")
            f.write("\n")


def load_sites(sites_path: str) -> list[str]:
    """Load sitemap URLs from a sites.txt file (one per line, # comments ok)."""
    urls = []
    with open(sites_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def process_site(
    sitemap_url: str,
    output_base: str | None,
    date_str: str | None,
    fetcher=None,
) -> None:
    """Run the full pipeline for a single sitemap root URL."""
    process_site_aggregate([sitemap_url], output_base, date_str, fetcher)


def process_site_aggregate(
    sitemap_urls: list[str],
    output_base: str | None,
    date_str: str | None,
    fetcher=None,
) -> None:
    """Run the full pipeline for one site with one or more sitemap roots.

    All roots must share the same hostname. Outputs go into a single
    OriginalFiles dir → merged into one master XML → one report → one tarball.
    Errors from any root are logged together. Filename collisions across roots
    are handled by the existing _used_names tracker.
    """
    if not sitemap_urls:
        return

    paths = build_paths(sitemap_urls[0], output_base, date_str)
    print(f"\nProcessing {len(sitemap_urls)} sitemap root(s) for {paths['site_name']}")
    print(f"Output: {paths['base']}")

    errors: list[dict] = []
    used_names: dict[str, int] = {}
    all_downloaded: list = []

    for i, root in enumerate(sitemap_urls, 1):
        print(f"\n[{i}/{len(sitemap_urls)}] {root}")
        try:
            from sitemap_downloader.downloader import download_sitemaps as _dl
            files = _dl(root, paths["originals"], errors, _used_names=used_names, fetcher=fetcher)
            all_downloaded.extend(files)
        except Exception as e:
            from datetime import datetime, timezone
            errors.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "url": root,
                "error_type": type(e).__name__,
                "error": str(e),
                "parent_index": None,
            })
            print(f"  ERROR on root {root}: {e}")

    print(f"\nDownloaded {len(all_downloaded)} sitemap file(s) total")
    if errors:
        write_errors(errors, paths["errors"])
        print(f"WARNING: {len(errors)} error(s) logged to {paths['errors']}")

    if not all_downloaded:
        print("ERROR: No sitemaps downloaded successfully. Skipping merge/analysis.")
        return

    total = merge_sitemaps(all_downloaded, paths["merged_file"])
    print(f"Merged into {paths['merged_file']} ({total:,} URLs)")

    all_urls = extract_urls_from_file(paths["merged_file"])
    report = generate_report(all_urls, paths["site_name"])
    paths["report"].write_text(report, encoding="utf-8")
    print(f"Analysis saved to {paths['report']}")

    archive = compress_originals(paths["originals"])
    print(f"Compressed originals to {archive}")

    print("Done!")


def _group_by_host(urls: list[str]) -> dict[str, list[str]]:
    """Group URLs by hostname (www-stripped) preserving order."""
    groups: dict[str, list[str]] = {}
    for u in urls:
        host = urlparse(u).netloc.replace("www.", "")
        groups.setdefault(host, []).append(u)
    return groups


def run(argv: list[str] | None = None) -> None:
    """Main entry point — download, merge, analyze."""
    args = parse_args(argv)

    urls: list[str] = []
    if args.sites:
        urls.extend(load_sites(args.sites))
        print(f"Loaded {len(urls)} site(s) from {args.sites}")
    if args.url:
        urls.append(args.url)
    if args.from_robots:
        print(f"Discovering sitemaps from {args.from_robots}/robots.txt ...")
        discovered = discover_sitemaps(args.from_robots)
        print(f"Found {len(discovered)} sitemap(s) in robots.txt")
        urls.extend(discovered)

    fetcher = build_default_fetcher(
        stealth=args.stealth,
        headless=not args.stealth_headful,
    )
    try:
        # Group by host so multiple sitemap roots for the same domain
        # (e.g. all 34 from --from-robots) merge into one output.
        groups = _group_by_host(urls)
        for host, group_urls in groups.items():
            print(f"\n=== {host}: {len(group_urls)} sitemap root(s) ===")
            process_site_aggregate(group_urls, args.output, args.date, fetcher=fetcher)
    finally:
        fetcher.close()


if __name__ == "__main__":
    run()
