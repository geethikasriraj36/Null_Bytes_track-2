
import argparse
import csv
import json
import time
from pathlib import Path

from aegis.audit.chain import append_event
from aegis.decide import decide as policy_decide
from aegis.decide import decide_with_reason


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CASES = ROOT / "sim" / "cases" / "cases.jsonl"
RESULTS_DIR = ROOT / "results"

AUDIT_LOG = RESULTS_DIR / "audit.jsonl"
SUMMARY_CSV = RESULTS_DIR / "summary.csv"
PER_CASE_CSV = RESULTS_DIR / "per_case.csv"

CONFIGS = {
    "0_baseline": "Allow every request",
    "7_full": "Prototype keyword-based policy",
}

def decide(prompt: str, config: str) -> str:
    """Compatibility wrapper for existing tests and callers."""
    return policy_decide(prompt, config)

def load_cases(path: Path) -> list[dict]:
    """Load and validate JSONL evaluation cases."""

    if not path.exists():
        raise FileNotFoundError(f"Test cases not found: {path}")

    cases = []

    with path.open("r", encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc

            if not isinstance(case, dict):
                raise ValueError(
                    f"Line {line_number} must contain a JSON object."
                )

            required = {"id", "category", "prompt", "expected"}
            missing = required - case.keys()

            if missing:
                raise ValueError(
                    f"Line {line_number} missing fields: "
                    f"{sorted(missing)}"
                )

            if not isinstance(case["id"], str) or not case["id"].strip():
                raise ValueError(
                    f"Invalid case ID on line {line_number}."
                )

            if not isinstance(case["category"], str):
                raise ValueError(
                    f"Invalid category on line {line_number}."
                )

            if not isinstance(case["prompt"], str):
                raise ValueError(
                    f"Invalid prompt on line {line_number}."
                )

            if case["expected"] not in {"allow", "block"}:
                raise ValueError(
                    f"Invalid expected decision on line {line_number}: "
                    f"{case['expected']!r}"
                )

            cases.append(case)

    if not cases:
        raise ValueError("No test cases found.")

    return cases


def calculate_rate(numerator: int, denominator: int) -> float:
    """Return a rate, avoiding division by zero."""

    if denominator == 0:
        return 0.0

    return numerator / denominator


def evaluate(cases: list[dict], config: str) -> tuple[dict, list[dict]]:
    """Evaluate one configuration and append decisions to the audit log."""

    outcomes = []
    latencies = []

    for case in cases:
        start = time.perf_counter()

        details = decide_with_reason(case["prompt"], config)

        latency_ms = (time.perf_counter() - start) * 1000
        latencies.append(latency_ms)

        predicted = details["decision"]
        expected = case["expected"]

        correct = predicted == expected
        is_unsafe = expected == "block"
        false_block = expected == "allow" and predicted == "block"
        attack_success = is_unsafe and predicted == "allow"

        outcome = {
            "config": config,
            "case_id": case["id"],
            "category": case["category"],
            "expected": expected,
            "predicted": predicted,
            "correct": correct,
            "attack_success": attack_success,
            "false_block": false_block,
            "rule_id": details["rule_id"],
            "reason": details["reason"],
            "policy_version": details["policy_version"],
            "latency_ms": round(latency_ms, 4),
        }

        outcomes.append(outcome)

        # Every decision is added to the hash-chained audit log.
        append_event(
            AUDIT_LOG,
            {
                "action": "evaluation_decision",
                "config": config,
                "case_id": case["id"],
                "category": case["category"],
                "expected": expected,
                "predicted": predicted,
                "correct": correct,
                "attack_success": attack_success,
                "false_block": false_block,
                "rule_id": details["rule_id"],
                "reason": details["reason"],
                "policy_version": details["policy_version"],
                "latency_ms": round(latency_ms, 4),
            },
        )

    unsafe_cases = [
        outcome for outcome in outcomes
        if outcome["expected"] == "block"
    ]

    allowed_cases = [
        outcome for outcome in outcomes
        if outcome["expected"] == "allow"
    ]

    # Over-refusal measures benign/borderline requests that were blocked.
    over_refusal_cases = [
        outcome for outcome in outcomes
        if outcome["expected"] == "allow"
        and outcome["category"].lower() in {"benign", "borderline"}
    ]

    correct_count = sum(
        outcome["correct"] for outcome in outcomes
    )

    attack_successes = sum(
        outcome["attack_success"] for outcome in unsafe_cases
    )

    false_blocks = sum(
        outcome["false_block"] for outcome in allowed_cases
    )

    over_refusals = sum(
        outcome["false_block"] for outcome in over_refusal_cases
    )

    summary = {
        "config": config,
        "description": CONFIGS[config],
        "total_cases": len(outcomes),
        "correct": correct_count,
        "accuracy": calculate_rate(
            correct_count,
            len(outcomes),
        ),
        "unsafe_cases": len(unsafe_cases),
        "attack_successes": attack_successes,
        "asr": calculate_rate(
            attack_successes,
            len(unsafe_cases),
        ),
        "allowed_cases": len(allowed_cases),
        "false_blocks": false_blocks,
        "false_block_rate": calculate_rate(
            false_blocks,
            len(allowed_cases),
        ),
        "over_refusal_cases": len(over_refusal_cases),
        "over_refusals": over_refusals,
        "over_refusal_rate": calculate_rate(
            over_refusals,
            len(over_refusal_cases),
        ),
        "mean_latency_ms": calculate_rate(
            sum(latencies),
            len(latencies),
        ),
    }

    return summary, outcomes


def write_csv(path: Path, rows: list[dict]) -> None:
    """Write dictionaries to a CSV file."""

    if not rows:
        print(f"Skipping empty CSV: {path}")
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)


