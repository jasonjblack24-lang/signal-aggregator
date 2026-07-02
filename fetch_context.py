#!/usr/bin/env python3
"""
Gridline RSS context fetcher.

Reads data/rss_sources.json and pulls external context signals for each
company from Google News RSS, Hacker News (via Algolia), and any configured
company blog feeds.

Writes results to data/account_context.json.

Usage:
    python3 fetch_context.py
    python3 fetch_context.py --lookback-days 90
    python3 fetch_context.py --max-per-source 10

No third-party dependencies. Standard library only.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

USER_AGENT = "GridlineRSSFetcher/1.0 (+https://example.local)"
REQUEST_TIMEOUT = 15
SLEEP_BETWEEN_REQUESTS = 0.6


# -----------------------------------------------------------------------------
# HTTP helper
# -----------------------------------------------------------------------------
def http_get(url, accept=None):
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return resp.read()


# -----------------------------------------------------------------------------
# Text cleaning
# -----------------------------------------------------------------------------
HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def strip_html(text):
    if not text:
        return ""
    cleaned = HTML_TAG_RE.sub(" ", text)
    cleaned = cleaned.replace("&nbsp;", " ").replace("&amp;", "&")
    cleaned = cleaned.replace("&quot;", '"').replace("&#39;", "'")
    cleaned = cleaned.replace("&lt;", "<").replace("&gt;", ">")
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def first_sentences(text, n=3):
    if not text:
        return ""
    text = strip_html(text)
    # Naive sentence split — good enough for snippets
    parts = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(parts[:n]).strip()


# -----------------------------------------------------------------------------
# Date parsing
# -----------------------------------------------------------------------------
def parse_rss_date(date_str):
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).date()
    except (TypeError, ValueError):
        pass
    # ISO 8601 fallback
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).date()
    except (TypeError, ValueError):
        return None


def parse_unix_timestamp(ts):
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).date()
    except (TypeError, ValueError):
        return None


# -----------------------------------------------------------------------------
# Source extraction
# -----------------------------------------------------------------------------
def extract_source_from_url(url):
    try:
        netloc = urllib.parse.urlparse(url).netloc
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc or "unknown"
    except Exception:
        return "unknown"


# -----------------------------------------------------------------------------
# RSS parsing (Google News + company blogs)
# -----------------------------------------------------------------------------
def parse_rss_feed(xml_bytes, default_source_label, cutoff_date, max_items):
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise RuntimeError(f"XML parse error: {e}")

    # Handle both RSS 2.0 (<channel><item>) and Atom (<feed><entry>)
    channel = root.find("channel")
    if channel is not None:
        entries = channel.findall("item")
        is_atom = False
    else:
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        is_atom = True

    for entry in entries:
        if is_atom:
            title = entry.findtext("{http://www.w3.org/2005/Atom}title", "").strip()
            link_elem = entry.find("{http://www.w3.org/2005/Atom}link")
            link = link_elem.get("href") if link_elem is not None else ""
            published = (
                entry.findtext("{http://www.w3.org/2005/Atom}published")
                or entry.findtext("{http://www.w3.org/2005/Atom}updated")
            )
            summary = (
                entry.findtext("{http://www.w3.org/2005/Atom}summary")
                or entry.findtext("{http://www.w3.org/2005/Atom}content")
                or ""
            )
        else:
            title = entry.findtext("title", "").strip()
            link = entry.findtext("link", "").strip()
            published = entry.findtext("pubDate")
            summary = entry.findtext("description") or ""

        item_date = parse_rss_date(published)
        if not item_date:
            continue
        if item_date < cutoff_date:
            continue

        if link:
            source_label = extract_source_from_url(link)
        else:
            source_label = default_source_label

        items.append({
            "date": item_date.isoformat(),
            "headline": strip_html(title),
            "url": link,
            "source": source_label,
            "raw_summary": first_sentences(summary, 3),
        })

        if len(items) >= max_items:
            break

    return items


# -----------------------------------------------------------------------------
# Source fetchers
# -----------------------------------------------------------------------------
def fetch_google_news(source, cutoff_date, max_items):
    url = source["url"]
    xml_bytes = http_get(url, accept="application/rss+xml, application/xml")
    return parse_rss_feed(xml_bytes, "Google News", cutoff_date, max_items)


def fetch_company_blog(source, cutoff_date, max_items):
    url = source["url"]
    xml_bytes = http_get(url, accept="application/rss+xml, application/atom+xml, application/xml")
    return parse_rss_feed(xml_bytes, source.get("label", "Company Blog"), cutoff_date, max_items)


def fetch_hacker_news(source, cutoff_date, max_items):
    query = source.get("query") or ""
    cutoff_ts = int(datetime.combine(cutoff_date, datetime.min.time(), tzinfo=timezone.utc).timestamp())
    params = {
        "query": query,
        "tags": "story",
        "numericFilters": f"created_at_i>{cutoff_ts}",
        "hitsPerPage": str(max_items),
    }
    url = "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(params)
    raw = http_get(url, accept="application/json")
    payload = json.loads(raw.decode("utf-8"))
    items = []
    for hit in payload.get("hits", []):
        item_date = parse_unix_timestamp(hit.get("created_at_i"))
        if not item_date:
            continue
        if item_date < cutoff_date:
            continue
        title = hit.get("title") or hit.get("story_title") or ""
        link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
        items.append({
            "date": item_date.isoformat(),
            "headline": title.strip(),
            "url": link,
            "source": "Hacker News",
            "raw_summary": "",
        })
        if len(items) >= max_items:
            break
    return items


SOURCE_HANDLERS = {
    "google_news": fetch_google_news,
    "hacker_news": fetch_hacker_news,
    "company_blog": fetch_company_blog,
    "research_blog": fetch_company_blog,
}


# -----------------------------------------------------------------------------
# Main fetch loop
# -----------------------------------------------------------------------------
def fetch_for_company(entry, cutoff_date, max_per_source, errors):
    company_id = entry["company_id"]
    company_name = entry["name"]
    records = []

    for source in entry.get("sources", []):
        stype = source.get("type")
        handler = SOURCE_HANDLERS.get(stype)
        label = source.get("label", stype)
        if handler is None:
            errors.append(f"{company_name} [{label}]: unsupported source type '{stype}'")
            continue
        try:
            items = handler(source, cutoff_date, max_per_source)
            for item in items:
                item["company_id"] = company_id
                # Order keys consistently
                records.append({
                    "company_id": item["company_id"],
                    "date": item["date"],
                    "headline": item["headline"],
                    "url": item["url"],
                    "source": item["source"],
                    "raw_summary": item["raw_summary"],
                })
        except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, ValueError) as e:
            errors.append(f"{company_name} [{label}]: {e}")
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    # Deduplicate by (headline, source) preserving most recent
    seen = {}
    for r in sorted(records, key=lambda r: r["date"], reverse=True):
        key = (r["headline"].lower(), r["source"])
        if key not in seen:
            seen[key] = r
    deduped = sorted(seen.values(), key=lambda r: r["date"], reverse=True)
    return deduped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources-file", default="data/rss_sources.json")
    parser.add_argument("--output-file", default="data/account_context.json")
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--max-per-source", type=int, default=8,
                        help="Maximum records to keep per source per company")
    parser.add_argument("--reference-date", default=None,
                        help="Anchor 'today' for cutoff calc (YYYY-MM-DD). Defaults to real today.")
    args = parser.parse_args()

    if not os.path.exists(args.sources_file):
        print(f"ERROR: sources file not found: {args.sources_file}", file=sys.stderr)
        sys.exit(1)

    with open(args.sources_file, "r", encoding="utf-8") as f:
        sources = json.load(f)

    if args.reference_date:
        today = datetime.strptime(args.reference_date, "%Y-%m-%d").date()
    else:
        today = date.today()
    cutoff_date = today - timedelta(days=args.lookback_days)

    print(f"Fetching external context")
    print(f"  Reference date : {today.isoformat()}")
    print(f"  Cutoff date    : {cutoff_date.isoformat()} ({args.lookback_days} day lookback)")
    print(f"  Companies      : {len(sources)}")
    print()

    all_records = []
    per_company_counts = {}
    errors = []

    for entry in sources:
        company_id = entry["company_id"]
        company_name = entry["name"]
        records = fetch_for_company(entry, cutoff_date, args.max_per_source, errors)
        per_company_counts[company_name] = len(records)
        all_records.extend(records)
        print(f"  {company_name:<22} {len(records):>3} records")

    os.makedirs(os.path.dirname(args.output_file) or ".", exist_ok=True)
    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2)

    # Summary
    dates = [r["date"] for r in all_records]
    earliest = min(dates) if dates else "n/a"
    latest = max(dates) if dates else "n/a"
    zero_companies = [name for name, c in per_company_counts.items() if c == 0]

    print()
    print(f"Total records       : {len(all_records)}")
    print(f"Date range          : {earliest} to {latest}")
    print(f"Companies w/ 0 hits : {len(zero_companies)}")
    if zero_companies:
        print("  " + ", ".join(zero_companies))
    print(f"Errors              : {len(errors)}")
    for err in errors:
        print(f"  - {err}")
    print()
    print(f"Wrote: {args.output_file}")


if __name__ == "__main__":
    main()
