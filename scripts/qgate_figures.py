"""Slide figures for Q-Gate (slides 8-9). Run after eval_qgate: python -m scripts.qgate_figures
Writes results/qgate_circuit.png (the overlap circuit) and results/qgate_e1.png (Q-Gate vs RBF, same split)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pennylane as qml

from aegis.qgate import kernel

OUT = Path("results")
OUT.mkdir(exist_ok=True)
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
QGATE, RBF = "#2a78d6", "#eb6834"          # categorical slots 1 and 2, fixed order

# ---------------------------------------------------------------- circuit (slide 8)
x = np.array([0.8, 2.1, 1.3, 2.7])
fig, ax = qml.draw_mpl(kernel._state_circuit, decimals=2, style="pennylane")(x)
fig.suptitle("Q-Gate feature map: 4 features -> 4 entangled qubits (ZZ map)", color=INK)
fig.savefig(OUT / "qgate_circuit.png", dpi=200, bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---------------------------------------------------------------- E1 bars (slide 9)
res = json.loads((OUT / "qgate_e1_e2.json").read_text())
metrics = [("auroc", "AUROC"), ("recall", "Recall"), ("precision", "Precision"), ("fpr", "False-positive rate\n(lower is better)")]
xs = np.arange(len(metrics))
w = 0.36
fig, ax = plt.subplots(figsize=(8, 4.2), facecolor=SURFACE)
ax.set_facecolor(SURFACE)
for k, (name, color, label) in enumerate([("qgate", QGATE, "Q-Gate (quantum kernel)"), ("rbf", RBF, "RBF (classical twin)")]):
    vals = [res[name][m] for m, _ in metrics]
    bars = ax.bar(xs + (k - 0.5) * (w + 0.02), vals, w, color=color, label=label, edgecolor=SURFACE, linewidth=2)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.2f}", ha="center", va="bottom", fontsize=9, color=INK)
ax.set_xticks(xs, [t for _, t in metrics], color=INK)
ax.set_ylim(0, 1.05)
ax.set_ylabel("score on held-out test split", color=MUTED)
ax.yaxis.grid(True, color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(GRID)
ax.tick_params(colors=MUTED, length=0)
n = res["E2"]["n_attacks"]
ax.set_title(f"Same 4 features, same split (test n = 116, {n} injections). "
             f"Only-caught-by: Q-Gate {res['E2']['qgate_only_catches']}, RBF {res['E2']['rbf_only_catches']}",
             fontsize=10, color=MUTED, loc="left")
ax.legend(frameon=False, loc="upper right", labelcolor=INK)
fig.tight_layout()
fig.savefig(OUT / "qgate_e1.png", dpi=200, facecolor=SURFACE)
print("wrote results/qgate_circuit.png and results/qgate_e1.png")
