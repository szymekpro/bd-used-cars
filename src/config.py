import os
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "real" / "used_cars_data.csv"
MINI_CSV = ROOT / "data" / "samples" / "mini_listings.csv"
OUTPUT_DIR = ROOT / "output"
DATASET_OUTPUT_DIR = OUTPUT_DIR / "dataset"
OTOMOTO_OUTPUT_DIR = OUTPUT_DIR / "otomoto"
HADOOP_OUTPUT_DIR = OUTPUT_DIR / "hadoop"
CA_FILE = ROOT / "certs" / "ca.pem"


def _load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def _mongo_uri(port: int, user_var: str, password_var: str) -> str:
    user = os.environ.get(user_var, "")
    password = os.environ.get(password_var, "")
    if not user or not password:
        return f"mongodb://localhost:{port}"
    return f"mongodb://{quote_plus(user)}:{quote_plus(password)}@localhost:{port}/?authSource=admin"


_load_env()
MONGO_URI = _mongo_uri(27017, "MONGO_LOCAL_USER", "MONGO_LOCAL_PASSWORD")
MONGO_PRIVATE_URI = _mongo_uri(27018, "MONGO_PRIVATE_USER", "MONGO_PRIVATE_PASSWORD")
DB_NAME = "used_cars"
COLLECTION = "listings"

SNAPSHOT_YEAR = 2020

DEFAULT_MAX_ROWS_DATASET = 20_000
DEFAULT_MAX_ROWS_OTOMOTO = None
CHUNK_SIZE = 10_000

MIN_PRICE = 1
MAX_PRICE = 1_000_000
MIN_YEAR = 1980
MAX_YEAR = 2021
MAX_MILEAGE = 500_000

OTOMOTO_DB_NAME = "otomoto"
OTOMOTO_COLLECTION = "offers"
AGG_DB_NAME = "used_cars_agg"
OTOMOTO_BASE_URL = "https://www.otomoto.pl"
OTOMOTO_LIST_PATH = "/osobowe"
OTOMOTO_USER_AGENT = "BigDataStudentProject/1.0"
OTOMOTO_DEFAULT_DELAY_SECONDS = 10.0
SCRAPE_TIMEOUT_SECONDS = 30

PL_MIN_PRICE = 1_000
PL_MAX_PRICE = 2_000_000
PL_MIN_YEAR = 1980
PL_MAX_MILEAGE_KM = 1_000_000
