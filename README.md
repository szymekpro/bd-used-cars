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

## Security (TLS and login)

Both MongoDB containers require TLS and a username and password.

```powershell
bash scripts/gen_certs.sh
copy .env.example .env
```

Edit `.env` and set the passwords, then `docker compose up -d`. `certs/` and `.env` are git-ignored. If you have old volumes created without authentication, run `docker compose down -v` first.

## Hadoop and HDFS

`docker compose up -d` also starts HDFS (namenode, datanode) and YARN (resourcemanager, nodemanager) from `hadoop/Dockerfile`: Apache Hadoop 3.3.6 plus Python 3.6, which Hadoop Streaming needs.

- NameNode UI: http://localhost:9870
- YARN UI: http://localhost:8088

```powershell
bash scripts/hdfs_upload.sh
```

Puts `data/real/used_cars_data.csv` into `/data/used_cars/` (the full file) and the first 50000 lines into `/data/sample/` for quick job tests.

### Hadoop Streaming jobs

```powershell
bash hadoop/run_jobs.sh sample
bash hadoop/run_jobs.sh full
```

Three jobs (Python 3 mapper and reducer in `hadoop/jobs/`), each reads the CSV from HDFS and writes TSV into `output/hadoop/<sample|full>/`:

| Job | Key | Output columns |
|---|---|---|
| `body_type` | body type | n, median price, mean price |
| `make_year` | make and year (`Make\|Year`) | n, mean price |
| `mileage_accidents` | mileage bin and accident flag (`Bin\|true/false/unknown`) | n, median price, mean price |

`hadoop/jobs/common.py` joins multi-line quoted records, drops malformed ones and reports counters (`records`, `malformed`, `no_id`, `bad_price`, `valid`) to Hadoop. Prices outside 1 to 1 000 000 are dropped, as in the pandas cleaning. The jobs do not remove duplicate `listing_id`.

## Output

- `output/dataset/`: `statystyki.json`, `sample_clean.csv`, `cena_*.png`.
- `output/otomoto/`: `otomoto_statystyki.json`, `otomoto_*.png`, `otomoto_oferty.csv`, `otomoto_scrape.json`.