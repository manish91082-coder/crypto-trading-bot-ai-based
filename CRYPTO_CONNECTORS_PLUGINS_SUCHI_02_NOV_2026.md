# Crypto connectors, skills और plugins की पूरी FREE सूची (2 Nov 2026)

## 0. सीधा जवाब
1. **इस फ़ाइल में सिर्फ़ free चीज़ें हैं।** Paid वाली शामिल नहीं हैं।
2. **कुल 82 free चीज़ें मिलीं:** 42 connectors (इनमें 4 plugin के रूप में भी हैं) और 40 सिर्फ़ plugin या skill।
3. **कोई अलग flash loan connector या plugin मौजूद नहीं है।** "flash loan" की खोज में directory से एक ही नतीजा आया और वह crypto का नहीं था। Flash loan के काम की चीज़ें सेक्शन 7 में हैं।
4. **हमारे काम के सबसे ऊपर के 8:** Buildix, CoinLobster, CryptoETF, Unlock Pulse, DAMO Market State, SatoshiMacro, Token Terminal, Helious। कारण सेक्शन 10 में हैं।
5. **इनमें से कोई भी जीतने वाली strategy नहीं देता।** ये सिर्फ़ data और औज़ार हैं। हर नया signal पहले test होगा।

## 1. सूची कैसे बनाई
| स्रोत | क्या किया | नतीजा |
|---|---|---|
| claude.ai/directory (आपके screenshot वाली सूची) | 318 crypto शब्दों से खोज | 2,677 listings देखीं |
| claude.com marketplace | sitemap की सारी listings का page पढ़ा | 1,578 पढ़ीं |
| Community plugin सूची | पूरी सूची छानी | 2,283 छाने |
| Plugin search | विषय के अनुसार खोज | बचे हुए plugins मिले |
| Endpoint जाँच | बिना key handshake और असली call | नीचे के निशान देखें |

**Saturation का सबूत:** आख़िरी दौर में 275 और listings देखने पर सिर्फ़ 1 नई crypto चीज़ (Unlock Pulse) मिली।

**Free के निशान:**

| निशान | मतलब |
|---|---|
| ✅ | बिना key असली data मिला, मैंने खुद चलाकर देखा |
| 🔌 | बिना key जुड़ा और tool सूची मिली; असली data नहीं माँगा |
| 🔑 | Free plan या free key है (सेवा की site या listing के अनुसार); account आपको बनाना होगा |
| 📦 | Plugin या skill मुफ़्त है; उसके पीछे की सेवा की जाँच नहीं की |

**उपयोग के निशान:** ⭐⭐⭐ सबसे काम का, ⭐⭐ उपयोगी, ⭐ थोड़ा, ❌ इस project के काम का नहीं।

## 2. Live बाज़ार और कीमत का data
| नाम | प्रकार | क्या करता है | Free | हमारे काम का |
|---|---|---|---|---|
| CoinGecko | Connector | कीमतें, charts, trending, sectors, gainers/losers, news | ✅ | ⭐⭐ Binance mirror का बैकअप, sector का हाल |
| CoinPaprika | Plugin | 12,000+ coins की कीमत, OHLCV, exchanges, coin events | 🔌 | ⭐⭐ बैकअप और coin events |
| DexPaprika | Plugin | 36 chains के DEX, pools और tokens | 📦 listing: free, बिना key | ⭐ DEX का data |
| Pyth | Connector | Crypto समेत कीमतें और candlesticks | ✅ | ⭐⭐ स्वतंत्र price cross-check |
| DAMO Market State | Connector | 44 crypto का market state, 10 timeframes | ✅ | ⭐⭐⭐ हमारे regime से तुलना; history दोबारा नहीं बदली जाती |
| MarketCrew | Connector | 370+ stocks, ETFs, crypto: levels, momentum, breadth | ✅ | ⭐ US market का breadth |
| Gemini | Connector | Exchange का ticker, order book, prediction markets | 🔌 | ⭐ दूसरे exchange का order book |
| Twelve Data | Connector | कीमतें और 100+ indicators (8/min, 800/दिन) | 🔑 | ⭐ बैकअप |
| CoinMarketCap | Connector | कीमतें, on-chain, तकनीकी विश्लेषण (15,000 credits/माह) | 🔑 laptop से timeout | ⭐ बैकअप |
| Alpha Vantage | Connector | Macro, commodities, crypto (25/दिन) | 🔑 | ⭐ थोड़ा macro |
| FMP | Connector | Economic calendar, COT (250/दिन) | 🔑 | ⭐ COT और calendar |
| TraderWAI Charts | Connector | OHLC, chart analysis, backtests | 🔑 Free plan | ⭐ chart cross-check |
| SiftingIO | Connector | Market snapshots और price bars | 🔑 "Start for free" | ⭐ बैकअप |

