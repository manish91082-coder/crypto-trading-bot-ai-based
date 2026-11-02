# Google Cloud पर ले जाने की runbook (16 अक्टूबर 2026)

**लक्ष्य:** पूरा daily system (Step 2, M4, Step 16, 16B, F4 + E11 shadow, N3, M10, F6 demo) PC की जगह cloud VM पर चले। इससे wake timers की ज़रूरत ख़त्म हो जाती है। कोई GitHub नहीं: files सीधे VM पर copy होंगी।

## तैयार files (`deploy/`)
| File | काम |
|---|---|
| `make_bundle.py` | Project का tar.gz और हर file का SHA256 manifest बनाता है। `archive/`, `.git`, `backups/`, `universe_hf`, `universe_pre2020_hf` छोड़ दिए जाते हैं (import graph से पक्का किया कि daily system को इनकी ज़रूरत नहीं)। आकार लगभग 5.6GB raw |
| `verify_bundle.py` | VM पर हर file का size और SHA256 manifest से मिलाता है |
| `setup_vm.sh` | Timezone Asia/Kolkata, Python 3.12 venv, pinned packages (`requirements.txt`), और `.env` (chmod 600) |
| `run_job.sh` | Cron wrapper: हर job को venv से चलाता है और start, end, exit code `logs/cron_status/<job>.csv` में लिखता है। M10 Linux पर यहीं से पढ़ता है |
| `crontab.txt` | वही समय (IST) जो Windows Task Scheduler में थे, साथ में F6 demo के लिए 10:30 और 11:00 |

## क्रम
1. **VM** (आपकी "हाँ" के बाद, क्योंकि इसमें पैसा लगता है)
   - Region **asia-south1 (Mumbai)**, क्योंकि Binance अमेरिकी IP addresses से API बंद रखता है।
   - Machine e2-medium (2 vCPU, 4GB), 50GB disk, Ubuntu 24.04 LTS।
   - नाम `cryptobot-1d-mumbai`।
2. **Binance तक पहुँच की जाँच (सबसे पहले):** VM से `api.binance.com`, `fapi.binance.com` और `demo-fapi.binance.com` के public ping/time endpoints। कोई भी block (HTTP 451 या 403) मिले तो region बदला जाएगा।
3. **Bundle:** PC पर उस दिन के सारे runs (11:00 IST) पूरे होने के बाद `python deploy/make_bundle.py E:\cryptobot_bundle`, फिर VM पर upload और `/opt/cryptobot` में unpack।
4. `bash deploy/setup_vm.sh`, फिर `venv/bin/python deploy/verify_bundle.py`। यह **BUNDLE PASS** होना चाहिए।
5. **Keys:** demo की keys आप VM पर `/opt/cryptobot/.env` में डालेंगे (`nano .env`)। मैं key कहीं नहीं लिखता।
6. **VM पर पूरे tests:**
   - `venv/bin/python src/audits/e2e_integration_test.py A B CD FULL16B`
   - `venv/bin/python src/audits/test_f6_mock_exchange.py`
   - `venv/bin/python src/audits/test_r1_engine_synthetic.py T8`

   ये सब PASS होने चाहिए। Windows और Linux का कोई फ़र्क (जैसे file name का case) यहीं पकड़ा जाएगा।
7. **Switch (एक दिन की सीमा पर, ताकि दो जगह ledger न बनें):**
   - (a) PC के `CryptoBot*` tasks **disable** होंगे। यह system setting है, इसलिए यह काम आपका है।
   - (b) VM पर `crontab deploy/crontab.txt` चलेगा।
   - (c) अगले दिन M10 status और सारे verifiers VM पर PASS होने चाहिए।
8. **PC की copy वैसी ही रखी जाएगी।** उसे मिटाना नहीं है, वह backup का काम करेगी।

## ध्यान रखने वाली बातें
- **90 दिन की hash-chain:** F4, 16B और shadow ledgers अपनी chain के साथ बिना बदलाव copy होते हैं। Switch वाले दिन दोनों मशीनें नहीं चलनी चाहिए।
- **पुराना VM `crypto-paper-trading-vm`** (us-central1, TERMINATED): आपके कहने पर अभी रहने दिया गया है।
- **`ghost-hunter-gcp`** (RUNNING) इस project का नहीं है, उसे छुआ नहीं जाएगा।
- **कीमत:** e2-medium का महीने का ख़र्च Google Cloud की pricing page पर देखकर पक्का करें। मैंने अभी इसे verify नहीं किया है।
