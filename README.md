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
- **Stealth fallback** — auto-switches to Playwright (with cookie warmup) when blocked by PerimeterX/Akamai/Cloudflare/DataDome
- **robots.txt discovery** — `--from-robots <url>` queues every `Sitemap:` entry from a site's robots.txt

## Installation

```bash
git clone https://github.com/yourusername/sitemap.git
cd sitemap
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Optional: stealth backend (for bot-walled sites)

```bash
pip install -e .[stealth]
playwright install chromium
```

Auto-engages when a normal request gets blocked. No code change needed.

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

### Bot-walled site (auto-fallback)

```bash
python run.py --from-robots https://www.walmart.com --output ./output
```

Tries plain `requests` first; switches to stealth Playwright (cookie warmup, persistent context, throttled) the moment a block is detected. Cookies persist across all sub-sitemaps in the run.

#### Tier-3 walls (PerimeterX / Akamai with CAPTCHA)

Sites like Walmart guard XML endpoints with a "press and hold" CAPTCHA that headless browsers cannot solve. Run headful so a human can solve once:

```bash
python run.py --from-robots https://www.walmart.com --stealth --stealth-headful
```

When the browser opens on the block page, hold the button until cleared. The cookie persists in the context and every sub-sitemap downloads automatically afterward.

### Options

```
positional arguments:
  url                   URL to the sitemap or sitemap index

options:
  --sites, -s           Path to sites.txt file (one URL per line)
  --from-robots URL     Discover sitemaps from <site>/robots.txt
  --output, -o          Base output directory (default: current directory)
  --date, -d            Date for folder naming (default: today, YYYY-MM-DD)
  --stealth             Force Playwright stealth from start (skip requests)
  --stealth-headful     Run stealth Playwright with visible browser
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
