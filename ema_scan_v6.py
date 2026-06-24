#!/usr/bin/env python3
"""
Early Trend Scanner v3.0
- All v2.3 functionality preserved
- NEW: Drill-down panel per flagged ETF showing top holdings ranked by momentum
- Holdings data: top 10-15 per ETF (hardcoded from ETF providers)
- Per-holding metrics: momentum score, EMA stack, RS vs SPY, 1W/1M/3M perf, 52W high proximity
- Click holding card → mini sparkline chart + stats overlay
"""

import os, sys, json
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

# ── Universe ─────────────────────────────────────────────────────────────────
TICKERS = {
    "US Sectors": {
        "XLB":  "Materials Select Sector",
        "XLC":  "Communication Services Select Sector",
        "XLE":  "Energy Select Sector",
        "XLF":  "Financial Select Sector",
        "XLI":  "Industrial Select Sector",
        "XLK":  "Technology Select Sector",
        "XLP":  "Consumer Staples Select Sector",
        "XLRE": "Real Estate Select Sector",
        "XLU":  "Utilities Select Sector",
        "XLV":  "Health Care Select Sector",
        "XLY":  "Consumer Discretionary Select Sector",
        "XHB":  "SPDR S&P Homebuilders",
        "XRT":  "SPDR S&P Retail",
        "KBE":  "SPDR S&P Bank",
        "KRE":  "SPDR S&P Regional Banking",
    },
    "Global / Regional": {
        "MCHI": "iShares MSCI China",
        "EIS":  "iShares MSCI Israel",
        "ECH":  "iShares MSCI Chile",
        "EEM":  "iShares MSCI Emerging Markets",
        "EMXC": "iShares MSCI EM ex China",
        "EWZ":  "iShares MSCI Brazil",
        "EWJ":  "iShares MSCI Japan",
        "EWY":  "iShares MSCI South Korea",
        "EWT":  "iShares MSCI Taiwan",
        "VWO":  "Vanguard FTSE Emerging Markets",
        "IEMG": "iShares MSCI Emerging Markets",
        "EFA":  "iShares MSCI EAFE",
        "VEA":  "Vanguard FTSE Developed Markets",
        "EWG":  "iShares MSCI Germany",
        "EWU":  "iShares MSCI United Kingdom",
        "EWC":  "iShares MSCI Canada",
        "EWA":  "iShares MSCI Australia",
        "EWH":  "iShares MSCI Hong Kong",
        "INDA": "iShares MSCI India",
    },
    "Commodities": {
        "GLD":  "SPDR Gold Shares",
        "SLV":  "iShares Silver Trust",
        "GDX":  "VanEck Gold Miners",
        "GDXJ": "VanEck Junior Gold Miners",
        "USO":  "United States Oil Fund",
        "UNG":  "United States Natural Gas Fund",
        "PDBC": "Invesco Optimum Yield Diversified Commodity",
        "DBA":  "Invesco DB Agriculture Fund",
        "MOO":  "VanEck Agribusiness",
    },
    "Crypto ETFs": {
        "BITO": "ProShares Bitcoin Strategy",
        "IBIT": "iShares Bitcoin Trust",
        "FBTC": "Fidelity Wise Origin Bitcoin",
        "ARKB": "ARK 21Shares Bitcoin",
        "GBTC": "Grayscale Bitcoin Trust",
    },
    "Thematic / Tech": {
        "QQQ":  "Invesco QQQ (Nasdaq-100)",
        "ARKK": "ARK Innovation",
        "BOTZ": "Global X Robotics & AI",
        "HUMN": "Defiance Humanoid Robotics",
        "BOTT": "iShares Robotics & AI Multisector",
        "ROBO": "ROBO Global Robotics & Automation",
        "SOXX": "iShares Semiconductor",
        "SMH":  "VanEck Semiconductor",
        "DRAM": "Roundhill Memory ETF",
        "ICLN": "iShares Global Clean Energy",
        "TAN":  "Invesco Solar",
        "BLOK": "Amplify Transformational Data Sharing",
        "FINX": "Global X FinTech",
        "KWEB": "KraneShares China Internet",
    },
    "Energy (Thematic)": {
        "XOP":  "SPDR S&P Oil & Gas Exploration & Production",
        "OIH":  "VanEck Oil Services",
        "AMLP": "Alerian MLP ETF",
    },
    "Defense & Aerospace": {
        "ITA":  "iShares U.S. Aerospace & Defense",
        "SHLD": "Global X Defense Tech",
    },
    "Healthcare (Thematic)": {
        "IBB":  "iShares Biotechnology",
        "XBI":  "SPDR S&P Biotech",
        "IHI":  "iShares U.S. Medical Devices",
        "IHF":  "iShares U.S. Healthcare Providers",
    },
    "Infrastructure & Real Assets": {
        "PAVE": "Global X U.S. Infrastructure Development",
        "IGF":  "iShares Global Infrastructure",
    },
    "Nuclear & Uranium": {
        "URA":  "Global X Uranium",
    },
    "Water": {
        "PHO":  "Invesco Water Resources",
    },
    "Bonds / Macro": {
        "TLT":  "iShares 20+ Year Treasury Bond",
        "IEF":  "iShares 7-10 Year Treasury Bond",
        "SHY":  "iShares 1-3 Year Treasury Bond",
        "HYG":  "iShares iBoxx High Yield Corporate Bond",
        "EMB":  "iShares JP Morgan USD Emerging Markets Bond",
        "UUP":  "Invesco DB US Dollar Index Bullish",
    },
}

