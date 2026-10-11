# 🛡️ जीरो-ट्रस्ट क्रिप्टो ट्रेडिंग बॉट: मास्टर रिसर्च और एग्जीक्यूशन फ्रेमवर्क

यह डॉक्यूमेंट एक "Zero-Trust Architecture" पर आधारित है। कोई भी डेटा, कोड या स्ट्रैटेजी बिना ग्राउंड-लेवल एविडेंस और मैथमेटिकल बैकटेस्टिंग के स्वीकार नहीं की गई है। इस प्रोजेक्ट का उद्देश्य ₹10,000 INR (~120 USDT) के शुरुआती कैपिटल को डेली कंपाउंडिंग और मिलिट्री-ग्रेड रिस्क मैनेजमेंट के जरिये सुरक्षित रूप से ग्रो करना है।

---

## 1. 🤖 AI रोल्स, लॉक्स और रूल्स (Strict AI Directives)

एक 'क्वांट लीड (Quant Lead)' और 'चीफ आर्किटेक्ट' के रूप में, मैंने अपने लिए निम्नलिखित रूल्स और लॉक्स (Locks) सेट किए हैं:

*   **Role 1: The Sceptic Analyst (शक्की विश्लेषक):** किसी भी इंडिकेटर (जैसे RSI, MACD) पर अंधा भरोसा नहीं करना। हर इंडिकेटर का काम 'प्राइस एक्शन' और 'वॉल्यूम' के साथ क्रॉस-वेरीफाई किया जाएगा।
*   **Role 2: The Risk Manager (रिस्क मैनेजर):** कैपिटल को सुरक्षित रखना पहली प्राथमिकता है। 2% डायनामिक रिस्क और 'पेसिमिस्टिक एग्जीक्यूशन' (Pessimistic Execution - बुरे से बुरे हालात की कल्पना) हमेशा एक्टिव रहेंगे।
*   **Role 3: The Code Auditor (कोड ऑडिटर):** मैं अपने खुद के लिखे गए कोड पर तब तक भरोसा नहीं करूँगा जब तक कि वह 'Look-ahead Bias' और 'False Signals' के लिए 100% टेस्ट न हो जाए।
*   **Lock 1 (Zero Cost Lock):** सिर्फ 100% फ्री और ओपन-सोर्स टूल्स (Python, Google Colab, Binance Vision, Yahoo Finance API) का इस्तेमाल होगा। कोई पेड सब्सक्रिप्शन नहीं।
*   **Lock 2 (Zero Hallucination Lock):** कोई भी 'सिमुलेटेड' रिजल्ट नहीं। सारे रिजल्ट्स ऐतिहासिक टिक-बाय-टिक (Tick-by-Tick) या 5-मिनट/15-मिनट के रॉ (Raw) कैंडल डेटा पर आधारित होंगे।
*   **Lock 3 (Military Discipline):** "नो इमोशन ट्रेडिंग।" एंट्री और एग्जिट सिर्फ गणित (Math) और डेटा-ड्रिवेन रूल्स पर काम करेंगे। 

---

## 2. 💰 कैपिटल और रिस्क मैनेजमेंट (The Compounding Engine)

*   **Initial Capital (शुरुआती निवेश):** ₹10,000 INR (लगभग 120.0 USDT)
*   **Position Sizing:** हर ट्रेड में करंट कैपिटल का सिर्फ **2%** रिस्क (SL हिट होने पर सिर्फ 2% का नुकसान)।
*   **Compounding Principle:** जैसे-जैसे कैपिटल बढ़ेगा, 2% की वैल्यू बढ़ेगी, जिससे प्रॉफिट (और पोजीशन साइज) भी एक्सपोनेंशियली (Exponentially) बढ़ेगा। अगर लॉस होता है, तो 2% की वैल्यू कम होगी, जिससे हमारा अकाउंट कभी 0 (Liquidate) नहीं होगा।
*   **Risk:Reward Ratio (R:R):** फिक्स्ड 1:1.5 (यानी 2.0x ATR का स्टॉप-लॉस और 3.0x ATR का टेक-प्रॉफिट)। 

