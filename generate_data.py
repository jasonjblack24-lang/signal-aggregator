#!/usr/bin/env python3
"""Gridline simulated CS dataset generator.

Design principles:
- The data manifest is observational, not interpretive.
- Pattern labels live in a separate evaluation_key.json file.
- All manifest summaries are derived from generated data.
- Patterns are embedded into behavior, not directly described.

Usage:
    python generate_data.py
    python generate_data.py --date 2026-05-01

Outputs (written to ./data):
    companies.json
    product_usage.json
    csm_activity.json
    support_tickets.json
    data_manifest.json    (agent-safe observational data)
    evaluation_key.json   (pattern labels for eval harness only)
"""

import argparse
import json
import os
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import mean

SEED = 42
random.seed(SEED)

START_DATE = date(2025, 11, 1)
END_DATE = date(2026, 4, 30)

PRODUCTS = {
    "Infrastructure": {"key": "infrastructure", "metric": "hosts_monitored", "range": (50, 2500)},
    "Logs": {"key": "logs", "metric": "log_volume_gb", "range": (100, 20000)},
    "RUM": {"key": "rum", "metric": "rum_sessions", "range": (10000, 5000000)},
    "CI Visibility": {"key": "ci_visibility", "metric": "pipelines_analyzed", "range": (50, 50000)},
    "Security": {"key": "security", "metric": "security_signals", "range": (25, 10000)},
}

PATTERNS = {
    "A": "Expansion Ready", "B": "Silent Churn Risk", "C": "Stalled Adoption",
    "D": "Healthy and Stable", "E": "Volatile / Ambiguous",
}

COMPANIES = {
    "A": ["Deploova", "Trackwell", "Peoplora", "Craftbench", "Baseriver", "Authara", "Cavora", "Mediark"],
    "B": ["Equira", "Payglint", "Haulcrest", "Medolia", "Buildveo", "Plendo", "Realmly"],
    "C": ["Postglow", "Jobwright", "Queuely", "Notifera", "Endpointly", "Gatewly", "Identara", "Grantly"],
    "D": ["Vulnara", "Flagpost", "Panelith", "Provisor", "Alertcrest", "Statusly",
          "Errorly", "Traceon", "Siteglow", "Edgewave"],
    "E": ["Codenest", "Modelyard", "Metricforge", "Framecraft", "Lexira", "Novalm", "Clustira"],
}

INDUSTRIES = {
    "Deploova": "Developer Platform", "Trackwell": "Project Management", "Peoplora": "HR Tech",
    "Craftbench": "Developer Tools", "Baseriver": "Database Platform", "Authara": "Authentication",
    "Cavora": "Database Infrastructure", "Mediark": "Media Software", "Equira": "Fintech",
    "Payglint": "Payments", "Haulcrest": "Logistics Tech", "Medolia": "Healthcare AI",
    "Buildveo": "Construction Tech", "Plendo": "Payments", "Realmly": "Consumer Social",
    "Postglow": "Developer Email Infrastructure", "Jobwright": "Developer Platform",
    "Queuely": "Developer Infrastructure", "Notifera": "Notification Infrastructure",
    "Endpointly": "API Platform", "Gatewly": "API Gateway", "Identara": "Authentication",
    "Grantly": "Authorization Platform", "Vulnara": "Security", "Flagpost": "Feature Management",
    "Panelith": "Observability", "Provisor": "Infrastructure Software",
    "Alertcrest": "Incident Management", "Statusly": "Status Monitoring",
    "Errorly": "Error Monitoring", "Traceon": "Application Monitoring",
    "Siteglow": "Developer Platform", "Edgewave": "CDN", "Codenest": "AI Coding",
    "Modelyard": "AI/ML", "Metricforge": "ML Tooling", "Framecraft": "Generative AI",
    "Lexira": "LLM Platform", "Novalm": "AI Models", "Clustira": "AI Infrastructure",
}

