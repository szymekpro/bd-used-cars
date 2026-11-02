from __future__ import annotations

import math

import pandas as pd


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


def run_analyses(df: pd.DataFrame) -> dict:
    return {
        "1_rozkład_ceny": price_distribution(df),
        "2_cena_a_wiek_i_przebieg": price_vs_usage(df),
        "3_cena_wg_nadwozia": price_by_body(df),
    }