---

## 3. 📈 टेक्निकल इंडिकेटर्स और उनके असली काम

हम केवल 5 इंडिकेटर्स का 'Zero-Trust' सेट इस्तेमाल करेंगे:

1.  **VWAP (Volume Weighted Average Price):** यह इंस्टीट्यूशनल प्लेयर्स का 'वैल्यू ज़ोन' है। इसके ऊपर प्राइस बुलिश है, नीचे बेयरिश है। 
2.  **EMA (20, 50, 200):** 
    *   **EMA 200:** मैक्रो ट्रेंड (Macro Trend) शील्ड। इसके खिलाफ हम कोई ट्रेड नहीं लेंगे।
    *   **EMA 50 & 20:** ये मोमेंटम और 'माइक्रो-ट्रेंड' तय करेंगे (विशेषकर 15-मिनट में)।
3.  **Bollinger Bands (20, 2.0 & 1.5):** यह हमारा ऑपरेटर 'ट्रैप हंटर' है। हम प्राइस के बैंड के बाहर जाने और फिर वापस अंदर क्लोज होने (Liquidity Sweep) का इंतज़ार करते हैं।
4.  **ATR (14 - Average True Range):** यह मार्केट की 'वोलैटिलिटी' नापेगा ताकि हमारे स्टॉप-लॉस और टारगेट फिक्स डॉलर अमाउंट की बजाय मार्केट की स्पीड के हिसाब से अपने-आप एडजस्ट (Dynamic) हों।
5.  **RVOL (Relative Volume):** पिछले 20 कैंडल्स के मुकाबले करंट कैंडल का वॉल्यूम। RVOL > 1.2 का मतलब है 'स्मार्ट मनी' (Whales) मार्केट में एंटर कर चुकी है।
6.  **RSI (14):** इसे केवल 'एक्स्ट्रीम थकावट' (Exhaustion) पकड़ने के लिए यूज़ करेंगे (RSI < 45 या RSI > 55)।

---

## 4. ⚡ द 5-मिनट मास्टरपीस (V11: Daily Compounder)

यह 5-मिनट के चार्ट के लिए सबसे आक्रामक (Aggressive) लेकिन सुरक्षित स्ट्रेटजी है। यह हर दिन के 'ऑपरेटर फेकआउट्स' का शिकार करके पैसा बनाती है।

### 5-मिनट के रूल्स:
*   **Macro Shield:** प्राइस `EMA 200` के ऊपर होना चाहिए (Long के लिए)।
*   **The Trap:** कैंडल का लो (Low) 'Bollinger Band (2.0)' के बाहर जाए, लेकिन क्लोजिंग (Close) बैंड के अंदर हो।
*   **Rejection:** कैंडल ग्रीन (Green) क्लोज होनी चाहिए (`Close > Open`)।
*   **Volume Shock:** `RVOL > 1.2` (वॉल्यूम में अचानक उछाल होना चाहिए)।
*   **Execution:** `Stop Loss = Entry - 2.0 ATR`, `Take Profit = Entry + 3.0 ATR`।