EMPLOYEE_RANGES = {"tiny": (50, 120), "small": (120, 300), "mid": (300, 1200), "large": (1200, 4000)}

COMPANY_SIZE_HINTS = {
    "Deploova": "mid", "Trackwell": "small", "Peoplora": "large", "Craftbench": "mid",
    "Baseriver": "small", "Authara": "small", "Cavora": "tiny", "Mediark": "small",
    "Equira": "large", "Payglint": "tiny", "Haulcrest": "small", "Medolia": "mid",
    "Buildveo": "mid", "Plendo": "small", "Realmly": "small",
    "Postglow": "tiny", "Jobwright": "tiny", "Queuely": "tiny", "Notifera": "small",
    "Endpointly": "small", "Gatewly": "tiny", "Identara": "small", "Grantly": "tiny",
    "Vulnara": "large", "Flagpost": "large", "Panelith": "large",
    "Provisor": "large", "Alertcrest": "large", "Statusly": "small",
    "Errorly": "small", "Traceon": "large", "Siteglow": "mid", "Edgewave": "large",
    "Codenest": "mid", "Modelyard": "large", "Metricforge": "mid",
    "Framecraft": "mid", "Lexira": "mid", "Novalm": "small", "Clustira": "mid",
}

FIRST_NAMES = ["Avery", "Jordan", "Taylor", "Morgan", "Skyler", "Riley", "Casey", "Jamie",
               "Parker", "Quinn", "Drew", "Cameron", "Blake", "Rowan", "Alex", "Elliot", "Sam", "Logan"]
LAST_NAMES = ["Morris", "Kline", "Patel", "Nguyen", "Chen", "Rivera", "Foster", "Bennett",
              "Hayes", "Turner", "Campbell", "Brooks", "Sullivan", "Reed", "Ward", "Price", "Diaz"]

CHAMPION_TITLES = ["Director of Platform Engineering", "Senior DevOps Engineer", "Engineering Manager",
                   "Director of Infrastructure", "Head of Reliability", "Observability Lead",
                   "Staff Platform Engineer"]
EXEC_TITLES = ["VP of Engineering", "CTO", "Chief Architect", "SVP Infrastructure", "VP Platform"]

PRODUCT_DISTRIBUTION = [
    (["Infrastructure"], 10),
    (["Infrastructure", "Logs"], 8),
    (["Infrastructure", "Logs", "RUM"], 7),
    (["Infrastructure", "Logs", "CI Visibility"], 6),
    (["Infrastructure", "Logs", "RUM", "CI Visibility"], 5),
    (["Infrastructure", "Logs", "RUM", "CI Visibility", "Security"], 4),
]


def slugify(name):
    return name.lower().replace(" & ", "-").replace(".", "").replace(" ", "-")


