# Backup manifest: क्या कहाँ रखा है (2 नवंबर 2026)

Laptop बंद होने पर काम न खोए, इसलिए पूरा project दो जगह रखा गया है।

| जगह | क्या है | पता |
|---|---|---|
| **Google Drive** (private) | पूरा folder, बिना कुछ छोड़े: code, सारा data, सारे logs, `archive/`, `.git`, `.env` | `gdrive:CRYPTO_TRADING_BOT_LAPTOP_FULL_BACKUP/` (नीचे देखें) |
| **GitHub** (public) | Code, reports, protocols, SHA locks, और 25 MB से छोटे evidence files | https://github.com/manish91082-coder/crypto-trading-bot-ai-based |

## Drive पर ढाँचा

| Folder | क्या है |
|---|---|
| `mirror/` | Code, reports, configs, `.env`: file-by-file, Drive पर सीधे खुलते हैं |
| `packed/` | `archive/`, `data/`, `logs/`, `.git`, `.claude` के हर sub-folder का एक `.tar` बंडल |

बंडल इसलिए बने क्योंकि Drive हर file पर लगभग 1 सेकंड लेता है, और data में दसियों हज़ार छोटी files हैं। File-by-file upload में दिनों लगते।

- हर बंडल का MD5 upload के दौरान निकाला जाता है और Drive के बताए MD5 से मिलाया जाता है।
- पूरी सूची `logs/backup_drive/packs_manifest.tsv` में है, जिसमें नाम, source, bytes, दोनों MD5 और status दर्ज हैं।
- बिना बदला folder अगली बार दोबारा नहीं भेजा जाता।
- Script: `src/tools/backup_drive.sh`।

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

**पूरा restore (Drive से):** पहले light files लाएँ:
```bash
rclone copy "gdrive:CRYPTO_TRADING_BOT_LAPTOP_FULL_BACKUP/mirror" "/e/crypto trading bot ai based 9 oct 2026"
```
फिर बंडल लाएँ:
```bash
rclone copy "gdrive:CRYPTO_TRADING_BOT_LAPTOP_FULL_BACKUP/packed" /e/restore_packs
```
फिर हर बंडल को project folder में खोलें:
```bash
for f in /e/restore_packs/*.tar; do tar -xf "$f" -C "/e/crypto trading bot ai based 9 oct 2026"; done
```

**सिर्फ़ code (GitHub से):**
```bash
git clone https://github.com/manish91082-coder/crypto-trading-bot-ai-based.git
```
इसके बाद `data/`, बड़े logs और `.env` Drive से लाएँ।

**Backup ताज़ा करना (laptop चालू होने पर):**
```bash
bash src/tools/backup_drive.sh
```
यह Drive पर कुछ delete नहीं करता। सिर्फ़ नई या बदली files और बदले हुए बंडल भेजता है।

## जाँच

- **बंडल:** हर `.tar` का local MD5 और Drive का MD5 `packs_manifest.tsv` में साथ-साथ दर्ज हैं। Status `OK` तभी लिखा जाता है जब दोनों बराबर हों।
- **mirror/:** `rclone check --one-way` से हर file का MD5 Drive से मिलाया जाता है।
- **चलते logs:** `OK_FILES_CHANGED_DURING_READ` का मतलब है कि पढ़ते समय कोई live log (जैसे desk या T2) बढ़ गया। बंडल फिर भी पूरा और सही है, और अगली run नया हिस्सा भेज देगी।
