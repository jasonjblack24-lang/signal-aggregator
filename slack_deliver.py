#!/usr/bin/env python3
"""Slack Delivery — Phase 4 of the Gridline CS workflow pipeline.

Reads the most recent (or date-specified) Slack message from output/ and
posts it to a Slack webhook.

Usage:
    python3 slack_deliver.py
    python3 slack_deliver.py --date 2026-05-01
    python3 slack_deliver.py --dry-run

Environment:
    SLACK_WEBHOOK  Incoming webhook URL (required unless --dry-run)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
SLACK_MAX_CHARS = 3000  # Slack mrkdwn text block limit


def find_message_file(date: str | None) -> Path:
    """Return the message file for the given date, or the most recent one."""
    if date:
        path = OUTPUT_DIR / f"slack_message_{date}.md"
        if not path.exists():
            sys.exit(f"Error: {path} does not exist.")
        return path

    files = sorted(glob.glob(str(OUTPUT_DIR / "slack_message_*.md")))
    if not files:
        sys.exit("Error: no slack_message_*.md files found in output/")
    return Path(files[-1])


def read_message(path: Path) -> str:
    return path.read_text().strip()


def chunk_message(text: str) -> list[str]:
    """Split text into chunks that fit within Slack's block size limit.

    Splits on newlines, accumulating lines until adding the next would
    exceed the limit. Each chunk is a self-contained string.
    """
    if len(text) <= SLACK_MAX_CHARS:
        return [text]

    chunks: list[str] = []
    current_lines: list[str] = []
    current_len = 0

    for line in text.splitlines(keepends=True):
        if current_len + len(line) > SLACK_MAX_CHARS and current_lines:
            chunks.append("".join(current_lines))
            current_lines = []
            current_len = 0
        current_lines.append(line)
        current_len += len(line)

    if current_lines:
        chunks.append("".join(current_lines))

    return chunks


def build_payload(text: str) -> dict:
    """Build a Slack API payload with mrkdwn section blocks."""
    chunks = chunk_message(text)
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": chunk}}
        for chunk in chunks
    ]
    # Fallback text for notifications (plain-text summary of first line)
    fallback = text.splitlines()[0] if text else "Daily CS Briefing"
    return {"text": fallback, "blocks": blocks}


def post_to_slack(webhook_url: str, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            body = resp.read().decode()
        if status != 200 or body != "ok":
            sys.exit(f"Slack returned unexpected response: HTTP {status} — {body!r}")
        print(f"Posted to Slack (HTTP {status}).")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        sys.exit(f"Slack webhook error: HTTP {exc.code} — {body!r}")
    except urllib.error.URLError as exc:
        sys.exit(f"Network error posting to Slack: {exc.reason}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Post CS briefing to Slack")
    parser.add_argument("--date", help="Date of the message file (YYYY-MM-DD)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the payload without sending",
    )
    args = parser.parse_args()

    message_file = find_message_file(args.date)
    text = read_message(message_file)
    payload = build_payload(text)

    print(f"Message file: {message_file}")
    print(f"Characters: {len(text)}  |  Chunks: {len(payload['blocks'])}")

    if args.dry_run:
        print("\n--- DRY RUN: payload ---")
        print(json.dumps(payload, indent=2))
        return

    webhook_url = os.environ.get("SLACK_WEBHOOK", "").strip()
    if not webhook_url:
        sys.exit(
            "Error: SLACK_WEBHOOK environment variable is not set.\n"
            "Run with --dry-run to preview without sending."
        )

    post_to_slack(webhook_url, payload)


if __name__ == "__main__":
    main()
