# Forward gates का कैलेंडर (A3), 28 अक्टूबर 2026

**यह file क्या है:**
- हर चल रहे forward test का locked नियम, उसकी तारीख, और 28 अक्टूबर की ज़मीनी स्थिति।
- स्थिति VM से read-only snapshot (2026-10-28 08:50 UTC) में पढ़ी गई है।
- नियम उन्हीं की protocol files से लिए गए हैं, यहाँ कोई नया नियम नहीं बनाया गया।
- **कब पढ़ें:** हर हफ़्ते एक बार, और हर तारीख वाले दिन।
- **Version:** VM और laptop दोनों पर release **R-2026.10.28-3** (`deploy/RELEASES.md`)।

## तारीख के क्रम में

| तारीख (UTC) | Gate | Locked नियम | 28 अक्टूबर की स्थिति | Source |
|---|---|---|---|---|
| **30 अक्टूबर**, 04:35 के बाद | Sleeve A: window F2 (27 अक्टूबर 04:00 से 30 अक्टूबर 04:00) | Window में ≥ 20 sleeve-A closes हों तभी वह गिनी जाती है | F1: 23 closes, **consistent** | `logs/paper_n1/SLEEVE_A_FORWARD_PROTOCOL_PREREGISTERED.md` (531cd10c…) |
| **31 अक्टूबर** (महीने का अंत) | FWD-WATCH interim | सिर्फ़ जानकारी, कोई फ़ैसला नहीं | FW1: 5 closed, FW2: 10 closed | `logs/fwd_watch/FWD_WATCH_PROTOCOL_PREREGISTERED.md` §4 |
| **2 नवंबर**, 04:35 के बाद | Sleeve A: F3, और **पहला संभावित फ़ैसला** | पहली 3 eligible windows में ≥ 2 "not consistent" निकलें या कोई "records suspect" हो, तो sleeve A हटाने का amendment बनेगा। ≤ 1 हो तो जाँच बंद, कुछ नहीं बदलेगा | F1 consistent; F2 और F3 बाकी | वही |
| 5, 8, 11 नवंबर | Sleeve A: F4–F6 | अगर कोई window "too few trades" निकली, तो फ़ैसला बाद की window पर जाएगा। F1…F6 में 3 eligible न मिलें तो नतीजा "insufficient" | n/a | वही |
| **9 नवंबर**, 02:05 के बाद | **TC tracking gate** (demo बनाम shadow) | 14 पूरे दिन (26 अक्टूबर से 8 नवंबर)। कम से कम 12 दिन रोज़ का फ़र्क ≤ 0.30% (30 USDT, 10k पर), और कुल फ़र्क ≤ 1.0% (100 USDT)। **FAIL होने पर real money का कोई protocol नहीं बनेगा** | 2/14 दिन: रोज़ का फ़र्क −0.48 और +0.05, कुल −1.25 USDT | `logs/eco/ECO_AMENDMENT_1_PREREGISTERED.md` §5 |
| ~17 नवंबर (**अनुमान**) | MK1 maker फ़ैसला | एक बार, ≥ 300 orders पर | 40 orders। ~13 orders/दिन की रफ़्तार से तारीख का अनुमान, कोई वादा नहीं | `logs/eco_maker/MK1_PROTOCOL_PREREGISTERED.md` |
| **26 नवंबर** | DDX alarm की सीमा बदलेगी | Live उम्र 31 दिन होते ही सीमा 30-दिन वाली से 90-दिन वाली हो जाएगी: पीला 7.36% → 11.14%, लाल 9.35% → 14.69% | Demo DD 1.24%, normal | `logs/eco/ECO_AMENDMENT_3_PREREGISTERED.md` |
| **1 दिसंबर** | ECO demo का पहला पूरा महीना बनाम P3 | सिर्फ़ तुलना | P3 का median महीना 9,985 (10k पर), सबसे बुरा 9,132, सबसे अच्छा 10,714 | `CONSOLIDATED_ACTION_PLAN_28_OCT_2026.md` W8 |
| **19 जनवरी 2027** | PaperN1 day-90 review | Report है, gate नहीं। Real money सिर्फ़ आपके फ़ैसले से, और 90 forward दिनों से पहले नहीं | 44 records, रोज़ exit 0 | `logs/paper_n1/PAPER_N1_PROTOCOL_PREREGISTERED.md` |
| **23 जनवरी 2027** | PaperSpotS1 day-90 | Process gate है, performance gate नहीं। अकेले यह real money authorise नहीं करेगा | Equity 1,008.57 | `logs/paper_spot_s1/PAPER_SPOT_S1_PROTOCOL_PREREGISTERED.md` |
| 25 जनवरी 2027 | DDX सीमा फिर बदलेगी | 180-दिन वाली सीमा: पीला 14.10%, लाल 18.00% | n/a | वही amendment 3 |
| ~2027 मध्य (protocol का अनुमान) | FWD-WATCH फ़ैसला | FW2 ≥ 200 closed trades पर (~11 महीने), FW1 ≥ 80 पर (~20 महीने) | 10 और 5 | FWD-WATCH protocol |

## लगातार चलने वाली निगरानी

**DDX drawdown alarm:** 28 अक्टूबर से live है, सिर्फ़ चेतावनी देता है।
- Demo, shadow और plan, तीनों पर हर घंटे चलता है।
- **कमी:** `.env` में Telegram keys नहीं हैं, इसलिए alarm phone पर नहीं आएगा। यह सिर्फ़ `logs/eco/alerts*/alerts.jsonl` में लिखा जाएगा, जो हर घंटे Drive पर जाती है।
- Phone पर alert चाहिए तो keys आपको खुद VM की `.env` में डालनी होंगी (`ECO_TELEGRAM_TOKEN`, `ECO_TELEGRAM_CHAT`)। मैं keys नहीं डालता।

**Job-failure alert:** अब crontab के सभी 29 jobs पर है। पहले यह सिर्फ़ 10 jobs पर था।

**Kill switch:** 30% पर ही है, इसमें कोई बदलाव नहीं।

## हर हफ़्ते की जाँच (read-only)

1. `venv/bin/python deploy/version_check.py` → `VERSION OK … R-…`
2. `logs/cron_status/*.csv`: हर job का आख़िरी exit code।
3. `logs/eco/tracking/`: TC table।
4. `logs/paper_n1/sleeve_a_forward/summary.json`।
5. MK1 और FWD-WATCH के status files।
6. `ECO_Alerts.out` की `dd …` line।
