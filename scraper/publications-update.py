#!/usr/bin/env python3
"""
Crawl a few websites, find PDF links, and add any NEW ones to pdf.json.

- Dedupes on a normalized URL against every translations[].url already in pdf.json
  (and against duplicates found during this run).
- New records follow the existing pdf.json schema.
- Run with --dry-run first to see what would be added without writing anything.

Usage (from repo root):
    python scraper/add_pdfs.py --dry-run
    python scraper/add_pdfs.py
    python scraper/add_pdfs.py --no-pdf-metadata      # skip downloading PDFs

Requires: requests, beautifulsoup4, pypdf (pypdf is optional with --no-pdf-metadata)
"""

import argparse
import io
import json
import re
import sys
import time
from collections import deque
from datetime import date
from pathlib import Path
from urllib import robotparser
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------- #
# CONFIG: edit this list. One entry per site to crawl.
#   start_urls : pages to begin on
#   depth      : how many link-hops to follow from each start URL (0 = only that page)
#   same_host  : only follow HTML links on the same host as the page they appear on
#   max_pages  : safety cap on pages fetched per site
#   series/type/language : defaults written into new records from this site
# --------------------------------------------------------------------------- #
SITES = [
        {
        "name": "NYC Vital Signs",
        "start_urls": ["https://www.nyc.gov/site/doh/data/data-publications/nyc-vital-signs.page"],
        "depth": 0,
        "same_host": True,
        "max_pages": 50,
        "series": "NYC Vital Signs",
        "type": "Vital Signs",
        "language": "en",
    },
    {
        "name": "Epi Data Briefs and Data Tables",
        "start_urls": ["https://www.nyc.gov/site/doh/data/data-publications/epi-data-briefs-and-data-tables.page"],
        "depth": 0,
        "same_host": True,
        "max_pages": 50,
        "series": "Epi Data Briefs and Data Tables",
        "type": "Data Brief",
        "language": "en",
    },
    {
        "name": "Epi Research Reports",
        "start_urls": ["https://www.nyc.gov/site/doh/data/data-publications/epi-research-reports.page"],
        "depth": 0,
        "same_host": True,
        "max_pages": 50,
        "series": "Epi Research Report",
        "type": "Research Report",
        "language": "en",
    },
        {
        "name": "Special Reports",
        "start_urls": ["https://www.nyc.gov/site/doh/data/data-publications/special-reports.page"],
        "depth": 0,
        "same_host": True,
        "max_pages": 50,
        "series": "Special Report",
        "type": "Special Report",
        "language": "en",
    },
    # {
    #     "name": "Another site",
    #     "start_urls": ["https://example.org/publications"],
    #     "depth": 1,
    #     "same_host": True,
    #     "max_pages": 50,
    #     "series": None,
    #     "type": "Report",
    #     "language": "en",
    # },
]

PDF_JSON = Path(__file__).resolve().parent.parent / "pdf.json"
USER_AGENT = "nychealth-publications-archive-scraper/1.0"  # long UAs with a "(+url)" suffix get 403'd by nyc.gov's CDN
REQUEST_DELAY = 1.0          # seconds between requests (be polite)
TIMEOUT = 30
MAX_PDF_BYTES = 25 * 1024 * 1024
GENERIC_LINK_TEXT = {"", "pdf", "download", "download pdf", "click here", "here", "read more", "view", "english"}

session = requests.Session()
session.headers["User-Agent"] = USER_AGENT
_last_request = 0.0
_robots = {}


# ------------------------------- helpers ----------------------------------- #

def normalize_url(url: str) -> str:
    """Canonical form used ONLY for dedupe comparisons (stored URLs stay as found)."""
    p = urlsplit(url.strip())
    path = quote(unquote(p.path), safe="/%:@!$&'()*+,;=-._~")
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, p.query, ""))  # drop #fragment


def is_pdf_url(url: str) -> bool:
    return urlsplit(url).path.lower().endswith(".pdf")