def daterange(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def choose_products():
    combinations = []
    for products, count in PRODUCT_DISTRIBUTION:
        combinations.extend([products] * count)
    random.shuffle(combinations)
    return combinations


def build_contract_usage(products, employee_count):
    usage = {}
    scale = max(1.0, employee_count / 100)
    for product in products:
        meta = PRODUCTS[product]
        low, high = meta["range"]
        baseline = int(random.randint(low, high) * scale)
        usage[meta["key"]] = {meta["metric"]: baseline}
    return usage


def build_feature_scores(pattern, products):
    scores = {}
    for product in products:
        key = PRODUCTS[product]["key"]
        if pattern == "A":
            scores[key] = random.randint(6, 9)
        elif pattern == "B":
            scores[key] = random.randint(3, 5)
        elif pattern == "C":
            scores[key] = random.randint(2, 4)
        elif pattern == "D":
            scores[key] = random.randint(5, 7)
        else:
            scores[key] = random.randint(3, 8)
    return scores


def calculate_health_score(pattern, champion_active, executive_active, feature_scores):
    base = {"A": 88, "B": 38, "C": 52, "D": 76, "E": 64}[pattern]
    avg_breadth = mean(feature_scores.values())
    score = base + (avg_breadth - 5) * 3
    score += 4 if champion_active else -6
    if executive_active:
        score += 3
    score += random.randint(-4, 4)
    return max(1, min(100, int(score)))


def create_company_objects(today):
    companies = []
    all_companies = []
    for pattern, names in COMPANIES.items():
        for name in names:
            all_companies.append((pattern, name))

    product_assignments = choose_products()
    contradictions = set(random.sample(range(40), 14))
    manifest_map = {}

    for idx, ((pattern, name), products) in enumerate(zip(all_companies, product_assignments)):
        company_id = slugify(name)
        size_range = EMPLOYEE_RANGES[COMPANY_SIZE_HINTS[name]]
        employee_count = random.randint(*size_range)
        arr = random.randint(80000, 800000)

        if pattern == "C":
            contract_start = today - timedelta(days=random.randint(90, 260))
        elif name in ["Payglint", "Haulcrest"]:
            contract_start = today - timedelta(days=random.randint(500, 650))
        else:
            contract_start = today - timedelta(days=random.randint(120, 700))

        renewal_date = today + timedelta(days=random.randint(60, 180))
        contract_usage = build_contract_usage(products, employee_count)
        feature_scores = build_feature_scores(pattern, products)

        if pattern == "B":
            champion_active = random.random() > 0.7
        else:
            champion_active = True

        executive_active = pattern in ["A", "D", "E"] or random.random() > 0.5

        contradiction = None
        if idx in contradictions:
            ctype = random.choice(["champion_false", "new_exec", "usage_spike", "high_breadth", "clean_signal"])
            if ctype == "champion_false":
                champion_active = False
                contradiction = "Champion marked inactive despite otherwise positive usage indicators."
            elif ctype == "new_exec":
                executive_active = True
                contradiction = "New executive sponsor engagement introduced within the last 30 days."
            elif ctype == "usage_spike":
                contradiction = "Anomalous usage spike that does not align with the account baseline."
            elif ctype == "high_breadth":
                rp = random.choice(products)
                feature_scores[PRODUCTS[rp]["key"]] = 9
                contradiction = "One product shows unusually high feature breadth for the account profile."
            else:
                contradiction = "One product exhibits unusually stable utilization despite overall volatility."

        health_score = calculate_health_score(pattern, champion_active, executive_active, feature_scores)

        company = {
            "company_id": company_id, "name": name, "industry": INDUSTRIES[name],
            "employee_count": employee_count, "arr": arr,
            "contract_start_date": contract_start.isoformat(),
            "renewal_date": renewal_date.isoformat(),
            "products_contracted": products, "contracted_usage": contract_usage,
            "feature_breadth_score": feature_scores,
            "champion_name": random_name(), "champion_title": random.choice(CHAMPION_TITLES),
            "champion_active": champion_active,
            "executive_sponsor_name": random_name(),
            "executive_sponsor_title": random.choice(EXEC_TITLES),
            "executive_sponsor_active": executive_active,
            "health_score": health_score,
        }
        companies.append(company)
        manifest_map[company_id] = {"pattern": pattern, "contradiction": contradiction}

    return companies, manifest_map


def generate_usage_records(companies, manifest_map):
    usage_records = []
    utilization_summary = defaultdict(dict)
    usage_snapshots = defaultdict(dict)

    for company in companies:
        company_id = company["company_id"]
        pattern = manifest_map[company_id]["pattern"]
        contradiction = manifest_map[company_id]["contradiction"]
        account_growth_rate = random.uniform(0.08, 0.15)
        churn_decline_rate = random.uniform(0.40, 0.60)

        for product in company["products_contracted"]:
            daily_values = []
            meta = PRODUCTS[product]
            key = meta["key"]
            metric = meta["metric"]
            baseline = company["contracted_usage"][key][metric]
            volatility_regime = random.choice(["high", "medium", "surge", "drop"])
            regime_remaining = random.randint(10, 28)

            for day_idx, current_date in enumerate(daterange(START_DATE, END_DATE)):
                if pattern == "A":
                    if day_idx < 90:
                        multiplier = random.uniform(0.82, 0.96)
                    else:
                        months_in = (day_idx - 90) / 30
                        multiplier = (1 + account_growth_rate) ** months_in
                elif pattern == "B":
                    if day_idx < 85:
                        multiplier = random.uniform(0.92, 1.08)
                    else:
                        decline_progress = (day_idx - 85) / 95
                        multiplier = 1.0 - (decline_progress * churn_decline_rate)
                        if day_idx > 150 and random.random() > 0.65:
                            multiplier *= random.uniform(0.03, 0.12)
                elif pattern == "C":
                    if day_idx < 45:
                        multiplier = 0.12 + ((day_idx / 45) * 0.38)
                    else:
                        multiplier = random.uniform(0.30, 0.48)
                elif pattern == "D":
                    multiplier = random.uniform(0.72, 0.88)
                else:
                    regime_remaining -= 1
                    if regime_remaining <= 0:
                        volatility_regime = random.choice(["high", "medium", "surge", "drop"])
                        regime_remaining = random.randint(7, 24)
                    if volatility_regime == "high":
                        multiplier = random.uniform(0.85, 1.15)
                    elif volatility_regime == "medium":
                        multiplier = random.uniform(0.65, 0.92)
                    elif volatility_regime == "surge":
                        multiplier = random.uniform(1.05, 1.35)
                    else:
                        multiplier = random.uniform(0.45, 0.70)

                if current_date.weekday() >= 5:
                    multiplier *= random.uniform(0.70, 0.80)
                multiplier *= random.uniform(0.94, 1.06)
                if random.random() < 0.01:
                    multiplier *= random.uniform(1.2, 1.6)

                value = max(0, baseline * multiplier)
                metric_value = round(value, 2) if metric == "log_volume_gb" else int(value)
                daily_values.append(metric_value)
                usage_records.append({
                    "company_id": company_id, "date": current_date.isoformat(),
                    "product": product, "metric_name": metric, "metric_value": metric_value,
                })

            # Inject usage_spike contradiction on first product only
            if (contradiction and contradiction.startswith("Anomalous usage spike")
                    and product == company["products_contracted"][0]):
                spike_offset = random.randint(140, 170)
                spike_date = START_DATE + timedelta(days=spike_offset)
                spike_value = baseline * random.uniform(1.8, 2.4)
                spike_typed = round(spike_value, 2) if metric == "log_volume_gb" else int(spike_value)
                for rec in reversed(usage_records):
                    if (rec["company_id"] == company_id and rec["product"] == product
                            and rec["date"] == spike_date.isoformat()):
                        rec["metric_value"] = spike_typed
                        if spike_offset < len(daily_values):
                            daily_values[spike_offset] = spike_typed
                        break

            first_30 = mean(daily_values[:30])
            last_30 = mean(daily_values[-30:])
            utilization_summary[company_id][key] = round(last_30 / baseline, 2)
            usage_snapshots[company_id][key] = {
                "first_30": round(first_30 / baseline, 2),
                "last_30": round(last_30 / baseline, 2),
                "delta": round((last_30 - first_30) / baseline, 2),
            }

    return usage_records, utilization_summary, usage_snapshots


NOTES_BY_PATTERN = {
    "A": ["Discussed infrastructure scaling plans tied to upcoming product launch.",
          "Customer shared positive feedback on observability coverage and deployment visibility.",
          "Renewal planning conversation suggested possible expansion into additional teams.",
          "Reviewed dashboard usage patterns ahead of new environment rollout.",
          "Champion outlined increased monitoring needs as headcount grows."],
    "B": ["Customer flagged inconsistent dashboard performance and delayed alert delivery.",
          "No response to previous outreach attempts from champion.",
          "Support escalation opened following complaints about log ingestion latency.",
          "Customer expressed frustration with feature gaps and roadmap timing.",
          "Reactive follow-up after critical alert failure during deployment window."],
    "C": ["Onboarding session focused on agent configuration and dashboard setup.",
          "Customer requested implementation guidance for CI Visibility workflows.",
          "Follow-up outreach sent after limited platform adoption during pilot period.",
          "Walked through best practices for tagging and host grouping.",
          "Light check-in following extended period of low engagement."],
    "D": ["Quarterly business review completed with positive feedback on uptime visibility.",
          "Routine check-in confirmed current observability coverage remains stable.",
          "Champion shared roadmap updates for internal infrastructure modernization.",
          "Discussed minor configuration optimizations during regular sync.",
          "Reviewed monthly usage report; no material changes flagged."],
    "E": ["Customer usage patterns fluctuating due to shifting research workloads.",
          "Executive sponsor mentioned experimentation cycles driving unpredictable utilization.",
          "Recent project spike increased infrastructure monitoring activity significantly.",
          "Discussed upcoming model release and associated infrastructure load expectations.",
          "Champion noted reorg may shift platform ownership in coming quarter."],
}


def generate_csm_note(pattern):
    return random.choice(NOTES_BY_PATTERN[pattern])


def generate_csm_activity(companies, manifest_map, today):
    activities = []
    gap_days = {}
    sim_window_days = (END_DATE - START_DATE).days

    for company in companies:
        company_id = company["company_id"]
        pattern = manifest_map[company_id]["pattern"]
        contradiction = manifest_map[company_id]["contradiction"]

        if pattern == "A":
            cadence_days = [0, 14, 30, 45, 60, 85, 110, 130]
            recent_gap = random.randint(45, 75)
        elif pattern == "B":
            cadence_days = [0, 55, 110, 145, 170]
            recent_gap = random.randint(60, 90)
        elif pattern == "C":
            cadence_days = [0, 7, 14, 21, 30, 40, 110, 160]
            recent_gap = random.randint(20, 45)
        elif pattern == "D":
            cadence_days = [0, 28, 56, 84, 112, 140, 168]
            recent_gap = random.randint(10, 28)
        else:
            cadence_days = sorted(random.sample(range(0, 180), 7))
            recent_gap = random.randint(5, 35)

        gap_days[company_id] = recent_gap

        # Anchor most recent meaningful touch at (today - recent_gap), keep cadence before it
        most_recent_touch = today - timedelta(days=recent_gap)
        anchored_offset = max(0, min(sim_window_days, (most_recent_touch - START_DATE).days))
        cadence_days = [d for d in cadence_days if d < anchored_offset] + [anchored_offset]

        for offset in cadence_days:
            interaction_date = START_DATE + timedelta(days=offset)
            if interaction_date > END_DATE:
                continue

            if pattern == "A":
                sentiment = random.choice(["green", "green", "yellow"])
                initiated_by = random.choice(["csm", "csm", "customer"])
            elif pattern == "B":
                sentiment = random.choice(["yellow", "green"]) if offset < 60 else random.choice(["yellow", "red", "red"])
                initiated_by = "customer"
            elif pattern == "C":
                sentiment = "green" if offset < 45 else "yellow"
                initiated_by = "csm"
            elif pattern == "D":
                sentiment = random.choice(["green", "green", "yellow"])
                initiated_by = random.choice(["csm", "customer"])
            else:
                sentiment = random.choice(["green", "yellow", "red"])
                initiated_by = random.choice(["csm", "customer"])

            contact = random.choices(
                ["champion", "executive_sponsor", "end_user", "unknown"],
                weights=[55, 20, 20, 5], k=1)[0]

            if pattern == "B" and offset > 100 and not company["champion_active"]:
                contact = random.choice(["end_user", "unknown", "unknown"])

            activity_type = random.choice(["email", "call", "qbr", "slack_message", "support_escalation"])
            if pattern == "B" and offset > 110:
                activity_type = random.choices(
                    ["support_escalation", "email", "call"], weights=[55, 30, 15], k=1)[0]

            activities.append({
                "company_id": company_id, "date": interaction_date.isoformat(),
                "activity_type": activity_type, "initiated_by": initiated_by,
                "contact": contact, "sentiment": sentiment,
                "notes": generate_csm_note(pattern),
            })

        if contradiction and "executive sponsor" in contradiction.lower():
            inject_date = END_DATE - timedelta(days=random.randint(5, 25))
            activities.append({
                "company_id": company_id, "date": inject_date.isoformat(),
                "activity_type": "call", "initiated_by": "customer",
                "contact": "executive_sponsor", "sentiment": "green",
                "notes": "Introductory meeting with new executive sponsor to review observability roadmap and renewal goals.",
            })

    activities.sort(key=lambda r: (r["company_id"], r["date"]))
    return activities, gap_days


TICKET_CATEGORIES = ["performance", "bug", "configuration", "feature_request", "outage", "data_quality"]


def generate_ticket_summary(category, product):
    templates = {
        "performance": f"Customer reported degraded {product} dashboard response times.",
        "bug": f"Unexpected behavior observed within {product} monitoring workflows.",
        "configuration": f"Customer requested help configuring {product} instrumentation.",
        "feature_request": f"Customer requested expanded reporting functionality for {product}.",
        "outage": f"Temporary service disruption impacted {product} visibility.",
        "data_quality": f"Customer identified missing or delayed telemetry data in {product}.",
    }
    return templates[category]


def generate_support_tickets(companies, manifest_map):
    tickets = []
    total_days = (END_DATE - START_DATE).days

    for company in companies:
        company_id = company["company_id"]
        pattern = manifest_map[company_id]["pattern"]
        products = company["products_contracted"]

        if pattern == "A":
            count = random.randint(3, 8)
            severity_pool = ["low", "low", "low", "medium"]
            category_pool = TICKET_CATEGORIES
            distribution = "even"
        elif pattern == "B":
            count = random.randint(12, 20)
            severity_pool = ["medium", "high", "high", "critical"]
            category_pool = ["performance", "outage", "data_quality", "bug"]
            distribution = "recent_heavy"
        elif pattern == "C":
            count = random.randint(4, 9)
            severity_pool = ["low", "medium", "medium"]
            category_pool = ["configuration", "configuration", "bug", "feature_request"]
            distribution = "early_heavy"
        elif pattern == "D":
            count = random.randint(5, 10)
            severity_pool = ["low", "medium"]
            category_pool = TICKET_CATEGORIES
            distribution = "even"
        else:
            count = random.randint(8, 16)
            severity_pool = ["low", "medium", "high"]
            category_pool = TICKET_CATEGORIES
            distribution = "spiky"

        for _ in range(count):
            if distribution == "recent_heavy":
                day_offset = random.randint(120, 180) if random.random() > 0.30 else random.randint(0, 119)
            elif distribution == "early_heavy":
                day_offset = random.randint(0, 60) if random.random() > 0.35 else random.randint(61, 180)
            elif distribution == "spiky":
                center = random.choice([30, 90, 150])
                day_offset = max(0, min(total_days, int(random.gauss(center, 10))))
            else:
                day_offset = random.randint(0, total_days)

            ticket_date = START_DATE + timedelta(days=day_offset)
            cat = random.choice(category_pool)
            tickets.append({
                "company_id": company_id, "date": ticket_date.isoformat(),
                "severity": random.choice(severity_pool),
                "product": random.choice(products), "category": cat,
                "status": random.choices(["open", "resolved"], weights=[25, 75], k=1)[0],
                "summary": generate_ticket_summary(cat, random.choice(products)),
            })

    tickets.sort(key=lambda r: (r["company_id"], r["date"]))
    return tickets


def build_support_ticket_trend(pattern):
    return {
        "A": "Ticket volume low and stable, predominantly low-severity requests.",
        "B": "Ticket volume increasing over the last 60 days with elevated severity.",
        "C": "Ticket volume concentrated around onboarding and configuration friction.",
        "D": "Ticket volume routine and operationally stable.",
        "E": "Ticket volume fluctuating in line with usage volatility.",
    }[pattern]


def generate_manifest_and_key(companies, manifest_map, utilization_summary, usage_snapshots, gap_days, today):
    manifest = []
    eval_key = []

    for company in companies:
        company_id = company["company_id"]
        pattern = manifest_map[company_id]["pattern"]
        contradiction = manifest_map[company_id]["contradiction"]

        product_descriptions = []
        for product in company["products_contracted"]:
            key = PRODUCTS[product]["key"]
            if key not in usage_snapshots[company_id]:
                continue
            snap = usage_snapshots[company_id][key]
            product_descriptions.append(
                f"{product} moved from {int(snap['first_30'] * 100)}% to {int(snap['last_30'] * 100)}% of baseline")

        embedded_story = (
            f"{company['name']}: " + "; ".join(product_descriptions[:3])
            + f". Last meaningful CSM touch occurred {gap_days[company_id]} days ago. "
            + ("Champion currently active. " if company["champion_active"] else "Champion currently inactive. ")
            + ("Executive sponsor currently active." if company["executive_sponsor_active"] else "Executive sponsor currently inactive.")
        )

        renewal_days_out = (datetime.fromisoformat(company["renewal_date"]).date() - today).days

        manifest.append({
            "company_id": company_id, "name": company["name"],
            "embedded_story": embedded_story,
            "signal_contradiction": contradiction,
            "csm_gap_days": gap_days[company_id],
            "champion_active": company["champion_active"],
            "executive_sponsor_active": company["executive_sponsor_active"],
            "products_contracted": company["products_contracted"],
            "renewal_days_out": renewal_days_out,
            "utilization_rate": dict(utilization_summary[company_id]),
            "support_ticket_trend": build_support_ticket_trend(pattern),
        })

        eval_key.append({
            "company_id": company_id, "name": company["name"],
            "pattern": pattern, "pattern_label": PATTERNS[pattern],
            "signal_contradiction": contradiction,
        })

    return manifest, eval_key


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-05-01",
                        help="Reference date for renewal/gap calculations (YYYY-MM-DD)")
    args = parser.parse_args()
    today = datetime.strptime(args.date, "%Y-%m-%d").date()

    os.makedirs("data", exist_ok=True)

    companies, manifest_map = create_company_objects(today)
    usage_records, utilization_summary, usage_snapshots = generate_usage_records(companies, manifest_map)
    csm_activity, gap_days = generate_csm_activity(companies, manifest_map, today)
    support_tickets = generate_support_tickets(companies, manifest_map)
    manifest, eval_key = generate_manifest_and_key(
        companies, manifest_map, utilization_summary, usage_snapshots, gap_days, today)

    outputs = {
        "companies.json": companies, "product_usage.json": usage_records,
        "csm_activity.json": csm_activity, "support_tickets.json": support_tickets,
        "data_manifest.json": manifest, "evaluation_key.json": eval_key,
    }

    for filename, data in outputs.items():
        write_json(os.path.join("data", filename), data)

    print("\nGridline simulated dataset generation complete\n")
    for filename, data in outputs.items():
        print(f"{filename}: {len(data)} records")

    print("\nCompany Summary\n")
    for company in companies:
        cid = company["company_id"]
        pattern = manifest_map[cid]["pattern"]
        contradiction = "Yes" if manifest_map[cid]["contradiction"] else "No"
        primary_key = PRODUCTS[company["products_contracted"][0]]["key"]
        utilization = utilization_summary[cid][primary_key]
        print(f"{company['name']:<20} Pattern={pattern} CSM Gap={gap_days[cid]:>3}d "
              f"Primary Util={utilization:.2f}x Contradiction={contradiction}")


if __name__ == "__main__":
    main()
