from __future__ import annotations

import pandas as pd

from src.config import MAX_MILEAGE, MAX_PRICE, MAX_YEAR, MIN_PRICE, MIN_YEAR, SNAPSHOT_YEAR

TEXT_COLS = [
    "vin",
    "make_name",
    "model_name",
    "body_type",
    "fuel_type",
    "city",
    "transmission",
    "listed_date",
]
BOOL_COLS = ["franchise_dealer", "frame_damaged", "has_accidents", "is_cpo"]
NUMBER_COLS = [
    "year",
    "mileage",
    "daysonmarket",
    "horsepower",
    "engine_displacement",
    "city_fuel_economy",
    "highway_fuel_economy",
]


def _series(df: pd.DataFrame, name: str) -> pd.Series:
    if name not in df.columns:
        return pd.Series(pd.NA, index=df.index, dtype="object")
    return df[name]


def _blank_to_na(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    text = text.replace({"": pd.NA, "--": pd.NA, "nan": pd.NA, "None": pd.NA, "null": pd.NA})
    return text


def _to_number(series: pd.Series) -> pd.Series:
    text = _blank_to_na(series)
    extracted = text.str.extract(r"([-+]?\d+(?:\.\d+)?)", expand=False)
    return pd.to_numeric(extracted, errors="coerce")


def _to_bool(series: pd.Series) -> pd.Series:
    text = _blank_to_na(series).str.lower()
    mapped = text.map({"true": True, "false": False, "1": True, "0": False})
    return mapped.astype("boolean")


COLUMN_ORDER = [
    "listing_id",
    "price",
    "year",
    "age_years",
    "mileage",
    "make_name",
    "model_name",
    "body_type",
    "fuel_type",
    "city",
    "daysonmarket",
    "horsepower",
    "franchise_dealer",
    "frame_damaged",
    "has_accidents",
    "is_cpo",
    "vin",
    "transmission",
    "listed_date",
    "engine_displacement",
    "city_fuel_economy",
    "highway_fuel_economy",
    "back_legroom_in",
]


def clean_dataset_chunk(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    stats = {
        "rows_read": int(len(df)),
        "dropped_no_id": 0,
        "dropped_bad_price": 0,
    }
    work = pd.DataFrame(index=df.index)
    work["listing_id"] = _to_number(_series(df, "listing_id"))
    missing_id = work["listing_id"].isna()
    stats["dropped_no_id"] = int(missing_id.sum())
    work = work.loc[~missing_id].copy()
    src = df.loc[work.index]
    work["listing_id"] = work["listing_id"].astype("int64")

    work["price"] = _to_number(_series(src, "price"))
    bad_price = work["price"].isna() | (work["price"] < MIN_PRICE) | (work["price"] > MAX_PRICE)
    stats["dropped_bad_price"] = int(bad_price.sum())
    work = work.loc[~bad_price].copy()
    src = src.loc[work.index]

    for name in TEXT_COLS:
        work[name] = _blank_to_na(_series(src, name))

    for name in NUMBER_COLS:
        work[name] = _to_number(_series(src, name))

    for name in BOOL_COLS:
        work[name] = _to_bool(_series(src, name))

    work.loc[(work["year"] < MIN_YEAR) | (work["year"] > MAX_YEAR), "year"] = pd.NA
    work.loc[(work["mileage"] < 0) | (work["mileage"] > MAX_MILEAGE), "mileage"] = pd.NA
    work["age_years"] = (SNAPSHOT_YEAR - work["year"]).clip(lower=0)

    legroom = _to_number(_series(src, "back_legroom"))
    work["back_legroom_in"] = legroom

    work["make_name"] = work["make_name"].str.replace(r"\s+", " ", regex=True)
    work = work[COLUMN_ORDER]
    return work.reset_index(drop=True), stats
