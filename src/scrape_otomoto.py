from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from urllib import robotparser

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.clean_otomoto import clean_otomoto_offers
from src.config import (
    OTOMOTO_BASE_URL,
    OTOMOTO_DEFAULT_DELAY_SECONDS,
    OTOMOTO_LIST_PATH,
    OTOMOTO_USER_AGENT,
    OTOMOTO_OUTPUT_DIR,
    SCRAPE_TIMEOUT_SECONDS,
)
from src.store import read_otomoto, upsert_otomoto

BLOCK_STATUSES = (403, 429)
DEFAULT_PAGES = 3300
DEFAULT_TARGET = 100_000
DEFAULT_BATCH = 1000
DEFAULT_BATCH_PAUSE = 180.0
DEFAULT_MAX_FAILURES = 5


def list_page_url(page: int) -> str:
    base = OTOMOTO_BASE_URL + OTOMOTO_LIST_PATH
    return base if page == 1 else f"{base}?page={page}"


def load_robots(session: requests.Session) -> robotparser.RobotFileParser:
    resp = session.get(OTOMOTO_BASE_URL + "/robots.txt", timeout=SCRAPE_TIMEOUT_SECONDS)
    resp.raise_for_status()
    rp = robotparser.RobotFileParser()
    rp.parse(resp.text.splitlines())
    return rp


def _digits(text: str | None) -> int | None:
    if not text:
        return None
    cleaned = re.sub(r"\D", "", text)
    return int(cleaned) if cleaned else None


def _seller(tokens: list[str]) -> str | None:
    if "Firma" in tokens:
        return "firma"
    if any(t.startswith("Prywatn") for t in tokens):
        return "prywatne"
    return None


def _location(tokens: list[str]) -> str | None:
    for token in tokens:
        if re.fullmatch(r".+\([^()]+\)", token) and len(token) < 80:
            return token
    return None


def _model_from_url(url: str, brand: str | None) -> str | None:
    slug = url.rsplit("/", 1)[-1].split("-ID")[0].lower()
    if not brand or not slug.startswith(brand.lower() + "-"):
        return None
    return " ".join(part.capitalize() for part in slug[len(brand) + 1 :].split("-") if part) or None