# ── Holdings map (top ~12 per ETF, US-tradeable tickers where available) ─────
# Korean/Taiwanese stocks listed as ADRs or US-listed where possible;
# otherwise native tickers (yfinance supports many KRX/TSE tickers)
HOLDINGS = {
    # US Sectors
    "XLB":  [("LIN","Linde"),("APD","Air Products"),("SHW","Sherwin-Williams"),("ECL","Ecolab"),("NEM","Newmont"),("FCX","Freeport-McMoRan"),("PPG","PPG Industries"),("NUE","Nucor"),("VMC","Vulcan Materials"),("IP","International Paper")],
    "XLC":  [("META","Meta Platforms"),("GOOGL","Alphabet A"),("GOOG","Alphabet C"),("NFLX","Netflix"),("T","AT&T"),("VZ","Verizon"),("TMUS","T-Mobile"),("DIS","Walt Disney"),("ATVI","Activision Blizzard"),("EA","Electronic Arts")],
    "XLE":  [("XOM","ExxonMobil"),("CVX","Chevron"),("COP","ConocoPhillips"),("EOG","EOG Resources"),("SLB","SLB"),("MPC","Marathon Petroleum"),("PSX","Phillips 66"),("PXD","Pioneer Natural Resources"),("VLO","Valero Energy"),("OXY","Occidental Petroleum")],
    "XLF":  [("BRK-B","Berkshire Hathaway"),("JPM","JPMorgan Chase"),("V","Visa"),("MA","Mastercard"),("BAC","Bank of America"),("WFC","Wells Fargo"),("GS","Goldman Sachs"),("MS","Morgan Stanley"),("SPGI","S&P Global"),("AXP","American Express")],
    "XLI":  [("GE","GE Aerospace"),("RTX","RTX Corp"),("CAT","Caterpillar"),("HON","Honeywell"),("UPS","UPS"),("BA","Boeing"),("DE","Deere & Co"),("LMT","Lockheed Martin"),("UNP","Union Pacific"),("ETN","Eaton")],
    "XLK":  [("MSFT","Microsoft"),("AAPL","Apple"),("NVDA","Nvidia"),("AVGO","Broadcom"),("AMD","AMD"),("CRM","Salesforce"),("ORCL","Oracle"),("INTC","Intel"),("QCOM","Qualcomm"),("ACN","Accenture")],
    "XLP":  [("PG","Procter & Gamble"),("KO","Coca-Cola"),("PEP","PepsiCo"),("COST","Costco"),("WMT","Walmart"),("PM","Philip Morris"),("MO","Altria"),("MDLZ","Mondelez"),("CL","Colgate-Palmolive"),("KHC","Kraft Heinz")],
    "XLRE": [("PLD","Prologis"),("AMT","American Tower"),("EQIX","Equinix"),("CCI","Crown Castle"),("PSA","Public Storage"),("O","Realty Income"),("WELL","Welltower"),("DLR","Digital Realty"),("AVB","AvalonBay"),("EQR","Equity Residential")],
    "XLU":  [("NEE","NextEra Energy"),("SO","Southern Co"),("DUK","Duke Energy"),("AEP","American Electric Power"),("SRE","Sempra"),("D","Dominion Energy"),("EXC","Exelon"),("PCG","PG&E"),("XEL","Xcel Energy"),("ED","Consolidated Edison")],
    "XLV":  [("LLY","Eli Lilly"),("UNH","UnitedHealth"),("JNJ","Johnson & Johnson"),("ABBV","AbbVie"),("MRK","Merck"),("TMO","Thermo Fisher"),("ABT","Abbott"),("DHR","Danaher"),("BMY","Bristol-Myers Squibb"),("AMGN","Amgen")],
    "XLY":  [("AMZN","Amazon"),("TSLA","Tesla"),("HD","Home Depot"),("MCD","McDonald's"),("NKE","Nike"),("LOW","Lowe's"),("SBUX","Starbucks"),("TJX","TJX Companies"),("BKNG","Booking Holdings"),("CMG","Chipotle")],
    "XHB":  [("DHI","D.R. Horton"),("LEN","Lennar"),("PHM","PulteGroup"),("NVR","NVR Inc"),("TOL","Toll Brothers"),("BLDR","Builders FirstSource"),("MHO","M/I Homes"),("IBP","Installed Building Products"),("TPH","Tri Pointe Homes"),("SKY","Skyline Champion")],
    "XRT":  [("AMZN","Amazon"),("TGT","Target"),("WMT","Walmart"),("COST","Costco"),("TJX","TJX Companies"),("ROST","Ross Stores"),("DG","Dollar General"),("DLTR","Dollar Tree"),("BBY","Best Buy"),("KSS","Kohl's")],
    "KBE":  [("JPM","JPMorgan Chase"),("BAC","Bank of America"),("WFC","Wells Fargo"),("C","Citigroup"),("USB","U.S. Bancorp"),("TFC","Truist Financial"),("PNC","PNC Financial"),("COF","Capital One"),("KEY","KeyCorp"),("CFG","Citizens Financial")],
    "KRE":  [("EWBC","East West Bancorp"),("IBOC","International Bancshares"),("WBS","Webster Financial"),("UMBF","UMB Financial"),("HBAN","Huntington Bancshares"),("RF","Regions Financial"),("CFG","Citizens Financial"),("FHN","First Horizon"),("SNV","Synovus Financial"),("CVBF","CVB Financial")],
    # Global / Regional
    "MCHI": [("BABA","Alibaba"),("TCEHY","Tencent"),("JD","JD.com"),("BIDU","Baidu"),("NIO","NIO"),("PDD","PDD Holdings"),("XPEV","XPeng"),("LI","Li Auto"),("NTES","NetEase"),("9988.HK","Alibaba HK")],
    "EIS":  [("CHKP","Check Point Software"),("NICE","NICE Systems"),("TEVA","Teva Pharmaceutical"),("MNDY","Monday.com"),("WIX","Wix.com"),("CYBR","CyberArk"),("GLBE","Global-E Online"),("DSGX","Descartes Systems"),("ESLT","Elbit Systems"),("CEVA","CEVA Inc")],
    "ECH":  [("SQM","SQM"),("ENELCHILE.SN","Enel Chile"),("LTM.SN","LATAM Airlines"),("COPEC.SN","Empresas Copec"),("FALABELLA.SN","Falabella"),("CCU","CCU"),("CMPC.SN","CMPC"),("CAP.SN","CAP"),("BSANTANDER.SN","Banco Santander Chile"),("CHILE.SN","Banco de Chile")],
    "EEM":  [("TSM","Taiwan Semiconductor"),("SAMSUNG","Samsung (via 005930.KS)"),("TCEHY","Tencent"),("BABA","Alibaba"),("RELIANCE.NS","Reliance Industries"),("2330.TW","TSMC Taiwan"),("005930.KS","Samsung Electronics"),("000660.KS","SK Hynix"),("INFY","Infosys"),("PDD","PDD Holdings")],
    "EMXC": [("TSM","Taiwan Semiconductor"),("2330.TW","TSMC Taiwan"),("005930.KS","Samsung Electronics"),("000660.KS","SK Hynix"),("RELIANCE.NS","Reliance Industries"),("INFY","Infosys"),("ITUB","Itaú Unibanco"),("TCS.NS","Tata Consultancy"),("VALE","Vale"),("HDB","HDFC Bank")],
    "EWZ":  [("VALE","Vale"),("ITUB","Itaú Unibanco"),("PETR4.SA","Petrobras"),("BBDC4.SA","Bradesco"),("B3SA3.SA","B3"),("ABEV3.SA","Ambev"),("WEGE3.SA","WEG"),("RENT3.SA","Localiza"),("RDOR3.SA","Rede D'Or"),("BBAS3.SA","Banco do Brasil")],
    "EWJ":  [("TM","Toyota"),("SONY","Sony"),("7203.T","Toyota Japan"),("6758.T","Sony Japan"),("9984.T","SoftBank"),("7974.T","Nintendo"),("6861.T","Keyence"),("8306.T","Mitsubishi UFJ"),("9432.T","NTT"),("4063.T","Shin-Etsu Chemical")],
    "EWY":  [("005930.KS","Samsung Electronics"),("000660.KS","SK Hynix"),("035420.KS","NAVER"),("005380.KS","Hyundai Motor"),("051910.KS","LG Chem"),("000270.KS","Kia"),("068270.KS","Celltrion"),("035720.KS","Kakao"),("105560.KS","KB Financial"),("055550.KS","Shinhan Financial")],
    "EWT":  [("TSM","Taiwan Semiconductor (US)"),("2330.TW","TSMC"),("2317.TW","Hon Hai/Foxconn"),("2454.TW","MediaTek"),("2308.TW","Delta Electronics"),("2382.TW","Quanta Computer"),("3711.TW","ASE Technology"),("2303.TW","United Microelectronics"),("2412.TW","Chunghwa Telecom"),("2881.TW","Fubon Financial")],
    "VWO":  [("TSM","Taiwan Semiconductor"),("TCEHY","Tencent"),("005930.KS","Samsung Electronics"),("BABA","Alibaba"),("RELIANCE.NS","Reliance Industries"),("VALE","Vale"),("ITUB","Itaú Unibanco"),("PDD","PDD Holdings"),("INFY","Infosys"),("HDB","HDFC Bank")],
    "IEMG": [("TSM","Taiwan Semiconductor"),("2330.TW","TSMC Taiwan"),("TCEHY","Tencent"),("005930.KS","Samsung Electronics"),("BABA","Alibaba"),("RELIANCE.NS","Reliance Industries"),("000660.KS","SK Hynix"),("PDD","PDD Holdings"),("INFY","Infosys"),("HDB","HDFC Bank")],
    "EFA":  [("NESN.SW","Nestle"),("NOVN.SW","Novartis"),("ROG.SW","Roche"),("ASML","ASML"),("TM","Toyota"),("SAP","SAP"),("LVMH.PA","LVMH"),("SHEL","Shell"),("AZN","AstraZeneca"),("HSBC","HSBC")],
    "VEA":  [("ASML","ASML"),("NESN.SW","Nestle"),("NOVN.SW","Novartis"),("TM","Toyota"),("SAP","SAP"),("SHEL","Shell"),("AZN","AstraZeneca"),("HSBC","HSBC"),("BP","BP"),("RIO","Rio Tinto")],
    "EWG":  [("SAP","SAP"),("SIE.DE","Siemens"),("ALV.DE","Allianz"),("DTE.DE","Deutsche Telekom"),("MBG.DE","Mercedes-Benz"),("BMW.DE","BMW"),("BAS.DE","BASF"),("MUV2.DE","Munich Re"),("BAYN.DE","Bayer"),("DBK.DE","Deutsche Bank")],
    "EWU":  [("SHEL","Shell"),("AZN","AstraZeneca"),("HSBC","HSBC"),("ULVR.L","Unilever"),("BP","BP"),("RIO","Rio Tinto"),("GSK","GSK"),("LSEG.L","London Stock Exchange"),("BHP","BHP"),("DGE.L","Diageo")],
    "EWC":  [("SHOP","Shopify"),("RY","Royal Bank of Canada"),("TD","TD Bank"),("CNR.TO","Canadian National Railway"),("ENB","Enbridge"),("BNS","Scotiabank"),("BMO","Bank of Montreal"),("CP","Canadian Pacific"),("TRP","TC Energy"),("BCE","BCE")],
    "EWA":  [("BHP","BHP"),("CBA.AX","Commonwealth Bank"),("RIO","Rio Tinto"),("CSL.AX","CSL"),("NAB.AX","NAB"),("WBC.AX","Westpac"),("ANZ.AX","ANZ"),("MQG.AX","Macquarie"),("WES.AX","Wesfarmers"),("TLS.AX","Telstra")],
    "EWH":  [("0005.HK","HSBC HK"),("0700.HK","Tencent"),("0939.HK","CCB"),("1398.HK","ICBC"),("0388.HK","HK Exchange"),("0941.HK","China Mobile"),("1299.HK","AIA Group"),("2318.HK","Ping An"),("0883.HK","CNOOC"),("0011.HK","Hang Seng Bank")],
    "INDA": [("RELIANCE.NS","Reliance Industries"),("INFY","Infosys"),("HDB","HDFC Bank"),("IBN","ICICI Bank"),("WIT","Wipro"),("TATAMOTORS.NS","Tata Motors"),("HDFCBANK.NS","HDFC Bank India"),("TCS.NS","Tata Consultancy"),("HINDUNILVR.NS","Hindustan Unilever"),("BAJFINANCE.NS","Bajaj Finance")],
    # Commodities
    "GLD":  [("NEM","Newmont"),("GOLD","Barrick Gold"),("AEM","Agnico Eagle"),("WPM","Wheaton Precious Metals"),("FNV","Franco-Nevada"),("KGC","Kinross Gold"),("AGI","Alamos Gold"),("OR","Osisko Gold"),("RGLD","Royal Gold"),("BTG","B2Gold")],
    "SLV":  [("WPM","Wheaton Precious Metals"),("PAAS","Pan American Silver"),("SILV","SilverCrest Metals"),("AG","First Majestic Silver"),("HL","Hecla Mining"),("CDE","Coeur Mining"),("MAG","MAG Silver"),("SSRM","SSR Mining"),("FSM","Fortuna Silver"),("EXK","Endeavour Silver")],
    "GDX":  [("NEM","Newmont"),("GOLD","Barrick Gold"),("AEM","Agnico Eagle"),("WPM","Wheaton Precious Metals"),("KGC","Kinross Gold"),("AGI","Alamos Gold"),("PAAS","Pan American Silver"),("OR","Osisko Gold"),("BTG","B2Gold"),("EDV","Endeavour Mining")],
    "GDXJ": [("AGI","Alamos Gold"),("OR","Osisko Gold"),("PAAS","Pan American Silver"),("KGC","Kinross Gold"),("BTG","B2Gold"),("MAG","MAG Silver"),("CDE","Coeur Mining"),("SILV","SilverCrest Metals"),("SSL","Sandstorm Gold"),("ASA","ASA Gold")],
    "USO":  [("XOM","ExxonMobil"),("CVX","Chevron"),("COP","ConocoPhillips"),("OXY","Occidental Petroleum"),("EOG","EOG Resources"),("PXD","Pioneer Natural Resources"),("DVN","Devon Energy"),("MRO","Marathon Oil"),("APA","APA Corp"),("FANG","Diamondback Energy")],
    "UNG":  [("EQT","EQT Corp"),("AR","Antero Resources"),("RRC","Range Resources"),("SWN","Southwestern Energy"),("CNX","CNX Resources"),("CTRA","Coterra Energy"),("CHK","Chesapeake Energy"),("CRK","Comstock Resources"),("GPOR","Gulfport Energy"),("KMI","Kinder Morgan")],
    "PDBC": [("XOM","ExxonMobil"),("CVX","Chevron"),("GLD","SPDR Gold"),("SLV","Silver Trust"),("DBA","Agriculture Fund"),("DBB","Base Metals"),("UNG","Natural Gas"),("CORN","Corn Fund"),("WEAT","Wheat Fund"),("SOYB","Soybean Fund")],
    "DBA":  [("DE","Deere & Co"),("ADM","Archer-Daniels-Midland"),("BG","Bunge"),("MOS","Mosaic"),("NTR","Nutrien"),("CF","CF Industries"),("FMC","FMC Corp"),("ICL","ICL Group"),("CTVA","Corteva"),("CORN","Teucrium Corn")],
    "MOO":  [("DE","Deere & Co"),("NTR","Nutrien"),("ADM","Archer-Daniels-Midland"),("MOS","Mosaic"),("CF","CF Industries"),("CTVA","Corteva"),("BG","Bunge"),("FMC","FMC Corp"),("AGCO","AGCO Corp"),("SYT","Syngenta")],
    # Crypto ETFs
    "BITO": [("MSTR","MicroStrategy"),("COIN","Coinbase"),("MARA","Marathon Digital"),("RIOT","Riot Platforms"),("CLSK","CleanSpark"),("BTBT","Bit Digital"),("HUT","Hut 8"),("BITF","Bitfarms"),("CIFR","Cipher Mining"),("WGMI","Valkyrie Bitcoin Miners")],
    "IBIT": [("MSTR","MicroStrategy"),("COIN","Coinbase"),("MARA","Marathon Digital"),("RIOT","Riot Platforms"),("CLSK","CleanSpark"),("HUT","Hut 8"),("BITF","Bitfarms"),("BTBT","Bit Digital"),("CIFR","Cipher Mining"),("SQ","Block Inc")],
    "FBTC": [("MSTR","MicroStrategy"),("COIN","Coinbase"),("MARA","Marathon Digital"),("RIOT","Riot Platforms"),("CLSK","CleanSpark"),("HUT","Hut 8"),("SQ","Block Inc"),("PYPL","PayPal"),("BITF","Bitfarms"),("BTBT","Bit Digital")],
    "ARKB": [("MSTR","MicroStrategy"),("COIN","Coinbase"),("SQ","Block Inc"),("HOOD","Robinhood"),("MARA","Marathon Digital"),("RIOT","Riot Platforms"),("CLSK","CleanSpark"),("HUT","Hut 8"),("BITF","Bitfarms"),("BTBT","Bit Digital")],
    "GBTC": [("MSTR","MicroStrategy"),("COIN","Coinbase"),("MARA","Marathon Digital"),("RIOT","Riot Platforms"),("CLSK","CleanSpark"),("HUT","Hut 8"),("BITF","Bitfarms"),("BTBT","Bit Digital"),("CIFR","Cipher Mining"),("SQ","Block Inc")],
    # Thematic / Tech
    "QQQ":  [("MSFT","Microsoft"),("AAPL","Apple"),("NVDA","Nvidia"),("AMZN","Amazon"),("META","Meta"),("GOOGL","Alphabet A"),("GOOG","Alphabet C"),("TSLA","Tesla"),("AVGO","Broadcom"),("COST","Costco")],
    "ARKK": [("TSLA","Tesla"),("COIN","Coinbase"),("ROKU","Roku"),("SQ","Block Inc"),("HOOD","Robinhood"),("PATH","UiPath"),("EXAS","Exact Sciences"),("TWLO","Twilio"),("CRSP","CRISPR Therapeutics"),("BEAM","Beam Therapeutics")],
    "BOTZ": [("NVDA","Nvidia"),("ISRG","Intuitive Surgical"),("ABB","ABB Ltd"),("FANUY","Fanuc"),("KEYENCE","Keyence (6861.T)"),("IRBT","iRobot"),("ZBRA","Zebra Technologies"),("BRKS","Brooks Automation"),("MKFG","Markforged"),("RBOT","Vicarious Surgical")],
    "HUMN": [("NVDA","Nvidia"),("TSLA","Tesla"),("GOOGL","Alphabet"),("MSFT","Microsoft"),("AMZN","Amazon"),("INTC","Intel"),("QCOM","Qualcomm"),("AMD","AMD"),("TER","Teradyne"),("ISRG","Intuitive Surgical")],
    "BOTT": [("NVDA","Nvidia"),("ISRG","Intuitive Surgical"),("ABB","ABB Ltd"),("TER","Teradyne"),("ZBRA","Zebra Technologies"),("BRKS","Brooks Automation"),("IRBT","iRobot"),("RMBS","Rambus"),("AIXI","Xiao-I Corp"),("RBOT","Vicarious Surgical")],
    "ROBO": [("ISRG","Intuitive Surgical"),("ABB","ABB Ltd"),("CGNX","Cognex"),("TER","Teradyne"),("ZBRA","Zebra Technologies"),("BRKS","Brooks Automation"),("IRBT","iRobot"),("NNDM","Nano Dimension"),("MKFG","Markforged"),("RRX","Rexnord")],
    "SOXX": [("NVDA","Nvidia"),("AMD","AMD"),("AVGO","Broadcom"),("QCOM","Qualcomm"),("MU","Micron"),("INTC","Intel"),("AMAT","Applied Materials"),("LRCX","Lam Research"),("KLAC","KLA Corp"),("MRVL","Marvell Technology")],
    "SMH":  [("NVDA","Nvidia"),("TSM","TSMC"),("AVGO","Broadcom"),("ASML","ASML"),("AMD","AMD"),("QCOM","Qualcomm"),("MU","Micron"),("AMAT","Applied Materials"),("LRCX","Lam Research"),("KLAC","KLA Corp")],
    "DRAM": [("005930.KS","Samsung Electronics"),("000660.KS","SK Hynix"),("MU","Micron Technology"),("WDC","Western Digital"),("STX","Seagate Technology"),("SNDK","SanDisk"),("KIOXIA.T","Kioxia Holdings"),("NAND","Solidigm/Memory ecosystem"),("AMAT","Applied Materials"),("LRCX","Lam Research")],
    "ICLN": [("NEE","NextEra Energy"),("ENPH","Enphase Energy"),("RUN","Sunrun"),("SEDG","SolarEdge"),("FSLR","First Solar"),("BEP","Brookfield Renewable"),("CWEN","Clearway Energy"),("AES","AES Corp"),("PLUG","Plug Power"),("BE","Bloom Energy")],
    "TAN":  [("ENPH","Enphase Energy"),("FSLR","First Solar"),("SEDG","SolarEdge"),("RUN","Sunrun"),("ARRY","Array Technologies"),("CSIQ","Canadian Solar"),("MAXN","Maxeon Solar"),("JKS","JinkoSolar"),("DQ","Daqo New Energy"),("SPWR","SunPower")],
    "BLOK": [("MSTR","MicroStrategy"),("COIN","Coinbase"),("MARA","Marathon Digital"),("RIOT","Riot Platforms"),("SQ","Block Inc"),("PYPL","PayPal"),("IBM","IBM"),("HIVE","HIVE Blockchain"),("BTBT","Bit Digital"),("HUT","Hut 8")],
    "FINX": [("SQ","Block Inc"),("PYPL","PayPal"),("HOOD","Robinhood"),("AFRM","Affirm"),("SOFI","SoFi Technologies"),("UPST","Upstart"),("OPEN","Opendoor"),("GDOT","Green Dot"),("LPRO","Open Lending"),("FOUR","Shift4 Payments")],
    "KWEB": [("BABA","Alibaba"),("TCEHY","Tencent"),("JD","JD.com"),("BIDU","Baidu"),("PDD","PDD Holdings"),("NTES","NetEase"),("XPEV","XPeng"),("NIO","NIO"),("LI","Li Auto"),("TIGR","UP Fintech")],
    # Energy (Thematic)
    "XOP":  [("MPC","Marathon Petroleum"),("VLO","Valero Energy"),("OXY","Occidental Petroleum"),("DVN","Devon Energy"),("FANG","Diamondback Energy"),("EOG","EOG Resources"),("COP","ConocoPhillips"),("APA","APA Corp"),("MRO","Marathon Oil"),("HES","Hess Corp")],
    "OIH":  [("SLB","SLB"),("HAL","Halliburton"),("BKR","Baker Hughes"),("FTI","TechnipFMC"),("NOV","NOV Inc"),("HP","Helmerich & Payne"),("WTTR","Select Water Solutions"),("RES","RPC Inc"),("LBRT","Liberty Energy"),("NR","Newpark Resources")],
    "AMLP": [("EPD","Enterprise Products Partners"),("ET","Energy Transfer"),("MPLX","MPLX LP"),("PAA","Plains All American"),("WMB","Williams Companies"),("OKE","ONEOK"),("KMI","Kinder Morgan"),("DCP","DCP Midstream"),("TRGP","Targa Resources"),("LNG","Cheniere Energy")],
    # Defense & Aerospace
    "ITA":  [("RTX","RTX Corp"),("LMT","Lockheed Martin"),("NOC","Northrop Grumman"),("GD","General Dynamics"),("BA","Boeing"),("GE","GE Aerospace"),("HII","Huntington Ingalls"),("TXT","Textron"),("HEI","HEICO Corp"),("LDOS","Leidos")],
    "SHLD": [("RTX","RTX Corp"),("LMT","Lockheed Martin"),("NOC","Northrop Grumman"),("GD","General Dynamics"),("PLTR","Palantir"),("BA","Boeing"),("HII","Huntington Ingalls"),("LDOS","Leidos"),("CACI","CACI International"),("SAIC","Science Applications")],
    # Healthcare (Thematic)
    "IBB":  [("AMGN","Amgen"),("GILD","Gilead Sciences"),("VRTX","Vertex Pharmaceuticals"),("REGN","Regeneron"),("BIIB","Biogen"),("MRNA","Moderna"),("ILMN","Illumina"),("ALNY","Alnylam Pharmaceuticals"),("SGEN","Seagen"),("BMRN","BioMarin")],
    "XBI":  [("EXAS","Exact Sciences"),("RGEN","Repligen"),("NKTR","Nektar Therapeutics"),("FOLD","Amicus Therapeutics"),("KRYS","Krystal Biotech"),("RXRX","Recursion Pharma"),("ARDX","Ardelyx"),("ACAD","ACADIA Pharmaceuticals"),("INVA","Innoviva"),("PTGX","Protagonist Therapeutics")],
    "IHI":  [("ABT","Abbott"),("MDT","Medtronic"),("ISRG","Intuitive Surgical"),("SYK","Stryker"),("BSX","Boston Scientific"),("EW","Edwards Lifesciences"),("BDX","Becton Dickinson"),("ZBH","Zimmer Biomet"),("HOLX","Hologic"),("NVCR","NovoCure")],
    "IHF":  [("UNH","UnitedHealth"),("ELV","Elevance Health"),("CVS","CVS Health"),("CI","Cigna"),("HUM","Humana"),("CNC","Centene"),("MOH","Molina Healthcare"),("DVA","DaVita"),("THC","Tenet Healthcare"),("HCA","HCA Healthcare")],
    # Infrastructure
    "PAVE": [("VMC","Vulcan Materials"),("MLM","Martin Marietta"),("NUE","Nucor"),("STLD","Steel Dynamics"),("URI","United Rentals"),("PWR","Quanta Services"),("EME","EMCOR Group"),("FAST","Fastenal"),("GWW","W.W. Grainger"),("CARR","Carrier Global")],
    "IGF":  [("NEE","NextEra Energy"),("AEE","Ameren"),("WM","Waste Management"),("ENB","Enbridge"),("ATO","Atmos Energy"),("CCI","Crown Castle"),("AMT","American Tower"),("D","Dominion Energy"),("WEC","WEC Energy"),("ES","Eversource Energy")],
    # Nuclear & Uranium
    "URA":  [("CCJ","Cameco"),("NXE","NexGen Energy"),("DNN","Denison Mines"),("UEC","Uranium Energy Corp"),("UUUU","Energy Fuels"),("URG","Ur-Energy"),("PALAF","Paladin Energy"),("BHP","BHP Group"),("BWXT","BWX Technologies"),("CEG","Constellation Energy")],
    # Water
    "PHO":  [("XYLEM","Xylem"),("AWK","American Water Works"),("WMS","Advanced Drainage Systems"),("RXO","RXO Inc"),("ITRI","Itron"),("FELE","Franklin Electric"),("AWR","American States Water"),("CWT","California Water Service"),("MSEX","Middlesex Water"),("YORW","York Water")],
    "TLT":  [("TBT","ProShares UltraShort 20+ Treasury"),("TMF","Direxion 20+ Treasury Bull 3x"),("VGLT","Vanguard Long-Term Treasury"),("EDV","Vanguard Extended Duration"),("ZROZ","PIMCO 25+ Year Zero Coupon"),("IEF","7-10yr Treasury"),("SHY","1-3yr Treasury"),("BND","Vanguard Total Bond"),("GOVT","iShares US Treasury"),("TIP","TIPS")],
    "IEF":  [("SHY","iShares 1-3yr Treasury"),("TLT","iShares 20+yr Treasury"),("BND","Vanguard Total Bond"),("VGIT","Vanguard Intermediate Treasury"),("TIP","TIPS"),("GOVT","iShares US Treasury"),("IGIB","Corp Bond"),("LQD","Investment Grade Corp"),("AGG","US Aggregate Bond"),("SCHZ","Schwab US Aggregate Bond")],
    "SHY":  [("BIL","SPDR 1-3 Month T-Bill"),("SHV","iShares Short Treasury"),("SGOV","iShares 0-3M Treasury"),("TBIL","US 3M T-Bill"),("TFLO","iShares Treasury Floating"),("USFR","WisdomTree Floating Rate"),("JPST","JPMorgan Ultra-Short Income"),("MINT","PIMCO Enhanced Short Maturity"),("FLOT","iShares Floating Rate Bond"),("GSY","Invesco Ultra Short Duration")],
    "HYG":  [("JNK","SPDR High Yield Bond"),("USHY","iShares Broad USD High Yield"),("SJNK","SPDR Short Term High Yield"),("ANGL","VanEck Fallen Angel HY"),("FALN","iShares Fallen Angels USD Bond"),("PHB","Invesco Fundamental High Yield"),("HYEM","VanEck EM High Yield Bond"),("BSJP","Invesco BulletShares 2025 HY"),("BSJQ","Invesco BulletShares 2026 HY"),("HYLB","Xtrackers USD High Yield")],
    "EMB":  [("VWOB","Vanguard EM Gov Bond"),("PCY","Invesco EM Sovereign Debt"),("LEMB","iShares EM Local Currency Bond"),("EBND","SPDR Bloomberg EM Local Bond"),("HYEM","VanEck EM High Yield Bond"),("EMHY","iShares EM High Yield Bond"),("EMCD","VanEck EM Investment Grade + BB"),("EMAG","VanEck EM Aggregate Bond"),("EMXC","iShares MSCI EM ex-China"),("EEM","iShares MSCI Emerging Markets")],
    "UUP":  [("FXE","Invesco Euro Currency"),("FXY","Invesco Japanese Yen"),("FXB","Invesco British Pound"),("FXF","Invesco Swiss Franc"),("FXC","Invesco Canadian Dollar"),("FXA","Invesco Australian Dollar"),("CYB","WisdomTree Chinese Yuan"),("CEW","WisdomTree EM Currency"),("DBV","Invesco G10 Currency Carry"),("USDU","WisdomTree Bloomberg Dollar")],
}

