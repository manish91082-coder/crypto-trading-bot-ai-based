# R2 cloud deploy log (19 अक्टूबर 2026, IST)

**Plan:** `deploy/R2_CLOUD_DEPLOY_PLAN.md`। हर कदम की जाँच PASS होने के बाद ही अगला कदम।

| # | कदम | सबूत | नतीजा |
|---|---|---|---|
| 0 | Laptop files बनाम regression के SHA | 6/6 MATCH (`REGRESSION_19_OCT_2026.txt`) | ✅ |
| 1a | VM crontab का backup | `/opt/cryptobot/deploy/crontab_backup_before_R2_20261019.txt` (19 lines) | ✅ |
| 1b | 8 files VM पर copy (recorder, 2 verifiers, shipper, 2 protocols, 2 CODE_CHANGES) | Laptop और VM के SHA 8/8 बराबर | ✅ |
| 2a | Recorder का पहला run VM पर (`data/forward_r2`) | run `20261019T135237Z`: 2,808 files, 11,80,699 rows, 2,810 requests, **0 HTTP errors**, 25 MB | ✅ |
| 2b | VM पर verifier (`logs/forward_recorder_r2/first_run_verify.txt`) | V1, V2a, V2, V3 (60/60 live replay), V4, V5, V6, V7, V8 = **9/9 PASS** | ✅ |
| 2c | Crontab: `37 1,5,9,13,17,21 * * *` FR2_Recorder | Diff में सिर्फ़ 2 नई lines (comment + job); install के बाद `crontab -l` == `deploy/crontab.txt` (SHA `6c21fd49…`, laptop पर भी वही); कुल 16 jobs | ✅ |
| 2d | पहला scheduled recorder run (21:37 IST) | cron से अपने-आप: run `20261019T160701Z`, exit 0, 577 files, 4,853 नए rows, 0 HTTP errors; verifier **9/9 PASS** (2 chained runs, 40/40 replay) | ✅ |
| 3a | Google Drive authorisation | उपयोगकर्ता की tunnel (PuTTY) + `rclone config create gdrive drive scope=drive.file` (VM)। उपयोगकर्ता के कहने पर Claude ने उनके Chrome में account manish91082@gmail.com चुना और consent दिया (scope: सिर्फ़ rclone की बनाई files)। **चूक:** जाँच में `rclone config show` और log से token Claude के tool output में छप गया। Token वाले logs हटाए गए (shred), `rclone.conf` 600। Rotation का विकल्प उपयोगकर्ता को दिया गया | ✅ (चूक दर्ज) |
| 3b | T6 | v1 (file-by-file) बहुत धीमा: ~7 s/file, 20 मिनट में 17 files → रोका गया। Locked v2 amendment (`071f2fe7…`, हर घंटे एक bundle); laptop tests 6/6। VM पर v2: **3,427 files एक bundle (30.5 MB) में 73 s में, verified**; 8 stdout logs rotate होकर free हुए। Verifier (Drive से download करके): W1–W4 **4/4 PASS**, 3,427/3,427 member md5 मिले | ✅ |
| 3c | Crontab में LogShip (`55 * * * *`) | Diff में सिर्फ़ 2 नई lines; install के बाद `crontab -l` == `deploy/crontab.txt` (SHA `77faaf58…`, laptop पर भी वही); कुल 17 jobs | ✅ |
| 3d | पहला scheduled LogShip (20:55 IST) | cron से अपने-आप: exit 0, 7 files का bundle verified; verifier **4/4 PASS** (2 घंटों के bundles download करके जाँचे, 3,434 members की md5 मिलीं) | ✅ |

**ज्ञात और जानबूझकर:**
- `deploy/crontab.txt` बदलने से master-audit verifier का A0 check (`1525e074…`, 17 अक्टूबर वाला) अब FAIL होगा। यह योजना के अनुसार है।
- M10 की रोज़ की report अपनी तय 7 jobs ही देखती है। FR2_Recorder और LogShip उसमें नहीं दिखेंगे। M10 (1D system) को जानबूझकर नहीं बदला गया। इन दोनों की निगरानी उनके अपने verifiers से रोज़ की cloud जाँच में होगी।
- 1D system की कोई file या job नहीं बदली गई। सिर्फ़ crontab में lines जुड़ीं।

## 2026-10-20 F6 "operations ready" check (after the 10:30 IST scheduled run, cron exit 0 at 05:00:39Z)
`verify_f6_testnet.py demo` on the VM: O1 PASS (20261020T050038_demo.json, 15 actions), O2 PASS (15 shorts, each exactly one correct STOP_MARKET algo order), O5 PASS (7 symbols ISOLATED x1), O3 PASS (positions = state, no extras). With O4 PASS from the 19-Oct drill -> F6 demo operations: READY (demo only; no mainnet path).

## 2026-10-21: PAPER-N1 forward recorder deploy (Step 6)

**Protocol:** `logs/paper_n1/PAPER_N1_PROTOCOL_PREREGISTERED.md` (`14bc8054…`). Public data only, NO orders.

