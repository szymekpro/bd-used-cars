from __future__ import annotations

import pandas as pd
from pymongo import MongoClient, ReplaceOne
from pymongo.errors import PyMongoError

from src.config import (
    CA_FILE,
    COLLECTION,
    DB_NAME,
    MONGO_PRIVATE_URI,
    MONGO_URI,
    OTOMOTO_COLLECTION,
    OTOMOTO_DB_NAME,
)


def get_client(uri: str) -> MongoClient:
    return MongoClient(uri, tls=True, tlsCAFile=str(CA_FILE), serverSelectionTimeoutMS=4000)


def _connection_error(target: str, exc: Exception) -> dict:
    return {
        "ok": False,
        "error": f"brak połączenia z MongoDB ({target}, {exc.__class__.__name__}): sprawdź docker compose ps, certs/ i plik .env",
    }


def _plain(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        value = value.item()
    return value


def _docs(df: pd.DataFrame) -> list[dict]:
    docs = []
    for row in df.to_dict(orient="records"):
        clean = {}
        for key, value in row.items():
            plain = _plain(value)
            if plain is not None:
                clean[key] = plain
        listing_id = int(clean["listing_id"])
        clean["_id"] = listing_id
        docs.append(clean)
    return docs


def _upsert_docs(docs: list[dict], uri: str, db_name: str, collection: str, target: str) -> dict:
    client = get_client(uri)
    try:
        client.admin.command("ping")
        col = client[db_name][collection]
        if not docs:
            return {"ok": True, "upserted": 0, "matched": 0, "documents": col.count_documents({})}
        ops = [ReplaceOne({"_id": doc["_id"]}, doc, upsert=True) for doc in docs]
        result = col.bulk_write(ops, ordered=False)
        return {
            "ok": True,
            "upserted": result.upserted_count,
            "matched": result.matched_count,
            "documents": col.count_documents({}),
        }
    except PyMongoError as exc:
        return _connection_error(target, exc)
    finally:
        client.close()


def upsert_listings(df: pd.DataFrame) -> dict:
    return _upsert_docs(_docs(df), MONGO_URI, DB_NAME, COLLECTION, "localhost:27017")


def upsert_otomoto(docs: list[dict]) -> dict:
    for doc in docs:
        doc["_id"] = doc["listing_id"]
    return _upsert_docs(docs, MONGO_PRIVATE_URI, OTOMOTO_DB_NAME, OTOMOTO_COLLECTION, "localhost:27018")


def read_otomoto(max_rows: int | None = None) -> pd.DataFrame:
    client = get_client(MONGO_PRIVATE_URI)
    try:
        client.admin.command("ping")
        rows = list(client[OTOMOTO_DB_NAME][OTOMOTO_COLLECTION].find({}, {"_id": 0}).limit(max_rows or 0))
    finally:
        client.close()
    return pd.DataFrame(rows)
