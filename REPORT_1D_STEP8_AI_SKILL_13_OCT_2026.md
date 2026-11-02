# 1D Step 8: क्या AI सच में सही entry/exit पहचानता है? — रिपोर्ट

**तारीख:** 13 अक्टूबर 2026 | **GitHub:** कुछ नहीं किया गया
**Protocol:** `logs/strategy_1d_step8_ai/STEP8_PROTOCOL_PREREGISTERED.md` (SHA256 `62047cb3...`), result से पहले lock हुआ।
**सारे नंबर:** `logs/strategy_1d_step8_ai/claims.json` से लिए गए। `src/audits/verify_step8_claims.py` ने हर नंबर अलग code से दोबारा जाँचा (V1–V5 PASS)।

## नतीजा एक लाइन में
**FAIL — कुछ deploy नहीं हुआ।**
- AI का entry दिमाग और exit दिमाग, दोनों random से थोड़े बेहतर हैं (AUC 0.534 और 0.526)। पर यह फायदा इतना छोटा है कि किस्मत से अलग **साबित नहीं** होता: 95% CI का निचला सिरा 0.50 से नीचे है।

## क्या बनाया (AI खुद तय करता है, कोई हाथ से लिखा trading नियम नहीं)
- **Universe:** 30 coins (डूबे LUNA, FTT, EOS, MATIC समेत)। हर साल सिर्फ उस समय के top-10 (volume से) में trade।
- **Entry दिमाग:** हर swing up-event पर अंदाज़ा लगाता है कि कीमत पहले +2 ATR पहुँचेगी या −1.5 ATR।
  - 5,164 उदाहरण, 46% "सही entry"।
- **Exit दिमाग:** हर खुले trade के हर दिन पर अंदाज़ा लगाता है कि "अभी निकलना सही है" या नहीं, यानी कीमत पहले −1 ATR गिरेगी या +1.5 ATR चढ़ेगी।
  - 1,26,510 उदाहरण।
- **Features:** सिर्फ price, volume और swing structure से, सब causal।
- **लगातार सीखना:** हर महीने की 1 तारीख को दोनों दिमाग दोबारा train होते हैं, सिर्फ पहले से पता चले नतीजों पर।
  - 69 महीने × 2 = 138 model fits। हर training size अलग से दोबारा गिनी गई (V4)।

## Skill test (अनदेखे data, 2021-01 → 2026-09, उस साल के tradable coins पर)

| | AI entry | नकली (labels shuffled) | AI exit | नकली exit |
|---|---|---|---|---|
| उदाहरण | 1,616 | 1,616 | 38,684 | 38,684 |
| AUC (0.5 = अंधा अंदाज़ा) | **0.534** | 0.478 | **0.526** | 0.462 |
| 95% CI | 0.490 – 0.579 | | 0.487 – 0.565 | |
| सबसे कम → सबसे ज़्यादा अंदाज़े वाले 20% हिस्से में असली सही-दर | 41% → 52% | 44% → 40% | 37% → 45% | |

**Gates:**
- G1 (entry): AUC ≥ 0.55 **✗**, CI > 0.50 **✗**, नकली से बेहतर ✓, ऊपरी हिस्सा > निचला ✓।
- G2 (exit): AUC ≥ 0.55 **✗**, CI > 0.50 **✗**, नकली से बेहतर ✓, ऊपरी हिस्सा > निचला ✓।

## Portfolio (point-in-time universe, $10k, 2021-01 → 2026-09)

| System | Final | CAGR | Max DD | Calmar | Trades |
|---|---|---|---|---|---|
| Baseline: हर swing पर entry | $16,699 | 9.3% | 57.0% | 0.164 | 400 |
| **AI entry + सामान्य exit** | **$20,589** | 13.4% | 45.8% | **0.293** | 301 |
| सामान्य entry + AI exit | $14,859 | 7.1% | 56.7% | 0.126 | 948 |
| AI entry + AI exit | $13,586 | 5.5% | **29.7%** | 0.185 | 547 |
| नकली AI (shuffled) | $22,046 | 14.8% | 53.9% | 0.274 | 326 |

**इसका मतलब:**
- **AI entry सबसे अच्छी संभावना है।** Baseline से बेहतर रहा, और Calmar में नकली से थोड़ा आगे (0.293 बनाम 0.274)। पर उसकी skill सांख्यिकीय रूप से साबित नहीं हुई, इसलिए नियम के हिसाब से deploy **नहीं**।
- **AI exit ने drawdown घटाया** (57% → 30%), पर कमाई भी मार दी। Exit का अंदाज़ा कमज़ोर है।
- **नकली AI ने भी $22,046 कमाए।** यानी इस अवधि में profit का बड़ा हिस्सा market और किस्मत का है, AI की समझ का नहीं।

## सच्चाई और आगे का रास्ता
1. Data (Binance API से 24/24 मेल), code, models और हिसाब असली हैं। पर **1D daily candles के इन features में अगले swing को पहचानने की ताकत बहुत कम है**, सिर्फ ~3% ऊपर।
2. Testnet पर पुराना Step 7 bot चल रहा है। उसकी skill भी साबित नहीं है। उसे "सीखा हुआ AI" नहीं, सिर्फ testing infrastructure मानें।
3. **Bot के ज़िंदा होने का सबूत:** `CryptoBot1D_HealthCheck` हर घंटे चलता है:
   - PID, heartbeat और exchange पर coins/stop orders का मिलान जाँचता है;
   - `logs/health/health_log.csv` में लिखता है;
   - bot मरा हो तो ALERT देता है (negative test से साबित)।
4. **आगे सुधार** (हर बार नया protocol नंबर, पहले से lock):
   - ज़्यादा जानकारी वाला data: 4H/1H candles से बने features, BTC dominance, funding/open interest;
   - ज़्यादा examples: ज़्यादा coins;
   - labels को trading cost के हिसाब से बनाना।
   - AI तभी deploy होगा जब CI > 0.50 साबित हो।
