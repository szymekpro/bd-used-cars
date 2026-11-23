from __future__ import annotations

from datetime import datetime

from src.config import PL_MAX_MILEAGE_KM, PL_MAX_PRICE, PL_MIN_PRICE, PL_MIN_YEAR


def _voivodeship(location: str | None) -> str | None:
    if not location:
        return None
    if "granic" in location.lower():
        return "zagranica"
    if "(" not in location or not location.endswith(")"):
        return None
    return location[location.rindex("(") + 1 : -1]


def _city(location: str | None) -> str | None:
    if not location or "(" not in location or "granic" in location.lower():
        return None
    return location[: location.rindex("(")].strip()


def _in_range(value, low, high) -> bool:
    return value is not None and low <= value <= high


def clean_otomoto_offers(records: list[dict], scraped_at: datetime) -> tuple[list[dict], dict]:
    scrape_year = scraped_at.year
    stats = {
        "rows_in": len(records),
        "dropped_no_id": 0,
        "dropped_duplicate_id": 0,
        "price_missing": 0,
        "price_out_of_range": 0,
        "year_out_of_range": 0,
        "mileage_out_of_range": 0,
    }
    seen: set[int] = set()
    out: list[dict] = []
    for rec in records:
        try:
            listing_id = int(rec.get("offer_id"))
        except (TypeError, ValueError):
            stats["dropped_no_id"] += 1
            continue
        if listing_id in seen:
            stats["dropped_duplicate_id"] += 1
            continue
        seen.add(listing_id)

        price = rec.get("price_pln")
        if price is None:
            stats["price_missing"] += 1
        elif not _in_range(price, PL_MIN_PRICE, PL_MAX_PRICE):
            stats["price_out_of_range"] += 1
            price = None

        year = rec.get("year")
        if year is not None and not _in_range(year, PL_MIN_YEAR, scrape_year):
            stats["year_out_of_range"] += 1
            year = None

        mileage = rec.get("mileage_km")
        if mileage is not None and not _in_range(mileage, 0, PL_MAX_MILEAGE_KM):
            stats["mileage_out_of_range"] += 1
            mileage = None

        seller = rec.get("seller_type")
        location = rec.get("location")
        out.append(
            {
                "listing_id": listing_id,
                "price": price,
                "year": year,
                "age_years": scrape_year - year if year is not None else None,
                "mileage": mileage,
                "make_name": rec.get("brand"),
                "model_name": rec.get("model"),
                "body_type": rec.get("body_type"),
                "fuel_type": rec.get("fuel_type"),
                "city": _city(location),
                "transmission": rec.get("gearbox"),
                "horsepower": rec.get("horsepower"),
                "engine_displacement": rec.get("engine_cm3"),
                "voivodeship": _voivodeship(location),
                "seller_type": seller,
                "is_pro": bool(rec.get("is_pro")),
                "url": rec.get("url"),
                "title": rec.get("title"),
                "scraped_at": scraped_at,
            }
        )
    stats["rows_kept"] = len(out)
    return out, stats
