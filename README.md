# US used cars — MVP

Loads a CSV of US used-car listings ([Kaggle, Ananay Mital](https://www.kaggle.com/datasets/ananaymital/us-used-cars-dataset), ~3M rows, ~10 GB), cleans it in chunks, writes listings to local MongoDB, and computes three stats: price distribution, correlation of price with age and mileage, and median price by body type.

Without the Kaggle file the same pipeline runs on `data/samples/mini_listings.csv`. A repeated run upserts by `listing_id` and does not insert duplicates. Results go to `output/`.

## Run

From the project directory, in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
docker compose up -d
.\.venv\Scripts\python -m src
```

MongoDB is optional. If Docker is not running, stats and plots are still written.

Full dataset (Kaggle account and `kaggle.json`):

```powershell
kaggle datasets download -d ananaymital/us-used-cars-dataset -p data/real --unzip
.\.venv\Scripts\python -m src --max-rows 50000
```

## Options

| Flag | Default | Meaning |
|---|---|---|
| `--input PATH` | `data/real/used_cars_data.csv` if present, otherwise the mini sample | CSV to read |
| `--max-rows N` | 20000 | Stop after the first N rows |
| `--chunk-size N` | 10000 | Rows read per chunk |
| `--skip-mongo` | off | Skip the database write |

```powershell
.\.venv\Scripts\python -m src --input data/samples/mini_listings.csv --max-rows 1000 --skip-mongo
```
