"""Render an interdependency heat map from data/interdependencies.csv.

Two outputs are produced:

* A pure-text heat map printed to stdout (works with no extra deps).
* An ASCII matrix written to reports/interdependency_heatmap.txt.

If matplotlib is available, also write reports/interdependency_heatmap.png.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "interdependencies.csv"
REPORTS = ROOT / "reports"


def load_matrix() -> tuple[List[str], Dict[tuple[str, str], float]]:
    sectors: list[str] = []
    coupling: Dict[tuple[str, str], float] = {}
    with DATA.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            a, b = row["sector_a"], row["sector_b"]
            for s in (a, b):
                if s not in sectors:
                    sectors.append(s)
            score = float(row["coupling"])
            coupling[(a, b)] = score
            coupling[(b, a)] = score
    return sectors, coupling


def _shade(score: float) -> str:
    blocks = " .:-=+*#%@"
    idx = min(len(blocks) - 1, int(score * (len(blocks) - 1)))
    return blocks[idx] * 2


def render_text() -> str:
    sectors, coupling = load_matrix()
    width = max(len(s) for s in sectors) + 1
    header = " " * (width + 1) + " ".join(f"{s[:6]:>6}" for s in sectors)
    lines = [header]
    for a in sectors:
        row_cells = []
        for b in sectors:
            if a == b:
                cell = "  ##  "
            else:
                score = coupling.get((a, b), 0.0)
                cell = f" {_shade(score)} {score:.2f}"
            row_cells.append(f"{cell:>6}")
        lines.append(f"{a:<{width}} " + " ".join(row_cells))
    legend = (
        "\nLegend: 0.00 weak coupling . . . 1.00 strong coupling. "
        "## = self.\n"
    )
    return "\n".join(lines) + legend


def render_png(path: Path) -> bool:
    try:
        import matplotlib  # type: ignore

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        return False

    sectors, coupling = load_matrix()
    n = len(sectors)
    m = np.zeros((n, n))
    for i, a in enumerate(sectors):
        for j, b in enumerate(sectors):
            m[i, j] = 1.0 if a == b else coupling.get((a, b), 0.0)

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(m, cmap="YlOrRd", vmin=0, vmax=1)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(sectors, rotation=45, ha="right")
    ax.set_yticklabels(sectors)
    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{m[i, j]:.2f}", ha="center", va="center", fontsize=8)
    ax.set_title("Energy-Water-Food + Grid: interdependency heat map")
    fig.colorbar(im, ax=ax, label="coupling strength")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return True


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    text = render_text()
    print(text)
    (REPORTS / "interdependency_heatmap.txt").write_text(text)
    if render_png(REPORTS / "interdependency_heatmap.png"):
        print(f"\nPNG written to {REPORTS / 'interdependency_heatmap.png'}")
    else:
        print("\n(matplotlib not installed - skipping PNG render)")


if __name__ == "__main__":
    main()
