# Sitemap Downloader & Analyzer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI tool that downloads all sitemap files from a website (handling sitemap indexes), merges them into a single master sitemap, and generates a URL analysis report as markdown.

**Architecture:** Single Python package with four focused modules — downloader (HTTP + sitemap index detection), merger (XML combination), analyzer (URL path counting + markdown), and CLI (argparse entry point). Each module has clear inputs/outputs and is independently testable.

**Tech Stack:** Python 3.10+, `requests` (HTTP), `xml.etree.ElementTree` (XML parsing), `argparse` (CLI), `gzip` (compressed sitemap handling)

---

## File Structure

```
sitemap_downloader/
  __init__.py          # Package init, version
  downloader.py        # Fetch sitemap index, detect type, download sub-sitemaps, save to disk
  merger.py            # Combine multiple sitemap XML files into one master sitemap
  analyzer.py          # Parse URLs from sitemap, count by path sections (3 levels), generate markdown
  cli.py               # argparse CLI entry point
requirements.txt       # requests
tests/
  conftest.py          # Shared fixtures (sample XML strings, tmp dirs)
  test_downloader.py   # Tests for sitemap fetching and index detection
  test_merger.py       # Tests for XML merging
  test_analyzer.py     # Tests for URL counting and markdown generation
```

**Responsibilities:**
- `downloader.py` — HTTP fetching, sitemap index vs regular sitemap detection, gzip decompression, saving files to `OriginalFiles/` folder
- `merger.py` — Reads downloaded XML files, extracts all `<url>` elements, writes a single valid sitemap XML
- `analyzer.py` — Parses URLs from merged sitemap, groups by path segments up to 3 levels deep, counts, generates markdown report
- `cli.py` — Parses CLI args (URL, optional date override), orchestrates download → merge → analyze pipeline, manages folder structure

---

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `sitemap_downloader/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create requirements.txt**

```
requests>=2.31.0
```

- [ ] **Step 2: Create package init**

```python
"""Sitemap downloader, merger, and analyzer."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create test conftest with shared XML fixtures**

```python
import pytest
from pathlib import Path

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

SAMPLE_SITEMAP_INDEX = f"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="{SITEMAP_NS}">
  <sitemap>
    <loc>https://www.example.com/sitemap-products.xml</loc>
  </sitemap>
  <sitemap>
    <loc>https://www.example.com/sitemap-pages.xml.gz</loc>
  </sitemap>
</sitemapindex>"""

SAMPLE_SITEMAP_1 = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="{SITEMAP_NS}">
  <url><loc>https://www.example.com/products/shoes</loc></url>
  <url><loc>https://www.example.com/products/shoes/running</loc></url>
  <url><loc>https://www.example.com/products/hats</loc></url>
</urlset>"""

SAMPLE_SITEMAP_2 = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="{SITEMAP_NS}">
  <url><loc>https://www.example.com/about</loc></url>
  <url><loc>https://www.example.com/blog/2024/post-1</loc></url>
  <url><loc>https://www.example.com/blog/2024/post-2</loc></url>
</urlset>"""


@pytest.fixture
def sample_sitemap_index():
    return SAMPLE_SITEMAP_INDEX


@pytest.fixture
def sample_sitemap_1():
    return SAMPLE_SITEMAP_1


@pytest.fixture
def sample_sitemap_2():
    return SAMPLE_SITEMAP_2


@pytest.fixture
def sample_original_files(tmp_path, sample_sitemap_1, sample_sitemap_2):
    """Write two sample sitemap files to a tmp dir, return the dir path."""
    originals = tmp_path / "OriginalFiles"
    originals.mkdir()
    (originals / "sitemap-products.xml").write_text(sample_sitemap_1)
    (originals / "sitemap-pages.xml").write_text(sample_sitemap_2)
    return originals
```

- [ ] **Step 4: Install dependencies and verify**

Run: `cd /Users/ashaikh/Projects/sitemap && pip install requests pytest`
Expected: Successful install

- [ ] **Step 5: Commit**

```bash
git add requirements.txt sitemap_downloader/__init__.py tests/conftest.py
git commit -m "chore: project setup with requirements and test fixtures"
```

---

### Task 2: Downloader — Sitemap Index Detection

**Files:**
- Create: `sitemap_downloader/downloader.py`
- Create: `tests/test_downloader.py`

- [ ] **Step 1: Write failing test — detect sitemap index vs regular sitemap**

```python
# tests/test_downloader.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/test_downloader.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement detection functions**