## 3. Derivatives, liquidation, whale और events
| नाम | प्रकार | क्या करता है | Free | हमारे काम का |
|---|---|---|---|---|
| Buildix: Hyperliquid Orderflow | Connector | Funding, liquidation levels, whale positioning, top traders | ✅ | ⭐⭐⭐ setup C और funding का context |
| CoinLobster | Connector + plugin | 18 exchanges के whale trades, liquidations, signals, orderbook | ✅ | ⭐⭐⭐ setup C; बिना login ~30 मिनट पुराना |
| Unlock Pulse | Connector | अगले 60 दिन के token unlocks, पिछले unlocks पर कीमत का व्यवहार | 🔌 | ⭐⭐⭐ हमारे 30 coins का event filter |
| INDICIA DESK | Connector | BTC/ETH options state, max pain, gamma regime | ✅ | ⭐⭐ options का context; परखी गई hypotheses |
| DEBYKO | Connector | 22 venues का perp data, हर मान के साथ समय | 🔑 free key, बिना card | ⭐⭐⭐ funding और OI की venue-तुलना |
| 0xArchive | Connector | Hyperliquid और Lighter के trades, order books | 🔑 Free: 30 दिन, 50k credits | ⭐⭐ order book research |
| AlphaYou | Connector + plugin | Smart money, CFTC positioning, Hyperliquid traders | ✅ | ⭐⭐ positioning data |
| FinzData | Connector | Point-in-time market data, COT, server backtests | 🔌 | ⭐⭐ COT research; शर्तें जाँचनी होंगी |
| Hagglyai | Connector | Pay-per-call APIs की तुलना | ✅ | ❌ |

## 4. ETF, cycle और sentiment
| नाम | प्रकार | क्या करता है | Free | हमारे काम का |
|---|---|---|---|---|
| CryptoETF | Connector + plugin | 16 coins के ETF का रोज़ का flow, fund के हिसाब से | ✅ key से 30 दिन का इतिहास | ⭐⭐⭐ 1d का नया non-price data |
| SatoshiMacro Market Data | Connector | Cycle model, altcoin season, BTC ETF flows | ✅ | ⭐⭐⭐ daily regime का context |
| Nakamoto Notes Bitcoin Barometer | Connector | 0-100 Heat Score, 10 on-chain और sentiment indicators | ✅ | ⭐⭐ daily context |
| cyclebottom-risk | Plugin | Crypto और index का 0-1 risk score | 📦 | ⭐ |
| Antevo Tremor Watch / 07:00 Brief | Connector | Market relationships का साप्ताहिक index, सुबह का brief | ✅ | ⭐ macro context |

