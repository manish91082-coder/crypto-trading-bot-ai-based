#!/bin/bash
# FWD-R2 runner (2026-10-29): runs forward_r2.py 2 minutes after every 15m bar close (the 8h / 1d strategies are re-checked each time too)
cd "$(dirname "$0")/../.."
while true; do
  m=$(date -u +%M); s=$(date -u +%S)
  if [ $((10#$m % 15)) -eq 2 ]; then
    PYTHONIOENCODING=utf-8 python src/live_paper/forward_r2.py 2>&1 | grep -E "FWD-R2| SA| SB| SC|Traceback|Error" 
    sleep 60
  fi
  sleep 20
done
