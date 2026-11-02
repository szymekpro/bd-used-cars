from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.analyze import run_analyses
from src.clean import clean_chunk
from src.config import CHUNK_SIZE, DEFAULT_MAX_ROWS, MINI_CSV, OUTPUT_DIR, RAW_CSV
from src.store import upsert_listings


def resolve_input(path: str | None) -> Path:
    if path:
        return Path(path)
    if RAW_CSV.exists():
        return RAW_CSV
    return MINI_CSV


def load_clean(path: Path, max_rows: int, chunk_size: int) -> tuple[pd.DataFrame, dict]:
    totals = {"rows_read": 0, "dropped_no_id": 0, "dropped_bad_price": 0}
    frames: list[pd.DataFrame] = []
    seen = 0
    reader = pd.read_csv(path, dtype=str, chunksize=chunk_size)
    for chunk in reader:
        if seen >= max_rows:
            break
        chunk = chunk.iloc[: max_rows - seen]
        seen += len(chunk)
        cleaned, stats = clean_chunk(chunk)
        for key in totals:
            totals[key] += stats[key]
        if len(cleaned):
            frames.append(cleaned)
    if not frames:
        raise SystemExit(f"Po czyszczeniu nie zostało żadnego wiersza: {path}")
    df = pd.concat(frames, ignore_index=True)
    before = len(df)
    df = df.drop_duplicates("listing_id", keep="last").reset_index(drop=True)
    totals["dropped_duplicate_id"] = before - len(df)
    totals["rows_kept"] = int(len(df))
    totals["source"] = str(path)
    return df, totals


def _usd(value, _pos):
    return f"{int(value):,}".replace(",", " ")