## 5. On-chain और blockchain data
| नाम | प्रकार | क्या करता है | Free | हमारे काम का |
|---|---|---|---|---|
| CryptoKeyhole | Connector | अपने nodes का on-chain data; metrics की लंबी सूची | ✅ | ⭐⭐⭐ daily backtest का उम्मीदवार |
| Token Terminal | Connector | Protocols का revenue और usage | 🔑 Free $0, core data | ⭐⭐⭐ fundamentals research |
| SQD | Connector | 200+ chains का data, Hyperliquid समेत | ✅ Free plan भी | ⭐⭐ on-chain research |
| GoldRush (Covalent) | Connector | Wallet balances, transactions, NFTs, कीमतें | 🔑 25,000 free credits | ⭐ wallets |
| Hgraph | Connector | GraphQL, SQL और RPC से chain data | 🔑 बिना card | ⭐ research |
| Etherscan | Connector | 60+ EVM chains: wallets, contracts, gas | 🔌 | ⭐ hack wallets पर नज़र; flash loan काम |
| Blockscout | Connector | Blockchain explorer data | 🔌 | ⭐ Etherscan जैसा |
| SoChain | Connector | BTC, LTC, DOGE, ZEC के balances और transactions | 🔌 | ⭐ |
| BlockchainQuery | Connector | 60+ networks की lookups | 🔑 listing: free; endpoint नहीं मिला | ⭐ |
| BackPoW | Connector | Mining, hashrate, cost of production, 128 networks | ✅ | ⭐ miner cost का context |
| Goldsky Docs | Connector | Goldsky के docs | 🔌 | ❌ |
| Scorechain | Connector | AML जाँच | 🔑 free wallet checks | ❌ |
| subgraph-mcp, subgraph-mcp-skills | Plugin | The Graph के 15,000+ subgraphs | 📦 | ⭐ DeFi data |
| sentio-ai-kit | Plugin | Blockchain data processors, SQL | 📦 | ❌ |
| helius | Plugin | Solana के tools और coding patterns | 🔑 Free: 1M credits | ❌ Solana build के लिए |
| keeperhub | Plugin | Contract monitoring workflows | 📦 | ❌ |
| hyperscope-plugins | Plugin | Hyperliquid trader और market analytics | 📦 | ⭐⭐ trader data |

## 6. Backtest, हिसाब और trading की skills
| नाम | प्रकार | क्या करता है | Free | हमारे काम का |
|---|---|---|---|---|
| TradingCalc | Connector + plugin | PnL, liquidation, funding का सटीक हिसाब | 🔌 listing: free, बिना signup | ⭐⭐ `lpt.py` की cross-check |
| AlphaPrime | Connector | Futures strategy backtest | 🔑 listing: free backtest | ⭐ |
| Deltalytix | Connector | Trading journal | 🔑 Basic free | ⭐ |
| claude-trading-skills-marketplace | Plugin | 52 trading skills | 📦 | ⭐ विचारों के लिए |
| tradememory | Plugin | AI traders के trades की memory | 📦 | ⭐ |
| algovault-skills | Plugin | Composite signals, funding arbitrage | 📦 | ⭐ बिना सबूत signal न मानें |
| orion-trading-intelligence | Plugin | BTC signals | 📦 | ⭐ वही शर्त |
| Crypto Spot Futures Analyzer | Plugin (skill) | Trade setups की जाँच के निर्देश | 📦 | ❌ data नहीं |
| Crypto & Bitcoin Analyst | Plugin (skill) | Charts और research के निर्देश | 📦 | ❌ data नहीं |
| Galleon DeFi Strategy | Plugin (skill) | DeFi backtest की विधि | 📦 | ❌ हमारा verifier ज़्यादा सख़्त है |
| bitcoin-companies | Plugin | BTC treasury कंपनियाँ | 📦 | ❌ |
| atp | Plugin | Crypto exchange features का design | 📦 | ❌ |
| stock-analysis-aisa | Plugin | Stock और crypto scoring | 📦 | ❌ |
| oneconnecter-plugin | Plugin | कई तरह का real-time data | 📦 | ❌ |
| signalslabs | Plugin | Geopolitical signals | 📦 | ⭐ macro |
| Helious | Connector | US macro calendar, yields, releases | ✅ keyless news और calendar; free key पर boards | ⭐⭐⭐ ForexFactory का बैकअप |
| acp-find | Plugin | On-chain agents की खोज | 📦 | ❌ |

