#!/usr/bin/env bash
# One-time VM setup (Ubuntu 24.04 LTS, Python 3.12). Run as the normal user with sudo rights, after the bundle is in /opt/cryptobot.
set -euo pipefail
ROOT=/opt/cryptobot
sudo timedatectl set-timezone Asia/Kolkata
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip cron
python3 --version
cd "$ROOT"
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r deploy/requirements.txt
chmod +x deploy/run_job.sh
[ -f .env ] || { umask 177; printf 'BINANCE_FUT_DEMO_KEY=\nBINANCE_FUT_DEMO_SECRET=\n' > .env; }
echo "setup done. Next: user fills $ROOT/.env (nano .env), then: venv/bin/python deploy/verify_bundle.py"