```python
# sitemap_downloader/downloader.py
"""Download sitemaps from websites, handling sitemap indexes and gzip."""

import gzip
import io
from pathlib import Path
from urllib.parse import urlparse

import requests
import xml.etree.ElementTree as ET

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
USER_AGENT = "SitemapDownloader/0.1 (+https://github.com/sitemap-downloader)"


def is_sitemap_index(xml_content: str) -> bool:
    """Check if XML content is a sitemap index (vs a regular urlset sitemap)."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return False
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    return tag == "sitemapindex"


def parse_sitemap_index_urls(xml_content: str) -> list[str]:
    """Extract sitemap URLs from a sitemap index XML string."""
    root = ET.fromstring(xml_content)
    ns = {"sm": SITEMAP_NS}
    return [loc.text for loc in root.findall(".//sm:sitemap/sm:loc", ns) if loc.text]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/test_downloader.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add sitemap_downloader/downloader.py tests/test_downloader.py
git commit -m "feat: sitemap index detection and URL extraction"
```

---

### Task 3: Downloader — HTTP Fetching & Saving

**Files:**
- Modify: `sitemap_downloader/downloader.py`
- Modify: `tests/test_downloader.py`

- [ ] **Step 1: Write failing test — fetch and decompress gzip content**

```python
# Add to tests/test_downloader.py
import gzip


def test_decompress_gzip_content(sample_sitemap_1):
    from sitemap_downloader.downloader import decompress_if_gzip

    compressed = gzip.compress(sample_sitemap_1.encode("utf-8"))
    result = decompress_if_gzip(compressed)
    assert "<urlset" in result


def test_decompress_plain_xml(sample_sitemap_1):
    from sitemap_downloader.downloader import decompress_if_gzip

    result = decompress_if_gzip(sample_sitemap_1.encode("utf-8"))
    assert "<urlset" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/test_downloader.py::test_decompress_gzip_content -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement decompression**

```python
# Add to sitemap_downloader/downloader.py

