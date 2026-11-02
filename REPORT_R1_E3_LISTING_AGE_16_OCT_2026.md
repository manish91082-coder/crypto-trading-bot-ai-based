# Round 1, E3: क्या AI की short skill सिर्फ़ "नए listed coin" का असर है? (16 अक्टूबर 2026)

**यह experiment सिर्फ़ जाँच के लिए है (diagnostic)।** इससे कोई नियम अपनाया या हटाया नहीं जाता। Protocol: `logs/research_r1/R1_PROTOCOL_PREREGISTERED.md` (SHA af95f224…, run से पहले lock)।

## सबूत
- **Run:** `python src/pipeline_1d/r1_run.py E3`
  - समय: 09:42–10:25 UTC (2,554 सेकंड)
  - stdout: `logs/research_r1/run_E3_stdout.txt`
- **Claims:** `logs/research_r1/claims_E3.json`
- **Verifier:** `python src/audits/verify_r1_claims.py E3`, नतीजा `verify_E3_stdout.txt` में:
  - V1 PASS: protocol, engine और runner के hash मिलते हैं।
  - V2 PASS: F7 short P&L, E3b short P&L, E3c median और reading rule सादे loops से दोबारा निकाले गए; equity और trades files से DD, 2022 और worst week भी दोबारा निकाले गए।
  - V3 PASS: age buckets के P&L shares F7 के trades से एक सादी age-गणना से दोबारा निकाले गए।
- **Verifier को पहले मज़बूत किया:** E3 का नतीजा देखने से पहले verifier में G5, `decision` field और reading rule की जाँच जोड़ी गई (`CODE_CHANGES_AFTER_LOCK.md` §5)।

## E3a: F7 RS के short trades, perp की उम्र के हिसाब से (तीनों sleeves मिलाकर)
| Perp की उम्र (entry पर) | Trades | F7 short P&L में हिस्सा | PF |
|---|---|---|---|
| < 60 दिन | 147 (3.3%) | **+32.1%** | **1.71** |
| 60–180 दिन | 273 | −20.7% | 0.82 |
| 180–365 दिन | 662 | −22.6% | 0.90 |
| ≥ 365 दिन | 3,343 | +111.1% | 1.11 |

- बिलकुल नए perps (60 दिन से कम) सिर्फ़ 3% trades हैं, लेकिन short के पूरे मुनाफ़े का लगभग एक-तिहाई इन्हीं से आता है।
- 60–365 दिन वाले perps पर AI के shorts कुल मिलाकर घाटे में रहे।

## E3b: बिना AI का नियम, "सबसे नए 5 perps short करो" (long book वही)
| | F7 RS (AI shorts) | E3b (उम्र का नियम) |
|---|---|---|
| Short P&L (sleeves का औसत) | $26,227 | **$26,388** |
| Short PF / payoff | 1.07 / 0.81 | **1.31** / 0.77 |
| Short trades | 4,425 | 762 |
| Final ($10k से) | **$88,401** | $71,922 |
| Max DD | 21.37% | 20.21% |
| 2022 | **+36.54%** | +0.78% |
| सबसे बुरा short दिन | −$6,454 | −$3,308 |
| सबसे बुरा हफ़्ता | −9.63% | −12.45% |
| DSR (N = 91) | — | 0.884 (< 0.95) |

## E3c: हर AI pick की जगह उसी उम्र-bucket से random coin (10 seeds)
Short P&L: −1,866, −9,043, −249, +10,650, +7,091, +3,800, −3,000, −10,668, −235, +9,502।
- **Median: −$242।** दसों seeds AI shorts ($26,227) से नीचे रहे।
- **Caveat:** random pick हर दिन नए सिरे से चुना जाता है, इसलिए इसमें ~7,200 short trades हुए, F7 से कहीं ज़्यादा turnover। इसका ज़्यादा cost E3c के नतीजे को नीचे खींचता है। यह protocol के हिसाब से ही है, लेकिन ध्यान रखने वाली बात है।

## Pre-registered reading rule का नतीजा
E3b short P&L ($26,388) ≥ 80% × F7 short P&L ($20,982)। इसलिए नियम के अनुसार नतीजा है: **"AI short skill not shown beyond listing age"**, यानी AI की short skill listing-age से आगे साबित नहीं हुई।

## मेरी ईमानदार व्याख्या (नियम के नतीजे को बदले बिना)
1. **AI की short side की ज़्यादातर बढ़त "नए listed coin गिरते हैं" वाले असर में दिखती है।** बिना AI का साधारण उम्र-नियम AI जितना ही short P&L देता है, और उसका PF (1.31) AI के PF (1.07) से बेहतर है।
2. **फिर भी AI का चुनाव random से बेहतर है:** उसी उम्र-bucket में random coins का median ≈ $0 रहा। ऊपर बताए turnover caveat के साथ इसका मतलब है कि AI हर bucket के अंदर कुछ जानकारी जोड़ता है।
3. **पूरे system के लिए उम्र-नियम बेहतर नहीं है:**
   - Final $71.9k बनाम F7 का $88.4k।
   - 2022 सिर्फ़ +0.8% बनाम +36.5%।
   - Worst week −12.45% बनाम −9.63%।
   - DSR 0.88।

   यानी AI shorts ने bear market (2022) में ज़्यादा मदद की।
4. **आगे क्या (यह कोई नया नियम नहीं, सिर्फ़ सुझाव है):** "उम्र" को AI के साथ मिलाने का विचार (जैसे AI ranking + नए perps को प्राथमिकता) Round 2 में अलग से pre-register करके ही जाँचा जा सकता है। E2 (उम्र ≥ 60 दिन वाला filter) इसका उल्टा है, और अगला उसी का नतीजा आएगा।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। ये backtest नतीजे हैं, भविष्य की गारंटी नहीं।
