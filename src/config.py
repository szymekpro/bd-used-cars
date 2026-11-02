from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "real" / "used_cars_data.csv"
MINI_CSV = ROOT / "data" / "samples" / "mini_listings.csv"
OUTPUT_DIR = ROOT / "output"

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "used_cars"
COLLECTION = "listings"

SNAPSHOT_YEAR = 2020

DEFAULT_MAX_ROWS = 20_000
CHUNK_SIZE = 10_000

MIN_PRICE = 1
MAX_PRICE = 1_000_000
MIN_YEAR = 1980
MAX_YEAR = 2021
MAX_MILEAGE = 500_000
