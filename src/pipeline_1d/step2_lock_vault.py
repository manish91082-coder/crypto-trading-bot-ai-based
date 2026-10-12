import sys
from pathlib import Path
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DATA_RAW_DIR, DATA_DIR, SYMBOLS

VAULT_DIR = DATA_DIR / "vault_holdout_2025_2026"
VAULT_DIR.mkdir(parents=True, exist_ok=True)

HOLDOUT_START = "2025-01-01"
HOLDOUT_END = "2026-09-30"

RESEARCH_END = "2024-12-31"

def lock_holdout_vault():
    print("=================================================================")
    print("STEP 2: ENFORCING BLIND HOLDOUT VAULT LOCK (2025-01 TO 2026-09)")
    print("Adversarial Anti-Overfitting Protocol: Law #3 Active")
    print("=================================================================")
    
    vault_manifest = []

    for symbol in SYMBOLS:
        raw_file = DATA_RAW_DIR / f"{symbol}_1d_Raw_5Years.csv"
        df = pd.read_csv(raw_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        # 1. Split Research Data vs Sealed Vault Data
        research_df = df[df['timestamp'] <= RESEARCH_END]
        vault_df = df[df['timestamp'] >= HOLDOUT_START]

        # 2. Save Sealed Vault
        vault_file = VAULT_DIR / f"{symbol}_1d_Vault_Holdout.csv"
        vault_df.to_csv(vault_file, index=False)

        # 3. Assertions
        assert len(vault_df) == 638, f"Expected 638 vault rows, got {len(vault_df)}"
        assert vault_df['timestamp'].min() == pd.to_datetime(HOLDOUT_START)
        assert vault_df['timestamp'].max() == pd.to_datetime(HOLDOUT_END)
        assert len(research_df) == 1188, f"Expected 1188 research rows, got {len(research_df)}"

        vault_manifest.append({
            'symbol': symbol,
            'research_rows': len(research_df),
            'research_range': f"{research_df['timestamp'].min().strftime('%Y-%m-%d')} to {research_df['timestamp'].max().strftime('%Y-%m-%d')}",
            'vault_rows': len(vault_df),
            'vault_range': f"{vault_df['timestamp'].min().strftime('%Y-%m-%d')} to {vault_df['timestamp'].max().strftime('%Y-%m-%d')}",
            'vault_file': vault_file.name
        })
        print(f"[*] Locked Vault for {symbol}: {len(vault_df)} candles sealed ({HOLDOUT_START} to {HOLDOUT_END})")

    # Save Vault Manifest
    pd.DataFrame(vault_manifest).to_csv(VAULT_DIR / "VAULT_MANIFEST.csv", index=False)
    print("\n=================================================================")
    print(f"VAULT SEALED: All 10 Coins ({638 * len(SYMBOLS)} Total Candles) Locked in '{VAULT_DIR.name}'")
    print("=================================================================")

if __name__ == '__main__':
    lock_holdout_vault()