### 5-Min V11 Python Code:
```python
import pandas as pd
import pandas_ta as ta
import numpy as np

print("   System Booting: V11 'DAILY COMPOUNDER & LOSS MINIMIZER' (5-MIN)...")

# 1. LOAD DATA
try:
    df = pd.read_csv('Raw_Data/ETHUSDT_5m_Raw_5Years.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df.dropna(subset=['timestamp'], inplace=True) 
    df.set_index('timestamp', inplace=True)
    df = df[df.index.year < 2030]
except FileNotFoundError:
    print("❌ Error: Raw Data file not found.")
    exit()

# 2. INDICATORS
df['EMA_200'] = ta.ema(df['close'], length=200)
bbands = ta.bbands(df['close'], length=20, std=2.0)
df['BBL'] = bbands[bbands.columns[0]]
df['BBU'] = bbands[bbands.columns[2]]
df['ATR_14'] = ta.atr(df['high'], df['low'], df['close'], length=14)
df['RVOL'] = df['volume'] / df['volume'].rolling(20).mean()
df.dropna(inplace=True)

# 3. BACKTESTING ENGINE
capital = 120.0  # $120 USDT (Approx ₹10,000 INR)
risk_per_trade_pct = 0.02
in_trade = False
trades = []

for index, row in df.iterrows():
    if not in_trade:
        # LONG ENTRY (Confirmed Sweep)
        macro_up = row['close'] > row['EMA_200']
        sweep_long = row['low'] < row['BBL'] and row['close'] > row['BBL']
        rejection_long = row['close'] > row['open']
        vol_shock_long = row['RVOL'] > 1.2
        
        if macro_up and sweep_long and rejection_long and vol_shock_long:
            in_trade = True
            entry_price = row['close']
            atr = row['ATR_14']
            
            sl_price = entry_price - (2.0 * atr)
            tp_price = entry_price + (3.0 * atr)
            
            sl_distance = entry_price - sl_price
            qty = (capital * risk_per_trade_pct) / sl_distance if sl_distance > 0 else 0
            
            current_trade = {'Type': 'LONG', 'Entry Time': index, 'Entry Price': entry_price, 'Qty': qty, 
                             'SL Target': sl_price, 'TP Target': tp_price}
            continue

        # SHORT ENTRY (Confirmed Fakeout)
        macro_down = row['close'] < row['EMA_200']
        sweep_short = row['high'] > row['BBU'] and row['close'] < row['BBU']
        rejection_short = row['close'] < row['open']
        vol_shock_short = row['RVOL'] > 1.2
        
        if macro_down and sweep_short and rejection_short and vol_shock_short:
            in_trade = True
            entry_price = row['close']
            atr = row['ATR_14']
            
            sl_price = entry_price + (2.0 * atr)
            tp_price = entry_price - (3.0 * atr)
            
            sl_distance = sl_price - entry_price
            qty = (capital * risk_per_trade_pct) / sl_distance if sl_distance > 0 else 0
            
            current_trade = {'Type': 'SHORT', 'Entry Time': index, 'Entry Price': entry_price, 'Qty': qty, 
                             'SL Target': sl_price, 'TP Target': tp_price}
            continue

    # 4. BINARY TRADE MANAGEMENT (Pessimistic)
    if in_trade:
        if current_trade['Type'] == 'LONG':
            if row['low'] <= current_trade['SL Target'] and row['high'] >= current_trade['TP Target']:
                loss = (current_trade['Entry Price'] - current_trade['SL Target']) * current_trade['Qty']
                capital -= loss
                current_trade['Result'] = 'LOSS'
                current_trade['Exit Time'] = index
                trades.append(current_trade)
                in_trade = False
            elif row['high'] >= current_trade['TP Target']:
                profit = (current_trade['TP Target'] - current_trade['Entry Price']) * current_trade['Qty']
                capital += profit
                current_trade['Result'] = 'WIN'
                current_trade['Exit Time'] = index
                trades.append(current_trade)
                in_trade = False
            elif row['low'] <= current_trade['SL Target']:
                loss = (current_trade['Entry Price'] - current_trade['SL Target']) * current_trade['Qty']
                capital -= loss
                current_trade['Result'] = 'LOSS'
                current_trade['Exit Time'] = index
                trades.append(current_trade)
                in_trade = False

        elif current_trade['Type'] == 'SHORT':
            if row['high'] >= current_trade['SL Target'] and row['low'] <= current_trade['TP Target']:
                loss = (current_trade['SL Target'] - current_trade['Entry Price']) * current_trade['Qty']
                capital -= loss
                current_trade['Result'] = 'LOSS'
                current_trade['Exit Time'] = index
                trades.append(current_trade)
                in_trade = False
            elif row['low'] <= current_trade['TP Target']:
                profit = (current_trade['Entry Price'] - current_trade['TP Target']) * current_trade['Qty']
                capital += profit
                current_trade['Result'] = 'WIN'
                current_trade['Exit Time'] = index
                trades.append(current_trade)
                in_trade = False
            elif row['high'] >= current_trade['SL Target']:
                loss = (current_trade['SL Target'] - current_trade['Entry Price']) * current_trade['Qty']
                capital -= loss
                current_trade['Result'] = 'LOSS'
                current_trade['Exit Time'] = index
                trades.append(current_trade)
                in_trade = False

if len(trades) > 0:
    print(f"Total Trades: {len(trades)}")
    print(f"Final Capital: ${capital:.2f}")
else:
    print("No trades triggered.")
```