## 7. Flash loan, DeFi और smart contract
**कोई अलग flash loan औज़ार नहीं है।** पास की चीज़ें ये हैं। ये इस trading project के नहीं, बल्कि आपके flash loan वाले अलग project के काम की हैं।

| नाम | प्रकार | Flash loan में काम | Free |
|---|---|---|---|
| RugProof | Plugin | `flash-loan-attacks`, `liquidation-cascade`, `mev-frontrunning`, `oracle-manipulation` skills; forge, slither, mythril runners | 📦 |
| solidity-lsp | Plugin | `.sol` फ़ाइलों की diagnostics और autocomplete | 📦 |
| aomi-transact, aomi-build | Plugin | Aave और DEX पर agents बनाना | 📦 |
| defi-skills | Plugin | DeFi intents से unsigned transaction बनाना; private key नहीं माँगता | 📦 |
| 0x | Plugin | ERC-20 swaps की guide | 📦 |
| Etherscan, Blockscout | Connector | Contracts, logs, gas की जाँच | 🔌 |
| barker-stablecoin-skills | Plugin | 500+ protocols के stablecoin yields; listing: free, बिना auth | 📦 |
| aptos-agent-skills | Plugin | Aptos dApps | 📦 |
| multiversx-by-joai | Plugin | MultiversX chain | 📦 |
| jpyc-dev-reference | Plugin | JPYC stablecoin reference | 📦 |
| karma | Plugin | Web3 grants | 📦 |
| XYO & XL1 Integration | Plugin | XL1 dApps | 📦 |

## 8. Wallets, payments, tax और सुरक्षा
इन सबका इस project में कोई उपयोग नहीं। सूची पूरी रखने के लिए दर्ज हैं।

| नाम | प्रकार | क्या करता है | Free |
|---|---|---|---|
| circle-skills | Plugin | USDC payments और wallets की skills | 📦 |
| phantom-connect | Plugin | Phantom wallet और Solana dApps | 📦 |
| coinvoyage-paykit-community | Plugin | Crypto payments लेना | 📦 |
| halliday-payments | Plugin | Crypto deposits और onramps | 📦 |
| mpp-inspector | Plugin | HTTP 402 payment endpoints की जाँच | 📦 |
| open-tax | Plugin | US tax तैयारी, crypto CSV समेत | 📦 |
| paidfor | Connector | x402 sellers की जाँच | 🔌 |
| Agorean | Connector | x402 sellers की reviews | 🔌 |

**ये free हैं, पर असली trade के लिए बने हैं; project paper-only है, इसलिए इन्हें नहीं जोड़ना:** tigerpass, vulcan, revolut-x plugin।

## 9. कीमत साबित नहीं हुई, इसलिए सूची से बाहर
इनका free होना मैं साबित नहीं कर पाया। इन्हें free मत मानिए।

Nansen (tools दिखे, पर call पर API key माँगी), Crypto.com, CoinDesk, Keel, Coinversa Pulse, Blockworks, The Tie, The Big Whale, The Coin Daily, Cryptowisser News, Massive, Stocktwits, Lukka (4 connectors), InfStones, Simple Mining, DollarTrader, DeltaFluency, AIOTA, Eagle Virtual, Chain of Title, Otto AI Stocks, Vibewatch, Nomina, LONA, TEXT TO QUANT, OnChainDiligence, Allium, TRES Finance, Tradefloor।

**Paid होने के कारण हटाए गए:** सिर्फ़ trial या paid plan वाली और प्रति call भुगतान वाली listings।

## 10. हमारे लिए क्या जोड़ें
| क्रम | क्या | क्यों | शर्त |
|---|---|---|---|
| 1 | Buildix + CoinLobster | Setup C में liquidation और funding का असली context | सिर्फ़ review में; signal नहीं |
| 2 | Unlock Pulse | बड़े unlock से पहले coin से दूर रहने का filter | Pre-registered test के बाद ही नियम |
| 3 | CryptoETF | 1d का नया data | Free में 30 दिन का इतिहास, रोज़ जमा करना होगा |
| 4 | DAMO, SatoshiMacro | हमारे regime का स्वतंत्र मिलान | सिर्फ़ तुलना |
| 5 | CryptoKeyhole, Token Terminal | लंबे daily इतिहास पर research | Protocol और SHA lock पहले |
| 6 | Helious, Pyth | Macro calendar और price का बैकअप | PRED-1 का source नहीं बदलेगा |
| 7 | DEBYKO | 22 venues की funding और OI तुलना | Free key आपको बनानी होगी |

