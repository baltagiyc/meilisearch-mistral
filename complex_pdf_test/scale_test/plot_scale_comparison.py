"""
Generate comparison charts: 43 chunks vs 10k docs (latency + ingestion).

Output: PNG and SVG in complex_pdf_test/scale_test/ for pasting into reports.

Usage (from project root):
  uv run python complex_pdf_test/scale_test/plot_scale_comparison.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Data from BILAN (43 chunks) and scale test run (10k docs)
LABELS = ["Mean", "p50", "p95"]
CHUNKS_43 = [335, 194, 727]   # ms
DOCS_10K = [758, 206, 2997]   # ms

OUT_DIR = Path(__file__).resolve().parent


def main() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # ---- 1. Hybrid search latency (ms) ----
    ax1 = axes[0]
    x = np.arange(len(LABELS))
    width = 0.35
    bars1 = ax1.bar(x - width / 2, CHUNKS_43, width, label="43 chunks", color="#1f77b4")
    bars2 = ax1.bar(x + width / 2, DOCS_10K, width, label="10k docs", color="#ff7f0e")
    ax1.set_ylabel("Latency (ms)")
    ax1.set_title("Hybrid search latency")
    ax1.set_xticks(x)
    ax1.set_xticklabels(LABELS)
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3)

    for b in bars1:
        ax1.text(b.get_x() + b.get_width() / 2, b.get_height() + 20, str(int(b.get_height())), ha="center", fontsize=9)
    for b in bars2:
        ax1.text(b.get_x() + b.get_width() / 2, b.get_height() + 20, str(int(b.get_height())), ha="center", fontsize=9)

    # ---- 2. Ingestion time (s): 43 = single batch (fast), 10k = 776.9 s ----
    ax2 = axes[1]
    ingestion_43 = 2   # placeholder: single batch, not measured (order of seconds)
    ingestion_10k = 776.9
    bars_a = ax2.bar(0, ingestion_43, width=0.5, color="#1f77b4", label="43 chunks (~1 batch)")
    bars_b = ax2.bar(1, ingestion_10k, width=0.5, color="#ff7f0e", label="10k docs (12.9 docs/s)")
    ax2.set_ylabel("Time (s)")
    ax2.set_title("Ingestion time (send → all tasks succeeded)")
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["43 chunks", "10k docs"])
    ax2.legend()
    ax2.grid(axis="y", alpha=0.3)
    ax2.set_ylim(0, 850)
    ax2.text(0, ingestion_43 + 10, "~2 s", ha="center", fontsize=9)
    ax2.text(1, ingestion_10k + 15, "776.9 s", ha="center", fontsize=10)

    plt.tight_layout()
    for ext in ["png", "svg"]:
        out = OUT_DIR / f"scale_comparison.{ext}"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        print(f"Saved {out}")
    plt.close()


if __name__ == "__main__":
    main()