BENCHMARK = "SPY"

# ── Data fetch ────────────────────────────────────────────────────────────────
def fetch_close(ticker, period_days=500):
    try:
        end   = datetime.today()
        start = end - timedelta(days=period_days)
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if df.empty:
            return None
        close = df["Close"].squeeze()
        close = close[~close.index.duplicated(keep="last")].sort_index()
        return close if len(close) >= 150 else None
    except Exception as e:
        print(f"  [fetch error] {ticker}: {e}")
        return None

# ── ETF signal analysis (unchanged from v2.3) ────────────────────────────────
def analyse(close, spy_close):
    if len(close) < 220:
        return None
    ema100 = close.ewm(span=100, adjust=False).mean()
    ema150 = close.ewm(span=150, adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()
    price_now  = close.iloc[-1]
    ema100_now = ema100.iloc[-1]
    ema150_now = ema150.iloc[-1]
    ema200_now = ema200.iloc[-1]
    if price_now <= ema200_now:
        return None
    ema200_slope = (ema200.iloc[-1] - ema200.iloc[-10]) / ema200.iloc[-10]
    if ema200_slope < -0.002:
        return None
    above200 = (close > ema200).astype(int)
    last_idx = len(above200) - 1
    cutoff   = last_idx - 20
    reclaim_idx = None
    for i in range(last_idx, max(cutoff, 1), -1):
        if above200.iloc[i] == 1 and above200.iloc[i - 1] == 0:
            days_below = 0
            for j in range(i - 1, max(i - 20, 0), -1):
                if above200.iloc[j] == 0:
                    days_below += 1
                else:
                    break
            if days_below >= 5:
                reclaim_idx = i
                break
    if reclaim_idx is None:
        return None
    days_since_reclaim = last_idx - reclaim_idx
    reclaim_price = close.iloc[reclaim_idx]
    extension_pct = (price_now / reclaim_price - 1) * 100
    if extension_pct > 20:
        return None
    common = close.index.intersection(spy_close.index)
    if len(common) < 50:
        return None
    c   = close.reindex(common)
    spy = spy_close.reindex(common)
    rs_now  = (c.iloc[-1]  / c.iloc[-21]  - 1) - (spy.iloc[-1]  / spy.iloc[-21]  - 1)
    rs_prev = (c.iloc[-25] / c.iloc[-46]  - 1) - (spy.iloc[-25] / spy.iloc[-46]  - 1)
    rs_flipped            = (rs_prev < 0) and (rs_now > 0)
    rs_strongly_improving = (rs_now - rs_prev) > 0.04
    if not (rs_flipped or rs_strongly_improving):
        return None
    pre_start  = max(reclaim_idx - 60, 0)
    pre_window = close.iloc[pre_start:reclaim_idx]
    if len(pre_window) < 20:
        return None
    range_ratio = pre_window.max() / pre_window.min()
    if range_ratio >= 1.20:
        return None
    above100 = price_now > ema100_now
    above150 = price_now > ema150_now
    if above100 and above150:
        ema_mode = "strict"
    elif above150:
        ema_mode = "medium150"
    else:
        ema_mode = "loose"
    return {
        "days_since_reclaim":      days_since_reclaim,
        "reclaim_price":           round(reclaim_price, 2),
        "extension_pct":           round(extension_pct, 1),
        "rs_now":                  round(rs_now  * 100, 2),
        "rs_prev":                 round(rs_prev * 100, 2),
        "rs_flipped":              rs_flipped,
        "consolidation_range_pct": round((range_ratio - 1) * 100, 1),
        "price":                   round(price_now, 2),
        "ema100":                  round(ema100_now, 2),
        "ema150":                  round(ema150_now, 2),
        "ema200":                  round(ema200_now, 2),
        "above100":                above100,
        "above150":                above150,
        "pct_above_ema100":        round((price_now / ema100_now - 1) * 100, 2),
        "pct_above_ema150":        round((price_now / ema150_now - 1) * 100, 2),
        "pct_above_ema200":        round((price_now / ema200_now - 1) * 100, 2),
        "ema_mode":                ema_mode,
    }

# ── ETF momentum score (0-100) ───────────────────────────────────────────────
def score_etf_momentum(sig, n_qualified_holdings, n_total_holdings):
    """
    Composite 0-100 score ranking flagged ETFs against each other.
    Inputs are all already computed during the ETF scan / holdings drill-down.
    """
    score = 0.0

    # 1. Reclaim freshness (0-25 pts) — fresher reclaim = stronger signal
    days = sig["days_since_reclaim"]
    freshness = max(0, 25 - days * 1.25)  # 0d=25, 10d=12.5, 20d=0
    score += freshness

    # 2. RS swing magnitude (0-25 pts) — bigger flip = stronger conviction
    rs_swing = sig["rs_now"] - sig["rs_prev"]
    rs_pts = min(25, max(0, rs_swing * 1.2))  # ~21pp swing maxes this out
    score += rs_pts

    # 3. Extension penalty (0-20 pts) — closer to reclaim point = more room left
    ext = abs(sig["extension_pct"])
    ext_pts = max(0, 20 - ext * 1.0)  # 0%=20, 20%=0
    score += ext_pts

    # 4. EMA stack depth (0-15 pts)
    stack_pts = {"strict": 15, "medium150": 8, "loose": 0}[sig["ema_mode"]]
    score += stack_pts

    # 5. Consolidation tightness (0-10 pts) — tighter base = cleaner setup
    consol = sig["consolidation_range_pct"]
    consol_pts = max(0, 10 - consol * 0.5)  # 0%=10, 20%=0
    score += consol_pts

    # 6. Holdings breadth (0-5 pts) — is the move broad-based or narrow?
    if n_total_holdings > 0:
        breadth_ratio = n_qualified_holdings / n_total_holdings
        breadth_pts = breadth_ratio * 5
    else:
        breadth_pts = 0
    score += breadth_pts

    return round(min(100, max(0, score)), 1)



def score_holding(close, spy_close):
    """Score a holding for momentum. Returns dict or None if insufficient data."""
    if close is None or len(close) < 60:
        return None
    try:
        price = float(close.iloc[-1])

        # Performance
        def perf(n):
            if len(close) > n:
                return round((close.iloc[-1] / close.iloc[-n] - 1) * 100, 1)
            return None

        p1w  = perf(5)
        p1m  = perf(21)
        p3m  = perf(63)

        # 52W high
        w52_high = float(close.tail(252).max())
        pct_from_52w = round((price / w52_high - 1) * 100, 1)
        near_52w = pct_from_52w >= -10

        # EMA stack
        ema20  = float(close.ewm(span=20,  adjust=False).mean().iloc[-1])
        ema50  = float(close.ewm(span=50,  adjust=False).mean().iloc[-1])
        ema200_val = float(close.ewm(span=200, adjust=False).mean().iloc[-1]) if len(close) >= 200 else None

        above_ema20  = price > ema20
        above_ema50  = price > ema50
        above_ema200 = (price > ema200_val) if ema200_val else None

        # Momentum score (0-10)
        score = 0
        if p1w  and p1w  > 0:  score += 1
        if p1w  and p1w  > 3:  score += 1
        if p1m  and p1m  > 5:  score += 1
        if p1m  and p1m  > 15: score += 1
        if p3m  and p3m  > 15: score += 1
        if p3m  and p3m  > 30: score += 1
        if above_ema20:        score += 1
        if above_ema50:        score += 1
        if above_ema200:       score += 1
        if near_52w:           score += 1

        # RS vs SPY (1M)
        rs_1m = None
        if spy_close is not None and len(spy_close) > 21 and len(close) > 21:
            common = close.index.intersection(spy_close.index)
            if len(common) > 21:
                c   = close.reindex(common)
                spy = spy_close.reindex(common)
                rs_1m = round(((c.iloc[-1]/c.iloc[-21]-1) - (spy.iloc[-1]/spy.iloc[-21]-1)) * 100, 1)

        # Sparkline data (last 60 days, normalised to 100 using price's day-0 base)
        spark_raw = close.tail(60).tolist()
        base = spark_raw[0] if spark_raw[0] != 0 else 1
        spark = [round(v / base * 100, 2) for v in spark_raw]

        # EMA overlay series (same 60-day window, same normalisation base as price)
        # Computed on full history so early-window EMA values are accurate, then sliced.
        ema20_series  = close.ewm(span=20,  adjust=False).mean().tail(60).tolist()
        ema50_series  = close.ewm(span=50,  adjust=False).mean().tail(60).tolist()
        spark_ema20 = [round(v / base * 100, 2) for v in ema20_series]
        spark_ema50 = [round(v / base * 100, 2) for v in ema50_series]
        spark_ema200 = None
        if len(close) >= 200:
            ema200_series = close.ewm(span=200, adjust=False).mean().tail(60).tolist()
            spark_ema200 = [round(v / base * 100, 2) for v in ema200_series]

        return {
            "price":         round(price, 2),
            "p1w":           p1w,
            "p1m":           p1m,
            "p3m":           p3m,
            "pct_from_52w":  pct_from_52w,
            "near_52w":      near_52w,
            "above_ema20":   above_ema20,
            "above_ema50":   above_ema50,
            "above_ema200":  above_ema200,
            "ema20":         round(ema20, 2),
            "ema50":         round(ema50, 2),
            "ema200":        round(ema200_val, 2) if ema200_val else None,
            "rs_1m":         rs_1m,
            "score":         score,
            "spark":         spark,
            "spark_ema20":   spark_ema20,
            "spark_ema50":   spark_ema50,
            "spark_ema200":  spark_ema200,
        }
    except Exception as e:
        return None

def analyse_holdings(etf_ticker, spy_close):
    """Fetch and score all holdings for a flagged ETF."""
    holdings = HOLDINGS.get(etf_ticker, [])
    if not holdings:
        return []
    results = []
    for ticker, name in holdings:
        print(f"      holding {ticker:<12} {name[:30]:<30} ...", end=" ", flush=True)
        close = fetch_close(ticker, period_days=400)
        h = score_holding(close, spy_close)
        if h:
            h["ticker"] = ticker
            h["name"]   = name
            results.append(h)
            print(f"score={h['score']}  1M={h['p1m']}%  RS={h['rs_1m']}%")
        else:
            print("no data")
    # ── Momentum filter ──
    # 1M > 0% (positive medium-term trend) + score >= 4 (enough confirmations).
    # 1W gate removed — a short weekly dip does not negate a genuine trend.
    qualified = [
        h for h in results
        if (h["p1m"] is not None and h["p1m"] > 0)
        and h["score"] >= 4
    ]
    qualified.sort(key=lambda x: (-x["score"], -(x["p1m"] or -999)))
    return qualified

# ── HTML ──────────────────────────────────────────────────────────────────────
CSS = """:root{
  --bg:#111827;--surface:#1a2336;--surface2:#1f2b40;--surface3:#263047;--border:#2d3f5c;
  --text:#dde4f0;--muted:#7a90b0;--bull:#00e09a;--warn:#f5a623;
  --accent:#6aa3f8;--flip:#c084fc;--loose:#fb923c;--red:#ff4d6d;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Noto Sans',sans-serif;padding:2.5rem;min-height:100vh}
.header{margin-bottom:2rem;border-bottom:1px solid var(--border);padding-bottom:1.5rem;
  display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:1rem}
.header h1{font-family:'Sora',sans-serif;font-size:2rem;font-weight:700;letter-spacing:-.02em;color:#fff;line-height:1}
.header h1 em{color:var(--accent);font-style:normal}
.subtitle{color:#8fa8c8;font-family:'Noto Sans',sans-serif;font-size:.7rem;margin-top:.4rem;line-height:1.9}
.run-meta{font-family:'Noto Sans',sans-serif;font-size:.7rem;color:#8fa8c8;text-align:right;line-height:2}
.stats{display:flex;gap:.9rem;margin-bottom:2rem;flex-wrap:wrap}
.stat{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1rem 1.4rem;flex:1;min-width:120px}
.stat-n{font-size:2.6rem;font-weight:800;line-height:1;margin-bottom:.3rem}
.stat-l{font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;color:#8fa8c8}
.n-bull{color:var(--bull)} .n-acc{color:var(--accent)} .n-flip{color:var(--flip)} .n-loose{color:var(--loose)}
.mode-bar{display:flex;align-items:center;gap:.75rem;margin-bottom:2rem;
  background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:.8rem 1.2rem;flex-wrap:wrap}
.mode-label{font-family:'Noto Sans',sans-serif;font-size:.65rem;color:#8fa8c8;text-transform:uppercase;letter-spacing:.1em;margin-right:.25rem}
.mode-btn{font-family:'Noto Sans',sans-serif;font-size:.7rem;font-weight:500;
  border-radius:7px;padding:.35rem .9rem;cursor:pointer;transition:all .15s;
  border:1px solid var(--border);background:var(--surface2);color:#8fa8c8}
.mode-btn:hover{color:var(--text);border-color:#8fa8c8}
.mode-btn.active-strict{background:rgba(0,224,154,.12);color:var(--bull);border-color:rgba(0,224,154,.4)}
.mode-btn.active-medium{background:rgba(106,163,248,.12);color:var(--accent);border-color:rgba(106,163,248,.4)}
.mode-btn.active-loose{background:rgba(251,146,60,.12);color:var(--loose);border-color:rgba(251,146,60,.4)}
.mode-desc{font-family:'Noto Sans',sans-serif;font-size:.62rem;color:#8fa8c8;margin-left:auto}
.section-label{font-size:.62rem;text-transform:uppercase;letter-spacing:.15em;color:#8fa8c8;
  margin:2rem 0 .8rem;padding-left:.7rem;border-left:2px solid var(--accent)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1rem;margin-bottom:.5rem}

/* ETF card */
.card{background:var(--surface);border:1px solid var(--border);border-radius:14px;
  transition:border-color .15s;position:relative}
.card-top{padding:1.3rem 1.4rem;cursor:pointer;transition:background .15s}
.card-top:hover{background:var(--surface2)}
.card[data-mode="strict"]{border-left:3px solid var(--bull)}
.card[data-mode="strict"]::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,var(--bull),transparent)}
.card[data-mode="medium150"]{border-left:3px solid var(--accent)}
.card[data-mode="medium150"]::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,var(--accent),transparent)}
.card[data-mode="loose"]{border-left:3px solid var(--loose)}
.card[data-mode="loose"]::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,var(--loose),transparent)}
.card-head{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.75rem;gap:.7rem}

/* ETF momentum score block */
.mscore-block{flex-shrink:0;border-radius:10px;padding:.5rem .65rem;text-align:center;
  min-width:58px;border:1px solid var(--border)}
.mscore-rank{font-family:'Noto Sans',sans-serif;font-size:.55rem;opacity:.75;line-height:1}
.mscore-num{font-size:1.4rem;font-weight:800;line-height:1.1;letter-spacing:-.03em}
.mscore-lbl{font-family:'Noto Sans',sans-serif;font-size:.45rem;letter-spacing:.1em;opacity:.75;margin-top:.15rem;line-height:1.5}
.mscore-high{background:rgba(0,224,154,.1);border-color:rgba(0,224,154,.35)}
.mscore-high .mscore-num{color:var(--bull)}
.mscore-mid{background:rgba(106,163,248,.1);border-color:rgba(106,163,248,.35)}
.mscore-mid .mscore-num{color:var(--accent)}
.mscore-low{background:rgba(251,146,60,.1);border-color:rgba(251,146,60,.35)}
.mscore-low .mscore-num{color:var(--loose)}
.ticker-block{display:flex;flex-direction:column;gap:.25rem}
.ticker{font-family:'Sora',sans-serif;font-size:1.5rem;font-weight:800;color:#fff;letter-spacing:-.03em;line-height:1}
.ticker-name{font-family:'Noto Sans',sans-serif;font-size:.62rem;color:#8fa8c8;line-height:1.4;max-width:200px}
.grp-tag{font-family:'Noto Sans',sans-serif;font-size:.55rem;background:var(--surface2);
  color:#7a90b0;border-radius:4px;padding:.15rem .45rem;display:inline-block;align-self:flex-start}
.badges{display:flex;flex-direction:column;gap:.35rem;align-items:flex-end}
.badge{font-family:'Noto Sans',sans-serif;font-size:.6rem;font-weight:500;
  border-radius:5px;padding:.2rem .55rem;letter-spacing:.05em;white-space:nowrap}
.b-fresh{background:rgba(0,224,154,.12);color:var(--bull);border:1px solid rgba(0,224,154,.25)}
.b-flip{background:rgba(192,132,252,.12);color:var(--flip);border:1px solid rgba(192,132,252,.25)}
.b-ext{background:rgba(106,163,248,.1);color:var(--accent);border:1px solid rgba(106,163,248,.2)}
.b-loose{background:rgba(251,146,60,.1);color:var(--loose);border:1px solid rgba(251,146,60,.2)}
.b-med{background:rgba(106,163,248,.1);color:var(--accent);border:1px solid rgba(106,163,248,.2)}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:.5rem;margin-bottom:.85rem}
.m{background:var(--surface2);border-radius:7px;padding:.45rem .6rem}
.m-v{font-family:'Noto Sans',sans-serif;font-size:.82rem;font-weight:500;color:#fff}
.m-l{font-size:.57rem;text-transform:uppercase;letter-spacing:.08em;color:#8fa8c8;margin-top:.1rem}
.pos{color:var(--bull)!important} .neg{color:var(--red)!important} .hl{color:var(--warn)!important}
.ema-stack{display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:.85rem}
.ema-pill{font-family:'Noto Sans',sans-serif;font-size:.6rem;border-radius:20px;padding:.2rem .65rem}
.ep-on{background:rgba(0,224,154,.07);color:var(--bull);border:1px solid rgba(0,224,154,.18)}
.ep-off{background:rgba(255,77,109,.07);color:var(--red);border:1px solid rgba(255,77,109,.18)}
.signals{display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:.6rem}
.sig{display:flex;align-items:center;gap:.35rem}
.dot{width:7px;height:7px;border-radius:50%}
.dot-on{background:var(--bull);box-shadow:0 0 7px var(--bull)}
.dot-flip{background:var(--flip);box-shadow:0 0 7px var(--flip)}
.dot-off{background:var(--border)}
.sig-lbl{font-family:'Noto Sans',sans-serif;font-size:.6rem;color:#8fa8c8}

/* ETF card drill hint */
.drill-hint{font-family:'Noto Sans',sans-serif;font-size:.58rem;color:var(--accent);
  display:flex;align-items:center;gap:.4rem;margin-top:.6rem;opacity:.8;transition:opacity .15s}
.card-top:hover .drill-hint{opacity:1}

/* ── Modal overlay ── */
.modal-backdrop{display:none;position:fixed;inset:0;background:rgba(5,10,20,.82);
  backdrop-filter:blur(4px);z-index:1000;align-items:center;justify-content:center;padding:1.5rem}
.modal-backdrop.open{display:flex}
.modal{background:var(--surface);border:1px solid var(--border);border-radius:18px;
  width:min(1075px,100%);max-height:94vh;display:flex;flex-direction:column;
  box-shadow:0 32px 80px rgba(0,0,0,.6);overflow:hidden;position:relative}

/* Modal header */
.modal-header{padding:1.2rem 1.5rem;border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:1rem;flex-shrink:0}
.modal-etf-ticker{font-family:'Sora',sans-serif;font-size:1.8rem;font-weight:800;color:#fff;letter-spacing:-.04em;line-height:1}
.modal-etf-name{font-family:'Noto Sans',sans-serif;font-size:.65rem;color:#8fa8c8;flex:1}
.modal-close{width:32px;height:32px;border-radius:50%;background:var(--surface2);
  border:1px solid var(--border);color:#8fa8c8;cursor:pointer;font-size:1rem;
  display:flex;align-items:center;justify-content:center;transition:all .15s;flex-shrink:0}
.modal-close:hover{background:var(--red);border-color:var(--red);color:#fff}

/* Modal body — two-column: list left, detail right */
.modal-body{display:grid;grid-template-columns:375px 1fr;flex:1;overflow:hidden;min-height:0}

/* Left: holdings list */
.modal-list{border-right:1px solid var(--border);overflow-y:auto;padding:.9rem}
.modal-list-title{font-size:.55rem;text-transform:uppercase;letter-spacing:.14em;color:#8fa8c8;
  padding:.2rem .5rem .7rem;border-bottom:1px solid var(--border);margin-bottom:.6rem}

/* Holding row */
.h-row{display:flex;align-items:center;gap:.6rem;padding:.55rem .6rem;border-radius:9px;
  cursor:pointer;transition:background .12s,border-color .12s;
  border:1px solid transparent;margin-bottom:.35rem}
.h-row:hover{background:var(--surface2);border-color:var(--border)}
.h-row.active{background:rgba(192,132,252,.1);border-color:rgba(192,132,252,.35)}
.h-row-rank{font-family:'Noto Sans',sans-serif;font-size:.6rem;color:#8fa8c8;width:1.2rem;flex-shrink:0;text-align:center}
.h-row-left{flex:1;min-width:0}
.h-row-ticker{font-family:'Sora',sans-serif;font-size:.95rem;font-weight:700;color:#fff;letter-spacing:-.01em;line-height:1.1}
.h-row-name{font-family:'Noto Sans',sans-serif;font-size:.55rem;color:#8fa8c8;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px}
.h-row-right{text-align:right;flex-shrink:0}
.h-row-score{font-family:'Noto Sans',sans-serif;font-size:.65rem;color:var(--bull);font-weight:600}
.h-row-perf{font-family:'Noto Sans',sans-serif;font-size:.58rem}

/* Right: holding detail pane */
.modal-detail{overflow-y:auto;padding:1.2rem 1.4rem;display:flex;flex-direction:column;gap:1rem}
.detail-empty{display:flex;align-items:center;justify-content:center;height:100%;
  font-family:'Noto Sans',sans-serif;font-size:.7rem;color:#8fa8c8;text-align:center;line-height:2.5}
.detail-header{display:flex;align-items:baseline;gap:.75rem;flex-wrap:wrap}
.detail-ticker{font-family:'Sora',sans-serif;font-size:2rem;font-weight:700;color:#fff;letter-spacing:-.02em;line-height:1}
.detail-name{font-family:'Noto Sans',sans-serif;font-size:.65rem;color:#8fa8c8}
.detail-price{font-family:'Noto Sans',sans-serif;font-size:1rem;font-weight:600;color:var(--accent);margin-left:auto}

/* Score bar */
.detail-score{display:flex;align-items:center;gap:.6rem}
.detail-score-label{font-family:'Noto Sans',sans-serif;font-size:.6rem;color:#8fa8c8;text-transform:uppercase;letter-spacing:.1em}
.big-dots{display:flex;gap:3px}
.bd{width:9px;height:9px;border-radius:50%;background:var(--border)}
.bd.on{background:var(--bull);box-shadow:0 0 5px var(--bull)}
.detail-score-num{font-family:'Noto Sans',sans-serif;font-size:.85rem;font-weight:700;color:var(--bull)}

/* Perf grid */
.detail-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:.5rem}
.dm{background:var(--surface2);border-radius:8px;padding:.55rem .7rem}
.dm-v{font-family:'Noto Sans',sans-serif;font-size:.9rem;font-weight:600}
.dm-l{font-size:.55rem;text-transform:uppercase;letter-spacing:.08em;color:#8fa8c8;margin-top:.15rem}

/* EMA pills */
.detail-emas{display:flex;gap:.4rem;flex-wrap:wrap}

/* Sparkline */
.detail-spark{background:var(--surface2);border-radius:10px;padding:1rem}
.spark-title{font-family:'Noto Sans',sans-serif;font-size:.58rem;color:#8fa8c8;
  text-transform:uppercase;letter-spacing:.1em}
.spark-title-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:.6rem;gap:.6rem}
.spark-legend{font-family:'Noto Sans',sans-serif;font-size:.58rem}
.etf-overlay-toggle{display:flex;align-items:center;gap:.4rem;font-family:'Noto Sans',sans-serif;
  font-size:.6rem;color:#8fa8c8;cursor:pointer;user-select:none}
.etf-overlay-toggle input{accent-color:var(--accent);cursor:pointer;width:13px;height:13px}
.spark-svg-big{width:100%;height:150px;display:block}
.spark-dates{font-family:'Noto Sans',sans-serif;font-size:.55rem;color:#8fa8c8;
  display:flex;justify-content:space-between;margin-top:.3rem}

.h-pill{font-family:'Noto Sans',sans-serif;font-size:.6rem;border-radius:12px;padding:.2rem .6rem}
.h-52w-yes{background:rgba(0,224,154,.07);color:var(--bull);border:1px solid rgba(0,224,154,.18)}
.h-52w-no{background:rgba(255,77,109,.07);color:var(--red);border:1px solid rgba(255,77,109,.18)}
.ep-on{background:rgba(0,224,154,.07);color:var(--bull);border:1px solid rgba(0,224,154,.18)}
.ep-off{background:rgba(255,77,109,.07);color:var(--red);border:1px solid rgba(255,77,109,.18)}

.tab-bar{display:flex;gap:.5rem;margin-bottom:1.5rem;border-bottom:1px solid var(--border);padding-bottom:0}
.tab-btn{font-family:'Noto Sans',sans-serif;font-size:.7rem;font-weight:600;
  letter-spacing:.08em;text-transform:uppercase;padding:.55rem 1.2rem;cursor:pointer;
  border:none;background:none;color:#8fa8c8;border-bottom:2px solid transparent;
  margin-bottom:-1px;transition:all .15s}
.tab-btn:hover{color:var(--text)}
.tab-btn.active{color:var(--accent);border-bottom-color:var(--accent)}
.tab-pane{display:none}
.tab-pane.active{display:block}

/* ETF Universe table */
.universe-group{margin-bottom:2rem}
.universe-group-label{font-size:.6rem;text-transform:uppercase;letter-spacing:.15em;color:#8fa8c8;
  margin-bottom:.6rem;padding-left:.7rem;border-left:2px solid var(--accent)}
.universe-table{width:100%;border-collapse:collapse}
.universe-table th{font-family:'Noto Sans',sans-serif;font-size:.58rem;text-transform:uppercase;
  letter-spacing:.1em;color:#8fa8c8;padding:.4rem .8rem;text-align:left;
  border-bottom:1px solid var(--border)}
.universe-table td{padding:.45rem .8rem;border-bottom:1px solid rgba(45,63,92,.4);vertical-align:middle}
.universe-table tr:hover td{background:var(--surface2)}
.u-ticker{font-size:.9rem;font-weight:800;color:#fff;letter-spacing:-.02em;font-family:'Sora',sans-serif}
.u-name{font-family:'Noto Sans',sans-serif;font-size:.62rem;color:#8fa8c8}
.u-flag{font-family:'Noto Sans',sans-serif;font-size:.58rem;font-weight:600;
  border-radius:5px;padding:.15rem .5rem;white-space:nowrap}
.u-flag-strict{background:rgba(0,224,154,.12);color:var(--bull);border:1px solid rgba(0,224,154,.3)}
.u-flag-medium{background:rgba(106,163,248,.12);color:var(--accent);border:1px solid rgba(106,163,248,.3)}
.u-flag-loose{background:rgba(251,146,60,.12);color:var(--loose);border:1px solid rgba(251,146,60,.3)}
.u-flag-none{color:#3a4f6a;font-size:.58rem;font-family:'Noto Sans',sans-serif}
.u-holdings{font-family:'Noto Sans',sans-serif;font-size:.6rem;color:#8fa8c8}
.universe-hint{font-family:'Noto Sans',sans-serif;font-size:.62rem;color:#8fa8c8;
  margin-bottom:1rem;line-height:1.8}
.empty{grid-column:1/-1;text-align:center;padding:4rem 2rem;
  font-family:'Noto Sans',sans-serif;font-size:.82rem;color:#8fa8c8;line-height:2.5}
.methodology{background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:1.2rem 1.4rem;margin-top:2.5rem;
  font-family:'Noto Sans',sans-serif;font-size:.63rem;color:#8fa8c8;line-height:2.2}
.methodology strong{color:var(--text)}
.footer{margin-top:1.5rem;font-family:'Noto Sans',sans-serif;font-size:.62rem;color:#8fa8c8;text-align:center}
.card.hidden{display:none}
.section-group.all-hidden{display:none}
/* ── Info tooltips (hover/tap to explain terms) ── */
.no-holdings{font-family:'Noto Sans',sans-serif;font-size:.63rem;color:#8fa8c8;padding:.5rem;text-align:center}
.tip{position:relative;cursor:help;border-bottom:1px dotted currentColor}
.tip:hover .tip-bubble, .tip:focus .tip-bubble, .tip:active .tip-bubble{
  opacity:1;visibility:visible;transform:translate(-50%,4px)}
.tip-bubble{position:absolute;top:calc(100% + 8px);left:50%;
  transform:translate(-50%,0);width:240px;max-width:80vw;
  background:#0c1422;border:1px solid var(--border);border-radius:8px;
  padding:.6rem .75rem;font-family:'Noto Sans',sans-serif;font-size:.65rem;
  font-weight:400;line-height:1.5;color:var(--text);letter-spacing:0;
  text-transform:none;opacity:0;visibility:hidden;transition:opacity .15s,transform .15s;
  pointer-events:none;z-index:200;box-shadow:0 8px 24px rgba(0,0,0,.4);
  text-align:left;white-space:normal;word-wrap:break-word}
.tip-bubble::after{content:'';position:absolute;bottom:100%;left:50%;
  transform:translateX(-50%);border:5px solid transparent;border-bottom-color:var(--border)}
@media (max-width: 768px){
  .tip-bubble{width:200px;font-size:.62rem}
}

/* ============================================================
   RESPONSIVE LAYER — mobile / narrow screens only.
   Everything above this point is untouched; these rules only
   activate below 768px and never affect desktop rendering.
   ============================================================ */
@media (max-width: 768px){
  body{padding:1rem}

  .header{flex-direction:column;align-items:flex-start;gap:.5rem}
  .header h1{font-size:1.5rem}
  .run-meta{text-align:left}

  .stats{gap:.5rem}
  .stat{min-width:0;flex:1 1 calc(50% - .5rem);padding:.75rem 1rem}
  .stat-n{font-size:1.9rem}
  .stat-l{font-size:.6rem}

  .mode-bar{padding:.7rem .8rem;gap:.5rem}
  .mode-btn{font-size:.62rem;padding:.3rem .6rem;flex:1 1 auto;text-align:center}
  .mode-desc{margin-left:0;width:100%;order:99}

  .tab-bar{overflow-x:auto;flex-wrap:nowrap;-webkit-overflow-scrolling:touch}
  .tab-btn{white-space:nowrap;font-size:.62rem;padding:.5rem .8rem}

  .cards{grid-template-columns:1fr;gap:.8rem}

  .card-top{padding:1rem 1.1rem}
  .card-head{flex-wrap:wrap}
  .badges{align-items:flex-start;width:100%}
  .metrics{grid-template-columns:repeat(2,1fr)}

  /* Modal: full-screen sheet instead of centered card */
  .modal-backdrop{padding:0}
  .modal{width:100%;height:100%;max-height:100vh;border-radius:0}
  .modal-header{padding:.9rem 1rem}
  .modal-etf-ticker{font-size:1.4rem}
  .modal-close{width:38px;height:38px}

  /* Stack list + detail vertically instead of side-by-side */
  .modal-body{grid-template-columns:1fr;grid-template-rows:auto 1fr;overflow-y:auto}
  .modal-list{border-right:none;border-bottom:1px solid var(--border);
    max-height:38vh;overflow-y:auto}
  .modal-detail{padding:1rem}

  .h-row{padding:.7rem .6rem}
  .h-row-name{max-width:110px}

  .detail-header{gap:.5rem}
  .detail-ticker{font-size:1.6rem}
  .detail-price{font-size:.9rem}
  .detail-metrics{grid-template-columns:repeat(2,1fr)}

  .spark-title-row{flex-wrap:wrap;gap:.4rem}
  .spark-svg-big{height:130px}

  .universe-table th, .universe-table td{padding:.4rem .5rem;font-size:.6rem}
  .u-name{display:none}

  .methodology{font-size:.6rem;padding:1rem}
}

@media (max-width: 420px){
  .stat{flex:1 1 100%}
  .metrics{grid-template-columns:1fr 1fr}
  .detail-metrics{grid-template-columns:1fr 1fr}
}
"""

JS = """
// -- Tab switching --
function switchTab(tab){
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-btn-'+tab).classList.add('active');
  document.getElementById('tab-pane-'+tab).classList.add('active');
}

// -- EMA filter mode --
const MODES = {
  strict:{desc:'Showing highest-conviction signals (above EMA100 + EMA150 + EMA200)',btnClass:'active-strict',show:['strict']},
  medium:{desc:'Showing signals above EMA200 + EMA150 (may be below EMA100)',btnClass:'active-medium',show:['strict','medium150']},
  loose: {desc:'Showing all EMA200 reclaims -- includes assets still below EMA100/150',btnClass:'active-loose',show:['strict','medium150','loose']}
};
function setMode(mode){
  const cfg=MODES[mode];
  ['strict','medium','loose'].forEach(m=>{
    document.getElementById('btn-'+m).className='mode-btn'+(m===mode?' '+cfg.btnClass:'');
  });
  document.getElementById('mode-desc').textContent=cfg.desc;
  document.querySelectorAll('.card').forEach(c=>{
    c.classList.toggle('hidden',!cfg.show.includes(c.dataset.mode));
  });
  document.querySelectorAll('.section-group').forEach(g=>{
    const has=[...g.querySelectorAll('.card')].some(c=>!c.classList.contains('hidden'));
    g.classList.toggle('all-hidden',!has);
  });
}

// ── Spark data (embedded at generation time) ─────────────────────────────────
const SPARK_DATA = __SPARK_JSON__;

// -- ETF's own price series (for overlay-on-stock-chart) --
const ETF_SPARK_DATA = __ETF_SPARK_JSON__;

// Overlay toggle state -- defaults to ON
let showEtfOverlay = true;

// ── Holdings data (embedded at generation time) ──────────────────────────────
const HOLDINGS_DATA = __HOLDINGS_JSON__;

// ── Modal state ──────────────────────────────────────────────────────────────
let activeEtf = null;
let activeTicker = null;

function openModal(etfTicker, etfName, e){
  if(e) e.stopPropagation();
  try {
  activeEtf = etfTicker;
  activeTicker = null;
  const backdrop = document.getElementById('modal-backdrop');
  document.getElementById('modal-etf-ticker').textContent = etfTicker;
  document.getElementById('modal-etf-name').textContent   = etfName;
  // Build holdings list
  const holdings = HOLDINGS_DATA[etfTicker] || [];
  const listEl = document.getElementById('modal-list-items');
  listEl.innerHTML = '';
  holdings.forEach((h, i) => {
    const row = document.createElement('div');
    row.className = 'h-row';
    row.dataset.ticker = h.ticker;
    const p1m = h.p1m != null ? `${h.p1m > 0 ? '+' : ''}${h.p1m.toFixed(1)}%` : 'n/a';
    const pClass = (h.p1m||0) > 0 ? 'pos' : 'neg';
    row.innerHTML = `
      <span class="h-row-rank">${i+1}</span>
      <div class="h-row-left">
        <div class="h-row-ticker">${h.ticker}</div>
        <div class="h-row-name">${h.name}</div>
      </div>
      <div class="h-row-right">
        <div class="h-row-score">${h.score}/10</div>
        <div class="h-row-perf ${pClass}">${p1m}</div>
      </div>`;
    row.addEventListener('click', (e) => { e.stopPropagation(); selectHolding(h, row); });
    listEl.appendChild(row);
  });
  // Reset detail pane
  document.getElementById('modal-detail').innerHTML =
    '<div class="detail-empty">← Select a holding to see details &amp; chart</div>';
  // If no holdings passed the filter, show message in list panel
  if(holdings.length === 0){
    listEl.innerHTML = '<div style="font-family:monospace;font-size:.65rem;color:#8fa8c8;padding:1rem;line-height:2;text-align:center">No holdings in momentum.<br>All top holdings have negative 1W or 1M performance.</div>';
  }
  backdrop.classList.add('open');
  document.body.style.overflow = 'hidden';
  // Auto-select first holding
  if(holdings.length > 0){
    const firstRow = listEl.querySelector('.h-row');
    if(firstRow) { selectHolding(holdings[0], firstRow); }
  }
  } catch(err) {
    alert('openModal error: ' + err.message + '\\n\\nCheck browser console (F12) for details.');
    console.error('openModal error:', err);
  }
}

function closeModal(e){
  if(e) e.stopPropagation();
  document.getElementById('modal-backdrop').classList.remove('open');
  document.body.style.overflow = '';
  activeEtf = null; activeTicker = null;
}

// Close on backdrop click (not modal itself)
document.addEventListener('DOMContentLoaded', () => {
  setMode('strict');
  document.getElementById('modal-backdrop').addEventListener('click', (e) => {
    if(e.target === e.currentTarget) closeModal();
  });
  // ESC key
  document.addEventListener('keydown', (e) => { if(e.key==='Escape') closeModal(); });
});

function selectHolding(h, rowEl){
  activeTicker = h.ticker;
  // Highlight row
  document.querySelectorAll('.h-row').forEach(r => r.classList.remove('active'));
  rowEl.classList.add('active');
  // Render detail pane
  renderDetail(h);
}

function renderDetail(h){
  try {
  const el = document.getElementById('modal-detail');
  const p1w  = h.p1w  != null ? `<span class="${h.p1w>=0?'pos':'neg'}">${h.p1w>0?'+':''}${h.p1w.toFixed(1)}%</span>` : '<span>n/a</span>';
  const p1m  = h.p1m  != null ? `<span class="${h.p1m>=0?'pos':'neg'}">${h.p1m>0?'+':''}${h.p1m.toFixed(1)}%</span>` : '<span>n/a</span>';
  const p3m  = h.p3m  != null ? `<span class="${h.p3m>=0?'pos':'neg'}">${h.p3m>0?'+':''}${h.p3m.toFixed(1)}%</span>` : '<span>n/a</span>';
  const rs   = h.rs_1m!= null ? `<span class="${h.rs_1m>=0?'pos':'neg'}">${h.rs_1m>0?'+':''}${h.rs_1m.toFixed(1)}%</span>` : '<span>n/a</span>';
  const e20  = h.above_ema20  ? 'ep-on' : 'ep-off';
  const e50  = h.above_ema50  ? 'ep-on' : 'ep-off';
  const e200 = h.above_ema200 ? 'ep-on' : 'ep-off';
  const w52c = h.near_52w     ? 'h-52w-yes' : 'h-52w-no';
  const w52t = `${(h.pct_from_52w != null && h.pct_from_52w > 0) ? '+' : ''}${h.pct_from_52w != null ? h.pct_from_52w.toFixed(1) : 'n/a'}% vs 52W high`;
  const bigDots = Array.from({length:10},(_,i)=>
    `<span class="bd ${i<h.score?'on':''}"></span>`).join('');

  el.innerHTML = `
    <div class="detail-header">
      <div class="detail-ticker">${h.ticker}</div>
      <div class="detail-name">${h.name}</div>
      <div class="detail-price">$${h.price != null ? h.price.toFixed(2) : 'n/a'}</div>
    </div>
    <div class="detail-score">
      <span class="detail-score-label">Momentum</span>
      <div class="big-dots">${bigDots}</div>
      <span class="detail-score-num">${h.score}/10</span>
    </div>
    <div class="detail-metrics">
      <div class="dm"><div class="dm-v">${p1w}</div><div class="dm-l">1 Week</div></div>
      <div class="dm"><div class="dm-v">${p1m}</div><div class="dm-l">1 Month</div></div>
      <div class="dm"><div class="dm-v">${p3m}</div><div class="dm-l">3 Month</div></div>
      <div class="dm"><div class="dm-v">${rs}</div><div class="dm-l"><span class="tip" tabindex="0">RS vs SPY<span class="tip-bubble">Relative Strength: this stock's 1-month return minus SPY's 1-month return. Positive means it's beating the broad market, not just rising with it.</span></span></div></div>
    </div>
    <div class="detail-emas">
      <span class="h-pill ${e20}"><span class="tip" tabindex="0">EMA20 ${h.above_ema20?'ON':'OFF'}<span class="tip-bubble">20-day Exponential Moving Average. The shortest-term trend reference used here &mdash; price above it suggests near-term momentum.</span></span></span>
      <span class="h-pill ${e50}"><span class="tip" tabindex="0">EMA50 ${h.above_ema50?'ON':'OFF'}<span class="tip-bubble">50-day Exponential Moving Average. A medium-term trend reference, between EMA20 and EMA200.</span></span></span>
      <span class="h-pill ${e200}"><span class="tip" tabindex="0">EMA200 ${h.above_ema200?'ON':'OFF'}<span class="tip-bubble">200-day Exponential Moving Average. The long-term trend line &mdash; the entire scanner is built around stocks/ETFs reclaiming this level.</span></span></span>
      <span class="h-pill ${w52c}">${w52t}</span>
    </div>
    <div class="detail-spark">
      <div class="spark-title-row">
        <span class="spark-title">60-Day Price Chart</span>
        <label class="etf-overlay-toggle">
          <input type="checkbox" id="etf-overlay-checkbox" ${showEtfOverlay ? 'checked' : ''}
            onchange="toggleEtfOverlay(this.checked)">
          <span>Show ${activeEtf || 'ETF'}</span>
        </label>
        <span id="spark-legend" class="spark-legend"></span>
      </div>
      <svg class="spark-svg-big" id="spark-big" viewBox="0 0 625 150" preserveAspectRatio="none"></svg>
      <div class="spark-dates"><span>60 days ago</span><span>Today</span></div>
    </div>`;

  // Draw sparkline
  const svgEl = document.getElementById('spark-big');
  drawSpark(svgEl, h.ticker, 625, 150);
  } catch(err) {
    console.error('renderDetail error:', err);
    document.getElementById('modal-detail').innerHTML =
      `<div class="detail-empty" style="color:#ff4d6d">JS Error: ${err.message}<br>Check browser console (F12)</div>`;
  }
}

function drawSpark(svgEl, ticker, W, H){
  const d = SPARK_DATA[ticker];
  if(!d || !d.price || d.price.length < 2){ svgEl.innerHTML='<text x="50%" y="50%" fill="#8fa8c8" font-size="10" text-anchor="middle">No chart data</text>'; return; }

  const price  = d.price;
  const ema20  = d.ema20  || null;
  const ema50  = d.ema50  || null;
  const ema200 = d.ema200 || null;

  // ETF overlay series -- rebased to start at the SAME point as the stock's
  // first price value, so both lines are visually comparable from day 0.
  let etfSeries = null;
  if(showEtfOverlay && activeEtf && ETF_SPARK_DATA[activeEtf]){
    const raw = ETF_SPARK_DATA[activeEtf];
    if(raw && raw.length === price.length){
      const rebase = price[0] / raw[0];
      etfSeries = raw.map(v => v * rebase);
    }
  }

  // Shared scale across all series so EMAs + ETF overlay line up correctly against price
  const allVals = [...price, ...(ema20||[]), ...(ema50||[]), ...(ema200||[]), ...(etfSeries||[])];
  const mn = Math.min(...allVals), mx = Math.max(...allVals);
  const range = (mx - mn) || 1;
  const pad = 8;

  const toPts = (series) => series.map((v,i)=>{
    const x = (i/(series.length-1))*(W-pad*2)+pad;
    const y = (H-pad*2)-((v-mn)/range)*(H-pad*2)+pad;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  const pricePts = toPts(price);
  const lastPt = pricePts.split(' ').pop().split(',');
  const priceColor = price[price.length-1] >= price[0] ? '#00e09a' : '#ff4d6d';
  const uid = ticker.replace(/[^a-zA-Z0-9]/g,'_');

  let emaLines = '';
  let legend = '<span style="color:#8fa8c8">Price</span>';
  if(ema20){
    emaLines += `<polyline points="${toPts(ema20)}" fill="none" stroke="#f5a623" stroke-width="1.3" stroke-dasharray="0" opacity="0.85"/>`;
    legend += ' &nbsp; <span style="color:#f5a623">— EMA20</span>';
  }
  if(ema50){
    emaLines += `<polyline points="${toPts(ema50)}" fill="none" stroke="#6aa3f8" stroke-width="1.3" opacity="0.85"/>`;
    legend += ' &nbsp; <span style="color:#6aa3f8">— EMA50</span>';
  }
  if(ema200){
    emaLines += `<polyline points="${toPts(ema200)}" fill="none" stroke="#c084fc" stroke-width="1.3" opacity="0.85"/>`;
    legend += ' &nbsp; <span style="color:#c084fc">— EMA200</span>';
  }
  let etfLine = '';
  if(etfSeries){
    etfLine = `<polyline points="${toPts(etfSeries)}" fill="none" stroke="#8fa8c8" stroke-width="1.6" stroke-dasharray="5,4" opacity="0.9"/>`;
    legend += ` &nbsp; <span style="color:#8fa8c8">- - ${activeEtf}</span>`;
  }

  svgEl.innerHTML = `
    <defs>
      <linearGradient id="sg_${uid}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${priceColor}" stop-opacity="0.25"/>
        <stop offset="100%" stop-color="${priceColor}" stop-opacity="0.02"/>
      </linearGradient>
    </defs>
    <polygon points="${pad},${H-pad} ${pricePts} ${W-pad},${H-pad}" fill="url(#sg_${uid})"/>
    ${etfLine}
    ${emaLines}
    <polyline points="${pricePts}" fill="none" stroke="${priceColor}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
    <circle cx="${lastPt[0]}" cy="${lastPt[1]}" r="4"
      fill="${priceColor}" stroke="var(--surface2)" stroke-width="2"/>`;

  const legendEl = document.getElementById('spark-legend');
  if(legendEl) legendEl.innerHTML = legend;
}

// -- ETF overlay toggle handler --
function toggleEtfOverlay(checked){
  showEtfOverlay = checked;
  if(activeTicker){
    const svgEl = document.getElementById('spark-big');
    if(svgEl) drawSpark(svgEl, activeTicker, 625, 150);
  }
}
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Early Trend Scanner — {date}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=Noto+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>

<!-- ── Modal overlay ── -->
<div class="modal-backdrop" id="modal-backdrop">
  <div class="modal" onclick="event.stopPropagation()">
    <div class="modal-header">
      <div id="modal-etf-ticker" class="modal-etf-ticker"></div>
      <div id="modal-etf-name"   class="modal-etf-name"></div>
      <button class="modal-close" onclick="closeModal(event)" title="Close (Esc)">✕</button>
    </div>
    <div class="modal-body">
      <div class="modal-list">
        <div class="modal-list-title">Holdings ranked by momentum</div>
        <div id="modal-list-items"></div>
      </div>
      <div class="modal-detail" id="modal-detail">
        <div class="detail-empty">← Select a holding to see details &amp; chart</div>
      </div>
    </div>
  </div>
</div>

<div class="header">
  <div>
    <h1>EARLY TREND <em>DETECTOR</em></h1>
    <div class="subtitle">
      EMA200 reclaim · RS flip · Prior consolidation · Not extended · Click any ETF card → holdings drill-down
    </div>
  </div>
  <div class="run-meta">{date}<br>Scanned: {total_scanned} ETFs<br>Signals: {total_signals}</div>
</div>
<div class="stats">
  <div class="stat"><div class="stat-n n-bull">{cnt_strict}</div> <div class="stat-l">Strict (100+150+200)</div></div>
  <div class="stat"><div class="stat-n n-acc" >{cnt_medium}</div><div class="stat-l">+Medium (200+150)</div></div>
  <div class="stat"><div class="stat-n n-loose">{cnt_loose}</div> <div class="stat-l">+Loose (200 only)</div></div>
  <div class="stat"><div class="stat-n n-flip" >{rs_flips}</div>  <div class="stat-l">Clean RS (Relative Strength) Flips</div></div>
  <div class="stat"><div class="stat-n n-acc"  >{fresh_signals}</div><div class="stat-l">Fresh signals (5 days or less)</div></div>
</div>
<div class="tab-bar">
  <button class="tab-btn active" id="tab-btn-signals" onclick="switchTab('signals')">SIGNALS</button>
  <button class="tab-btn" id="tab-btn-universe" onclick="switchTab('universe')">ETF UNIVERSE</button>
</div>

<div class="tab-pane active" id="tab-pane-signals">
<div class="mode-bar">
  <span class="mode-label">EMA Filter:</span>
  <button class="mode-btn active-strict" id="btn-strict" onclick="setMode('strict')">STRICT — above EMA100 + EMA150 + EMA200</button>
  <button class="mode-btn" id="btn-medium" onclick="setMode('medium')">MEDIUM — above EMA200 + EMA150 only</button>
  <button class="mode-btn" id="btn-loose"  onclick="setMode('loose')">LOOSE — above EMA200 only</button>
  <span class="mode-desc" id="mode-desc">Showing highest-conviction signals only</span>
</div>
<div id="results">{results_html}</div>
<div class="methodology">
  <strong>ETF Signal conditions (all required):</strong><br>
  1. <strong>Above EMA200</strong> — current price above EMA200<br>
  2. <strong>EMA200 Reclaim</strong> — crossed above EMA200 within last 20 trading days (was below >= 5 days prior)<br>
  3. <strong>EMA200 Slope</strong> — EMA200 is flat or rising (not in a downtrend)<br>
  4. <strong>Not Extended</strong> — price within 20% of reclaim point<br>
  5. <strong>RS Improving</strong> — RS vs SPY was negative 25d ago, positive now (or 4pp+ swing)<br>
  6. <strong>Prior Consolidation</strong> — price moved less than 20% in 60 days before reclaim<br><br>
  <strong>Holdings momentum score (0-10):</strong>
  1W &gt;0% +1 · 1W &gt;3% +1 · 1M &gt;5% +1 · 1M &gt;15% +1 · 3M &gt;15% +1 · 3M &gt;30% +1 · Above EMA20 +1 · Above EMA50 +1 · Above EMA200 +1 · Within 10% of 52W High +1
</div>
</div>

<div class="tab-pane" id="tab-pane-universe">
<div class="universe-hint">
  Full ETF universe scanned each run. To add a new ETF, insert it into the TICKERS dict in ema_scan_v4.py and add its top holdings to the HOLDINGS dict.
</div>
{universe_html}
</div>
<div class="footer">Data: Yahoo Finance · Not investment advice · Do your own research</div>
<script>{js}</script>
</body>
</html>"""

def tip(label, explanation):
    """Wrap a label in a hoverable tooltip span. Used for badges/labels
    across the dashboard so users can hover/tap to see what a term means."""
    return f'<span class="tip" tabindex="0">{label}<span class="tip-bubble">{explanation}</span></span>'


def fmt_pct(v, show_plus=True):
    if v is None: return "n/a"
    s = f"{v:+.1f}%" if show_plus else f"{v:.1f}%"
    return s

def render_card(ticker, name, group, sig, holdings_data):
    """ETF card — clicking opens the modal. No inline drill-down."""
    mode = sig["ema_mode"]
    mode_badge = {"strict": f'<span class="badge b-fresh">{tip("STRICT &#x2713;", "Price is above EMA100, EMA150, and EMA200 simultaneously &mdash; the highest-conviction signal tier.")}</span>',
                  "medium150": f'<span class="badge b-med">{tip("MEDIUM", "Price is above EMA200 and EMA150, but may still be below EMA100. A moderate-conviction signal.")}</span>',
                  "loose": f'<span class="badge b-loose">{tip("LOOSE", "Price is only above EMA200. The broadest, lowest-conviction signal tier.")}</span>'}[mode]
    flip_badge = (f'<span class="badge b-flip">{tip("RS FLIP &#x2713;", "Relative Strength Flip: this ETF was underperforming SPY (the S&amp;P 500) 25 days ago and has since flipped to outperforming it &mdash; or swung by 4+ percentage points. A sign the trend is genuinely changing, not just drifting with the market.")}</span>'
                  if sig["rs_flipped"] else "")
    flip_dot   = "dot-flip" if sig["rs_flipped"] else "dot-on"
    above100, above150 = sig["above100"], sig["above150"]
    # Safe JS string: escape quotes in name
    safe_name = name.replace("'", "\\'").replace('"', '&quot;')
    n_holdings = len(holdings_data)
    if n_holdings > 0:
        drill_hint = f"▶ &nbsp; {n_holdings} holdings in momentum — click to explore"
    else:
        drill_hint = "▶ &nbsp; No holdings currently in momentum"

    # Momentum score badge (color-coded by tier)
    mscore = sig.get("momentum_score")
    mrank  = sig.get("momentum_rank")
    if mscore is not None:
        if mscore >= 70:   mscore_css = "mscore-high"
        elif mscore >= 45: mscore_css = "mscore-mid"
        else:              mscore_css = "mscore-low"
        mscore_html = f'''<div class="mscore-block {mscore_css}">
      <div class="mscore-rank">#{mrank}</div>
      <div class="mscore-num">{mscore:.0f}</div>
      <div class="mscore-lbl">{tip("MOMENTUM<br>SCORE", "A 0-100 composite score combining reclaim freshness, RS swing size, how extended the price is, EMA stack depth, base tightness, and breadth of qualifying holdings. Higher = stronger, fresher trend. ETFs are ranked by this score.")}</div>
    </div>'''
    else:
        mscore_html = ""

    return f"""<div class="card" data-mode="{mode}"
  onclick="openModal('{ticker}', '{safe_name}', event)">
  <div class="card-top">
    <div class="card-head">
      {mscore_html}
      <div class="ticker-block">
        <div class="ticker">{ticker}</div>
        <div class="ticker-name">{name}</div>
        <span class="grp-tag">{group}</span>
      </div>
      <div class="badges">
        <span class="badge b-fresh">{tip(f"RECLAIM {sig['days_since_reclaim']}d AGO", "Days since price first crossed back above the EMA200, after having been below it for at least 5 trading days. Fresher reclaims (lower numbers) suggest an earlier-stage trend.")}</span>
        {flip_badge}{mode_badge}
        <span class="badge b-ext">{tip(f"+{sig['extension_pct']:.1f}% FROM ENTRY", "How far price has moved from the EMA200 reclaim point. Lower numbers mean the move is fresher and less extended &mdash; potentially more room left to run.")}</span>
      </div>
    </div>
    <div class="metrics">
      <div class="m"><div class="m-v">${sig['price']}</div><div class="m-l">Price</div></div>
      <div class="m"><div class="m-v {'pos' if sig['rs_now']>0 else 'neg'}">{sig['rs_now']:+.1f}%</div><div class="m-l">{tip("RS vs SPY", "Relative Strength vs SPY: this ETF's return minus SPY's return over the same window. Positive means it's outperforming the broad market, not just rising with it.")}</div></div>
      <div class="m"><div class="m-v {'pos' if sig['rs_prev']>0 else 'neg'}">{sig['rs_prev']:+.1f}%</div><div class="m-l">{tip("RS 25d Ago", "What the Relative Strength reading was 25 trading days ago, for comparison against today's value &mdash; this is what flips from negative to positive in an RS Flip.")}</div></div>
      <div class="m"><div class="m-v">${sig['reclaim_price']}</div><div class="m-l">Reclaim Price</div></div>
      <div class="m"><div class="m-v hl">{sig['consolidation_range_pct']:.1f}%</div><div class="m-l">{tip("Prior Range", "The price range (high vs low) in the 60 days before the EMA200 reclaim. A tighter range suggests a cleaner base before the breakout.")}</div></div>
      <div class="m"><div class="m-v pos">+{sig['pct_above_ema200']:.1f}%</div><div class="m-l">vs EMA200</div></div>
    </div>
    <div class="ema-stack">
      <span class="ema-pill {'ep-on' if above100 else 'ep-off'}">{tip(f"EMA100 ${sig['ema100']} ({'+' if above100 else '-'}{abs(sig['pct_above_ema100']):.1f}%)", "100-day Exponential Moving Average. A medium-term trend reference &mdash; price above it is a bullish sign on that timeframe.")}</span>
      <span class="ema-pill {'ep-on' if above150 else 'ep-off'}">{tip(f"EMA150 ${sig['ema150']} ({'+' if above150 else '-'}{abs(sig['pct_above_ema150']):.1f}%)", "150-day Exponential Moving Average. Sits between the EMA100 and EMA200 in sensitivity.")}</span>
      <span class="ema-pill ep-on">{tip(f"EMA200 ${sig['ema200']} (+{sig['pct_above_ema200']:.1f}%)", "200-day Exponential Moving Average. The core long-term trend line this entire scanner is built around &mdash; reclaiming it is the primary signal.")}</span>
    </div>
    <div class="signals">
      <div class="sig"><span class="dot dot-on"></span><span class="sig-lbl">EMA200 &#x2713;</span></div>
      <div class="sig"><span class="dot {'dot-on' if above150 else 'dot-off'}"></span><span class="sig-lbl">EMA150</span></div>
      <div class="sig"><span class="dot {'dot-on' if above100 else 'dot-off'}"></span><span class="sig-lbl">EMA100</span></div>
      <div class="sig"><span class="dot {flip_dot}"></span><span class="sig-lbl">{tip("RS FLIP", "Whether Relative Strength vs SPY has flipped from negative to positive (or swung sharply) in the last 25 days.")}</span></div>
      <div class="sig"><span class="dot dot-on"></span><span class="sig-lbl">{tip("CONSOLIDATION &#x2713;", "Confirms price moved less than 20% in the 60 days before the reclaim &mdash; i.e. it was basing quietly, not already trending hard.")}</span></div>
    </div>
    <div class="drill-hint">{drill_hint}</div>
  </div>
</div>"""

# ── Main ──────────────────────────────────────────────────────────────────────
def build_universe_html(flagged_map):
    """Build ETF universe table. flagged_map: {ticker: ema_mode}"""
    html = ""
    for group, tmap in TICKERS.items():
        rows = ""
        for ticker, name in tmap.items():
            mode = flagged_map.get(ticker)
            if mode == "strict":
                flag = '<span class="u-flag u-flag-strict">STRICT</span>'
            elif mode == "medium150":
                flag = '<span class="u-flag u-flag-medium">MEDIUM</span>'
            elif mode == "loose":
                flag = '<span class="u-flag u-flag-loose">LOOSE</span>'
            else:
                flag = '<span class="u-flag-none">—</span>'
            n_holdings = len(HOLDINGS.get(ticker, []))
            rows += f"""<tr>
  <td><span class="u-ticker">{ticker}</span></td>
  <td><span class="u-name">{name}</span></td>
  <td>{flag}</td>
  <td><span class="u-holdings">{n_holdings} holdings mapped</span></td>
</tr>"""
        html += f"""<div class="universe-group">
  <div class="universe-group-label">{group}</div>
  <table class="universe-table">
    <thead><tr>
      <th>Ticker</th><th>Name</th><th>Signal</th><th>Holdings</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>"""
    return html


def main():
    print(f"\n{'='*60}")
    print(f"EARLY TREND SCANNER v6.0 [Responsive: Sora/Noto Sans, mobile layer added] — {datetime.today().strftime('%A, %B %d, %Y')}")
    print(f"{'='*60}\n")

    print("Fetching benchmark (SPY)...")
    spy_close = fetch_close(BENCHMARK)
    if spy_close is None:
        sys.exit("Could not fetch SPY. Check internet connection.")

    all_tickers = [(t, n, grp) for grp, tmap in TICKERS.items() for t, n in tmap.items()]
    found = []

    # Phase 1: scan ETFs
    print("\n── Phase 1: ETF scan ──")
    for ticker, name, group in all_tickers:
        print(f"  {ticker:<6} {name[:35]:<35} ...", end=" ", flush=True)
        close = fetch_close(ticker)
        if close is None:
            print("no data / skipped"); continue
        sig = analyse(close, spy_close)
        if sig:
            found.append((ticker, name, group, sig))
            print(f"✓ [{sig['ema_mode'].upper():<8}]  reclaim={sig['days_since_reclaim']}d  RS:{sig['rs_prev']:+.1f}%→{sig['rs_now']:+.1f}%  ext={sig['extension_pct']:.1f}%")
        else:
            print("—")

    found.sort(key=lambda x: (x[3]["days_since_reclaim"], x[3]["extension_pct"]))

    # Phase 2: holdings drill-down for flagged ETFs
    print(f"\n── Phase 2: Holdings analysis for {len(found)} flagged ETF(s) ──")
    spark_data = {}  # ticker -> {price, ema20, ema50, ema200} normalised series
    holdings_by_etf = {}
    etf_spark_data = {}  # ETF ticker -> own normalised 60d price series (for overlay)
    for ticker, name, group, sig in found:
        print(f"\n  {ticker} — fetching holdings...")
        h_list = analyse_holdings(ticker, spy_close)
        holdings_by_etf[ticker] = h_list
        # Collect spark data for all holdings
        for h in h_list:
            spark_data[h["ticker"]] = {
                "price":  h["spark"],
                "ema20":  h["spark_ema20"],
                "ema50":  h["spark_ema50"],
                "ema200": h["spark_ema200"],
            }
        # ETF's own 60-day spark (for the overlay-on-stock-chart feature)
        etf_close = fetch_close(ticker, period_days=400)
        if etf_close is not None and len(etf_close) >= 60:
            etf_raw = etf_close.tail(60).tolist()
            etf_base = etf_raw[0] if etf_raw[0] != 0 else 1
            etf_spark_data[ticker] = [round(v / etf_base * 100, 2) for v in etf_raw]
        # Momentum score: needs qualified vs total holdings count
        n_total = len(HOLDINGS.get(ticker, []))
        n_qualified = len(h_list)
        sig["momentum_score"] = score_etf_momentum(sig, n_qualified, n_total)

    # Rank flagged ETFs by momentum score (highest first)
    found.sort(key=lambda x: -x[3]["momentum_score"])
    for rank, (ticker, name, group, sig) in enumerate(found, start=1):
        sig["momentum_rank"] = rank

    # Build HTML
    groups_seen = {}
    for ticker, name, group, sig in found:
        groups_seen.setdefault(group, []).append((ticker, name, sig))

    results_html = ""
    for group, items in groups_seen.items():
        results_html += f'<div class="section-group"><div class="section-label">{group}</div><div class="cards">'
        for ticker, name, sig in items:
            h_list = holdings_by_etf.get(ticker, [])
            results_html += render_card(ticker, name, group, sig, h_list)
        results_html += "</div></div>"

    if not results_html:
        results_html = '<div class="cards"><div class="empty">No signals this week.<br>Market extended or in consolidation — stay patient.</div></div>'

    cnt_strict = sum(1 for _,_,_,s in found if s["ema_mode"] == "strict")
    cnt_medium = sum(1 for _,_,_,s in found if s["ema_mode"] in ("strict","medium150"))
    cnt_loose  = len(found)
    rs_flips   = sum(1 for _,_,_,s in found if s["rs_flipped"])
    fresh      = sum(1 for _,_,_,s in found if s["days_since_reclaim"] <= 5)

    # Build holdings JSON for modal (strip spark from main payload; spark goes separately)
    holdings_for_js = {}
    for ticker, h_list in holdings_by_etf.items():
        SPARK_KEYS = {"spark", "spark_ema20", "spark_ema50", "spark_ema200"}
        holdings_for_js[ticker] = [{k: v for k, v in h.items() if k not in SPARK_KEYS} for h in h_list]

    def ascii_safe(s):
        return (s.replace('✓', 'ON').replace('✗', 'OFF').replace('←', '<-')
                 .encode("ascii", "replace").decode("ascii"))

    js_final = ascii_safe(JS \
        .replace("__SPARK_JSON__",     json.dumps(spark_data)) \
        .replace("__HOLDINGS_JSON__",  json.dumps(holdings_for_js)) \
        .replace("__ETF_SPARK_JSON__", json.dumps(etf_spark_data)))

    flagged_map = {ticker: sig["ema_mode"] for ticker, _, _, sig in found}
    universe_html = build_universe_html(flagged_map)

    html = HTML_TEMPLATE \
        .replace("{css}",           ascii_safe(CSS)) \
        .replace("{js}",            js_final) \
        .replace("{date}",          datetime.today().strftime("%A, %B %d, %Y at %H:%M")) \
        .replace("{total_scanned}", str(len(all_tickers))) \
        .replace("{total_signals}", str(len(found))) \
        .replace("{cnt_strict}",    str(cnt_strict)) \
        .replace("{cnt_medium}",    str(cnt_medium)) \
        .replace("{cnt_loose}",     str(cnt_loose)) \
        .replace("{rs_flips}",      str(rs_flips)) \
        .replace("{fresh_signals}", str(fresh)) \
        .replace("{results_html}",  results_html) \
        .replace("{universe_html}", universe_html)

    out_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "docs", "index.html"
    )
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8-sig") as f:
        f.write(html)

    print(f"\n{'='*60}")
    print(f"Strict:{cnt_strict}  Medium:{cnt_medium}  Loose:{cnt_loose}  RS Flips:{rs_flips}  Fresh:{fresh}")
    print(f"Report → {out_file}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
