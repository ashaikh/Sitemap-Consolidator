# Sitemap Downloader & Analyzer

Download, merge, and analyze website sitemaps. Handles sitemap indexes with hundreds of sub-sitemaps, multi-locale sites (Shopify, etc.), and gzip-compressed files.

## Features

- **Recursive sitemap index handling** — automatically detects and downloads all sub-sitemaps
- **Multi-locale support** — correctly handles sites with 100+ locale-specific sitemaps without filename collisions
- **Gzip decompression** — transparent handling of `.xml.gz` sitemaps
- **Merge & deduplicate** — combines all sitemaps into a single master XML file
- **URL analysis** — generates a markdown report with section counts up to 4 levels deep
- **Batch processing** — process multiple sites from a `sites.txt` file
- **Compression** — archives original sitemaps as `.tar.gz` to save disk space
- **Retry logic** — automatic retries with backoff for failed requests

## Installation

```bash
git clone https://github.com/yourusername/sitemap.git
cd sitemap
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Single site

```bash
python run.py https://www.example.com/sitemap.xml --output ./output
```

### Batch mode

Add URLs to `sites.txt` (one per line), then:

```bash
python run.py --sites sites.txt --output ./output
```

### Options

```
positional arguments:
  url                   URL to the sitemap or sitemap index

options:
  --sites, -s           Path to sites.txt file (one URL per line)
  --output, -o          Base output directory (default: current directory)
  --date, -d            Date for folder naming (default: today, YYYY-MM-DD)
```

## Output Structure

```
output/
  example.com/
    2026-01-01/
      OriginalFiles.tar.gz              # compressed original sitemaps
      MergedSitemap/
        example.com-2026-01-01.xml      # merged master sitemap
        example.com-2026-01-01.md       # URL analysis report
```

## Analysis Report

The markdown report includes:

- **Total URL count** for the entire site
- **Top-level section breakdown** with counts and percentages
- **Detailed breakdown** up to 4 levels deep, sorted by URL count

## License

MIT