**जोड़ने का तरीका:** Settings → Customize → Connectors या Plugins → नाम खोजें → Add। Login या key वाले काम आपको करने होंगे।

## 11. सीमाएँ
- **Directory की खोज fuzzy है और बड़ी खोज में ऊपर के 50 नतीजे ही दिखाती है।** इसलिए 318 शब्द चलाए। फिर भी 100% की गणितीय गारंटी नहीं दी जा सकती; सबूत यह है कि आख़िर में नई crypto listing लगभग मिलनी बंद हो गई।
- **Connector सिर्फ़ Claude की बातचीत में चलते हैं,** हमारे Python loops और cloud VM में नहीं।
- **कुछ endpoints का पता मैंने अंदाज़े या public MCP registry से लगाया।** Pyth, SQD और Token Terminal इसी तरह मिले। Directory वाला connector थोड़ा अलग हो सकता है।
- **📦 का मतलब सिर्फ़ इतना है कि plugin मुफ़्त है।** पीछे की सेवा की सीमा या कीमत अलग हो सकती है।
- **Free की शर्तें बदल सकती हैं।** यह 2 Nov 2026 की स्थिति है। कुछ free plans निजी उपयोग तक सीमित हैं।
- **इन सेवाओं का text बाहरी data है।** Community plugins बाहरी डेवलपरों के हैं; जोड़ने से पहले उनके अधिकार देखें।
- **Skills tab में आपकी अपनी crypto skill कोई नहीं है।** अलग से कोई public skills catalog नहीं मिला; skills plugins के अंदर ही आती हैं।

## 12. स्रोत
- [claude.ai directory](https://claude.ai/directory?q=crypto)
- [claude.com marketplace](https://claude.com/marketplace/connectors-plugins)
- [Community plugin सूची](https://raw.githubusercontent.com/anthropics/claude-plugins-community/main/.claude-plugin/marketplace.json)
- [MCP registry](https://registry.modelcontextprotocol.io/v0/servers)
- [CoinGecko MCP docs](https://docs.coingecko.com/ai-integration/mcp-server)
- [CoinLobster developers](https://coinlobster.com/developers)
- [CryptoKeyhole MCP](https://cryptokeyhole.com/mcp)
- [cryptoetf PyPI](https://pypi.org/project/cryptoetf/)
- [CoinPaprika agent guide](https://coinpaprika.com/api/agent-guide.md)
- [Token Terminal pricing](https://tokenterminal.com/pricing)
- [0xArchive pricing](https://0xarchive.io/pricing)
- [DEBYKO](https://debyko.com)
- [GoldRush pricing](https://goldrush.dev/pricing)
- [Hgraph pricing](https://hgraph.com/pricing)
- [SQD pricing](https://www.sqd.dev/pricing)
- [Helius pricing](https://www.helius.dev/pricing)
- [TraderWAI pricing](https://traderwai.com/pricing)
- [Etherscan MCP docs](https://docs.etherscan.io/build-with-ai/mcp)
- [Twelve Data limits](https://support.twelvedata.com/en/articles/5194820-api-call-limits)
- [Alpha Vantage support](https://alphavantage.co/support/)
- [FMP free plan](https://site.financialmodelingprep.com/developer/docs/blog/how-to-sign-up-and-use-a-free-stock-market-data-api)
- [CoinMarketCap API plans](https://coinmarketcap.com/academy/uk/article/understanding-crypto-api-subscription-models-for-traders-in-2026)

यह research है, निवेश सलाह नहीं। मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।
