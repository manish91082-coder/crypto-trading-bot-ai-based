#!/usr/bin/env bash
# Asks for the Binance DEMO futures API key and secret (hidden input) and writes /opt/cryptobot/.env (owner-only, 600).
# The values are never printed; only their lengths are shown. Run on the VM:  bash /opt/cryptobot/deploy/set_demo_keys.sh
set -euo pipefail
ENVF=/opt/cryptobot/.env
read -rsp "Binance DEMO futures API Key: " K; echo
read -rsp "Binance DEMO futures Secret Key: " S; echo
K="$(printf '%s' "$K" | tr -d '[:space:]')"; S="$(printf '%s' "$S" | tr -d '[:space:]')"
if [ ${#K} -ne 64 ] || [ ${#S} -ne 64 ]; then
  echo "ERROR: expected 64 characters each, got key ${#K}, secret ${#S}. Nothing written."; exit 1
fi
umask 177
printf 'BINANCE_FUT_DEMO_KEY=%s\nBINANCE_FUT_DEMO_SECRET=%s\n' "$K" "$S" > "$ENVF"
chmod 600 "$ENVF"
unset K S
echo "OK: $ENVF written (key 64 chars, secret 64 chars, permissions $(stat -c %a "$ENVF"))."
