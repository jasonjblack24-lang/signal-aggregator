#!/usr/bin/env python3
"""Evaluation Harness — Phase 5 of the Gridline CS workflow pipeline.

Compares the Hypothesis Former's verdicts against the ground-truth
evaluation key and reports precision, recall, F1, and a per-pattern
breakdown with a list of misses worth reviewing.

Pattern definitions (from evaluation_key.json):
  A — Expansion Ready     → the expansion playbook should fire
  B — Silent Churn Risk   → should NOT fire (wrong playbook)
  C — Stalled Adoption    → should NOT fire (wrong playbook)
  D — Healthy and Stable  → should NOT fire (no action needed)
  E — Volatile/Ambiguous  → could go either way; fires noted separately

Scoring logic:
  TP  Pattern A account with verdict "fire"
  FN  Pattern A account without verdict "fire" (missed opportunity)
  FP  Pattern B/C/D account with verdict "fire" (wrong playbook fired)
  TN  Pattern B/C/D account without verdict "fire" (correctly suppressed)
  UF  Pattern E account with verdict "fire" (unexpected — not penalised
      as hard FP but surfaced for review, since E is legitimately ambiguous)

Precision is reported two ways:
  strict   counts UF (Pattern E fires) as false positives
  lenient  counts only Pattern B/C/D fires as false positives

Usage:
    python3 eval_harness.py
    python3 eval_harness.py --hypotheses output/hypotheses_2026-05-01.json
    python3 eval_harness.py --output-json output/eval_2026-05-01.json
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"

EVAL_KEY_PATH = DATA_DIR / "evaluation_key.json"

# Patterns the expansion playbook should fire on
TARGET_PATTERNS = {"A"}
# Patterns it should never fire on (hard false positives)
HARD_NEGATIVE_PATTERNS = {"B", "C", "D"}
# Genuinely ambiguous — fires noted but not penalised
AMBIGUOUS_PATTERNS = {"E"}

FIRE_VERDICTS = {"fire"}


def find_hypotheses_file(path: str | None) -> Path:
    if path:
        p = Path(path)
        if not p.exists():
            sys.exit(f"Error: {p} does not exist.")
        return p
    files = sorted(glob.glob(str(OUTPUT_DIR / "hypotheses_*.json")))
    if not files:
        sys.exit("Error: no hypotheses_*.json files found in output/")
    return Path(files[-1])


def load_json(path: Path) -> list | dict:
    with open(path) as f:
        return json.load(f)


def safe_div(num: int, denom: int) -> float:
    return num / denom if denom else 0.0


def f1(precision: float, recall: float) -> float:
    return safe_div(2 * precision * recall, precision + recall)


def run_eval(hypotheses_path: Path) -> dict:
    eval_key_raw: list = load_json(EVAL_KEY_PATH)
    hypotheses_raw: dict = load_json(hypotheses_path)

    key_by_id = {e["company_id"]: e for e in eval_key_raw}
    hyp_by_id = {h["company_id"]: h for h in hypotheses_raw["hypotheses"]}

    # Ensure all key accounts appear in hypotheses
    missing = set(key_by_id) - set(hyp_by_id)
    if missing:
        print(f"Warning: {len(missing)} accounts in eval key missing from hypotheses: {sorted(missing)}")

    results: list[dict] = []

    for cid, key_entry in sorted(key_by_id.items()):
        hyp_entry = hyp_by_id.get(cid)
        pattern = key_entry["pattern"]
        pattern_label = key_entry["pattern_label"]
        contradiction = key_entry.get("signal_contradiction")
        verdict = hyp_entry["verdict"] if hyp_entry else "missing"
        confidence = hyp_entry.get("confidence") if hyp_entry else None
        fired = verdict in FIRE_VERDICTS

        if pattern in TARGET_PATTERNS:
            outcome = "TP" if fired else "FN"
        elif pattern in HARD_NEGATIVE_PATTERNS:
            outcome = "FP" if fired else "TN"
        elif pattern in AMBIGUOUS_PATTERNS:
            outcome = "UF" if fired else "TN_ambig"
        else:
            outcome = "unknown"

        results.append({
            "company_id": cid,
            "name": key_entry["name"],
            "pattern": pattern,
            "pattern_label": pattern_label,
            "verdict": verdict,
            "confidence": confidence,
            "outcome": outcome,
            "signal_contradiction": contradiction,
        })

    # Aggregate counts
    counts = {k: 0 for k in ("TP", "FN", "FP", "TN", "UF", "TN_ambig")}
    for r in results:
        counts[r["outcome"]] += 1

    recall = safe_div(counts["TP"], counts["TP"] + counts["FN"])
    precision_strict = safe_div(counts["TP"], counts["TP"] + counts["FP"] + counts["UF"])
    precision_lenient = safe_div(counts["TP"], counts["TP"] + counts["FP"])
    f1_strict = f1(precision_strict, recall)
    f1_lenient = f1(precision_lenient, recall)

    # Per-pattern breakdown
    pattern_breakdown: dict[str, dict] = {}
    for r in results:
        p = r["pattern"]
        label = r["pattern_label"]
        if p not in pattern_breakdown:
            pattern_breakdown[p] = {
                "label": label,
                "total": 0,
                "fired": 0,
                "accounts": [],
            }
        pattern_breakdown[p]["total"] += 1
        if r["verdict"] in FIRE_VERDICTS:
            pattern_breakdown[p]["fired"] += 1
        pattern_breakdown[p]["accounts"].append({
            "company_id": r["company_id"],
            "verdict": r["verdict"],
            "outcome": r["outcome"],
        })

    # Miss lists
    false_negatives = [r for r in results if r["outcome"] == "FN"]
    false_positives = [r for r in results if r["outcome"] == "FP"]
    unexpected_fires = [r for r in results if r["outcome"] == "UF"]

    return {
        "hypotheses_file": str(hypotheses_path),
        "as_of_date": hypotheses_raw.get("as_of_date"),
        "playbook": hypotheses_raw.get("playbook"),
        "counts": counts,
        "metrics": {
            "recall": round(recall, 4),
            "precision_strict": round(precision_strict, 4),
            "precision_lenient": round(precision_lenient, 4),
            "f1_strict": round(f1_strict, 4),
            "f1_lenient": round(f1_lenient, 4),
        },
        "pattern_breakdown": pattern_breakdown,
        "false_negatives": false_negatives,
        "false_positives": false_positives,
        "unexpected_fires": unexpected_fires,
        "all_results": results,
    }


def print_report(ev: dict) -> None:
    sep = "─" * 60

    print(f"\n{sep}")
    print(f"  EVALUATION REPORT — {ev['as_of_date']}  |  playbook: {ev['playbook']}")
    print(sep)
    print(f"  Source: {ev['hypotheses_file']}")
    print()

    c = ev["counts"]
    m = ev["metrics"]

    print("  OVERALL METRICS")
    print(f"  {'Recall (Pattern A coverage):':<38} {m['recall']:.1%}")
    print(f"  {'Precision (strict, E counts as FP):':<38} {m['precision_strict']:.1%}")
    print(f"  {'Precision (lenient, E excluded):':<38} {m['precision_lenient']:.1%}")
    print(f"  {'F1 strict:':<38} {m['f1_strict']:.3f}")
    print(f"  {'F1 lenient:':<38} {m['f1_lenient']:.3f}")
    print()

    print("  OUTCOME COUNTS")
    print(f"  {'TP  (Pattern A fired):':<38} {c['TP']}")
    print(f"  {'FN  (Pattern A missed):':<38} {c['FN']}")
    print(f"  {'FP  (B/C/D incorrectly fired):':<38} {c['FP']}")
    print(f"  {'TN  (B/C/D correctly suppressed):':<38} {c['TN']}")
    print(f"  {'UF  (Pattern E unexpected fires):':<38} {c['UF']}")
    print(f"  {'TN~ (Pattern E correctly suppressed):':<38} {c['TN_ambig']}")
    print()

    print("  PER-PATTERN BREAKDOWN")
    for pattern in sorted(ev["pattern_breakdown"]):
        pb = ev["pattern_breakdown"][pattern]
        fired = pb["fired"]
        total = pb["total"]
        bar = "✓" * fired + "·" * (total - fired)
        note = ""
        if pattern == "A":
            note = " ← target"
        elif pattern == "E":
            note = " ← ambiguous"
        print(f"  Pattern {pattern}  {pb['label']:<22}  {fired}/{total} fired  [{bar}]{note}")
    print()

    if ev["false_negatives"]:
        print("  FALSE NEGATIVES — Pattern A accounts that did not fire")
        for r in ev["false_negatives"]:
            contra = f"  ⚡ contradiction: {r['signal_contradiction']}" if r["signal_contradiction"] else ""
            print(f"    • {r['name']:<20} verdict={r['verdict']}{contra}")
        print()

    if ev["false_positives"]:
        print("  FALSE POSITIVES — Pattern B/C/D accounts that fired (wrong playbook)")
        for r in ev["false_positives"]:
            print(f"    • {r['name']:<20} pattern={r['pattern']} ({r['pattern_label']})  confidence={r['confidence']}")
        print()

    if ev["unexpected_fires"]:
        print("  UNEXPECTED FIRES — Pattern E (Volatile/Ambiguous) accounts that fired")
        print("  (Not penalised — surfaced for human review)")
        for r in ev["unexpected_fires"]:
            contra = f"\n    ⚡ contradiction: {r['signal_contradiction']}" if r["signal_contradiction"] else ""
            print(f"    • {r['name']:<20} confidence={r['confidence']}{contra}")
        print()

    if not ev["false_negatives"] and not ev["false_positives"]:
        print("  ✓ No false negatives or hard false positives.")
        print()

    print(sep)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Hypothesis Former against ground truth")
    parser.add_argument("--hypotheses", help="Path to hypotheses JSON file")
    parser.add_argument("--output-json", help="Write full eval results to this JSON file")
    args = parser.parse_args()

    hypotheses_path = find_hypotheses_file(args.hypotheses)
    ev = run_eval(hypotheses_path)
    print_report(ev)

    if args.output_json:
        out_path = Path(args.output_json)
        with open(out_path, "w") as f:
            json.dump(ev, f, indent=2)
        print(f"  Full results written to {out_path}\n")


if __name__ == "__main__":
    main()
