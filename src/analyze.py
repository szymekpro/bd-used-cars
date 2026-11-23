from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
from pymongo.errors import PyMongoError

from src.config import OTOMOTO_OUTPUT_DIR
from src.plots import age_mileage, group_bar, price_histogram, price_vs_horsepower
from src.store import read_otomoto

OTOMOTO_UNIT = "PLN"


def _round(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), 2)


def price_distribution(df: pd.DataFrame) -> dict:
    price = df["price"]
    return {
        "n": int(price.shape[0]),
        "mean": _round(price.mean()),
        "median": _round(price.median()),
        "std": _round(price.std(ddof=1)) if len(price) > 1 else None,
        "min": _round(price.min()),
        "max": _round(price.max()),
        "skew": _round(price.skew()) if len(price) > 2 else None,
    }


def price_vs_usage(df: pd.DataFrame) -> dict:
    out = {}
    for col, label in (("age_years", "age_years"), ("mileage", "mileage")):
        pair = df[["price", col]].dropna()
        corr = pair["price"].corr(pair[col]) if len(pair) > 2 else float("nan")
        out[label] = {"n": int(len(pair)), "pearson_r": _round(corr)}
    return out


def price_by_body(df: pd.DataFrame) -> list[dict]:
    grouped = (
        df.dropna(subset=["body_type"])
        .groupby("body_type", dropna=True)["price"]
        .agg(n="size", median="median", mean="mean")
        .sort_values("n", ascending=False)
        .reset_index()
    )
    rows = []
    for row in grouped.itertuples(index=False):
        rows.append(
            {
                "body_type": row.body_type,
                "n": int(row.n),
                "median_price": _round(row.median),
                "mean_price": _round(row.mean),
            }
        )
    return rows


def price_by_group(df: pd.DataFrame, column: str, min_n: int = 1) -> list[dict]:
    grouped = (
        df.dropna(subset=[column, "price"])
        .groupby(column)["price"]
        .agg(n="size", median="median", mean="mean")
        .reset_index()
    )
    grouped = grouped[grouped["n"] >= min_n].sort_values("n", ascending=False)
    return [
        {
            column: str(row[column]),
            "n": int(row["n"]),
            "median_price": _round(row["median"]),
            "mean_price": _round(row["mean"]),
        }
        for _, row in grouped.iterrows()
    ]


def price_vs_numeric(df: pd.DataFrame, column: str) -> dict:
    pair = df[["price", column]].dropna()
    corr = pair["price"].corr(pair[column]) if len(pair) > 2 else float("nan")
    return {"n": int(len(pair)), "pearson_r": _round(corr)}


def analyze_dataset(df: pd.DataFrame) -> dict:
    return {
        "1_rozkład_ceny": price_distribution(df),
        "2_cena_a_wiek_i_przebieg": price_vs_usage(df),
        "3_cena_wg_nadwozia": price_by_body(df),
        "4_cena_wg_paliwa": price_by_group(df, "fuel_type"),
        "5_cena_vs_moc": price_vs_numeric(df, "horsepower"),
    }


def run_otomoto(out_dir: Path = OTOMOTO_OUTPUT_DIR, max_rows: int | None = None, skip_mongo: bool = False) -> dict:
    if skip_mongo:
        return {"ok": False, "skipped": True}
    try:
        df = read_otomoto(max_rows)
    except PyMongoError as exc:
        return {"ok": False, "error": f"brak połączenia z bazą otomoto ({exc.__class__.__name__}), uruchom: docker compose up -d"}
    if df.empty:
        return {"ok": False, "error": "baza otomoto jest pusta, najpierw uruchom: python -m src.scrape_otomoto"}

    out_dir.mkdir(parents=True, exist_ok=True)
    analyses = {
        "1_rozkład_ceny_pln": price_distribution(df),
        "2_cena_a_wiek_i_przebieg": price_vs_usage(df),
        "3_cena_wg_paliwa": price_by_group(df, "fuel_type"),
        "4_cena_wg_województwa": price_by_group(df, "voivodeship", min_n=10),
        "5_cena_vs_moc": price_vs_numeric(df, "horsepower"),
    }
    plots = [
        price_histogram(df, out_dir / "otomoto_cena_histogram.png", OTOMOTO_UNIT),
        age_mileage(df, out_dir / "otomoto_cena_a_uzycie.png", OTOMOTO_UNIT),
        group_bar(df, "fuel_type", out_dir / "otomoto_cena_paliwo.png", OTOMOTO_UNIT, "Mediana ceny wg paliwa"),
        group_bar(
            df,
            "voivodeship",
            out_dir / "otomoto_cena_wojewodztwo.png",
            OTOMOTO_UNIT,
            "Mediana ceny wg województwa (min. 10 ofert)",
            min_n=10,
        ),
        price_vs_horsepower(df, out_dir / "otomoto_cena_moc.png", OTOMOTO_UNIT),
    ]
    report = {
        "source": "MongoDB (baza prywatna) otomoto.offers",
        "n_documents": int(len(df)),
        "analyses": analyses,
        "files": {"plots": [p for p in plots if p]},
    }
    (out_dir / "otomoto_statystyki.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return {
        "ok": True,
        "n": int(len(df)),
        "price": analyses["1_rozkład_ceny_pln"],
        "usage": analyses["2_cena_a_wiek_i_przebieg"],
    }