def save_plots(df: pd.DataFrame, out_dir: Path) -> list[str]:
    paths = []
    price = df["price"]
    cap = float(price.quantile(0.99))
    shown = price[price <= cap]
    hidden = int((price > cap).sum())
    median = float(price.median())
    mean = float(price.mean())

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(shown, bins=40, color="#2c5f8a", edgecolor="white")
    ax.axvline(median, color="#c47b2b", linewidth=2, label=f"mediana {_usd(median, None)}")
    ax.axvline(mean, color="#1f4e3d", linewidth=2, linestyle="--", label=f"średnia {_usd(mean, None)}")
    ax.set_title(f"Rozkład ceny (oś do 99. percentyla, {hidden} droższych aut poza wykresem)")
    ax.set_xlabel("Cena (USD)")
    ax.set_ylabel("Liczba ogłoszeń")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_usd))
    ax.legend()
    fig.tight_layout()
    hist = out_dir / "cena_histogram.png"
    fig.savefig(hist, dpi=120)
    plt.close(fig)
    paths.append(str(hist))

    body = (
        df.dropna(subset=["body_type"])
        .groupby("body_type")["price"]
        .agg(n="size", median="median")
        .sort_values("median", ascending=True)
    )
    if len(body):
        labels = [f"{name}  (n={int(n)})" for name, n in zip(body.index, body["n"])]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(labels, body["median"], color="#c47b2b")
        ax.set_title("Mediana ceny wg typu nadwozia")
        ax.set_xlabel("Mediana ceny (USD)")
        ax.xaxis.set_major_formatter(plt.FuncFormatter(_usd))
        fig.tight_layout()
        bars = out_dir / "cena_nadwozie.png"
        fig.savefig(bars, dpi=120)
        plt.close(fig)
        paths.append(str(bars))

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    aged = df.dropna(subset=["age_years"])
    age_stats = aged.groupby("age_years")["price"].agg(n="size", median="median")
    age_stats = age_stats[age_stats["n"] >= 30]
    axes[0].plot(age_stats.index, age_stats["median"], marker="o", color="#2c5f8a")
    axes[0].set_title("Mediana ceny wg wieku")
    axes[0].set_xlabel("Wiek auta (lata od 2020)")
    axes[0].set_ylabel("Mediana ceny (USD)")
    axes[0].yaxis.set_major_formatter(plt.FuncFormatter(_usd))

    driven = df.dropna(subset=["mileage"]).copy()
    mile_labels = ["0–20 tys.", "20–40 tys.", "40–60 tys.", "60–80 tys.", "80–100 tys.", "100–150 tys.", "150–500 tys."]
    driven["mileage_bin"] = pd.cut(
        driven["mileage"],
        bins=[0, 20_000, 40_000, 60_000, 80_000, 100_000, 150_000, 500_000],
        labels=mile_labels,
    )
    mile_med = driven.groupby("mileage_bin", observed=True)["price"].median()
    axes[1].bar(range(len(mile_med)), mile_med.values, color="#2c5f8a")
    axes[1].set_xticks(range(len(mile_med)))
    axes[1].set_xticklabels(list(mile_med.index), rotation=30, ha="right")
    axes[1].set_title("Mediana ceny wg przebiegu")
    axes[1].set_xlabel("Przebieg (mile)")
    axes[1].set_ylabel("Mediana ceny (USD)")
    axes[1].yaxis.set_major_formatter(plt.FuncFormatter(_usd))
    fig.tight_layout()
    usage = out_dir / "cena_a_uzycie.png"
    fig.savefig(usage, dpi=120)
    plt.close(fig)
    paths.append(str(usage))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="MVP: próbka ogłoszeń aut używanych")
    parser.add_argument("--input", help="Ścieżka do CSV. Domyślnie data/real, a jak go nie ma — mini próbka.")
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument("--skip-mongo", action="store_true")
    args = parser.parse_args()

    path = resolve_input(args.input)
    if not path.exists():
        raise SystemExit(f"Nie ma pliku: {path}")

    df, clean_stats = load_clean(path, args.max_rows, args.chunk_size)
    analyses = run_analyses(df)
    mongo = {"ok": False, "skipped": True}
    if not args.skip_mongo:
        mongo = upsert_listings(df)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sample_path = OUTPUT_DIR / "sample_clean.csv"
    df.to_csv(sample_path, index=False)
    plots = save_plots(df, OUTPUT_DIR)
    if path.resolve() == MINI_CSV.resolve():
        note = "Mini próbka sprawdza tylko ścieżkę. Te liczby nie opisują rynku."
    else:
        note = (
            f"Pierwsze {clean_stats['rows_read']} wierszy prawdziwego CSV, "
            "nie cały zbiór (ok. 3 mln ogłoszeń)."
        )
    report = {
        "note": note,
        "cleaning": clean_stats,
        "mongo": mongo,
        "analyses": analyses,
        "files": {"sample": str(sample_path), "plots": plots},
    }
    report_path = OUTPUT_DIR / "statystyki.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    price = analyses["1_rozkład_ceny"]
    usage = analyses["2_cena_a_wiek_i_przebieg"]
    print(f"Źródło: {path}")
    print(
        f"Wiersze: wczytane {clean_stats['rows_read']}, "
        f"zostawione {clean_stats['rows_kept']}, "
        f"odrzucone bez id {clean_stats['dropped_no_id']}, "
        f"zła cena {clean_stats['dropped_bad_price']}, "
        f"duplikaty id {clean_stats['dropped_duplicate_id']}"
    )
    print(
        f"Cena USD: średnia {price['mean']}, mediana {price['median']}, "
        f"skośność {price['skew']}"
    )
    print(
        f"Korelacja cena–wiek r={usage['age_years']['pearson_r']} "
        f"(n={usage['age_years']['n']}), "
        f"cena–przebieg r={usage['mileage']['pearson_r']} "
        f"(n={usage['mileage']['n']})"
    )
    if mongo.get("ok"):
        print(
            f"Mongo: upsert nowych {mongo['upserted']}, "
            f"nadpisanych {mongo['matched']}, "
            f"dokumentów w kolekcji {mongo['documents']}"
        )
    elif mongo.get("skipped"):
        print("Mongo: pominięte (--skip-mongo)")
    else:
        print(f"Mongo niedostępne, analizy i tak zapisane. Powód: {mongo.get('error')}")
    print(f"Wynik: {report_path}")


if __name__ == "__main__":
    main()