def parse_listing_page(html: str, page: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for art in soup.find_all("article"):
        offer_id = art.get("data-id")
        if not offer_id:
            continue
        link = art.find("a", href=re.compile(r"/osobowe/oferta/"))
        if link is None:
            continue

        params = {el["data-parameter"]: el.get_text(" ", strip=True) for el in art.find_all(attrs={"data-parameter": True})}
        tokens = list(art.stripped_strings)
        joined = " | ".join(tokens)
        price_match = re.search(r"(\d[\d\s\u00a0]*)\s*\|\s*PLN", joined)
        hp_match = re.search(r"\b(\d{2,4})\s*KM\b", joined)
        cm3_match = re.search(r"\b(\d{3,5})\s*cm3\b", joined)
        title_node = art.find(["h1", "h2"])
        title = title_node.get_text(" ", strip=True) if title_node else None
        brand = title.split()[0] if title else None
        href = link["href"].split("?")[0]
        url = href if href.startswith("http") else OTOMOTO_BASE_URL + href
        year = params.get("year")

        records.append(
            {
                "offer_id": offer_id,
                "url": url,
                "brand": brand,
                "model": _model_from_url(url, brand),
                "title": title,
                "year": int(year) if year and year.isdigit() else None,
                "mileage_km": _digits(params.get("mileage")),
                "fuel_type": params.get("fuel_type"),
                "body_type": None,
                "gearbox": params.get("gearbox"),
                "location": _location(tokens),
                "seller_type": _seller(tokens),
                "is_pro": "Wyróżnione" in tokens,
                "price_pln": _digits(price_match.group(1)) if price_match else None,
                "horsepower": int(hp_match.group(1)) if hp_match else None,
                "engine_cm3": int(cm3_match.group(1)) if cm3_match else None,
                "page": page,
            }
        )
    return records


def _export_csv(csv_path, mongo: dict, all_docs: list[dict]) -> str:
    export = read_otomoto() if mongo.get("ok") else pd.DataFrame(all_docs)
    try:
        export.to_csv(csv_path, index=False)
        return "zapisany"
    except PermissionError:
        return "ZABLOKOWANY (zamknij plik i uruchom ponownie)"


def run(args) -> dict:
    started = datetime.now(timezone.utc)
    csv_path = OTOMOTO_OUTPUT_DIR / "otomoto_oferty.csv"
    report_path = OTOMOTO_OUTPUT_DIR / "otomoto_scrape.json"
    OTOMOTO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": OTOMOTO_USER_AGENT, "Accept-Language": "pl-PL,pl;q=0.9"})
    robots = load_robots(session)

    scrape_stats = {"pages_requested": 0, "pages_failed": 0, "cards_seen": 0, "duplicates_in_run": 0, "stopped_reason": None}
    clean_totals: dict[str, int] = {}
    seen_ids: set[str] = set()
    new_total = updated_total = 0
    since_batch = 0
    consecutive_failures = 0
    mongo = {"ok": False, "skipped": True}
    all_docs: list[dict] = []

    for page in range(1, args.pages + 1):
        if len(seen_ids) >= args.target:
            scrape_stats["stopped_reason"] = f"osiągnięto cel {args.target} ofert"
            break

        url = list_page_url(page)
        if not robots.can_fetch(OTOMOTO_USER_AGENT, url):
            scrape_stats["stopped_reason"] = f"robots.txt zabrania: {url}"
            break
        try:
            resp = session.get(url, timeout=SCRAPE_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            resp = None
            print(f"Strona {page}: błąd połączenia ({exc.__class__.__name__}), pomijam", flush=True)
        scrape_stats["pages_requested"] += 1

        if resp is not None and resp.status_code in BLOCK_STATUSES:
            scrape_stats["stopped_reason"] = f"HTTP {resp.status_code} na stronie {page} (blokada), zatrzymano"
            print(scrape_stats["stopped_reason"], flush=True)
            break
        if resp is None or resp.status_code != 200:
            scrape_stats["pages_failed"] += 1
            consecutive_failures += 1
            print(f"Strona {page}: błąd pobierania ({consecutive_failures} z rzędu), pomijam", flush=True)
            if consecutive_failures >= args.max_failures:
                scrape_stats["stopped_reason"] = f"{consecutive_failures} nieudanych stron z rzędu, zatrzymano"
                print(scrape_stats["stopped_reason"], flush=True)
                break
            time.sleep(args.delay)
            continue
        consecutive_failures = 0

        offers = parse_listing_page(resp.text, page)
        if not offers:
            scrape_stats["stopped_reason"] = (
                f"strona {page} (HTTP 200) bez kart: możliwa blokada albo koniec listy, sprawdź ręcznie"
            )
            print(scrape_stats["stopped_reason"], flush=True)
            break

        fresh = []
        for offer in offers:
            scrape_stats["cards_seen"] += 1
            if offer["offer_id"] in seen_ids:
                scrape_stats["duplicates_in_run"] += 1
                continue
            seen_ids.add(offer["offer_id"])
            fresh.append(offer)

        cleaned, cstats = clean_otomoto_offers(fresh, scraped_at=started)
        for key, value in cstats.items():
            clean_totals[key] = clean_totals.get(key, 0) + value
        all_docs.extend(cleaned)

        if not args.skip_mongo and cleaned:
            result = upsert_otomoto(cleaned)
            if not result.get("ok"):
                mongo = result
                print(f"Baza otomoto niedostępna: {result.get('error')}", flush=True)
                break
            mongo = result
            new_total += result["upserted"]
            updated_total += result["matched"]

        since_batch += len(fresh)
        print(f"Strona {page}: {len(offers)} ofert, unikalnych w przebiegu {len(seen_ids)}", flush=True)

        if since_batch >= args.batch:
            since_batch = 0
            csv_status = _export_csv(csv_path, mongo, all_docs)
            print(f"-- paczka {args.batch} ofert: przerwa {args.batch_pause:.0f} s, CSV {csv_status}", flush=True)
            time.sleep(args.batch_pause)
        else:
            time.sleep(args.delay)

    csv_status = _export_csv(csv_path, mongo, all_docs)
    report = {
        "source": OTOMOTO_BASE_URL + OTOMOTO_LIST_PATH,
        "started_at": started.isoformat(),
        "delay_seconds": args.delay,
        "batch": args.batch,
        "batch_pause_seconds": args.batch_pause,
        "target": args.target,
        "scrape": scrape_stats,
        "cleaning": clean_totals,
        "mongo": {"new": new_total, "updated": updated_total, "ok": mongo.get("ok"), "documents": mongo.get("documents")},
        "unique_offers_this_run": len(seen_ids),
        "files": {"csv": str(csv_path), "csv_status": csv_status},
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Scraping ofert otomoto.pl -> baza otomoto (MongoDB) + CSV")
    parser.add_argument("--pages", type=int, default=DEFAULT_PAGES, help="Maksymalna liczba stron listingu")
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET, help="Zatrzymaj po tylu unikalnych ofertach")
    parser.add_argument("--delay", type=float, default=OTOMOTO_DEFAULT_DELAY_SECONDS, help="Odstęp między stronami [s]")
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH, help="Co tyle ofert robimy dłuższą przerwę")
    parser.add_argument("--batch-pause", type=float, default=DEFAULT_BATCH_PAUSE, help="Długość przerwy co paczkę [s]")
    parser.add_argument("--max-failures", type=int, default=DEFAULT_MAX_FAILURES, help="Zatrzymaj po tylu błędach z rzędu")
    parser.add_argument("--skip-mongo", action="store_true")
    args = parser.parse_args()

    report = run(args)
    scrape_stats = report["scrape"]
    print(
        f"Scraping: strony {scrape_stats['pages_requested']}, karty {scrape_stats['cards_seen']}, "
        f"unikalne oferty {report['unique_offers_this_run']}, duplikaty w przebiegu {scrape_stats['duplicates_in_run']}"
    )
    if scrape_stats["stopped_reason"]:
        print(f"Zatrzymano: {scrape_stats['stopped_reason']}")
    mongo = report["mongo"]
    if mongo.get("ok"):
        print(f"Baza otomoto: nowe {mongo['new']}, nadpisane {mongo['updated']}, dokumentów w kolekcji {mongo['documents']}")
    print(f"CSV {report['files']['csv']}: {report['files']['csv_status']}")


if __name__ == "__main__":
    main()
