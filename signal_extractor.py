#!/usr/bin/env python3
"""Signal Extractor — first agent in the Gridline CS workflow pipeline.

Reads all available data files, computes derived metrics per account,
and produces a structured signal summary for downstream agents.

Usage:
    python3 signal_extractor.py
    python3 signal_extractor.py --as-of-date 2026-05-01
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
from collections import Counter
from datetime import date, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Theme classification
# ---------------------------------------------------------------------------

THEME_KEYWORDS = {
    "funding": ["raises", "series a", "series b", "series c", "series d", "series e",
                "funding round", "valuation", "valued at", "investment", "raises $"],
    "layoffs": ["lays off", "layoffs", "cuts staff", "workforce reduction", "downsizing"],
    "leadership_change": ["appoints", "new ceo", "new cto", "new cfo", "steps down",
                          "resigns", "joins as", "promoted to", "departure"],
    "acquisition": ["acquires", "acquired by", "merger", "to buy", "to acquire"],
    "product_launch": ["launches", "announces", "unveils", "introduces", "releases",
                       "rolls out", "new product"],
    "hiring": ["hiring", "expanding team", "hires", "growth in headcount"],
    "restructure": ["restructuring", "reorganization", "pivots", "shifts strategy"],
    "partnership": ["partners with", "partnership", "integration with"],
    "outage": ["outage", "downtime", "incident", "service disruption"],
}


def classify_theme(headline: str) -> str | None:
    lower = headline.lower()
    for theme, keywords in THEME_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return theme
    return None


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def parse_date(s: str) -> date:
    return date.fromisoformat(s)


def days_ago(d: date, as_of: date) -> int:
    return (as_of - d).days


# ---------------------------------------------------------------------------
# Utilization computation
# ---------------------------------------------------------------------------

def compute_utilization(usage_records: list, baseline: float, as_of: date) -> dict:
    """Compute utilization block for one product of one company."""
    # Build a dict of date -> value for the 90-day window
    window_start = as_of - timedelta(days=90)
    window_records = {
        parse_date(r["date"]): r["metric_value"]
        for r in usage_records
        if window_start <= parse_date(r["date"]) < as_of
    }

    def mean_range(start: date, end: date) -> float | None:
        vals = [v for d, v in window_records.items() if start <= d < end]
        return statistics.mean(vals) if vals else None

    last_30_start = as_of - timedelta(days=30)
    mid_30_start = as_of - timedelta(days=60)
    far_30_start = as_of - timedelta(days=90)
    last_15_start = as_of - timedelta(days=15)
    prior_15_start = as_of - timedelta(days=30)

    last_30_mean = mean_range(last_30_start, as_of)
    far_30_mean = mean_range(far_30_start, mid_30_start)
    last_15_mean = mean_range(last_15_start, as_of)
    prior_15_mean = mean_range(prior_15_start, last_15_start)
    mid_30_mean = mean_range(mid_30_start, last_30_start)

    current_rate = round(last_30_mean / baseline, 2) if last_30_mean and baseline else 0.0

    # trend_90d: last 30 vs days 60-90 ago
    def classify_trend(recent: float | None, older: float | None, all_vals: list) -> str:
        if recent is None or older is None:
            return "stable"
        pct_change = (recent - older) / older if older else 0
        if pct_change > 0.10:
            return "increasing"
        if pct_change < -0.10:
            return "declining"
        # Check volatility: std dev of weekly means > 25% of overall mean
        if all_vals:
            overall_mean = statistics.mean(all_vals)
            if overall_mean > 0:
                weekly_means = []
                for week in range(13):
                    week_start = as_of - timedelta(days=90 - week * 7)
                    week_end = week_start + timedelta(days=7)
                    wvals = [v for d, v in window_records.items() if week_start <= d < week_end]
                    if wvals:
                        weekly_means.append(statistics.mean(wvals))
                if len(weekly_means) >= 3:
                    try:
                        wstd = statistics.stdev(weekly_means)
                        if wstd / overall_mean > 0.25:
                            return "volatile"
                    except statistics.StatisticsError:
                        pass
        return "stable"

    all_90d_vals = list(window_records.values())
    trend_90d = classify_trend(last_30_mean, far_30_mean, all_90d_vals)
    trend_30d = classify_trend(last_15_mean, prior_15_mean, all_90d_vals)

    # delta_pct: (last_30 mean − first_30 of 90d window mean) / first_30 mean
    if last_30_mean is not None and far_30_mean is not None and far_30_mean != 0:
        delta_pct = round((last_30_mean - far_30_mean) / far_30_mean, 2)
    else:
        delta_pct = 0.0

    # crossed_baseline: any day in last 30 had value > 1.0x baseline
    crossed_baseline = any(
        v > baseline
        for d, v in window_records.items()
        if d >= last_30_start
    )

    return {
        "current_rate": current_rate,
        "trend_90d": trend_90d,
        "trend_30d": trend_30d,
        "delta_pct": delta_pct,
        "crossed_baseline": crossed_baseline,
    }


# ---------------------------------------------------------------------------
# Engagement computation
# ---------------------------------------------------------------------------

def compute_engagement(activities: list, company: dict, as_of: date) -> dict:
    activities_sorted = sorted(activities, key=lambda a: a["date"], reverse=True)

    if not activities_sorted:
        return {
            "csm_gap_days": (as_of - as_of).days,
            "last_touch_sentiment": None,
            "sentiment_trajectory": "insufficient_data",
            "champion_active": company.get("champion_active"),
            "executive_sponsor_active": company.get("executive_sponsor_active"),
            "recent_contact_mix": [],
            "initiated_by_recent": None,
            "touches_last_60d": 0,
            "touches_last_90d": 0,
        }

    last_activity_date = parse_date(activities_sorted[0]["date"])
    csm_gap_days = (as_of - last_activity_date).days

    last_touch_sentiment = activities_sorted[0].get("sentiment")

    # Sentiment trajectory: last 5 activities
    last5 = activities_sorted[:5]
    sentiments = [a.get("sentiment") for a in last5]
    last3_sentiments = sentiments[:3]

    if len(sentiments) < 3:
        trajectory = "insufficient_data"
    elif sum(1 for s in sentiments if s == "green") >= 4:
        trajectory = "stable_green"
    elif sum(1 for s in sentiments if s == "red") > 0 and any(s == "red" for s in last3_sentiments):
        trajectory = "drifting_red"
    elif sum(1 for s in sentiments if s == "yellow") >= 3 and not any(s == "red" for s in sentiments):
        trajectory = "stable_yellow"
    else:
        trajectory = "mixed"

    recent_contact_mix = [a.get("contact") for a in last5]

    initiated_counts = Counter(a.get("initiated_by") for a in last5)
    if initiated_counts:
        max_count = max(initiated_counts.values())
        top = [k for k, v in initiated_counts.items() if v == max_count]
        initiated_by_recent = top[0] if len(top) == 1 else "mixed"
    else:
        initiated_by_recent = None

    cutoff_60 = as_of - timedelta(days=60)
    cutoff_90 = as_of - timedelta(days=90)
    touches_last_60d = sum(1 for a in activities if parse_date(a["date"]) >= cutoff_60)
    touches_last_90d = sum(1 for a in activities if parse_date(a["date"]) >= cutoff_90)

    return {
        "csm_gap_days": csm_gap_days,
        "last_touch_sentiment": last_touch_sentiment,
        "sentiment_trajectory": trajectory,
        "champion_active": company.get("champion_active"),
        "executive_sponsor_active": company.get("executive_sponsor_active"),
        "recent_contact_mix": recent_contact_mix,
        "initiated_by_recent": initiated_by_recent,
        "touches_last_60d": touches_last_60d,
        "touches_last_90d": touches_last_90d,
    }


# ---------------------------------------------------------------------------
# Support computation
# ---------------------------------------------------------------------------

def compute_support(tickets: list, as_of: date) -> dict:
    cutoff_30 = as_of - timedelta(days=30)
    cutoff_60 = as_of - timedelta(days=60)
    cutoff_90 = as_of - timedelta(days=90)

    t30 = [t for t in tickets if parse_date(t["date"]) >= cutoff_30]
    t60 = [t for t in tickets if parse_date(t["date"]) >= cutoff_60]
    t60_to_30 = [t for t in tickets if cutoff_60 <= parse_date(t["date"]) < cutoff_30]
    t90 = [t for t in tickets if parse_date(t["date"]) >= cutoff_90]

    HIGH_SEVERITY = {"critical", "high"}

    def has_high(ticket_list):
        return any(t["severity"] in HIGH_SEVERITY for t in ticket_list)

    if not t60:
        severity_trend = "none"
    elif has_high(t30) and len(t30) > len(t60_to_30):
        severity_trend = "escalating"
    elif has_high(t60):
        if abs(len(t30) - len(t60_to_30)) <= 1:
            severity_trend = "stable_high"
        else:
            severity_trend = "escalating" if len(t30) > len(t60_to_30) else "stable_high"
    else:
        severity_trend = "stable_low"

    # Category concentration: 60%+ of last-60-day tickets share a category
    category_concentration = None
    if t60:
        cat_counts = Counter(t["category"] for t in t60)
        top_cat, top_count = cat_counts.most_common(1)[0]
        if top_count / len(t60) >= 0.60:
            category_concentration = top_cat

    open_count = sum(1 for t in tickets if t.get("status") == "open")

    return {
        "tickets_last_30d": len(t30),
        "tickets_last_60d": len(t60),
        "tickets_last_90d": len(t90),
        "severity_trend": severity_trend,
        "category_concentration": category_concentration,
        "open_count": open_count,
    }


# ---------------------------------------------------------------------------
# External signals computation
# ---------------------------------------------------------------------------

def compute_external(signals: list, as_of: date) -> dict:
    cutoff_90 = as_of - timedelta(days=90)
    signals_90d = [s for s in signals if parse_date(s["date"]) >= cutoff_90]

    classified = []
    for s in signals_90d:
        theme = classify_theme(s.get("headline", ""))
        if theme:
            classified.append({
                "date": s["date"],
                "headline": s["headline"],
                "source": s.get("source", ""),
                "theme": theme,
            })

    classified.sort(key=lambda x: x["date"], reverse=True)
    notable = classified[:4]
    themes = list(dict.fromkeys(s["theme"] for s in notable))

    return {
        "signal_count_90d": len(signals_90d),
        "notable_signals": notable,
        "signal_themes": themes,
    }


# ---------------------------------------------------------------------------
# Account context
# ---------------------------------------------------------------------------

def compute_account_context(company: dict, manifest_entry: dict, as_of: date) -> dict:
    products_contracted = company.get("products_contracted", [])

    renewal_date_str = company.get("renewal_date")
    if renewal_date_str:
        renewal_days_out = (parse_date(renewal_date_str) - as_of).days
    else:
        renewal_days_out = manifest_entry.get("renewal_days_out")

    contract_start_str = company.get("contract_start_date")
    contract_age_days = (as_of - parse_date(contract_start_str)).days if contract_start_str else None

    breadth_scores = company.get("feature_breadth_score", {})
    if breadth_scores:
        feature_breadth_avg = round(statistics.mean(breadth_scores.values()), 1)
    else:
        feature_breadth_avg = None

    return {
        "products_contracted": products_contracted,
        "renewal_days_out": renewal_days_out,
        "contract_age_days": contract_age_days,
        "feature_breadth_avg": feature_breadth_avg,
        "arr": company.get("arr"),
    }


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------

def compute_anomalies(utilization: dict, engagement: dict, support: dict,
                      external: dict, account_ctx: dict) -> list:
    anomalies = []

    csm_gap = engagement.get("csm_gap_days", 0)
    renewal_days = account_ctx.get("renewal_days_out")
    severity_trend = support.get("severity_trend", "none")
    signal_themes = external.get("signal_themes", [])
    touches_60d = engagement.get("touches_last_60d", 0)

    increasing_products = []
    declining_products = []

    for product, util in utilization.items():
        trend_30d = util.get("trend_30d")
        delta_pct = util.get("delta_pct", 0)

        # Rule 1: Growth + engagement gap
        # Fire on trend_30d OR trend_90d increasing so we catch accounts that
        # have grown significantly over the window but plateaued recently.
        trend_is_increasing = (trend_30d == "increasing" or
                               util.get("trend_90d") == "increasing")
        if trend_is_increasing and delta_pct > 0.20 and csm_gap >= 45:
            pct_str = f"{round(delta_pct * 100)}%"
            anomalies.append(
                f"Sustained growth of {pct_str} in {product} over last 30 days "
                f"while CSM gap exceeds {csm_gap} days"
            )

        # Rule 2: Decline + champion gone
        if trend_30d == "declining" and delta_pct < -0.20 and not engagement.get("champion_active"):
            anomalies.append(f"Declining {product} utilization with inactive champion")

        if trend_30d == "increasing":
            increasing_products.append((product, delta_pct))
        if trend_30d == "declining":
            declining_products.append((product, delta_pct))

    # Rule 3: Support escalation + low engagement
    if severity_trend == "escalating" and touches_60d < 2:
        anomalies.append("Support severity escalating with minimal recent CSM engagement")

    # Rule 4: External signal + flat usage
    growth_themes = {"funding", "product_launch", "hiring"}
    matching_themes = [t for t in signal_themes if t in growth_themes]
    if matching_themes and not increasing_products:
        theme = matching_themes[0]
        anomalies.append(
            f"External growth signal present ({theme}) without corresponding usage movement"
        )

    # Rule 5: Cross-product breadth
    multi_growing = [(p, d) for p, d in increasing_products if d > 0.15]
    if len(multi_growing) >= 2:
        product_list = ", ".join(p for p, _ in multi_growing)
        anomalies.append(f"Growth across multiple products: {product_list}")

    # Rule 6: Renewal proximity + risk signal
    has_declining = bool(declining_products)
    if renewal_days is not None and renewal_days < 90 and (severity_trend == "escalating" or has_declining):
        anomalies.append(
            f"Renewal within {renewal_days} days with active risk signal"
        )

    # Rule 7: Sentiment drift
    if engagement.get("sentiment_trajectory") == "drifting_red":
        anomalies.append("Customer sentiment trending negative across recent interactions")

    return anomalies


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def load_json(path: str):
    with open(path) as f:
        return json.load(f)


def build_product_key(product_name: str) -> str:
    """Convert product display name to contracted_usage key."""
    return product_name.lower().replace(" ", "_")


def get_baseline(company: dict, product_name: str) -> float | None:
    key = build_product_key(product_name)
    cu = company.get("contracted_usage", {}).get(key, {})
    vals = list(cu.values())
    return vals[0] if vals else None


def process_account(company: dict, usage_by_company: dict, activities_by_company: dict,
                    tickets_by_company: dict, signals_by_company: dict,
                    manifest_by_company: dict, as_of: date) -> dict:
    cid = company["company_id"]

    manifest_entry = manifest_by_company.get(cid, {})
    company_activities = activities_by_company.get(cid, [])
    company_tickets = tickets_by_company.get(cid, [])
    company_signals = signals_by_company.get(cid, [])
    company_usage = usage_by_company.get(cid, [])

    # Utilization block
    utilization = {}
    for product_name in company.get("products_contracted", []):
        baseline = get_baseline(company, product_name)
        if baseline is None or baseline == 0:
            continue
        product_records = [
            r for r in company_usage
            if r["product"] == product_name
        ]
        util = compute_utilization(product_records, baseline, as_of)
        utilization[product_name] = util

    engagement = compute_engagement(company_activities, company, as_of)
    support = compute_support(company_tickets, as_of)
    external = compute_external(company_signals, as_of)
    account_ctx = compute_account_context(company, manifest_entry, as_of)

    anomalies = compute_anomalies(utilization, engagement, support, external, account_ctx)

    # Rule 8: Manifest signal_contradiction note
    contradiction = manifest_entry.get("signal_contradiction")
    if contradiction:
        anomalies.append(f"Manifest note: {contradiction}")

    return {
        "company_id": cid,
        "name": company["name"],
        "as_of_date": as_of.isoformat(),
        "utilization": utilization,
        "engagement": engagement,
        "support": support,
        "external": external,
        "account_context": account_ctx,
        "anomalies": anomalies,
    }


def main():
    parser = argparse.ArgumentParser(description="Gridline Signal Extractor")
    parser.add_argument("--as-of-date", default="2026-05-01",
                        help="Reference date for signal computation (YYYY-MM-DD)")
    args = parser.parse_args()
    as_of = parse_date(args.as_of_date)

    data_dir = os.path.join(os.path.dirname(__file__), "data")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    companies = load_json(os.path.join(data_dir, "companies.json"))
    product_usage = load_json(os.path.join(data_dir, "product_usage.json"))
    csm_activity = load_json(os.path.join(data_dir, "csm_activity.json"))
    support_tickets = load_json(os.path.join(data_dir, "support_tickets.json"))
    data_manifest = load_json(os.path.join(data_dir, "data_manifest.json"))

    # External per-account signals are not part of this dataset.
    account_context: list = []

    # Index by company_id
    usage_by_company: dict[str, list] = {}
    for r in product_usage:
        usage_by_company.setdefault(r["company_id"], []).append(r)

    activities_by_company: dict[str, list] = {}
    for r in csm_activity:
        activities_by_company.setdefault(r["company_id"], []).append(r)

    tickets_by_company: dict[str, list] = {}
    for r in support_tickets:
        tickets_by_company.setdefault(r["company_id"], []).append(r)

    signals_by_company: dict[str, list] = {}
    for r in account_context:
        signals_by_company.setdefault(r["company_id"], []).append(r)

    manifest_by_company: dict[str, dict] = {
        m["company_id"]: m for m in data_manifest
    }

    results = []
    for company in companies:
        record = process_account(
            company, usage_by_company, activities_by_company,
            tickets_by_company, signals_by_company, manifest_by_company, as_of
        )
        results.append(record)

    results.sort(key=lambda r: r["company_id"])

    output_path = os.path.join(output_dir, f"signals_{as_of.isoformat()}.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    total = len(results)
    anomaly_counts = [len(r["anomalies"]) for r in results]
    avg_anomalies = round(sum(anomaly_counts) / total, 2) if total else 0
    high_signal = [r["company_id"] for r in results if len(r["anomalies"]) >= 3]

    print(f"Signal Extractor complete.")
    print(f"  Accounts processed: {total}")
    print(f"  Average anomalies per account: {avg_anomalies}")
    print(f"  High-signal accounts (3+ anomalies): {', '.join(high_signal) if high_signal else 'none'}")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    main()
