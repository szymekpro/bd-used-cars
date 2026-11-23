from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

MILEAGE_BINS = [0, 20_000, 40_000, 60_000, 80_000, 100_000, 150_000, 200_000, 1_000_000]
MILEAGE_LABELS = ["0–20 tys.", "20–40 tys.", "40–60 tys.", "60–80 tys.", "80–100 tys.", "100–150 tys.", "150–200 tys.", "200 tys.+"]


def _fmt(value, _pos=None):
    return f"{int(value):,}".replace(",", " ")


def price_histogram(df: pd.DataFrame, path: Path, unit: str) -> str:
    price = df["price"].dropna()
    cap = float(price.quantile(0.99))
    shown = price[price <= cap]
    hidden = int((price > cap).sum())
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(shown, bins=40, color="#2c5f8a", edgecolor="white")
    ax.axvline(float(price.median()), color="#c47b2b", linewidth=2, label=f"mediana {_fmt(price.median())} {unit}")
    ax.axvline(float(price.mean()), color="#1f4e3d", linewidth=2, linestyle="--", label=f"średnia {_fmt(price.mean())} {unit}")
    ax.set_title(f"Rozkład ceny (oś do 99. percentyla, {hidden} droższych poza wykresem)")
    ax.set_xlabel(f"Cena ({unit})")
    ax.set_ylabel("Liczba ogłoszeń")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_fmt))
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return str(path)


def age_mileage(df: pd.DataFrame, path: Path, unit: str) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    aged = df.dropna(subset=["age_years", "price"])
    age_stats = aged.groupby("age_years")["price"].agg(n="size", median="median")
    age_stats = age_stats[age_stats["n"] >= 30]
    axes[0].plot(age_stats.index, age_stats["median"], marker="o", color="#2c5f8a")
    axes[0].set_title("Mediana ceny wg wieku")
    axes[0].set_xlabel("Wiek auta (lata)")
    axes[0].set_ylabel(f"Mediana ceny ({unit})")
    axes[0].yaxis.set_major_formatter(plt.FuncFormatter(_fmt))

    driven = df.dropna(subset=["mileage", "price"]).copy()
    driven["mileage_bin"] = pd.cut(driven["mileage"], bins=MILEAGE_BINS, labels=MILEAGE_LABELS)
    mile_med = driven.groupby("mileage_bin", observed=True)["price"].median()
    axes[1].bar(range(len(mile_med)), mile_med.values, color="#2c5f8a")
    axes[1].set_xticks(range(len(mile_med)))
    axes[1].set_xticklabels(list(mile_med.index), rotation=30, ha="right")
    axes[1].set_title("Mediana ceny wg przebiegu")
    axes[1].set_xlabel("Przebieg")
    axes[1].set_ylabel(f"Mediana ceny ({unit})")
    axes[1].yaxis.set_major_formatter(plt.FuncFormatter(_fmt))
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return str(path)


def group_bar(df: pd.DataFrame, column: str, path: Path, unit: str, title: str, min_n: int = 1, top: int | None = None) -> str | None:
    grouped = df.dropna(subset=[column, "price"]).groupby(column)["price"].agg(n="size", median="median")
    grouped = grouped[grouped["n"] >= min_n].sort_values("n", ascending=False)
    if top:
        grouped = grouped.head(top)
    if grouped.empty:
        return None
    grouped = grouped.sort_values("median")
    labels = [f"{name} (n={int(n)})" for name, n in zip(grouped.index, grouped["n"])]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(labels, grouped["median"], color="#c47b2b")
    ax.set_title(title)
    ax.set_xlabel(f"Mediana ceny ({unit})")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_fmt))
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return str(path)


def price_vs_horsepower(df: pd.DataFrame, path: Path, unit: str) -> str | None:
    pair = df[["price", "horsepower"]].dropna()
    if pair.empty:
        return None
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.scatter(pair["horsepower"], pair["price"], s=6, alpha=0.3, color="#2c5f8a")
    ax.set_title("Cena a moc silnika")
    ax.set_xlabel("Moc (KM)")
    ax.set_ylabel(f"Cena ({unit})")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_fmt))
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return str(path)