---

## 5. 🎯 द 15-मिनट मास्टरपीस (V24: The Dual-Trap Compounder)

15-मिनट का टाइमफ्रेम बहुत अधिक स्टेबल होता है, इसलिए हमने 'Dual-Trap' (दोहरे जाल) का निर्माण किया है।

### 15-मिनट के रूल्स:
*   **Macro Alignment:** 15-मिनट के चार्ट पर `EMA 50` > `EMA 200` होना चाहिए (यह 1-घंटे का अपट्रेंड कन्फर्म करता है), और करंट प्राइस `VWAP` और `EMA 200` दोनों के ऊपर होना चाहिए।
*   **Trigger A (Deep Sweep):** प्राइस 'Bollinger Band 2.0' के बाहर जाए और अंदर क्लोज हो।
*   **Trigger B (Shallow Sweep):** प्राइस 'Bollinger Band 1.5' के बाहर जाए, लेकिन साथ ही `RSI 14 < 45` (ठंडा/Oversold) हो और वॉल्यूम शॉक `RVOL > 1.2` हो।
*   **Rejection:** कैंडल ग्रीन (Green) क्लोज होनी चाहिए (`Close > Open`)।
*   **Execution:** `Stop Loss = Entry - 2.0 ATR`, `Take Profit = Entry + 3.0 ATR`।

