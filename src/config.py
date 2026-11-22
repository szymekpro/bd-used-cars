from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "real" / "used_cars_data.csv"
MINI_CSV = ROOT / "data" / "samples" / "mini_listings.csv"
OUTPUT_DIR = ROOT / "output"
DATASET_OUTPUT_DIR = OUTPUT_DIR / "dataset"
OTOMOTO_OUTPUT_DIR = OUTPUT_DIR / "otomoto"
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "used_cars"
COLLECTION = "listings"

SNAPSHOT_YEAR = 2020

DEFAULT_MAX_ROWS_DATASET = 20_000
DEFAULT_MAX_ROWS_OTOMOTO = None  # None = wszystkie oferty z bazy
CHUNK_SIZE = 10_000

MIN_PRICE = 1
MAX_PRICE = 1_000_000
MIN_YEAR = 1980
MAX_YEAR = 2021
MAX_MILEAGE = 500_000

MONGO_PRIVATE_URI = "mongodb://localhost:27018"
OTOMOTO_DB_NAME = "otomoto"
OTOMOTO_COLLECTION = "offers"
OTOMOTO_BASE_URL = "https://www.otomoto.pl"
OTOMOTO_LIST_PATH = "/osobowe"
OTOMOTO_USER_AGENT = "BigDataStudentProject/1.0"
OTOMOTO_DEFAULT_DELAY_SECONDS = 10.0
SCRAPE_TIMEOUT_SECONDS = 30

PL_MIN_PRICE = 1_000
PL_MAX_PRICE = 2_000_000
PL_MIN_YEAR = 1980
PL_MAX_MILEAGE_KM = 1_000_000
