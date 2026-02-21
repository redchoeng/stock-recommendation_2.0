# -*- coding: utf-8 -*-
"""
config.py — 티커 리스트 상수
(분석 임계값/기술지표 상수는 각 Mixin 클래스에 위치)
"""

# ============================================================================
# 사전 정의된 티커 리스트 (Yahoo Finance 섹터 기반 재분류)
# ============================================================================

# 기술주/성장주 (Technology, Digital Platform, Biotech Growth)
GROWTH_TICKERS = [
    # ========== Technology - Semiconductors (21) ==========
    'NVDA', 'AMD', 'INTC', 'QCOM', 'TXN', 'MU', 'AVGO', 'MRVL', 'ADI', 'ON',
    'MPWR', 'MCHP', 'ASML', 'LRCX', 'AMAT', 'KLAC', 'NXPI', 'ENTG', 'WOLF',
    'SWKS', 'QRVO', 'CRUS', 'SLAB', 'TER', 'ONTO',

    # ========== Technology - Software & Cloud (35) ==========
    'MSFT', 'ORCL', 'CRM', 'ADBE', 'INTU', 'NOW', 'SNOW', 'WDAY', 'TEAM',
    'DDOG', 'ADSK', 'CDNS', 'SNPS', 'PANW', 'CRWD', 'ZS', 'FTNT', 'NET',
    'MDB', 'ESTC', 'CFLT', 'GTLB', 'DOCN', 'DBX', 'BOX', 'SHOP', 'HUBS',
    'ZM', 'DOCU', 'APPN', 'OKTA', 'CYBR', 'VRNS', 'QLYS', 'RPD', 'TENB', 'S',
    'CHKP', 'BILL', 'VEEV',

    # ========== Technology - AI & Data (4) ==========
    'PLTR', 'AI', 'PATH', 'U',

    # ========== Technology - Hardware & Infrastructure (12) ==========
    'AAPL', 'DELL', 'HPE', 'SMCI', 'ANET', 'CSCO', 'JNPR', 'AKAM',
    'NTAP', 'STX', 'WDC', 'PSTG',

    # ========== Technology - Fintech (7) ==========
    'PYPL', 'SQ', 'AFRM', 'UPST', 'SOFI', 'NU', 'V', 'MA',

    # ========== Technology - Business Services (4) ==========
    'ADP', 'PAYX',

    # ========== Communication Services - Digital Platform (12) ==========
    'GOOGL', 'GOOG', 'META', 'NFLX', 'TTD',  # 디지털 광고/스트리밍
    'EA', 'TTWO', 'RBLX', 'NTES',  # 게임
    'WBD', 'SIRI', 'FOX', 'FOXA',  # 미디어/엔터테인먼트

    # ========== Consumer Cyclical - Digital/EV (10) ==========
    'AMZN', 'TSLA', 'MELI', 'ABNB', 'BKNG', 'DASH', 'PDD', 'JD',  # 이커머스/플랫폼
    'LULU', 'CPRT',  # 성장형 소비재

    # ========== Healthcare - Biotech & Growth (18) ==========
    'LLY',  # 비만/당뇨 신약 (성장)
    'MRNA', 'REGN', 'VRTX', 'BIIB',  # 바이오텍
    'ISRG', 'DXCM', 'ALGN', 'IDXX', 'PODD',  # 의료기기 성장
    'ILMN', 'EXAS', 'TECH',  # 진단/연구
    'TMO', 'DHR', 'A',  # 생명과학 장비

    # ========== Industrials - High Growth (5) ==========
    'SMR', 'OKLO',  # 소형모듈원자로 (SMR) - 신기술
    'GEV',  # GE Vernova - 에너지 기술
    'SYM', 'VRSK'  # 자동화/데이터
]

