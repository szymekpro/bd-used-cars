from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config import AGG_DB_NAME, HADOOP_OUTPUT_DIR
from src.store import upsert_aggregates


def _rows(path: Path, columns: int) -> list[list[str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != columns:
            raise SystemExit(f"Zły wiersz w {path.name}: {line!r}")
        rows.append(parts)
    return rows


def body_type_docs(path: Path) -> list[dict]:
    return [
        {
            "_id": key,
            "body_type": key,
            "n": int(n),
            "median_price": float(median),
            "mean_price": float(mean),
        }
        for key, n, median, mean in _rows(path, 4)
    ]


def make_year_docs(path: Path) -> list[dict]:
    docs = []
    for key, n, mean in _rows(path, 3):
        make, year = key.rsplit("|", 1)
        docs.append({"_id": key, "make_name": make, "year": int(year), "n": int(n), "mean_price": float(mean)})
    return docs


def mileage_accidents_docs(path: Path) -> list[dict]:
    docs = []
    for key, n, median, mean in _rows(path, 4):
        mileage_bin, accidents = key.split("|", 1)
        docs.append(
            {
                "_id": key,
                "mileage_bin": mileage_bin,
                "has_accidents": accidents,
                "n": int(n),
                "median_price": float(median),
                "mean_price": float(mean),
            }
        )
    return docs


JOBS = {
    "body_type": ("agg_body_type", body_type_docs),
    "make_year": ("agg_make_year", make_year_docs),
    "mileage_accidents": ("agg_mileage_accidents", mileage_accidents_docs),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Wczytuje wyniki jobów Hadoopa (TSV) do MongoDB jako agregaty.")
    parser.add_argument("--source", choices=["sample", "full"], default="full", help="Podkatalog output/hadoop z wynikami.")
    args = parser.parse_args()

    folder = HADOOP_OUTPUT_DIR / args.source
    report = {}
    failed = False
    for job, (collection, parse) in JOBS.items():
        path = folder / f"{job}.tsv"
        if not path.exists():
            raise SystemExit(f"Brak pliku {path}. Najpierw: bash hadoop/run_jobs.sh {args.source}")
        docs = parse(path)
        result = upsert_aggregates(collection, docs)
        report[collection] = {"rows": len(docs), **result}
        if not result.get("ok"):
            failed = True
            print(f"{collection}: błąd. {result.get('error')}")
            continue
        print(
            f"{AGG_DB_NAME}.{collection}: wczytane {len(docs)}, "
            f"nowych {result['upserted']}, nadpisanych {result['matched']}, "
            f"dokumentów w kolekcji {result['documents']}"
        )
    (folder / "mongo_load.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