def allowed_by_robots(url: str) -> bool:
    p = urlsplit(url)
    origin = f"{p.scheme}://{p.netloc}"
    if origin not in _robots:
        # Fetch with OUR session/User-Agent. RobotFileParser.read() uses urllib's default
        # UA, which CDNs often 403 -- and it treats a 403 as "disallow everything".
        rp = None
        r = get(origin + "/robots.txt", retries=2)
        if r is None:
            print(f"  ! couldn't fetch {origin}/robots.txt; proceeding without it")
        elif r.status_code == 200:
            rp = robotparser.RobotFileParser()
            rp.parse(r.text.splitlines())
        elif r.status_code in (401, 403):
            print(f"  ! {origin}/robots.txt returned HTTP {r.status_code} (likely bot blocking, "
                  f"not a real rule). Proceeding; if pages 403 too, ask the web team to allowlist the scraper.")
        else:
            print(f"  - {origin}/robots.txt returned HTTP {r.status_code}; treating as no restrictions")
        _robots[origin] = rp
    rp = _robots[origin]
    return True if rp is None else rp.can_fetch(USER_AGENT, url)


def get(url: str, retries: int = 3, **kw):
    """Polite GET with delay + simple retry/backoff. Returns Response or None."""
    global _last_request
    for attempt in range(retries):
        wait = REQUEST_DELAY - (time.time() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.time()
        try:
            r = session.get(url, timeout=TIMEOUT, **kw)
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt * 2)
                continue
            return r
        except requests.RequestException as e:
            print(f"  ! {url}: {e}", file=sys.stderr)
            time.sleep(2 ** attempt)
    return None


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "untitled"


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def parse_pdf_date(s):
    """'D:20260114114513-05'00'' -> date(2026, 1, 14) or None."""
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})", s or "")
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None


# ------------------------------- crawling ---------------------------------- #

def crawl_site(site: dict):
    """Yield (pdf_url, link_text, found_on_page) for a site."""
    seen_pages = set()
    queue = deque((normalize_url(u), 0) for u in site["start_urls"])
    pages = 0
    while queue and pages < site.get("max_pages", 50):
        page_url, depth = queue.popleft()
        if page_url in seen_pages:
            continue
        seen_pages.add(page_url)
        if not allowed_by_robots(page_url):
            print(f"  - robots.txt disallows {page_url}")
            continue
        r = get(page_url)
        if r is None:
            print(f"  ! no response for {page_url}")
            continue
        ctype = r.headers.get("Content-Type", "")
        if r.status_code != 200 or "html" not in ctype:
            print(f"  ! skipped {page_url}: HTTP {r.status_code}, Content-Type '{ctype}'")
            continue
        pages += 1
        soup = BeautifulSoup(r.text, "html.parser")
        host = urlsplit(r.url).netloc.lower()
        anchors = soup.find_all("a", href=True)
        pdfs_here = set()
        for a in anchors:
            href = a["href"].strip()
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            full = urljoin(r.url, href)
            if urlsplit(full).scheme not in ("http", "https"):
                continue
            if is_pdf_url(full):
                pdfs_here.add(normalize_url(full))
                yield full, clean_text(a.get_text(" ")), r.url
            elif depth < site.get("depth", 0):
                if site.get("same_host", True) and urlsplit(full).netloc.lower() != host:
                    continue
                queue.append((normalize_url(full), depth + 1))
        # Fallback: PDF URLs sitting in the raw HTML outside <a href> (data-attrs, scripts, etc.)
        for m in re.finditer(r"""["'(]([^"'()\s<>]+?\.pdf)(?:\?[^"'()\s<>]*)?["')]""", r.text, re.I):
            full = urljoin(r.url, m.group(1).replace("\\/", "/"))
            if urlsplit(full).scheme in ("http", "https") and normalize_url(full) not in pdfs_here:
                pdfs_here.add(normalize_url(full))
                yield full, "", r.url
        print(f"  crawled (depth {depth}) {page_url}: HTTP 200, {len(anchors)} links, "
              f"{len(pdfs_here)} PDF links, {len(r.text):,} bytes")


# --------------------------- record construction --------------------------- #