| # | कदम | सबूत | नतीजा |
|---|---|---|---|
| P0 | Laptop पर replay gate (2025-03 … 2025-09, 1,284 cycles; `verify_paper_replay.py`) | Run 1: P4 FAIL, क्योंकि replay harness में SHIB/BONK के नाम का bug था (`CODE_NOTES` 1, सबूत रखा गया)। Run 2: entries 99.3% / 99.9%, कीमतें 100%, exits 100%, D legs 40/40 | ✅ 4/4 |
| P1 | 7 files VM पर copy (engine, `tf_edge_map`, config, protocol + SHA, CODE_NOTES, live verifier) | Laptop और VM के SHA 7/7 बराबर | ✅ |
| P2 | VM पर test cycle (T = 2026-10-21 04:00 UTC) | Exit 0, 54 positions, 558 requests, 1 error (SXPUSDT perp delisted → HTTP 400 → illiquid माना गया); verifier 5/5 | ✅ |
| P2b | Init-per-TF fix (`CODE_NOTES` 2) | 1-महीने का replay: 4,341 signal actions हूबहू वही। Test cycle को `data/paper_n1_test_cycle_20261021` में रखा; engine SHA `fa7de425…` (laptop = VM); ताज़ा पहला cycle exit 0; verifier 5/5 | ✅ |
| P3 | Crontab | Backup `deploy/crontab_backup_before_PAPERN1_20261021.txt` (`77faaf58…`)। Diff में सिर्फ़ 3 नई lines (1 comment + 2 jobs: PaperN1 `41 1,5,9,13,17,21`, PaperN1_Verify `20 7`)। Install के बाद `crontab -l` == `deploy/crontab.txt` (`a9848770…`); कुल 19 jobs | ✅ |

1D system की कोई file या job नहीं बदली गई। F6 वैसे का वैसा है; risk module उसमें नहीं जोड़ा गया (कारण: report, भाग 4)।

## ECO: single 10k ecosystem, PLAN mode (2026-10-22, protocol `logs/eco/ECO_PROTOCOL_PREREGISTERED.md` 15a3c837…)

| # | Step | Evidence | Status |
|---|---|---|---|
| E1 | Files to the VM (new files only, no existing file changed): `src/eco/{eco_core,eco_exchange,eco_orchestrator}.py`, `src/audits/verify_eco_live.py`, `deploy/eco_config.json`, `deploy/eco_history_daily_returns.csv`, `logs/eco/*` | `sha256sum -c` on the VM: 7/7 OK | ✅ |
| E2 | First manual plan cycle (T 2026-10-21 19:03 UTC) | ok; both producers verified (N1 T 16:00, F4 as-of 10-20); weights 1D 0.539 / N1 0.461; 25 target symbols, 20 paper fills, 5 inside the band; `verify_eco_live` 7/7 | ✅ |
| E3 | Crontab | Backup `deploy/crontab_backup_before_ECO_20261022.txt` (a9848770…). Diff = 3 new lines (comment + `50 * * * *` ECO_Plan + `25 7 * * *` ECO_Verify). After install, `crontab -l` == `deploy/crontab.txt` (daf36ed1…), 21 jobs | ✅ |

- **Not changed:** F6 and the 1D jobs. ECO plan mode sends no orders and uses no keys.
- **Demo cut-over (E-6)** needs the user's yes, and the R2 decision first (`logs/eco/E3_E4_RESULTS.md`).

## ECO amendment 1 deploy (2026-10-22 ~01:37 IST, still PLAN mode, no orders)

| # | Step | Evidence | Status |
|---|---|---|---|
| A1 | Laptop tests before the upload | `test_eco_core.py` 25/25. `verify_eco.py e2 a1 replay run3 run4` 8/9: R2 FAIL 1.20% is the known, recorded E-3 result. V6 (T4 from raw 5m) and V7 (guard count) PASS | ✅ |
| A2 | Upload through `staging_eco` | SHA check 11/11 OK. Backup of the old ECO files in `backups/eco_v1_before_A1_20261022/`. No ECO lock was active | ✅ |
| A3 | Manual plan cycle (20:06 UTC) | ok; `verify_eco_live` 7/7. L2 now lists config v1 4d4b784a and v2 f32f3f3a (both in CODE_CHANGES 5). Would-be exchange stops: 35 (20 guards, 15 1D-short) | ✅ |

- Crontab unchanged (daf36ed1…).
- F6, the 1D jobs and PaperN1 untouched.
- The demo cut-over waits for its gate (≥ 72 plan cycles, 3 days of 7/7) and the user's go.

## LogShip v3: ECO and PAPER-N1 folders on Drive (2026-10-22, amendment `logs/log_ship/LOG_SHIP_PROTOCOL_V3_AMENDMENT.md` 634f5b18…)

| # | Step | Evidence | Status |
|---|---|---|---|
| L1 | Gap found | Files written in the last 24 h outside the v2 mirror: `data/eco`, `logs/eco`, `data/paper_n1`, configs. The `live_1d` / `1h` market caches stay out by the v1 decision | ✅ |
| L2 | Laptop tests | Fresh VM copies with the rclone stub: T1–T6 7/7 PASS. New T6: 22 v3 files in the first verified bundle with equal md5. W4 13/13 | ✅ |
| L3 | VM deploy | After the 05:25 UTC run finished (lock gone): staging SHA 5/5. Backup in `backups/logship_v2_before_v3_20261022/`. After the copy, SHA 5/5 | ✅ |
| L4 | Real run via `run_job.sh` (05:29–05:30 UTC) | rc 0, `verified=True`, 33 members: `data/eco` 2, `logs/eco` 7, `data/paper_n1` 2, `logs/paper_n1` 3, test-cycle 2, configs 3, crontab backups 3 | ✅ |
| L5 | `verify_log_ship.py` on real Drive | W1 (v3 lock) / W2 / W3 / W4 (13/13) all PASS | ✅ |

- Crontab unchanged.
- VM freeing rules unchanged (F1 `.out`, F2 backups older than 2 days). The VM disk is at 27%.