# 가치주/배당주 (Traditional Sectors, Stable Earnings) - S&P 500 기반 확장
VALUE_TICKERS = [
    # ========== Financial Services - Banks (29) ==========
    'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'USB', 'PNC', 'TFC', 'BK',
    'STT', 'COF', 'SCHW', 'BLK', 'AXP',
    'CFG', 'HBAN', 'RF', 'KEY', 'FITB', 'ZION', 'MTB', 'FHN', 'CMA', 'EWBC',
    'WAL', 'SNV', 'VLY', 'OZK',
    'STT', 'COF', 'SCHW', 'BLK', 'AXP', 'MTB',

    # ========== Financial Services - Insurance (20) ==========
    'BRK-B', 'PGR', 'TRV', 'ALL', 'CB', 'AIG', 'MET', 'PRU', 'AFL', 'AMP',
    'CINF', 'L', 'GL', 'WRB', 'RGA', 'HIG', 'PFG', 'LNC', 'AIZ', 'SYF',
    'MMC', 'AON', 'WTW', 'AJG', 'BRO', # 대형 보험 중개사 위주로 재편

    # ========== Financial Services - Capital Markets & Data (15) ==========
    'SPGI', 'MCO', 'ICE', 'CME', 'NDAQ', 'MSCI',  # 거래소/데이터
    'MMC', 'AON', 'WTW',  # 보험중개
    'FIS', 'FISV', 'GPN', 'CPAY', 'JKHY', 'BR',  # 결제/금융기술

    # ========== Real Estate - REITs (35) ==========
    'PLD', 'AMT', 'CCI', 'EQIX', 'PSA', 'DLR', 'O', 'WELL', 'SPG', 'AVB',
    'EQR', 'VTR', 'ARE', 'INVH', 'ESS', 'MAA', 'UDR', 'CPT', 'HST', 'REG',
    'CBRE', 'IRM', 'COLD', 'REXR', 'FR', 'KRC', 'BXP', 'VNO', 'SLG', 'JBGS',
    'SBAC', 'KIM', 'EXR', 'GLPI', 'SUI',  # S&P 500 추가

    # ========== Healthcare - Traditional Pharma & Plans (30) ==========
    'JNJ', 'UNH', 'ABBV', 'MRK', 'PFE', 'BMY', 'AMGN', 'GILD',
    'CVS', 'CI', 'ELV', 'HUM', 'CNC', 'MOH',  # 헬스케어 플랜
    'MDT', 'SYK', 'BSX', 'ZBH', 'BAX', 'BDX', 'RMD',  # 의료기기 (안정)
    'HOLX', 'XRAY', 'ENOV', 'MMSI', 'ZTS',  # 기타 헬스케어
    'ABT', 'HCA', 'MCK', 'CAH', 'GEHC',  # S&P 500 추가

    # ========== Consumer Defensive - Staples (35) ==========
    'PG', 'KO', 'PEP', 'WMT', 'COST', 'PM', 'MO', 'CL', 'KMB', 'GIS',
    'HSY', 'MDLZ', 'MNST', 'KDP', 'KHC', 'STZ', 'TAP', 'CPB', 'CAG', 'SJM',
    'CHD', 'CLX', 'DG', 'DLTR', 'TGT',
    'EL', 'HRL', 'MKC', 'LW', 'TSN', 'SYY', 'ADM', 'BG',  # S&P 500 추가
    'ORLY', 'AZO',  # 자동차부품 (필수소비재 성격)

    # ========== Consumer Cyclical - Traditional Retail & Restaurant (25) ==========
    'HD', 'LOW', 'TJX', 'ROST', 'BBY', 'ULTA', 'NKE',  # 리테일
    'MCD', 'SBUX', 'YUM', 'CMG', 'DPZ', 'DRI', 'TXRH', 'CBRL', 'BLMN', 'CAKE',  # 레스토랑
    'F', 'GM', 'APTV', 'BWA', 'LEA', 'GNTX', 'LKQ', 'GPC',  # 자동차/부품

    # ========== Energy - Oil & Gas (20) ==========
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY',
    'DVN', 'FANG', 'HAL', 'BKR', 'APA', 'CTRA', 'NOV', 'RIG',
    'TRGP', 'WMB',  # 미드스트림

    # ========== Energy - Uranium (7) ==========
    'CCJ', 'UEC', 'URG', 'UUUU', 'LEU', 'BWXT',  # 우라늄/원자력

    # ========== Industrials - Aerospace & Defense (12) ==========
    'LMT', 'RTX', 'BA', 'NOC', 'GD', 'LHX', 'HII', 'KTOS',
    'TDG', 'HWM', 'TXT', 'LDOS',  # S&P 500 추가

    # ========== Industrials - Infrastructure & Construction (15) ==========
    'STRL', 'FIX', 'MTZ', 'EME', 'PWR', 'PRIM', 'DY', 'AGX', 'SPXC', 'OSK',
    'BLDR', 'SSD',
    'J', 'ACM', 'FLR',  # 엔지니어링

    # ========== Industrials - Transportation & Logistics (15) ==========
    'UNP', 'UPS', 'CSX', 'NSC', 'FDX', 'SAIA', 'CHRW', 'ODFL', 'KEX',
    'DAL', 'UAL', 'LUV', 'ALK',  # 항공사
    'EXPD', 'JBHT',  # 물류

    # ========== Industrials - Machinery & Equipment (35) ==========
    'CAT', 'DE', 'HON', 'MMM', 'GE', 'EMR', 'ETN', 'ITW', 'PH', 'CMI',
    'ROK', 'DOV', 'IR', 'XYL', 'AAON', 'RBC', 'POWL', 'AIT', 'GVA',
    'URI', 'CARR', 'OTIS', 'TT', 'GNRC', 'AOS', 'MLI',
    'WM', 'RSG', 'JCI', 'FAST', 'PCAR', 'CTAS',
    'GWW', 'FTV', 'AME', 'SNA', 'IEX',  # S&P 500 추가

    # ========== Basic Materials (25) ==========
    'LIN', 'APD', 'ECL', 'SHW', 'DD', 'NEM', 'FCX', 'NUE', 'VMC', 'MLM',
    'PPG', 'IFF', 'ALB', 'CE', 'CF', 'MP',  # 희토류
    'DOW', 'LYB', 'EMN', 'FMC',  # 화학
    'BALL', 'PKG', 'IP', 'AVY', 'AMCR',  # 포장재

    # ========== Utilities (25) ==========
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL', 'ED', 'ES',
    'WEC', 'PEG', 'AWK', 'ETR', 'FE', 'CEG', 'VST',  # 전력
    'ATO', 'NI', 'CNP', 'DTE', 'CMS', 'LNT', 'EVRG', 'PPL',  # S&P 500 추가

    # ========== Communication Services - Telecom (5) ==========
    'VZ', 'T', 'TMUS', 'CHTR', 'CMCSA'
]