def fetch_pdf_metadata(url: str):
    """Download a PDF and read its metadata. Returns (islive, metadata_dict_or_None)."""
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("pypdf is required (pip install pypdf) or run with --no-pdf-metadata")
    r = get(url, stream=True)
    if r is None or r.status_code != 200:
        return False, None
    try:
        chunks, size = [], 0
        for chunk in r.iter_content(65536):
            size += len(chunk)
            if size > MAX_PDF_BYTES:
                print(f"  ! {url} larger than {MAX_PDF_BYTES // 1024 // 1024} MB, skipping metadata")
                return True, None
            chunks.append(chunk)
        info = PdfReader(io.BytesIO(b"".join(chunks))).metadata or {}
    except Exception as e:
        print(f"  ! couldn't read PDF metadata for {url}: {e}", file=sys.stderr)
        return True, None
    return True, {
        "pdf_title": info.get("/Title"),
        "pdf_author": info.get("/Author"),
        "pdf_subject": info.get("/Subject"),
        "pdf_keywords": info.get("/Keywords"),
        "pdf_created": info.get("/CreationDate"),
    }


def build_record(url, link_text, site, existing_ids, with_metadata):
    islive, meta = fetch_pdf_metadata(url) if with_metadata else (True, None)
    meta = meta or {}

    filename = Path(unquote(urlsplit(url).path)).stem
    link_text = link_text if link_text.lower() not in GENERIC_LINK_TEXT else ""
    title = link_text or clean_text(meta.get("pdf_title") or "") or filename.replace("-", " ").replace("_", " ")

    # Best guess at publication date: first of the month the PDF was created, else today.
    created = parse_pdf_date(meta.get("pdf_created"))
    pub = (created.replace(day=1) if created else date.today()).isoformat()

    rec_id = f"{slugify(title)}-{pub}"
    base, n = rec_id, 2
    while rec_id in existing_ids:          # keep ids unique
        rec_id, n = f"{base}-{n}", n + 1
    existing_ids.add(rec_id)

    kw = [k.strip().lower() for k in re.split(r"[,;]", meta.get("pdf_keywords") or "") if k.strip()]
    lang = site.get("language", "en")

    # Key order mirrors the existing records so diffs stay clean.
    return {
        "id": rec_id,
        "title": title,
        "subtitle": None,
        "description": clean_text(meta.get("pdf_subject") or "") or None,
        "series": site.get("series"),
        "volume": None,
        "issue": None,
        "publication_date": pub,
        "year": int(pub[:4]),
        "type": site.get("type", "Report"),
        "topics": [],
        "keywords": kw,
        "languages": [lang],
        "audience": [],
        "department": None,
        "translations": [{"language": lang, "url": url, "islive": islive}],
        "featured_image": None,
        "pdf_metadata": {
            "pdf_title": meta.get("pdf_title"),
            "pdf_author": meta.get("pdf_author"),
            "pdf_subject": meta.get("pdf_subject"),
            "pdf_keywords": meta.get("pdf_keywords"),
            "pdf_created": meta.get("pdf_created"),
        },
        "created_at": date.today().isoformat(),
        "updated_at": date.today().isoformat(),
    }


# ---------------------------------- main ----------------------------------- #

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="show what would be added; don't write pdf.json")
    ap.add_argument("--no-pdf-metadata", action="store_true", help="don't download new PDFs to read their metadata")
    ap.add_argument("--json-path", type=Path, default=PDF_JSON)
    args = ap.parse_args()

    records = json.loads(args.json_path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        sys.exit(f"Expected {args.json_path} to contain a JSON list")

    known_urls = {normalize_url(t["url"]) for r in records for t in r.get("translations", []) if t.get("url")}
    existing_ids = {r.get("id") for r in records}
    print(f"Loaded {len(records)} records, {len(known_urls)} unique URLs")

    new_records = []
    for site in SITES:
        print(f"\n== {site['name']}")
        found = skipped = 0
        for url, text, source in crawl_site(site):
            key = normalize_url(url)
            if key in known_urls:
                skipped += 1
                continue
            known_urls.add(key)  # also dedupes within this run
            found += 1
            print(f"  + {url}")
            new_records.append(build_record(url, text, site, existing_ids, not args.no_pdf_metadata))
        print(f"  {found} new, {skipped} already in pdf.json")

    print(f"\nTotal new: {len(new_records)}")
    if not new_records:
        return
    if args.dry_run:
        print("--dry-run: nothing written")
        return

    records.extend(new_records)
    tmp = args.json_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(args.json_path)
    print(f"Wrote {args.json_path}")


if __name__ == "__main__":
    main()