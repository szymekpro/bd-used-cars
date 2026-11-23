#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose exec -T namenode bash -c 'hdfs dfs -mkdir -p /data/used_cars /data/sample && hdfs dfs -put -f /input/used_cars_data.csv /data/used_cars/used_cars_data.csv'
docker compose exec -T namenode bash -c 'head -n 50000 /input/used_cars_data.csv | hdfs dfs -put -f - /data/sample/used_cars_sample.csv'
docker compose exec -T namenode hdfs dfs -ls -h /data/used_cars /data/sample
