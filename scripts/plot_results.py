
import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
SUMMARY_FILE = RESULTS_DIR / "summary.csv"


def load_summary():
    if not SUMMARY_FILE.exists():
        raise FileNotFoundError(
            f"Summary CSV not found: {SUMMARY_FILE}\n"
            "Run python -m eval.run first."
        )

    with SUMMARY_FILE.open("r", newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError("summary.csv contains no evaluation results.")

    return rows


def plot_safety_metrics(rows):
    configs = [row["config"] for row in rows]

    metrics = {
        "Accuracy": "accuracy",
        "Attack Success Rate": "asr",
        "False-Block Rate": "false_block_rate",
        "Over-Refusal Rate": "over_refusal_rate",
    }

    x = list(range(len(configs)))
    width = 0.18

    fig, ax = plt.subplots(figsize=(11, 6))

    for index, (label, column) in enumerate(metrics.items()):
        values = [
            float(row[column]) * 100
            for row in rows
        ]

        positions = [
            position + (index - (len(metrics) - 1) / 2) * width
            for position in x
        ]

        bars = ax.bar(
            positions,
            values,
            width,
            label=label,
        )

        ax.bar_label(
            bars,
            fmt="%.1f%%",
            padding=2,
            fontsize=8,
        )

    ax.set_title("Aegis Safety Evaluation")
    ax.set_xlabel("Configuration")
    ax.set_ylabel("Rate (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(configs)
    ax.set_ylim(0, 120)
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()

    output = RESULTS_DIR / "safety_metrics.png"
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {output}")


def plot_latency(rows):
    configs = [row["config"] for row in rows]

    latencies = [
        float(row["mean_latency_ms"])
        for row in rows
    ]

    fig, ax = plt.subplots(figsize=(8, 5))

    bars = ax.bar(configs, latencies, width=0.5)

    ax.bar_label(
        bars,
        fmt="%.4f ms",
        padding=4,
    )

    ax.set_title("Aegis Mean Decision Latency")
    ax.set_xlabel("Configuration")
    ax.set_ylabel("Latency (milliseconds)")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()

    output = RESULTS_DIR / "latency.png"
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {output}")


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_summary()

    plot_safety_metrics(rows)
    plot_latency(rows)

    print("\nChart generation completed.")


if __name__ == "__main__":
    main()
