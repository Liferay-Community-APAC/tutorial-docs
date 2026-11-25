#!/usr/bin/env bash
# Classify one UTC day of webserver logs.
# Usage: run-classifier.sh YYYY-MM-DD LOG_DIR [OUT_DIR]
#   LOG_DIR holds that day's log files, e.g. the 24 hourly .log.gz files
#   written by the webserver log backup (S3 folder .../year=YYYY/month=MM/day=DD/).
# TM_SALT must be set in the environment (a random secret of 16+ characters,
# kept out of source control; rotate it to stop visitors being linked across periods).
set -euo pipefail
DAY="${1:?usage: run-classifier.sh YYYY-MM-DD LOG_DIR [OUT_DIR]}"
LOG_DIR="${2:?usage: run-classifier.sh YYYY-MM-DD LOG_DIR [OUT_DIR]}"
OUT_DIR="${3:-out/$DAY}"
: "${TM_SALT:?TM_SALT is not set}"
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 "$HERE/classify_traffic.py" --out "$OUT_DIR" --data "${DATA_DIR:-data}" --beacon --verify-dns \
  "$LOG_DIR/*${DAY}*.log*"
