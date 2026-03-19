#!/usr/bin/env python3
"""Run the sitemap downloader from the command line.

Usage:
    python run.py https://www.example.com/sitemap.xml
    python run.py https://www.example.com/sitemap.xml --output ./output --date 2026-01-01
"""
from sitemap_downloader.cli import run

if __name__ == "__main__":
    run()
