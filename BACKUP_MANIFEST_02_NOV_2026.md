# Backup manifest: क्या कहाँ रखा है (2 नवंबर 2026)

Laptop बंद होने पर काम न खोए, इसलिए पूरा project दो जगह रखा गया है।

| जगह | क्या है | पता |
|---|---|---|
| **Google Drive** (private) | पूरा folder, बिना कुछ छोड़े: code, सारा data, सारे logs, `archive/`, `.git`, `.env` | `gdrive:CRYPTO_TRADING_BOT_LAPTOP_FULL_BACKUP/crypto trading bot ai based 9 oct 2026` |
| **GitHub** (public) | Code, reports, protocols, SHA locks, और 25 MB से छोटे evidence files | https://github.com/manish91082-coder/crypto-trading-bot-ai-based |

## GitHub पर क्या नहीं है (सिर्फ़ Drive पर)

- `.env`: testnet keys हैं, इसलिए public repo में कभी नहीं।
- `archive/`: पुराना retired system।
- `data/`: market data (कई GB), जो public Binance/Bybit history से दोबारा भी निकल सकता है। पहले से tracked `data/raw/*_1d_Raw_5Years.csv` files repo में बनी रहती हैं।
- `logs/btc_alltf_2026_10_28/` (~27 GB) और `logs/btc_alltf_r2_2026_10_29/` (~5.3 GB)।
- 25 MB से बड़ी 26 files (prediction CSVs, parquet)। इनकी सूची `.gitignore` के आख़िरी हिस्से में है।
- `.claude/worktrees/` और `.claude/settings.local.json`।

GitHub 100 MB से बड़ी file नहीं लेता, और कई GB का public repo भी ठीक से नहीं चलता। इसलिए यह बँटवारा किया गया है।

## Secrets की जाँच (push से पहले)

- Push होने वाली 8,864 files में `.env` की असली values खोजी गईं: एक भी नहीं मिली।
- GitHub token, OpenAI key, Google key, Telegram bot token, private key और 64-अक्षर वाली exchange key के patterns भी खोजे गए। सिर्फ़ 2 false positive मिले ("risk-management" और "risk-parity" शब्द)।
- VM की demo keys VM की `.env` में हैं, laptop पर नहीं।

## GitHub history के बारे में

- Remote पर 12 अक्टूबर के 14 commits थे जो laptop पर नहीं थे (ChatGPT session के 1D fixes और `.github/workflows`)।
- उन्हें merge किया गया पर tree laptop वाला रखा गया (`git merge -s ours`)। मतलब वे commits history में सुरक्षित हैं, कुछ delete नहीं हुआ, पर current files laptop वाली हैं।
- इससे `.github/workflows` भी current tree से हट गए, इसलिए push पर कोई GitHub Action नहीं चलेगा।

## Restore कैसे करें

**पूरा restore (Drive से):**
```bash
rclone copy "gdrive:CRYPTO_TRADING_BOT_LAPTOP_FULL_BACKUP/crypto trading bot ai based 9 oct 2026" "/e/crypto trading bot ai based 9 oct 2026"
```

**सिर्फ़ code (GitHub से):**
```bash
git clone https://github.com/manish91082-coder/crypto-trading-bot-ai-based.git
```
इसके बाद `data/`, बड़े logs और `.env` Drive से लाएँ।

**Backup ताज़ा करना (laptop चालू होने पर):**
```bash
rclone copy "/e/crypto trading bot ai based 9 oct 2026" "gdrive:CRYPTO_TRADING_BOT_LAPTOP_FULL_BACKUP/crypto trading bot ai based 9 oct 2026" --exclude "__pycache__/**"
```
`rclone copy` Drive पर कुछ delete नहीं करता, सिर्फ़ नई या बदली files भेजता है।

## जाँच

Upload पूरा होने के बाद `rclone check --one-way` चलाया जाता है, जो हर file का MD5 Drive से मिलाता है। नतीजा `logs/backup_2026_11_02/` में रहता है।