def decompress_if_gzip(content: bytes) -> str:
    """Decompress gzip content if applicable, otherwise decode as UTF-8."""
    if content[:2] == b"\x1f\x8b":  # gzip magic number
        return gzip.decompress(content).decode("utf-8")
    return content.decode("utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/test_downloader.py -v`
Expected: 5 passed

- [ ] **Step 5: Write failing test — full download orchestration**

```python
# Add to tests/test_downloader.py
from unittest.mock import patch
from tests.conftest import SAMPLE_SITEMAP_INDEX, SAMPLE_SITEMAP_1, SAMPLE_SITEMAP_2


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
```

> **Note:** We patch `fetch_url` directly rather than `requests.get`. This is more resilient — if `fetch_url`'s internals change (e.g., switching to a Session with retries in Task 7), our mock still works.

- [ ] **Step 6: Run test to verify it fails**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/test_downloader.py::test_download_sitemaps_creates_files -v`
Expected: FAIL

- [ ] **Step 7: Implement download orchestration**

```python
# Add to sitemap_downloader/downloader.py

def fetch_url(url: str) -> bytes:
    """Fetch a URL and return raw bytes."""
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.content


def download_sitemaps(sitemap_url: str, output_dir: Path) -> list[Path]:
    """Download all sitemaps from a URL. Handles sitemap indexes recursively.

    Args:
        sitemap_url: URL to the sitemap or sitemap index
        output_dir: Directory to save downloaded files (OriginalFiles/)

    Returns:
        List of paths to downloaded sitemap files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    content = fetch_url(sitemap_url)
    xml_str = decompress_if_gzip(content)

    if is_sitemap_index(xml_str):
        sub_urls = parse_sitemap_index_urls(xml_str)
        # Save the index file itself
        index_path = output_dir / _filename_from_url(sitemap_url)
        index_path.write_text(xml_str, encoding="utf-8")

        downloaded = []
        for url in sub_urls:
            try:
                downloaded.extend(download_sitemaps(url, output_dir))
            except Exception as e:
                print(f"  Warning: failed to download {url}: {e}")
        return downloaded
    else:
        # Regular sitemap — save it
        filename = _filename_from_url(sitemap_url)
        filepath = output_dir / filename
        filepath.write_text(xml_str, encoding="utf-8")
        return [filepath]


def _filename_from_url(url: str) -> str:
    """Extract a clean filename from a sitemap URL."""
    parsed = urlparse(url)
    name = Path(parsed.path).name
    # Strip .gz extension since we decompress
    if name.endswith(".gz"):
        name = name[:-3]
    return name or "sitemap.xml"
```

- [ ] **Step 8: Run all tests**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/test_downloader.py -v`
Expected: 6 passed

- [ ] **Step 9: Commit**

```bash
git add sitemap_downloader/downloader.py tests/test_downloader.py
git commit -m "feat: download sitemaps with gzip support and index recursion"
```

---

### Task 4: Merger — Combine Sitemaps into One Master XML

**Files:**
- Create: `sitemap_downloader/merger.py`
- Create: `tests/test_merger.py`

- [ ] **Step 1: Write failing test — extract URLs from sitemap files**

```python
# tests/test_merger.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/test_merger.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement merger**

```python
# sitemap_downloader/merger.py
"""Merge multiple sitemap XML files into a single master sitemap."""

import xml.etree.ElementTree as ET
from pathlib import Path

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def extract_urls_from_file(filepath: Path) -> list[str]:
    """Extract all <loc> URLs from a sitemap XML file."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    ns = {"sm": SITEMAP_NS}
    return [loc.text for loc in root.findall(".//sm:url/sm:loc", ns) if loc.text]


def merge_sitemaps(sitemap_files: list[Path], output_path: Path) -> int:
    """Merge multiple sitemap files into one master sitemap.

    Args:
        sitemap_files: List of paths to individual sitemap XML files
        output_path: Where to write the merged sitemap

    Returns:
        Total number of URLs in the merged sitemap
    """
    all_urls: list[str] = []
    for f in sitemap_files:
        all_urls.extend(extract_urls_from_file(f))

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_urls: list[str] = []
    for url in all_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    # Build merged XML
    ET.register_namespace("", SITEMAP_NS)
    urlset = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for url in unique_urls:
        url_elem = ET.SubElement(urlset, f"{{{SITEMAP_NS}}}url")
        loc_elem = ET.SubElement(url_elem, f"{{{SITEMAP_NS}}}loc")
        loc_elem.text = url

    tree = ET.ElementTree(urlset)
    ET.indent(tree, space="  ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, xml_declaration=True, encoding="unicode")

    return len(unique_urls)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/test_merger.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add sitemap_downloader/merger.py tests/test_merger.py
git commit -m "feat: merge multiple sitemaps into single master XML"
```

---

### Task 5: Analyzer — URL Counting & Markdown Report

**Files:**
- Create: `sitemap_downloader/analyzer.py`
- Create: `tests/test_analyzer.py`

- [ ] **Step 1: Write failing test — count URLs by path section**

```python
# tests/test_analyzer.py
from sitemap_downloader.analyzer import count_sections, generate_report

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


def test_count_sections_level_3():
    counts = count_sections(SAMPLE_URLS, max_depth=3)
    assert counts["/products/shoes/running"] == 1
    assert counts["/products/shoes/casual"] == 1
    assert counts["/products/shoes"] == 3  # shoes + running + casual
    assert counts["/blog/2024"] == 2


def test_generate_report_contains_total():
    report = generate_report(SAMPLE_URLS, "example.com")
    assert "8" in report  # total URLs
    assert "example.com" in report
    assert "/products" in report
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/test_analyzer.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement analyzer**

```python
# sitemap_downloader/analyzer.py
"""Analyze sitemap URLs and generate markdown reports."""

from collections import defaultdict
from datetime import date
from urllib.parse import urlparse


def count_sections(urls: list[str], max_depth: int = 3) -> dict[str, int]:
    """Count URLs by path section up to max_depth levels.

    Each URL contributes to every level of its path hierarchy.
    E.g., /products/shoes/running counts toward:
      /products (level 1), /products/shoes (level 2), /products/shoes/running (level 3)

    Args:
        urls: List of full URLs
        max_depth: Maximum path depth to analyze (default 3)

    Returns:
        Dict mapping path prefixes to URL counts
    """
    counts: dict[str, int] = defaultdict(int)

    for url in urls:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")

        if not path:
            counts["/"] += 1
            continue

        segments = path.strip("/").split("/")
        for depth in range(1, min(len(segments), max_depth) + 1):
            prefix = "/" + "/".join(segments[:depth])
            counts[prefix] += 1

        # If URL is at a depth less than its segments, it's already counted
        # If URL path is exactly at depth N, the loop handles it

    return dict(counts)


def generate_report(urls: list[str], site_name: str) -> str:
    """Generate a markdown analysis report for the given URLs.

    Args:
        urls: List of all URLs from the sitemap
        site_name: Display name of the site

    Returns:
        Markdown string with the report
    """
    total = len(urls)
    counts = count_sections(urls, max_depth=3)
    today = date.today().isoformat()

    # Sort sections: level 1 first, then by count descending
    level_1 = {k: v for k, v in counts.items() if k.count("/") == 1 and k != "/"}
    level_1_sorted = sorted(level_1.items(), key=lambda x: x[1], reverse=True)

    lines = [
        f"# Sitemap Analysis: {site_name}",
        f"",
        f"**Date:** {today}",
        f"**Total URLs:** {total:,}",
        f"",
        f"## Top-Level Sections",
        f"",
        f"| Section | URLs | % of Total |",
        f"|---------|------|-----------|",
    ]

    for section, count in level_1_sorted:
        pct = (count / total) * 100
        lines.append(f"| `{section}` | {count:,} | {pct:.1f}% |")

    # Homepage / root
    root_count = counts.get("/", 0)
    if root_count:
        pct = (root_count / total) * 100
        lines.append(f"| `/` (root) | {root_count:,} | {pct:.1f}% |")

    # Detailed breakdown (levels 2-3)
    lines.extend(["", "## Detailed Breakdown (up to 3 levels)", ""])

    for section, _ in level_1_sorted:
        # Find all sub-sections under this top-level
        sub_sections = {
            k: v for k, v in counts.items()
            if k.startswith(section + "/") and k != section
        }
        if not sub_sections:
            continue

        lines.append(f"### `{section}`")
        lines.append("")
        lines.append(f"| Sub-section | URLs |")
        lines.append(f"|-------------|------|")

        sub_sorted = sorted(sub_sections.items(), key=lambda x: x[1], reverse=True)
        for sub, count in sub_sorted[:20]:  # Cap at 20 to keep report readable
            lines.append(f"| `{sub}` | {count:,} |")

        if len(sub_sorted) > 20:
            lines.append(f"| ... and {len(sub_sorted) - 20} more | |")
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/test_analyzer.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add sitemap_downloader/analyzer.py tests/test_analyzer.py
git commit -m "feat: URL section analysis and markdown report generation"
```

---

### Task 6: CLI — Entry Point & Pipeline Orchestration

**Files:**
- Create: `sitemap_downloader/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing test — CLI argument parsing**

```python
# tests/test_cli.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/test_cli.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement CLI module**

```python
# sitemap_downloader/cli.py
"""CLI entry point for sitemap downloader."""

import argparse
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from sitemap_downloader.downloader import download_sitemaps
from sitemap_downloader.merger import merge_sitemaps, extract_urls_from_file
from sitemap_downloader.analyzer import generate_report
# Note: we read URLs from the MERGED file for the report, ensuring
# the total count matches the merged sitemap (deduplicated).


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/test_cli.py -v`
Expected: 3 passed

- [ ] **Step 5: Run all tests**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/ -v`
Expected: All 11 tests passed

- [ ] **Step 6: Commit**

```bash
git add sitemap_downloader/cli.py tests/test_cli.py
git commit -m "feat: CLI entry point with download/merge/analyze pipeline"
```

---

### Task 7: Integration Test with Real Sites

**Files:**
- Modify: `sitemap_downloader/downloader.py` (add retry/timeout handling)
- Create: `tests/test_integration.py`

- [ ] **Step 1: Add retry logic to downloader for robustness**

Add to the top of `downloader.py`:

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def _session() -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers["User-Agent"] = USER_AGENT
    return session
```

Update `fetch_url` to use the session:

```python
def fetch_url(url: str) -> bytes:
    """Fetch a URL and return raw bytes."""
    session = _session()
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.content
```

- [ ] **Step 2: Write integration test (marked slow)**

```python
# tests/test_integration.py
"""Integration tests — require network access. Run with: pytest -m integration"""
import pytest
from pathlib import Path
from sitemap_downloader.cli import run

pytestmark = pytest.mark.integration


@pytest.mark.integration
def test_full_pipeline_finditparts(tmp_path):
    run([
        "https://www.finditparts.com/sitemap.xml",
        "--output", str(tmp_path),
        "--date", "2026-03-18",
    ])
    base = tmp_path / "finditparts.com" / "2026-03-18"
    assert (base / "OriginalFiles").exists()
    originals = list((base / "OriginalFiles").glob("*.xml"))
    assert len(originals) >= 1
    assert (base / "MergedSitemap" / "finditparts.com-2026-03-18.xml").exists()
    assert (base / "MergedSitemap" / "finditparts.com-2026-03-18.md").exists()

    # Check report has content
    report = (base / "MergedSitemap" / "finditparts.com-2026-03-18.md").read_text()
    assert "Total URLs" in report


@pytest.mark.integration
def test_full_pipeline_aloyoga(tmp_path):
    run([
        "https://www.aloyoga.com/sitemap.xml",
        "--output", str(tmp_path),
        "--date", "2026-03-18",
    ])
    base = tmp_path / "aloyoga.com" / "2026-03-18"
    assert (base / "MergedSitemap" / "aloyoga.com-2026-03-18.xml").exists()
    assert (base / "MergedSitemap" / "aloyoga.com-2026-03-18.md").exists()
```

- [ ] **Step 3: Configure pytest markers**

Add to `pyproject.toml` (or create it):

```toml
[tool.pytest.ini_options]
markers = [
    "integration: tests that require network access (deselect with '-m not integration')",
]
```

- [ ] **Step 4: Run unit tests (skip integration)**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/ -v -m "not integration"`
Expected: All unit tests pass

- [ ] **Step 5: Run integration tests**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/test_integration.py -v -m integration --timeout=120`
Expected: 2 passed (may take 30-60s per site)

- [ ] **Step 6: Fix any issues found during integration testing**

Common issues to watch for:
- Some sites return sitemap index pointing to nested indexes (need recursive handling — already built in)
- Some sitemaps use non-standard namespaces or no namespace at all
- Very large sitemaps may need streaming/iterparse

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: add retry logic and integration tests for real sites"
```

---

### Task 8: Polish — Entry Point Script & Usage

**Files:**
- Create: `run.py` (simple entry point)
- Modify: `sitemap_downloader/cli.py` (add progress output)

- [ ] **Step 1: Create simple run script at project root**

```python
#!/usr/bin/env python3
"""Run the sitemap downloader from the command line.

Usage:
    python run.py https://www.example.com/sitemap.xml
    python run.py https://www.example.com/sitemap.xml --output ./output --date 2026-01-01
"""
from sitemap_downloader.cli import run

if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Add progress output to downloader**

Modify `download_sitemaps` in `downloader.py` to print progress:

```python
# In the sitemap index branch of download_sitemaps:
        print(f"  Found sitemap index with {len(sub_urls)} sub-sitemaps")
        downloaded = []
        for i, url in enumerate(sub_urls, 1):
            print(f"  Downloading [{i}/{len(sub_urls)}]: {url.split('/')[-1]}")
            downloaded.extend(download_sitemaps(url, output_dir))
        return downloaded
```

- [ ] **Step 3: Run full test suite**

Run: `cd /Users/ashaikh/Projects/sitemap && python -m pytest tests/ -v -m "not integration"`
Expected: All tests pass

- [ ] **Step 4: Test CLI manually**

Run: `cd /Users/ashaikh/Projects/sitemap && python run.py https://www.finditparts.com/sitemap.xml --output ./output --date 2026-03-18`
Expected: Files created in `./output/finditparts.com/2026-03-18/`

- [ ] **Step 5: Commit**

```bash
git add run.py sitemap_downloader/
git commit -m "feat: add run script and download progress output"
```

---

## Summary of Output Structure

```
output/
  finditparts.com/
    2026-03-18/
      OriginalFiles/
        sitemap.xml              # index file
        sitemap-products.xml     # individual sitemaps
        sitemap-pages.xml
        ...
      MergedSitemap/
        finditparts.com-2026-03-18.xml   # merged master sitemap
        finditparts.com-2026-03-18.md    # analysis report
```
