from __future__ import annotations

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

from src.config import AGG_DB_NAME, HADOOP_OUTPUT_DIR, MONGO_PRIVATE_URI  # noqa: E402
from src.store import get_client  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK = "#0b0b0b"
INK_DIM = "#52514e"
GRID = "#e4e3df"
MILEAGE_ORDER = ["0-20k", "20-40k", "40-60k", "60-80k", "80-100k", "100-150k", "150-500k"]
MILEAGE_LABELS = ["0–20", "20–40", "40–60", "60–80", "80–100", "100–150", "150–500"]


def _fmt(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


def _style(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_DIM, labelsize=9)
    ax.grid(axis="x" if ax.get_xlabel() == "" else "y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def plot_body_type(db, out_dir) -> str:
    rows = sorted(db.agg_body_type.find(), key=lambda d: d["median_price"])
    labels = [f"{d['body_type']}  (n = {_fmt(d['n'])})" for d in rows]
    values = [d["median_price"] for d in rows]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    bars = ax.barh(labels, values, color=SERIES[0], height=0.62)
    for bar, value in zip(bars, values):
        ax.text(bar.get_width() + 400, bar.get_y() + bar.get_height() / 2, f"{_fmt(value)} $", va="center", fontsize=9, color=INK)
    ax.set_xlabel("Mediana ceny (USD)", color=INK_DIM, fontsize=9)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: _fmt(v)))
    ax.set_xlim(0, max(values) * 1.15)
    _style(ax)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    path = out_dir / "hadoop_nadwozie.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return str(path)


def plot_accidents(db, out_dir) -> str:
    docs = {(d["mileage_bin"], d["has_accidents"]): d for d in db.agg_mileage_accidents.find()}
    clean = [docs[(b, "false")]["median_price"] for b in MILEAGE_ORDER]
    crashed = [docs[(b, "true")]["median_price"] for b in MILEAGE_ORDER]
    xs = range(len(MILEAGE_ORDER))
    width = 0.38
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.bar([x - width / 2 - 0.01 for x in xs], clean, width, color=SERIES[0], label="bez wypadku")
    ax.bar([x + width / 2 + 0.01 for x in xs], crashed, width, color=SERIES[1], label="po wypadku")
    for x, a, b in zip(xs, clean, crashed):
        ax.text(x, max(a, b) + 700, f"−{(1 - b / a) * 100:.0f}%", ha="center", fontsize=9, color=INK)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(MILEAGE_LABELS)
    ax.set_xlabel("Przebieg (tys. mil)", color=INK_DIM, fontsize=9)
    ax.set_ylabel("Mediana ceny (USD)", color=INK_DIM, fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: _fmt(v)))
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    _style(ax)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    path = out_dir / "hadoop_wypadki.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return str(path)


def plot_makes(db, out_dir, top: int = 5, first_year: int = 2005, last_year: int = 2020, min_n: int = 30) -> str:
    totals: dict[str, int] = {}
    for d in db.agg_make_year.find():
        totals[d["make_name"]] = totals.get(d["make_name"], 0) + d["n"]
    makes = sorted(totals, key=totals.get, reverse=True)[:top]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ends = []
    for color, make in zip(SERIES, makes):
        points = sorted(
            (d["year"], d["mean_price"])
            for d in db.agg_make_year.find({"make_name": make, "year": {"$gte": first_year, "$lte": last_year}, "n": {"$gte": min_n}})
        )
        years = [p[0] for p in points]
        prices = [p[1] for p in points]
        ax.plot(years, prices, color=color, linewidth=2, marker="o", markersize=4)
        ends.append([prices[-1], years[-1], make])
    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 1500)
    for y, x, make in ends:
        ax.text(x + 0.3, y, make, color=INK, fontsize=9, va="center")
    ax.set_xlabel("Rocznik", color=INK_DIM, fontsize=9)
    ax.set_ylabel("Średnia cena (USD)", color=INK_DIM, fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: _fmt(v)))
    ax.set_xlim(first_year - 0.5, last_year + 2.2)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend(makes, frameon=False, fontsize=9, loc="upper left")
    _style(ax)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    path = out_dir / "hadoop_marki.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return str(path)


def main() -> None:
    argparse.ArgumentParser(description="Wykresy z agregatów Hadoopa zapisanych w MongoDB (used_cars_agg).").parse_args()
    client = get_client(MONGO_PRIVATE_URI)
    try:
        db = client[AGG_DB_NAME]
        if db.agg_body_type.count_documents({}) == 0:
            raise SystemExit("Brak agregatów w Mongo. Najpierw: python -m src.load_hadoop_results")
        HADOOP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        for path in (plot_body_type(db, HADOOP_OUTPUT_DIR), plot_accidents(db, HADOOP_OUTPUT_DIR), plot_makes(db, HADOOP_OUTPUT_DIR)):
            print(f"Zapisano {path}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
