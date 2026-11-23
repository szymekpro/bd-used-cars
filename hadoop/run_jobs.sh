#!/usr/bin/env bash
set -euo pipefail
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."

SRC="${1:-sample}"
case "$SRC" in
  sample) INPUT=/data/sample/used_cars_sample.csv ;;
  full) INPUT=/data/used_cars/used_cars_data.csv ;;
  *) echo "usage: $0 [sample|full]" >&2; exit 1 ;;
esac

JAR=/opt/hadoop/share/hadoop/tools/lib/hadoop-streaming-3.3.6.jar

run_job() {
  local name="$1" mapper="$2" reducer="$3"
  echo "=== job $name ($SRC) ==="
  docker compose exec -T namenode bash -c "
    set -e
    hdfs dfs -rm -r -f /results/$SRC/$name >/dev/null 2>&1 || true
    hadoop jar $JAR \
      -D mapreduce.job.name=$name-$SRC \
      -D mapreduce.job.reduces=1 \
      -files /jobs/common.py,/jobs/$mapper,/jobs/$reducer \
      -input $INPUT \
      -output /results/$SRC/$name \
      -mapper 'python3 $mapper' \
      -reducer 'python3 $reducer' 2>&1 | grep -E 'map [0-9]+%|completed|Failed|Parser|malformed|records|valid|bad_price|no_id|Job .* (completed|failed)|ERROR'
    mkdir -p /results_local/$SRC
    hdfs dfs -getmerge /results/$SRC/$name /results_local/$SRC/$name.tsv
    rm -f /results_local/$SRC/.*.crc
  "
}

run_job body_type mapper_body.py reducer_stats.py
run_job make_year mapper_make_year.py reducer_mean.py
run_job mileage_accidents mapper_mileage.py reducer_stats.py
ls -l output/hadoop/"$SRC"
