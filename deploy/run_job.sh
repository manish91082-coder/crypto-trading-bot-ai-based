#!/usr/bin/env bash
# cron wrapper: runs one job with the project venv, logs start / end / exit code to logs/cron_status/<job>.csv
# usage: run_job.sh <job_name> <script relative to project root> [args...]
set -u
ROOT="/opt/cryptobot"
JOB="$1"; shift
SCRIPT="$1"; shift
mkdir -p "$ROOT/logs/cron_status"
[ -f "$ROOT/.env" ] && set -a && . "$ROOT/.env" && set +a          # keys entered by the user on the VM (chmod 600)
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
cd "$ROOT" && "$ROOT/venv/bin/python" "$SCRIPT" "$@" >> "$ROOT/logs/cron_status/${JOB}.out" 2>&1
RC=$?
END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
F="$ROOT/logs/cron_status/${JOB}.csv"
[ -f "$F" ] || echo "start_utc,end_utc,exit_code" > "$F"
echo "$START,$END,$RC" >> "$F"
exit $RC