### 15-Min V24 Python Code:
```python
import pandas as pd
import pandas_ta as ta
import numpy as np

print("   System Booting: V24 'THE 15-MIN DUAL-TRAP COMPOUNDER'...")

# 1. LOAD DATA
try:
    df = pd.read_csv('Raw_Data/ETHUSDT_15m_Raw_5Years.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df.dropna(subset=['timestamp'], inplace=True) 
    df.set_index('timestamp', inplace=True)
    df = df[df.index.year < 2030]
except FileNotFoundError:
    print("❌ Error: Raw Data file not found.")
    exit()

# 2. INDICATORS (Dual Traps)
df['EMA_50'] = ta.ema(df['close'], length=50)
df['EMA_200'] = ta.ema(df['close'], length=200)
df['VWAP'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])

bbands_20 = ta.bbands(df['close'], length=20, std=2.0)
df['BBL_2_0'] = bbands_20[bbands_20.columns[0]]
df['BBU_2_0'] = bbands_20[bbands_20.columns[2]]

bbands_15 = ta.bbands(df['close'], length=20, std=1.5)
df['BBL_1_5'] = bbands_15[bbands_15.columns[0]]
df['BBU_1_5'] = bbands_15[bbands_15.columns[2]]

df['RSI_14'] = ta.rsi(df['close'], length=14)
df['ATR_14'] = ta.atr(df['high'], df['low'], df['close'], length=14)
df['RVOL'] = df['volume'] / df['volume'].rolling(20).mean()
df.dropna(inplace=True)

# 3. BACKTESTING ENGINE
capital = 120.0 
risk_per_trade_pct = 0.02 
in_trade = False
trades = []

for index, row in df.iterrows():
    if not in_trade:
        # MACRO ALIGNMENT (The Shield)
        htf_bullish = row['EMA_50'] > row['EMA_200']
        macro_up = row['close'] > row['EMA_200'] and row['close'] > row['VWAP']
        
        # TRIGGER A: Deep Sweep
        trigger_a_long = row['low'] < row['BBL_2_0'] and row['close'] > row['BBL_2_0']
        
        # TRIGGER B: Shallow Sweep
        trigger_b_long = (row['low'] < row['BBL_1_5'] and row['close'] > row['BBL_1_5']) and \
                         (row['RSI_14'] < 45) and (row['RVOL'] > 1.2)
        
        rejection_long = row['close'] > row['open'] 
        
        if htf_bullish and macro_up and (trigger_a_long or trigger_b_long) and rejection_long:
            in_trade = True
            entry_price = row['close']
            atr = row['ATR_14']
            
            sl_price = entry_price - (2.0 * atr)
            tp_price = entry_price + (3.0 * atr)
            
            sl_dist = entry_price - sl_price
            qty = (capital * risk_per_trade_pct) / sl_dist if sl_dist > 0 else 0
            
            current_trade = {'Type': 'LONG', 'Entry Price': entry_price, 'Qty': qty, 
                             'SL Target': sl_price, 'TP Target': tp_price}
            continue

        # SHORT LOGIC
        htf_bearish = row['EMA_50'] < row['EMA_200']
        macro_down = row['close'] < row['EMA_200'] and row['close'] < row['VWAP']
        
        trigger_a_short = row['high'] > row['BBU_2_0'] and row['close'] < row['BBU_2_0']
        trigger_b_short = (row['high'] > row['BBU_1_5'] and row['close'] < row['BBU_1_5']) and \
                          (row['RSI_14'] > 55) and (row['RVOL'] > 1.2)
        
        rejection_short = row['close'] < row['open']
        
        if htf_bearish and macro_down and (trigger_a_short or trigger_b_short) and rejection_short:
            in_trade = True
            entry_price = row['close']
            atr = row['ATR_14']
            
            sl_price = entry_price + (2.0 * atr)
            tp_price = entry_price - (3.0 * atr)
            
            sl_dist = sl_price - entry_price
            qty = (capital * risk_per_trade_pct) / sl_dist if sl_dist > 0 else 0
            
            current_trade = {'Type': 'SHORT', 'Entry Price': entry_price, 'Qty': qty, 
                             'SL Target': sl_price, 'TP Target': tp_price}
            continue

    # 4. BINARY TRADE MANAGEMENT (Pessimistic)
    if in_trade:
        if current_trade['Type'] == 'LONG':
            if row['low'] <= current_trade['SL Target'] and row['high'] >= current_trade['TP Target']:
                loss = (current_trade['Entry Price'] - current_trade['SL Target']) * current_trade['Qty']
                capital -= loss
                trades.append(current_trade)
                in_trade = False
            elif row['high'] >= current_trade['TP Target']:
                profit = (current_trade['TP Target'] - current_trade['Entry Price']) * current_trade['Qty']
                capital += profit
                trades.append(current_trade)
                in_trade = False
            elif row['low'] <= current_trade['SL Target']:
                loss = (current_trade['Entry Price'] - current_trade['SL Target']) * current_trade['Qty']
                capital -= loss
                trades.append(current_trade)
                in_trade = False

        elif current_trade['Type'] == 'SHORT':
            if row['high'] >= current_trade['SL Target'] and row['low'] <= current_trade['TP Target']:
                loss = (current_trade['SL Target'] - current_trade['Entry Price']) * current_trade['Qty']
                capital -= loss
                trades.append(current_trade)
                in_trade = False
            elif row['low'] <= current_trade['TP Target']:
                profit = (current_trade['Entry Price'] - current_trade['TP Target']) * current_trade['Qty']
                capital += profit
                trades.append(current_trade)
                in_trade = False
            elif row['high'] >= current_trade['SL Target']:
                loss = (current_trade['SL Target'] - current_trade['Entry Price']) * current_trade['Qty']
                capital -= loss
                trades.append(current_trade)
                in_trade = False

if len(trades) > 0:
    print(f"Total Trades: {len(trades)}")
    print(f"Final Capital: ${capital:.2f}")
else:
    print("No trades triggered.")
```
