# Used cars: dataset + otomoto.pl

Imports used-car listings into MongoDB, cleans them, and computes price statistics and charts.

| Source | Input | Database | Currency |
|---|---|---|---|
| dataset | Kaggle CSV or mini sample | local MongoDB, `localhost:27017`, `used_cars.listings` | USD |
| otomoto | scraped from otomoto.pl | private MongoDB, `localhost:27018`, `otomoto.offers` | PLN |

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
docker compose up -d
```

## Analysis

```powershell
.\.venv\Scripts\python -m src                                   # dataset + otomoto (if the database has offers)
.\.venv\Scripts\python -m src --max-rows-dataset 50000 --max-rows-otomoto 5000
.\.venv\Scripts\python -m src --skip-mongo                      # no database, so no otomoto analysis
```

| Option | Default | Applies to | Meaning |
|---|---|---|---|
| `--input PATH` | `data/real`, else mini sample | dataset | CSV file |
| `--max-rows-dataset N` | 20000 | dataset | first N CSV rows |
| `--max-rows-otomoto N` | all | otomoto | N offers read from the database |
| `--chunk-size N` | 10000 | dataset | CSV read chunk size |
| `--skip-mongo` | off | both | no database writes or reads; otomoto analysis skipped |

Defaults live in `src/config.py`.

Dependencies:
- The otomoto analysis reads the database, so scrape first: `python -m src.scrape_otomoto`. If the database is empty, the analysis is skipped with a message.
- `python -m src` never scrapes.

## Dataset (full)

```powershell
kaggle datasets download -d ananaymital/us-used-cars-dataset -p data/real --unzip
.\.venv\Scripts\python -m src --max-rows-dataset 50000
```

## Scrape otomoto.pl

```powershell
.\.venv\Scripts\python -m src.scrape_otomoto --target 20000 --delay 10 --batch 1000 --batch-pause 10
```

- Waits `--delay` seconds between pages and `--batch-pause` seconds every `--batch` offers.
- Stops on HTTP 403/429, after `--max-failures` (default 5) failed pages in a row, or on an empty page.
- Saves every page to MongoDB immediately. Re-runs update existing offers by `listing_id` and do not duplicate them.
- Rebuilds `output/otomoto_oferty.csv` from the database after each batch.

Other options: `--pages` (default 3300), `--skip-mongo`.

`franchise_dealer` is not collected: a company seller is not necessarily a dealer.

## Output

- `output/dataset/`: `statystyki.json`, `sample_clean.csv`, `cena_*.png`.
- `output/otomoto/`: `otomoto_statystyki.json`, `otomoto_*.png`, `otomoto_oferty.csv`, `otomoto_scrape.json`.