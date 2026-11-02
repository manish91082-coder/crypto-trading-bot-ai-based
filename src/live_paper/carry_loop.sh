#!/bin/bash
# T2-CARRY runner (2026-11-02): forward_carry.py 5 minutes after every hour close. A missed hour is harmless, the next run recomputes from public history.
cd "$(dirname "$0")/../.."
while true; do
  m=$(date -u +%M)
  if [ "$m" = "05" ]; then
    PYTHONIOENCODING=utf-8 python src/live_paper/forward_carry.py 2>&1 | grep -E "T2-CARRY|Traceback|Error|ABORT"
    sleep 60
  fi
  sleep 20
done