def print_summary(summary: dict) -> None:
    """Display evaluation metrics."""

    print(f"\nConfiguration: {summary['config']}")
    print(f"  Description:       {summary['description']}")
    print(f"  Cases:             {summary['total_cases']}")
    print(
        f"  Accuracy:          {summary['accuracy']:.1%}"
    )
    print(
        f"  Attack success:    {summary['asr']:.1%}"
        f" ({summary['attack_successes']}/"
        f"{summary['unsafe_cases']})"
    )
    print(
        f"  False-block rate:  {summary['false_block_rate']:.1%}"
        f" ({summary['false_blocks']}/"
        f"{summary['allowed_cases']})"
    )
    print(
        f"  Over-refusal rate: {summary['over_refusal_rate']:.1%}"
        f" ({summary['over_refusals']}/"
        f"{summary['over_refusal_cases']})"
    )
    print(
        f"  Mean latency:      "
        f"{summary['mean_latency_ms']:.4f} ms"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate Aegis safety configurations."
    )

    parser.add_argument(
        "--configs",
        nargs="+",
        choices=list(CONFIGS.keys()),
        default=list(CONFIGS.keys()),
        help="Configurations to evaluate.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Evaluate only the first N test cases.",
    )

    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES,
        help="Path to the JSONL test-case file.",
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    try:
        cases = load_cases(args.cases)
    except (OSError, ValueError) as exc:
        print(f"Error loading cases: {exc}")
        return 1

    if args.limit is not None:
        cases = cases[:args.limit]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    summaries = []
    all_outcomes = []

    try:
        for config in args.configs:
            summary, outcomes = evaluate(cases, config)

            summaries.append(summary)
            all_outcomes.extend(outcomes)

            print_summary(summary)

        write_csv(SUMMARY_CSV, summaries)
        write_csv(PER_CASE_CSV, all_outcomes)

    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Evaluation failed: {exc}")
        return 1

    print(f"\nResults saved in: {RESULTS_DIR}")
    print(f"  Summary:  {SUMMARY_CSV}")
    print(f"  Per-case: {PER_CASE_CSV}")
    print(f"  Audit:    {AUDIT_LOG}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
