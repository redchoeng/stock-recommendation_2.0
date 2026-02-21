# -*- coding: utf-8 -*-
"""
Project Titan - US Stock Decision Support System
Advanced 2-Stage Filtering Analysis for NASDAQ 100, Value Stocks, and S&P 500
"""

import os
import yfinance as yf
import pandas as pd
import time
from datetime import datetime, timezone
from tabulate import tabulate
import pytz

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

    # ========== Financial Services - Insurance (20) ==========
    'BRK-B', 'PGR', 'TRV', 'ALL', 'CB', 'AIG', 'MET', 'PRU', 'AFL', 'AMP',
    'CINF', 'L', 'GL', 'WRB', 'RGA', 'HIG', 'PFG', 'LNC', 'AIZ', 'SYF',

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


class TitanAnalyzer:
    # 필터링 기준
    MIN_MARKET_CAP = 10_000_000_000  # $10B
    MIN_PRICE = 5.0  # $5
    MIN_AVG_VOLUME = 1_000_000  # 100만주

    # 펀더멘털 점수는 _calc_gradient_score()에서 max_pts로 직접 지정

    # 섹터별 점수 - 성장주 (비중 축소: 20% → 10%)
    SCORE_SECTOR_TIER1 = 10  # AI, 반도체, 클라우드, 사이버보안, 국방, 원자력
    SCORE_SECTOR_TIER2 = 8   # 소프트웨어, EV, 바이오텍, 신재생에너지, 희토류
    SCORE_SECTOR_TIER3 = 5   # 헬스케어, 산업자동화, 핀테크
    SCORE_SECTOR_TIER4 = 3   # 전통 에너지, 소비재, 유틸리티
    SCORE_SECTOR_DEFAULT = 1 # 분류 미매칭 (최소 보장)

    # 섹터별 점수 - 가치주 (비중 축소: 20% → 10%)
    VALUE_SECTOR_TIER1 = 10  # 필수소비재, 헬스케어 (배당귀족)
    VALUE_SECTOR_TIER2 = 8   # 유틸리티, 금융 (안정적 배당)
    VALUE_SECTOR_TIER3 = 5   # 산업재, 에너지, 부동산 (가치 섹터)
    VALUE_SECTOR_TIER4 = 3   # 기술주, 경기민감 소비재 (성장주 영역)
    VALUE_SECTOR_DEFAULT = 1 # 분류 미매칭 (최소 보장)

    # 트럼프 정부 정책 방향 보너스/페널티
    POLICY_BONUS = 3          # 정책 수혜 섹터 가산점
    POLICY_PENALTY = -3       # 정책 역풍 섹터 감점

    # 섹터 순환매 분석용 ETF 매핑
    SECTOR_ETF_MAP = {
        'Technology': 'XLK',
        'Financial Services': 'XLF',
        'Energy': 'XLE',
        'Healthcare': 'XLV',
        'Industrials': 'XLI',
        'Utilities': 'XLU',
        'Consumer Defensive': 'XLP',
        'Consumer Cyclical': 'XLY',
        'Communication Services': 'XLC',
        'Basic Materials': 'XLB',
        'Real Estate': 'XLRE',
    }
    ROTATION_BONUS_INFLOW = 3       # 수급유입 (핫섹터 + 가속)
    ROTATION_BONUS_TURNING = 5      # 순환매 기대 (소외 + 반등)
    ROTATION_BONUS_WATCHING = 1     # 관심 (중위 + 가속)
    ROTATION_PENALTY_OVERHEAT = -2  # 과열주의 (핫 + 감속)
    ROTATION_PENALTY_COLD = -3      # 소외 지속

    # 섹터별 ROE 기준 (자본구조 차이 반영)
    # {sector: (excellent_threshold, good_threshold)}
    SECTOR_ROE_THRESHOLDS = {
        'Utilities': (12, 6),              # 인프라 자산 대비 ROE 구조적 저조 (평균 8-12%)
        'Real Estate': (12, 5),            # REIT: 배당 90% 의무분배로 ROE 왜곡 (O 2.5%, PLD 6.1%)
        'Energy': (15, 8),                 # 자본집약 산업, 유가 사이클 (XOM 11%, CVX 7%)
        'Consumer Defensive': (20, 10),    # 기본 기준 유지 (KO 43%, PG 31%)
        'Industrials': (20, 10),           # 기본 기준 유지
        'Technology': (20, 10),
        'Healthcare': (20, 10),
        'Financial Services': (20, 10),
    }
    DEFAULT_ROE_THRESHOLD = (20, 10)

    # 섹터별 매출성장률 기준 (성숙/방어 업종 차등 적용)
    # {sector: (high_threshold, good_threshold)}
    SECTOR_REVENUE_GROWTH_THRESHOLDS = {
        'Consumer Defensive': (8, 3),      # 성숙 산업 (KO 2.4%, PG 1.5%, WMT 5.8%)
        'Energy': (10, 3),                 # 유가 사이클, 마이너스 성장 빈번 (XOM -1.3%)
        'Utilities': (10, 5),              # 규제 산업, 안정적 저성장 (NEE 20% 예외적)
        'Financial Services': (10, 3),     # 성숙 산업 (JPM 2.5%, BRK 2.1%)
        'Healthcare': (12, 5),             # 특허주기 영향 (MRK 5%, BMY 1.3%)
        'Industrials': (15, 8),            # 방산 포함, 정부계약 특성 (LMT 9%, GD 7.8%)
        'Real Estate': (10, 3),            # REIT: 안정적 임대수익 (PLD 4%, O 10%)
        'Communication Services': (15, 8),
        'Consumer Cyclical': (15, 8),
        'Technology': (20, 10),            # 기본 기준 유지 (고성장 기대)
        'Basic Materials': (15, 8),
    }
    DEFAULT_REVENUE_GROWTH_THRESHOLD = (20, 10)


    # 섹터별 OPM 기준 (저마진 업종 차등 적용)
    # {sector: (excellent_threshold, good_threshold)}
    SECTOR_OPM_THRESHOLDS = {
        # 저마진 업종 - 유통/소매/식품유통
        'Consumer Defensive': (7, 3),    # WMT 3.7%, COST 3.7%, PG 23%
        'Consumer Cyclical': (12, 6),    # HD 15%, NKE 12%, MCD 45%
        # 중간 마진 업종
        'Industrials': (15, 8),          # GE 19%, RTX 11%, CAT 20%
        'Energy': (15, 8),               # XOM 16%, CVX 14%
        'Basic Materials': (15, 8),      # LIN 24%, NUE 12%
        'Real Estate': (15, 8),          # REITs
        'Communication Services': (15, 8),
        'Utilities': (15, 8),            # NEE 22%
        # 고마진 업종 - 기본 기준 유지
        'Financial Services': (20, 10),
        'Healthcare': (20, 10),
        'Technology': (20, 10),
    }
    DEFAULT_OPM_THRESHOLD = (20, 10)  # 기본값

    # 업종(industry) 레벨 OPM 오버라이드 (섹터 기준보다 우선)
    INDUSTRY_OPM_OVERRIDES = {
        'Aerospace & Defense': (10, 5),     # 방산: 정부계약 저마진 (LMT 9%, HII 5.9%)
        'Computer Hardware': (10, 3),       # 서버/하드웨어: 조립 저마진 (SMCI 3.7%)
        'Scientific & Technical Instruments': (10, 5),
        'Healthcare Plans': (5, 1),         # 건강보험: 구조적 극저마진 (UNH 0.3%, CI 3.3%)
    }

    # ===== 가치주 모드 전용 기준 =====
    # 배당수익률 기준 {sector: (excellent%, good%)} — 높을수록 좋음
    VALUE_DIVIDEND_THRESHOLDS = {
        'Utilities': (5.0, 3.0),
        'Real Estate': (5.0, 3.0),
        'Energy': (5.0, 2.5),
        'Consumer Defensive': (4.0, 2.0),
        'Financial Services': (3.5, 1.5),
        'Industrials': (3.0, 1.5),
        'Healthcare': (3.0, 1.5),
        'Communication Services': (3.0, 1.5),
        'Consumer Cyclical': (3.0, 1.0),
        'Basic Materials': (4.0, 2.0),
        'Technology': (2.0, 0.5),
    }
    DEFAULT_VALUE_DIVIDEND_THRESHOLD = (4.0, 2.0)

    # PER 기준 (역방향: 낮을수록 좋음) {sector: (good_upper, fair_upper)}
    VALUE_PER_THRESHOLDS = {
        'Technology': (20, 35),
        'Healthcare': (18, 30),
        'Consumer Cyclical': (15, 25),
        'Consumer Defensive': (18, 28),
        'Financial Services': (12, 20),
        'Utilities': (18, 28),
        'Real Estate': (18, 30),
        'Energy': (12, 20),
        'Industrials': (15, 25),
        'Communication Services': (15, 25),
        'Basic Materials': (12, 20),
    }
    DEFAULT_VALUE_PER_THRESHOLD = (15, 25)

    # 부채비율(D/E) 기준 (역방향: 낮을수록 좋음) {sector: (good_upper, fair_upper)}
    VALUE_DE_THRESHOLDS = {
        'Financial Services': (300, 600),   # 은행: 레버리지 구조적 높음
        'Real Estate': (150, 300),
        'Utilities': (150, 250),
        'Communication Services': (100, 200),
        'Energy': (80, 150),
        'Healthcare': (80, 150),
        'Consumer Defensive': (80, 150),
        'Consumer Cyclical': (80, 150),
        'Industrials': (80, 150),
        'Basic Materials': (80, 150),
        'Technology': (50, 100),
    }
    DEFAULT_VALUE_DE_THRESHOLD = (80, 150)

    # 기술적 점수 재설계 (전문가급, 총 50점)
    # 1. 추세 분석 (20점) - MA5/20/60/120 + 일목균형표 + MACD + ADX
    SCORE_MA120 = 2        # 장기 추세 (6개월)
    SCORE_MA60 = 2         # 중기 추세 (3개월)
    SCORE_MA20 = 3         # 단기 추세 (1개월)
    SCORE_MA5 = 2          # 초단기 모멘텀 (1주)
    SCORE_MACD_BULLISH = 4
    SCORE_MACD_SIGNAL = 2
    SCORE_ICHIMOKU = 3     # 일목균형표 (구름위+TK크로스+미래구름)
    SCORE_ADX_STRONG = 2

    # 2. 모멘텀 (10점)
    SCORE_RSI_OPTIMAL = 5
    SCORE_RSI_GOOD = 3
    SCORE_RSI_OVERSOLD = 2
    SCORE_STOCH_OPTIMAL = 5
    SCORE_STOCH_GOOD = 2

    # 3. 거래량 (8점)
    SCORE_VOLUME_EXTREME = 4    # 3배 이상
    SCORE_VOLUME_HIGH = 3       # 2-3배
    SCORE_VOLUME_MODERATE = 2   # 1.5-2배
    SCORE_VOLUME_NORMAL = 1     # 1.2-1.5배
    SCORE_OBV_RISING = 4

    # 4. 변동성 (7점)
    SCORE_BB_POSITION = 4
    SCORE_ATR_EXPANSION = 3

    # 5. 가격 패턴 (5점)
    SCORE_PRICE_POSITION = 5

    # RSI 임계값
    RSI_OVERSOLD = 30
    RSI_OPTIMAL_MIN = 40
    RSI_OPTIMAL_MAX = 60
    RSI_GOOD_MAX = 70
    RSI_OVERBOUGHT = 70

    # 역발상 보너스/페널티 (하이브리드 전략)
    SCORE_OVERSOLD_QUALITY_BONUS = 10  # 과매도 우량주 보너스
    SCORE_OVERBOUGHT_PENALTY = -5      # 과열주 감점

    # 기타 설정

    def __init__(self):
        self.results = []
        self.analysis_mode = 'growth'  # 'growth' or 'value'

    def get_sp500_tickers(self):
        """S&P 500 티커 리스트 다운로드"""
        print("📥 S&P 500 티커 리스트 다운로드 중...")
        try:
            table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
            tickers = table['Symbol'].tolist()
            # 특수문자 처리 (BRK.B -> BRK-B for yfinance)
            tickers = [t.replace('.', '-') for t in tickers]
            print(f"✅ {len(tickers)}개 종목 로드 완료\n")
            return tickers
        except Exception as e:
            print(f"❌ S&P 500 리스트 다운로드 실패: {e}")
            return []

    def _meets_stage1_criteria(self, info):
        """1단계 필터 조건 충족 여부 확인"""
        market_cap = info.get('marketCap', 0)
        current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
        avg_volume = info.get('averageVolume', 0)

        return (market_cap and market_cap > self.MIN_MARKET_CAP and
                current_price and current_price > self.MIN_PRICE and
                avg_volume and avg_volume > self.MIN_AVG_VOLUME)

    def _print_progress(self, current, total, interval=50):
        """진행 상황 출력"""
        if current % interval == 0 or current == total:
            print(f"진행: {current}/{total} ({current/total*100:.1f}%)")

    def stage1_quick_filter(self, tickers):
        """1단계: 빠른 스크리닝 (시가총액, 거래량, 가격)"""
        print("=" * 70)
        print(f"🔍 STAGE 1: 빠른 스크리닝 (시가총액 > ${self.MIN_MARKET_CAP/1e9:.0f}B, "
              f"거래량 > {self.MIN_AVG_VOLUME/1e6:.0f}M, 가격 > ${self.MIN_PRICE})")
        print("=" * 70)

        filtered = []
        total = len(tickers)

        for i, ticker in enumerate(tickers, 1):
            try:
                self._print_progress(i, total)

                stock = yf.Ticker(ticker)
                info = stock.info

                if self._meets_stage1_criteria(info):
                    market_cap = info.get('marketCap', 0)
                    current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
                    avg_volume = info.get('averageVolume', 0)

                    filtered.append({
                        'ticker': ticker,
                        'market_cap': market_cap,
                        'price': current_price,
                        'volume': avg_volume
                    })

                # API 제한 회피
                if i % 10 == 0:
                    time.sleep(0.3)

            except Exception:
                # 에러는 조용히 스킵
                pass

        print(f"\n✅ 1단계 완료: {len(filtered)}개 종목 선정 (원본 {total}개)\n")
        return [item['ticker'] for item in filtered]

    @staticmethod
    def _calc_gradient_score(value, excellent, good, max_pts):
        """선형 보간 점수 계산 (커트라인 점프 제거)

        구간별 점수:
        - value > excellent*1.3: max_pts (만점, 확실한 우수)
        - excellent ~ excellent*1.3: max_pts*0.8 ~ max_pts (우수 구간 보간)
        - good ~ excellent: max_pts*0.4 ~ max_pts*0.8 (양호 구간 보간)
        - good*0.5 ~ good: 1 ~ max_pts*0.4 (미달이지만 인정)
        - < good*0.5: 0
        """
        if value <= 0:
            return 0

        fair = good * 0.5
        top = excellent * 1.3  # 확실한 우수 기준

        if value >= top:
            return max_pts
        elif value >= excellent:
            # excellent ~ top 구간: 80% ~ 100%
            ratio = (value - excellent) / (top - excellent) if top > excellent else 1
            pts = max_pts * (0.8 + 0.2 * ratio)
        elif value >= good:
            # good ~ excellent 구간: 40% ~ 80%
            ratio = (value - good) / (excellent - good) if excellent > good else 1
            pts = max_pts * (0.4 + 0.4 * ratio)
        elif value >= fair:
            # fair ~ good 구간: 5% ~ 40%
            ratio = (value - fair) / (good - fair) if good > fair else 1
            pts = max_pts * (0.05 + 0.35 * ratio)
        else:
            return 0

        return round(pts)

    @staticmethod
    def _calc_inverse_gradient_score(value, good_upper, fair_upper, max_pts):
        """역방향 선형 보간 (낮을수록 좋은 지표: PER, 부채비율)

        구간별 점수:
        - value <= good_upper * 0.6: max_pts (만점, 확실한 저평가)
        - good_upper*0.6 ~ good_upper: max_pts*0.8 ~ max_pts
        - good_upper ~ fair_upper: max_pts*0.4 ~ max_pts*0.8
        - fair_upper ~ fair_upper*1.5: max_pts*0.05 ~ max_pts*0.4
        - > fair_upper*1.5: 0
        """
        if value <= 0:
            return 0

        excellent = good_upper * 0.6
        poor = fair_upper * 1.5

        if value <= excellent:
            return max_pts
        elif value <= good_upper:
            ratio = (good_upper - value) / (good_upper - excellent) if good_upper > excellent else 1
            pts = max_pts * (0.8 + 0.2 * ratio)
        elif value <= fair_upper:
            ratio = (fair_upper - value) / (fair_upper - good_upper) if fair_upper > good_upper else 1
            pts = max_pts * (0.4 + 0.4 * ratio)
        elif value <= poor:
            ratio = (poor - value) / (poor - fair_upper) if poor > fair_upper else 1
            pts = max_pts * (0.05 + 0.35 * ratio)
        else:
            return 0

        return round(pts)

    def _get_fundamental_score(self, info):
        """기본적 분석 점수 (최대 50점)"""
        score = 0
        comments = []
        breakdown = {
            'roe_score': 0, 'roe_value': 0,
            'opm_score': 0, 'opm_value': 0,
            'revenue_growth_score': 0, 'revenue_growth_value': None,
            'sector_score': 0, 'sector_name': '',
            # 가치주 전용 필드
            'dividend_yield_score': 0, 'dividend_yield_value': None,
            'per_score': 0, 'per_value': None,
            'debt_equity_score': 0, 'debt_equity_value': None,
        }

        try:
            sector = info.get('sector', '')
            industry = info.get('industry', '')

            # ===== 가치주 모드: 배당/저평가/안정성 중심 (50점) =====
            if self.analysis_mode == 'value':
                # 1. 배당수익률 (12점)
                div_yield = info.get('dividendYield')
                if div_yield and div_yield > 0:
                    # yfinance: 보통 decimal(0.019=1.9%) 반환하지만 일부 종목은 percentage(1.9) 반환
                    div_pct = div_yield if div_yield >= 1 else div_yield * 100
                    breakdown['dividend_yield_value'] = div_pct
                    dy_exc, dy_good = self.VALUE_DIVIDEND_THRESHOLDS.get(
                        sector, self.DEFAULT_VALUE_DIVIDEND_THRESHOLD)
                    dy_pts = self._calc_gradient_score(div_pct, dy_exc, dy_good, 12)
                    score += dy_pts
                    breakdown['dividend_yield_score'] = dy_pts
                    if dy_pts >= 6:
                        comments.append(f"배당{div_pct:.1f}%")

                # 2. PER 저평가 (12점, 역방향 - 낮을수록 좋음)
                per = info.get('trailingPE')
                if per and per > 0:
                    breakdown['per_value'] = per
                    per_good, per_fair = self.VALUE_PER_THRESHOLDS.get(
                        sector, self.DEFAULT_VALUE_PER_THRESHOLD)
                    per_pts = self._calc_inverse_gradient_score(per, per_good, per_fair, 12)
                    score += per_pts
                    breakdown['per_score'] = per_pts
                    if per_pts >= 6:
                        comments.append(f"PER:{per:.1f}")

                # 3. ROE (8점, 가치주는 비중 축소)
                roe = info.get('returnOnEquity')
                roe_excellent, roe_good = self.SECTOR_ROE_THRESHOLDS.get(
                    sector, self.DEFAULT_ROE_THRESHOLD)
                if roe:
                    roe_pct = roe * 100
                    breakdown['roe_value'] = roe_pct
                    roe_pts = self._calc_gradient_score(roe_pct, roe_excellent, roe_good, 8)
                    score += roe_pts
                    breakdown['roe_score'] = roe_pts
                    if roe_pts >= 4:
                        comments.append(f"ROE:{roe_pct:.1f}%")

                # 4. 부채비율 D/E (8점, 역방향 - 낮을수록 안정적)
                de = info.get('debtToEquity')
                if de is not None and de >= 0:
                    breakdown['debt_equity_value'] = de
                    de_good, de_fair = self.VALUE_DE_THRESHOLDS.get(
                        sector, self.DEFAULT_VALUE_DE_THRESHOLD)
                    de_pts = self._calc_inverse_gradient_score(de, de_good, de_fair, 8)
                    score += de_pts
                    breakdown['debt_equity_score'] = de_pts
                    if de_pts >= 4:
                        comments.append(f"D/E:{de:.0f}")
                elif sector in ('Financial Services', 'Real Estate'):
                    # 금융/부동산: yfinance D/E 데이터 없는 경우 중간 점수 부여
                    de_pts = round(8 * 0.5)
                    score += de_pts
                    breakdown['debt_equity_score'] = de_pts

                # 5. 섹터 (10점)
                breakdown['sector_name'] = sector
                sector_score, sector_name, sector_comment = self._get_value_sector_score(sector, industry)
                score += sector_score
                breakdown['sector_score'] = sector_score
                breakdown['sector_name'] = sector_name
                if sector_comment:
                    comments.append(sector_comment)

                # 트럼프 정책 보너스/페널티
                policy_bonus, policy_comment = self._get_trump_policy_bonus(
                    sector, industry, sector_name)
                if policy_bonus != 0:
                    score += policy_bonus
                    breakdown['policy_bonus'] = policy_bonus
                    comments.append(policy_comment)

            # ===== 성장주 모드: ROE/OPM/매출성장 중심 (50점) =====
            else:
                # 1. ROE (섹터별 차등 기준, 선형 보간, 15점)
                roe = info.get('returnOnEquity')
                roe_excellent, roe_good = self.SECTOR_ROE_THRESHOLDS.get(
                    sector, self.DEFAULT_ROE_THRESHOLD)
                if roe:
                    roe_pct = roe * 100
                    breakdown['roe_value'] = roe_pct
                    roe_pts = self._calc_gradient_score(roe_pct, roe_excellent, roe_good, 15)
                    score += roe_pts
                    breakdown['roe_score'] = roe_pts
                    if roe_pts >= 8:
                        comments.append(f"ROE:{roe_pct:.1f}%")

                # 2. Operating Margin (업종/섹터별 차등 기준, 15점)
                opm = info.get('operatingMargins')
                opm_excellent, opm_good = self.INDUSTRY_OPM_OVERRIDES.get(
                    industry, self.SECTOR_OPM_THRESHOLDS.get(
                        sector, self.DEFAULT_OPM_THRESHOLD))
                if opm:
                    opm_pct = opm * 100
                    breakdown['opm_value'] = opm_pct
                    opm_pts = self._calc_gradient_score(opm_pct, opm_excellent, opm_good, 15)
                    score += opm_pts
                    breakdown['opm_score'] = opm_pts
                    if opm_pts >= 8:
                        comments.append(f"OPM:{opm_pct:.1f}%")

                # 3. Revenue Growth (매출 성장률, 10점)
                revenue_growth = info.get('revenueGrowth')
                rg_high, rg_good = self.SECTOR_REVENUE_GROWTH_THRESHOLDS.get(
                        sector, self.DEFAULT_REVENUE_GROWTH_THRESHOLD)
                if revenue_growth:
                    rg_pct = revenue_growth * 100
                    breakdown['revenue_growth_value'] = rg_pct
                    rg_pts = self._calc_gradient_score(rg_pct, rg_high, rg_good, 10)
                    score += rg_pts
                    breakdown['revenue_growth_score'] = rg_pts

                # 3-1. 고성장 투자기업 보정 (매출 30%+ & ROE/OPM 적자)
                if revenue_growth and revenue_growth > 0.30:
                    roe_val = roe * 100 if roe else 0
                    opm_val = opm * 100 if opm else 0
                    if roe_val < 0 and breakdown['roe_score'] == 0:
                        growth_credit = round(15 * 0.4)
                        score += growth_credit
                        breakdown['roe_score'] = growth_credit
                        comments.append("성장투자")
                    if opm_val < 0 and breakdown['opm_score'] == 0:
                        growth_credit = round(15 * 0.4)
                        score += growth_credit
                        breakdown['opm_score'] = growth_credit

                # 4. Sector & Industry (세분화된 분류)
                breakdown['sector_name'] = f"{sector}"
                ind_lower = industry.lower()

                # Tier 1: AI, 반도체, 클라우드, 사이버보안, 국방
                if any(keyword in ind_lower for keyword in ['semiconductor', 'chip', 'artificial intelligence', 'computer hardware']):
                    score += self.SCORE_SECTOR_TIER1
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER1
                    breakdown['sector_name'] = "AI/반도체"
                    comments.append("AI/반도체")
                elif any(keyword in ind_lower for keyword in ['cloud', 'data center', 'infrastructure software']):
                    score += self.SCORE_SECTOR_TIER1
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER1
                    breakdown['sector_name'] = "클라우드"
                    comments.append("클라우드")
                elif any(keyword in ind_lower for keyword in ['cybersecurity', 'security software', 'information security']):
                    score += self.SCORE_SECTOR_TIER1
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER1
                    breakdown['sector_name'] = "사이버보안"
                    comments.append("사이버보안")
                elif any(keyword in ind_lower for keyword in ['aerospace', 'defense', 'military']):
                    score += self.SCORE_SECTOR_TIER1
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER1
                    breakdown['sector_name'] = "국방/항공"
                    comments.append("국방/항공")

                # Tier 2: 소프트웨어, EV, 바이오텍, 신재생, 원자력, 희토류, 가전
                elif sector == 'Technology' and any(keyword in ind_lower for keyword in ['software', 'application', 'saas']):
                    score += self.SCORE_SECTOR_TIER2
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER2
                    breakdown['sector_name'] = "소프트웨어"
                    comments.append("소프트웨어")
                elif any(keyword in ind_lower for keyword in ['consumer electronics']):
                    score += self.SCORE_SECTOR_TIER2
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER2
                    breakdown['sector_name'] = "가전/생태계"
                    comments.append("가전/생태계")
                elif any(keyword in ind_lower for keyword in ['electric vehicle', 'ev ', 'battery', 'lithium']):
                    score += self.SCORE_SECTOR_TIER2
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER2
                    breakdown['sector_name'] = "전기차/배터리"
                    comments.append("전기차/배터리")
                elif any(keyword in ind_lower for keyword in ['biotech', 'genomic', 'gene therapy', 'crispr']):
                    score += self.SCORE_SECTOR_TIER2
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER2
                    breakdown['sector_name'] = "바이오텍"
                    comments.append("바이오텍")
                elif any(keyword in ind_lower for keyword in ['solar', 'wind', 'renewable', 'clean energy', 'hydrogen']):
                    score += self.SCORE_SECTOR_TIER2
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER2
                    breakdown['sector_name'] = "신재생에너지"
                    comments.append("신재생에너지")
                elif any(keyword in ind_lower for keyword in ['nuclear', 'uranium', 'reactor', 'enrichment', 'smr']):
                    score += self.SCORE_SECTOR_TIER2
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER2
                    breakdown['sector_name'] = "원자력/우라늄"
                    comments.append("원자력/우라늄")
                elif any(keyword in ind_lower for keyword in ['rare earth', 'lithium', 'cobalt', 'nickel', 'critical mineral']):
                    score += self.SCORE_SECTOR_TIER2
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER2
                    breakdown['sector_name'] = "희토류/전략소재"
                    comments.append("희토류/전략소재")
                elif sector == 'Communication Services':
                    score += self.SCORE_SECTOR_TIER2
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER2
                    breakdown['sector_name'] = "디지털인프라"
                    comments.append("디지털인프라")

                # Tier 3: 헬스케어, 산업자동화, 핀테크
                elif sector == 'Healthcare' and 'biotech' not in ind_lower:
                    score += self.SCORE_SECTOR_TIER3
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER3
                    breakdown['sector_name'] = "헬스케어"
                    comments.append("헬스케어")
                elif sector == 'Industrials' and any(keyword in ind_lower for keyword in ['automation', 'robot', 'machinery']):
                    score += self.SCORE_SECTOR_TIER3
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER3
                    breakdown['sector_name'] = "산업자동화"
                    comments.append("산업자동화")
                elif any(keyword in ind_lower for keyword in ['fintech', 'payment', 'financial technology']):
                    score += self.SCORE_SECTOR_TIER3
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER3
                    breakdown['sector_name'] = "핀테크"
                    comments.append("핀테크")
                elif sector == 'Industrials':
                    score += self.SCORE_SECTOR_TIER3
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER3
                    breakdown['sector_name'] = "산업재"
                    comments.append("산업재")
                elif sector == 'Financial Services':
                    score += self.SCORE_SECTOR_TIER3
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER3
                    breakdown['sector_name'] = "금융"
                    comments.append("금융")

                # Tier 3: 전통 에너지 (미국 에너지 정책 수혜, TIER4→TIER3 상향)
                elif sector == 'Energy' and 'renewable' not in industry.lower():
                    score += self.SCORE_SECTOR_TIER3
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER3
                    breakdown['sector_name'] = "에너지"
                    comments.append("에너지")
                # 원자력 유틸리티 (CEG, VST 등 Independent Power) → TIER2 (원자력 수혜)
                elif sector == 'Utilities' and 'independent power' in industry.lower():
                    score += self.SCORE_SECTOR_TIER2
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER2
                    breakdown['sector_name'] = "원자력발전"
                    comments.append("원자력발전")

                # Tier 4: 소비재, 일반 유틸리티 (5점)
                elif sector in ['Consumer Cyclical', 'Consumer Defensive']:
                    score += self.SCORE_SECTOR_TIER4
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER4
                    breakdown['sector_name'] = "소비재"
                    comments.append("소비재")
                elif sector == 'Utilities':
                    score += self.SCORE_SECTOR_TIER4
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER4
                    breakdown['sector_name'] = "유틸리티"
                    comments.append("유틸리티")

                # Default: 분류 미매칭 (최소 1점 보장)
                else:
                    score += self.SCORE_SECTOR_DEFAULT
                    breakdown['sector_score'] = self.SCORE_SECTOR_DEFAULT
                    breakdown['sector_name'] = sector or "기타"

                # 트럼프 정책 보너스/페널티 적용 (성장주 모드)
                policy_bonus, policy_comment = self._get_trump_policy_bonus(
                    sector, industry, breakdown.get('sector_name', ''))
                if policy_bonus != 0:
                    score += policy_bonus
                    breakdown['policy_bonus'] = policy_bonus
                    comments.append(policy_comment)

                # 성장주 모드 섹터 적합도 스케일링
                # 비핵심 성장 섹터(Tier3 이하)는 ROE/OPM/RevGrowth 점수 축소
                # 핵심 성장 섹터(반도체, 클라우드 등)와 공정 비교를 위해
                sector_tier = breakdown.get('sector_score', 0)
                if sector_tier <= self.SCORE_SECTOR_TIER3:  # 5점 이하
                    base_scores = breakdown.get('roe_score', 0) + breakdown.get('opm_score', 0) + breakdown.get('revenue_growth_score', 0)
                    scale = 0.7 + 0.3 * (sector_tier / self.SCORE_SECTOR_TIER1)  # Tier3=0.85, Tier4=0.79, Default=0.73
                    scaled_base = int(base_scores * scale)
                    score -= (base_scores - scaled_base)
                    comments.append(f"비핵심섹터 조정")

        except Exception:
            pass

        return score, comments, breakdown

    def _get_trump_policy_bonus(self, sector, industry, sector_name=""):
        """트럼프 정부 거시 정책 방향에 따른 섹터 보너스/페널티

        수혜 섹터 (+3):
        - 에너지(화석연료): Drill Baby Drill, 파리협정 탈퇴, LNG 수출 확대
        - 국방/항공: 국방비 증액, NATO 압박 → 유럽 방산 지출↑
        - 금융: 은행 규제 완화, 바젤III 완화, 암호화폐 친화
        - 산업재/제조: 리쇼어링, 관세 정책, 인프라 투자
        - 원자력: 에너지 독립, AI 전력 수요, SMR 지원
        - 희토류/전략소재: 중국 의존 탈피, 공급망 안보

        역풍 섹터 (-3):
        - 신재생에너지: IRA 보조금 축소/폐지 위험, 규제 완화로 경쟁력↓
        - 전기차/배터리: EV 보조금 삭감, 연비규제 완화
        """
        ind_lower = industry.lower() if industry else ""

        # === 수혜 섹터 ===
        # 에너지 (화석연료) - 원유, 가스, 정유, 파이프라인
        if sector == 'Energy' and 'renewable' not in ind_lower and 'solar' not in ind_lower:
            return self.POLICY_BONUS, "[Policy]트럼프 에너지정책 수혜"

        # 국방/항공
        if any(kw in ind_lower for kw in ['aerospace', 'defense', 'military']):
            return self.POLICY_BONUS, "[Policy]트럼프 국방비증액 수혜"

        # 금융 (미국 은행, 보험만 - 핀테크/해외 금융 제외)
        if sector == 'Financial Services' and any(kw in ind_lower for kw in ['bank', 'insurance', 'asset management', 'capital market', 'financial exchange']):
            return self.POLICY_BONUS, "[Policy]트럼프 금융규제완화 수혜"

        # 산업재/제조 (리쇼어링, 인프라)
        if sector == 'Industrials':
            return self.POLICY_BONUS, "[Policy]트럼프 리쇼어링/관세 수혜"

        # 원자력
        if any(kw in ind_lower for kw in ['nuclear', 'uranium', 'reactor', 'enrichment', 'smr']):
            return self.POLICY_BONUS, "[Policy]트럼프 원자력정책 수혜"
        if sector == 'Utilities' and 'independent power' in ind_lower:
            return self.POLICY_BONUS, "[Policy]트럼프 원자력정책 수혜"

        # 희토류/전략소재
        if any(kw in ind_lower for kw in ['rare earth', 'critical mineral', 'cobalt', 'nickel']):
            return self.POLICY_BONUS, "[Policy]트럼프 공급망안보 수혜"

        # === 역풍 섹터 ===
        # 신재생에너지
        if any(kw in ind_lower for kw in ['solar', 'wind', 'renewable', 'clean energy', 'hydrogen']):
            return self.POLICY_PENALTY, "[Policy]트럼프 IRA축소 역풍"

        # 전기차/배터리
        if any(kw in ind_lower for kw in ['electric vehicle', 'ev ', 'battery', 'lithium']):
            return self.POLICY_PENALTY, "[Policy]트럼프 EV보조금삭감 역풍"

        return 0, ""

    def _get_value_sector_score(self, sector, industry):
        """가치주 모드용 섹터 점수 (배당/안정성 중심)"""
        industry_lower = industry.lower()

        # Tier 1 (20점): 필수소비재, 헬스케어 (배당귀족 다수 포함)
        if sector == 'Consumer Defensive':
            return self.VALUE_SECTOR_TIER1, "필수소비재", "필수소비재"
        if sector == 'Healthcare' and 'biotech' not in industry_lower:
            return self.VALUE_SECTOR_TIER1, "헬스케어", "헬스케어"

        # Tier 2 (15점): 유틸리티, 금융 (안정적 배당)
        if sector == 'Utilities':
            return self.VALUE_SECTOR_TIER2, "유틸리티", "유틸리티"
        if sector == 'Financial Services':
            return self.VALUE_SECTOR_TIER2, "금융", "금융"
        # 부동산 - REITs
        if sector == 'Real Estate':
            return self.VALUE_SECTOR_TIER2, "부동산/REITs", "부동산/REITs"

        # Tier 3 (10점): 산업재, 에너지, 통신
        if sector == 'Industrials':
            return self.VALUE_SECTOR_TIER3, "산업재", "산업재"
        if sector == 'Energy':
            return self.VALUE_SECTOR_TIER3, "에너지", "에너지"
        if sector == 'Communication Services' and any(kw in industry_lower for kw in ['telecom', 'wireless']):
            return self.VALUE_SECTOR_TIER3, "통신", "통신"
        # 소재 (화학, 금속 등)
        if sector == 'Basic Materials':
            return self.VALUE_SECTOR_TIER3, "소재", "소재"

        # Tier 4 (5점): 기술주, 경기민감 소비재 (가치주에서는 낮은 점수)
        if sector == 'Technology':
            return self.VALUE_SECTOR_TIER4, "기술주", "기술주"
        if sector == 'Consumer Cyclical':
            return self.VALUE_SECTOR_TIER4, "경기소비재", "경기소비재"
        if sector == 'Communication Services':  # 디지털 미디어 등
            return self.VALUE_SECTOR_TIER4, "미디어/엔터", "미디어/엔터"

        # 기타 섹터 (최소 보장)
        return self.VALUE_SECTOR_DEFAULT, sector if sector else "기타", sector if sector else ""

    def _get_technical_score(self, hist, current_price):
        """전문가급 기술적 분석 (최대 50점)"""
        from ta.trend import MACD, ADXIndicator
        from ta.momentum import RSIIndicator, StochasticOscillator
        from ta.volatility import BollingerBands, AverageTrueRange
        from ta.volume import OnBalanceVolumeIndicator

        score = 0
        comments = []
        breakdown = {
            # 추세 (15점) - MA5/20/60/120 + MACD + 일목균형표 + ADX
            'trend_score': 0, 'ma5': 0, 'ma20': 0, 'ma60': 0, 'ma120': 0,
            'macd_score': 0, 'ichimoku_score': 0, 'adx_score': 0,
            # 모멘텀 (12점)
            'momentum_score': 0, 'rsi_value': 0, 'rsi_score': 0,
            'stoch_score': 0, 'stoch_k': 0, 'stoch_d': 0,
            # 거래량 (10점)
            'volume_score': 0, 'volume_ratio': 0, 'obv_score': 0,
            # 변동성 (8점)
            'volatility_score': 0, 'bb_position': 0, 'atr_score': 0,
            # 가격 패턴 (5점)
            'pattern_score': 0, 'price_position': 0
        }

        try:
            if len(hist) < 120:
                return 0, ["데이터부족"], breakdown

            close = hist['Close']
            volume = hist['Volume']

            # ==================== 1. 추세 분석 (16점) ====================
            trend_score = 0

            # 다층 이동평균 (스윙매매 최적화: 5/20/60/120)
            ma5 = close.rolling(window=5).mean().iloc[-1]
            ma20 = close.rolling(window=20).mean().iloc[-1]
            ma60 = close.rolling(window=60).mean().iloc[-1]
            ma120 = close.rolling(window=120).mean().iloc[-1]

            breakdown['ma5'] = ma5
            breakdown['ma20'] = ma20
            breakdown['ma60'] = ma60
            breakdown['ma120'] = ma120

            if current_price > ma120:
                trend_score += self.SCORE_MA120
                comments.append("MA120↑")
            if current_price > ma60:
                trend_score += self.SCORE_MA60
            if current_price > ma20:
                trend_score += self.SCORE_MA20
            if current_price > ma5:
                trend_score += self.SCORE_MA5

            # MACD
            macd = MACD(close=close)
            macd_line = macd.macd().iloc[-1]
            macd_signal = macd.macd_signal().iloc[-1]

            if macd_line > macd_signal:
                if macd_line > 0:
                    trend_score += self.SCORE_MACD_BULLISH
                    comments.append("MACD골든")
                else:
                    trend_score += self.SCORE_MACD_SIGNAL
                breakdown['macd_score'] = self.SCORE_MACD_BULLISH if macd_line > 0 else self.SCORE_MACD_SIGNAL

            # 일목균형표 (Ichimoku Cloud)
            ichimoku_score = 0
            high_9 = hist['High'].rolling(window=9).max()
            low_9 = hist['Low'].rolling(window=9).min()
            high_26 = hist['High'].rolling(window=26).max()
            low_26 = hist['Low'].rolling(window=26).min()

            tenkan = (high_9 + low_9) / 2      # 전환선
            kijun = (high_26 + low_26) / 2      # 기준선
            senkou_a = ((tenkan + kijun) / 2).shift(26)   # 선행스팬A
            senkou_b = ((hist['High'].rolling(window=52).max() + hist['Low'].rolling(window=52).min()) / 2).shift(26)

            tenkan_now = tenkan.iloc[-1]
            kijun_now = kijun.iloc[-1]
            span_a = senkou_a.iloc[-1] if len(senkou_a.dropna()) > 0 else 0
            span_b = senkou_b.iloc[-1] if len(senkou_b.dropna()) > 0 else 0
            cloud_top = max(span_a, span_b)
            cloud_bottom = min(span_a, span_b)

            breakdown['ichimoku_tenkan'] = float(tenkan_now) if tenkan_now else 0
            breakdown['ichimoku_kijun'] = float(kijun_now) if kijun_now else 0
            breakdown['ichimoku_cloud_top'] = float(cloud_top) if cloud_top else 0
            breakdown['ichimoku_cloud_bottom'] = float(cloud_bottom) if cloud_bottom else 0

            # 구름 위 가격 (+1), TK 크로스 (+1), 미래 구름 양운 (+1)
            if current_price > cloud_top:
                ichimoku_score += 1
                comments.append("구름↑")
            if tenkan_now > kijun_now:
                ichimoku_score += 1
                comments.append("TK골든")
            if span_a > span_b:
                ichimoku_score += 1

            trend_score += ichimoku_score
            breakdown['ichimoku_score'] = ichimoku_score

            # ADX (추세 강도)
            adx = ADXIndicator(high=hist['High'], low=hist['Low'], close=close)
            adx_value = adx.adx().iloc[-1]

            if adx_value > 25:
                trend_score += self.SCORE_ADX_STRONG
                breakdown['adx_score'] = self.SCORE_ADX_STRONG
                comments.append(f"ADX:{adx_value:.0f}")

            breakdown['trend_score'] = trend_score
            score += trend_score

            # ==================== 추세 필터 ====================
            is_downtrend = trend_score < 8

            # ==================== 2. 모멘텀 (12점) ====================
            momentum_score = 0

            # RSI
            rsi_ind = RSIIndicator(close=close, window=14)
            rsi = rsi_ind.rsi().iloc[-1]
            breakdown['rsi_value'] = rsi

            if self.RSI_OPTIMAL_MIN <= rsi <= self.RSI_OPTIMAL_MAX:
                momentum_score += self.SCORE_RSI_OPTIMAL
                breakdown['rsi_score'] = self.SCORE_RSI_OPTIMAL
                comments.append(f"RSI:{rsi:.0f}*")
            elif self.RSI_OVERSOLD <= rsi < self.RSI_GOOD_MAX:
                momentum_score += self.SCORE_RSI_GOOD
                breakdown['rsi_score'] = self.SCORE_RSI_GOOD
                comments.append(f"RSI:{rsi:.0f}")
            elif rsi < self.RSI_OVERSOLD:
                # 하락 추세에서 과매도는 매수 신호가 아님 (떨어지는 칼)
                if not is_downtrend:
                    momentum_score += self.SCORE_RSI_OVERSOLD
                    breakdown['rsi_score'] = self.SCORE_RSI_OVERSOLD
                    comments.append(f"RSI:{rsi:.0f}↓")
                else:
                    # 하락 추세에서는 보너스 없음
                    comments.append(f"RSI:{rsi:.0f}⚠")

            # Stochastic
            stoch = StochasticOscillator(high=hist['High'], low=hist['Low'], close=close)
            stoch_k = stoch.stoch().iloc[-1]
            stoch_d = stoch.stoch_signal().iloc[-1]

            breakdown['stoch_k'] = stoch_k
            breakdown['stoch_d'] = stoch_d

            if stoch_k > stoch_d and stoch_k < 80:
                momentum_score += self.SCORE_STOCH_OPTIMAL
                breakdown['stoch_score'] = self.SCORE_STOCH_OPTIMAL
                comments.append("Stoch골든")
            elif stoch_k > stoch_d:
                momentum_score += self.SCORE_STOCH_GOOD
                breakdown['stoch_score'] = self.SCORE_STOCH_GOOD

            breakdown['momentum_score'] = momentum_score
            score += momentum_score

            # ==================== 3. 거래량 (10점) ====================
            volume_score = 0

            avg_volume = volume.rolling(window=20).mean().iloc[-1]
            current_volume = volume.iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            breakdown['volume_ratio'] = volume_ratio

            # 등급별 점수
            if volume_ratio >= 3.0:
                volume_score += self.SCORE_VOLUME_EXTREME
                comments.append(f"거래량{volume_ratio:.1f}x")
            elif volume_ratio >= 2.0:
                volume_score += self.SCORE_VOLUME_HIGH
                comments.append(f"거래량{volume_ratio:.1f}x")
            elif volume_ratio >= 1.5:
                volume_score += self.SCORE_VOLUME_MODERATE
            elif volume_ratio >= 1.2:
                volume_score += self.SCORE_VOLUME_NORMAL

            # OBV (누적 거래량)
            obv = OnBalanceVolumeIndicator(close=close, volume=volume)
            obv_values = obv.on_balance_volume()
            obv_ma = obv_values.rolling(window=20).mean()

            if len(obv_values) >= 20 and obv_values.iloc[-1] > obv_ma.iloc[-1]:
                volume_score += self.SCORE_OBV_RISING
                breakdown['obv_score'] = self.SCORE_OBV_RISING
                comments.append("OBV↑")

            breakdown['volume_score'] = volume_score
            score += volume_score

            # ==================== 4. 변동성 (8점) ====================
            volatility_score = 0

            # Bollinger Bands
            bb = BollingerBands(close=close)
            bb_high = bb.bollinger_hband().iloc[-1]
            bb_low = bb.bollinger_lband().iloc[-1]
            bb_mid = bb.bollinger_mavg().iloc[-1]

            # 볼린저 밴드 내 위치 (0-1)
            bb_position = (current_price - bb_low) / (bb_high - bb_low) if (bb_high - bb_low) > 0 else 0.5
            breakdown['bb_position'] = bb_position
            breakdown['bb_upper'] = float(bb_high)
            breakdown['bb_lower'] = float(bb_low)
            breakdown['bb_mid'] = float(bb_mid)

            if 0.3 <= bb_position <= 0.7:
                volatility_score += self.SCORE_BB_POSITION  # 중간 위치 (안정)
            elif bb_position < 0.3:
                # 하락 추세에서 BB 하단은 매수 신호가 아님
                if not is_downtrend:
                    volatility_score += 3  # 하단 (반등 기대)
                    comments.append("BB하단")
                # 하락 추세에서는 보너스 없음

            # ATR (변동성 확장)
            atr = AverageTrueRange(high=hist['High'], low=hist['Low'], close=close)
            atr_current = atr.average_true_range().iloc[-1]
            atr_avg = atr.average_true_range().rolling(window=14).mean().iloc[-1]

            if atr_current > atr_avg:
                volatility_score += self.SCORE_ATR_EXPANSION
                breakdown['atr_score'] = self.SCORE_ATR_EXPANSION

            breakdown['atr_value'] = float(atr_current)
            breakdown['volatility_score'] = volatility_score
            score += volatility_score

            # ==================== 5. 가격 패턴 (5점) ====================
            pattern_score = 0

            # 52주 고/저 대비 위치
            high_52w = close.rolling(window=252).max().iloc[-1]
            low_52w = close.rolling(window=252).min().iloc[-1]
            price_position = (current_price - low_52w) / (high_52w - low_52w) if (high_52w - low_52w) > 0 else 0.5
            breakdown['price_position'] = price_position

            if price_position >= 0.9:
                pattern_score += self.SCORE_PRICE_POSITION
                comments.append("52주고점근처")
            elif price_position >= 0.7:
                pattern_score += 3
            elif 0.5 <= price_position < 0.7:
                pattern_score += 2

            breakdown['pattern_score'] = pattern_score
            score += pattern_score

            # ==================== 추세 필터 정보 저장 ====================
            # 하락 추세 플래그 저장 (페널티는 시장 상태 파악 후 적용)
            breakdown['is_downtrend'] = is_downtrend
            if is_downtrend:
                comments.append(f"⚠하락추세")

        except Exception as e:
            print(f"Technical analysis error: {e}")
            pass

        return score, comments, breakdown

    def _get_verdict(self, total_score, market_regime='neutral'):
        """시장 상태에 따른 적응형 투자 판단"""
        # 시장 상태별 기준 점수
        if market_regime == 'bull':
            # 상승장: 인플레이션 방지 (기준 상향)
            strong_buy_threshold = 85
            buy_threshold = 75
            hold_threshold = 65
        elif market_regime == 'bear':
            # 하락장: 디플레이션 보정 (기준 하향)
            strong_buy_threshold = 75
            buy_threshold = 65
            hold_threshold = 55
        else:  # neutral or sideways
            # 중립/횡보: 기본 기준
            strong_buy_threshold = 80
            buy_threshold = 70
            hold_threshold = 60

        # 판정
        if total_score >= strong_buy_threshold:
            return "Strong Buy ★"
        elif total_score >= buy_threshold:
            return "Buy"
        elif total_score >= hold_threshold:
            return "Hold"
        else:
            return "Avoid"

    def _analyze_sector_rotation(self):
        """섹터 순환매 분석 — ETF 모멘텀 기반

        핫 섹터에서 소외 섹터로 자금이 이동하는 순환매 패턴 감지.
        각 섹터의 1주 수익률과 모멘텀 가속/감속을 분석하여
        수급유입/과열주의/순환매 기대/소외 지속 등의 국면을 판별.
        """
        try:
            etf_tickers = list(self.SECTOR_ETF_MAP.values())
            data = yf.download(etf_tickers, period='1mo', progress=False)

            if data.empty:
                return {}

            results = {}
            for sector, etf in self.SECTOR_ETF_MAP.items():
                try:
                    close = data['Close'][etf].dropna()
                    if len(close) < 10:
                        continue

                    # 1주 수익률
                    week_return = (close.iloc[-1] / close.iloc[-5] - 1) * 100
                    # 모멘텀 가속/감속: 최근 5일 vs 이전 5일
                    recent_5d = (close.iloc[-1] / close.iloc[-5] - 1) * 100
                    prev_5d = (close.iloc[-6] / close.iloc[-10] - 1) * 100
                    acceleration = recent_5d - prev_5d

                    results[sector] = {
                        'etf': etf,
                        'week_return': round(week_return, 2),
                        'acceleration': round(acceleration, 2),
                    }
                except Exception:
                    continue

            if not results:
                return {}

            # 1주 수익률 기준으로 순위 매기기
            sorted_sectors = sorted(results.items(), key=lambda x: x[1]['week_return'], reverse=True)
            total = len(sorted_sectors)
            top_cutoff = max(total // 3, 1)
            bottom_cutoff = total - top_cutoff

            for rank, (sector, info) in enumerate(sorted_sectors):
                info['rank'] = rank + 1
                acc = info['acceleration']

                if rank < top_cutoff:
                    # 핫 섹터 (상위 1/3)
                    if acc > 0:
                        info['rotation_bonus'] = self.ROTATION_BONUS_INFLOW
                        info['phase'] = '수급유입'
                    else:
                        info['rotation_bonus'] = self.ROTATION_PENALTY_OVERHEAT
                        info['phase'] = '과열주의'
                elif rank >= bottom_cutoff:
                    # 소외 섹터 (하위 1/3)
                    if acc > 0:
                        info['rotation_bonus'] = self.ROTATION_BONUS_TURNING
                        info['phase'] = '순환매 기대'
                    else:
                        info['rotation_bonus'] = self.ROTATION_PENALTY_COLD
                        info['phase'] = '소외 지속'
                else:
                    # 중위 섹터
                    if acc > 0.5:
                        info['rotation_bonus'] = self.ROTATION_BONUS_WATCHING
                        info['phase'] = '관심'
                    else:
                        info['rotation_bonus'] = 0
                        info['phase'] = '중립'

            return dict(sorted_sectors)

        except Exception as e:
            print(f"  ⚠️ 섹터 순환매 분석 실패: {e}")
            return {}

    def _detect_market_regime(self):
        """시장 상태 감지 (Bull/Bear/Sideways)"""
        try:
            from ta.trend import ADXIndicator

            # S&P 500 분석
            spy = yf.Ticker('^GSPC')
            hist = spy.history(period='1y')

            if len(hist) < 120:
                return 'neutral', {}, "데이터 부족"

            close = hist['Close']
            current_price = close.iloc[-1]

            # 이동평균 (시장 전체는 MA60/120)
            ma60 = close.rolling(window=60).mean().iloc[-1]
            ma120 = close.rolling(window=120).mean().iloc[-1]

            # 추세 방향 (최근 3개월)
            price_3m_ago = close.iloc[-63] if len(close) >= 63 else close.iloc[0]
            trend_3m = (current_price - price_3m_ago) / price_3m_ago

            # 추세 방향 (최근 6개월)
            price_6m_ago = close.iloc[-126] if len(close) >= 126 else close.iloc[0]
            trend_6m = (current_price - price_6m_ago) / price_6m_ago

            # ADX (추세 강도)
            adx = ADXIndicator(high=hist['High'], low=hist['Low'], close=close)
            adx_value = adx.adx().iloc[-1]

            # 신호 카운트
            bull_signals = 0
            bear_signals = 0

            # 1. 가격 vs MA120
            if current_price > ma120:
                bull_signals += 1
            else:
                bear_signals += 1

            # 2. MA60 vs MA120
            if ma60 > ma120:
                bull_signals += 1
            else:
                bear_signals += 1

            # 3. 3개월 추세
            if trend_3m > 0.05:  # +5% 이상
                bull_signals += 1
            elif trend_3m < -0.05:  # -5% 이상
                bear_signals += 1

            # 4. 6개월 추세
            if trend_6m > 0.10:  # +10% 이상
                bull_signals += 1
            elif trend_6m < -0.10:  # -10% 이상
                bear_signals += 1

            # 시장 상태 결정
            if adx_value < 20:  # 약한 추세
                regime = 'sideways'
                regime_kr = '횡보장'
                regime_emoji = '↔️'
            elif bull_signals >= 3:
                regime = 'bull'
                regime_kr = '상승장'
                regime_emoji = '📈'
            elif bear_signals >= 3:
                regime = 'bear'
                regime_kr = '하락장'
                regime_emoji = '📉'
            else:
                regime = 'neutral'
                regime_kr = '중립'
                regime_emoji = '➡️'

            details = {
                'current': current_price,
                'ma60': ma60,
                'ma120': ma120,
                'trend_3m': trend_3m * 100,  # 퍼센트로
                'trend_6m': trend_6m * 100,  # 퍼센트로
                'adx': adx_value,
                'bull_signals': bull_signals,
                'bear_signals': bear_signals
            }

            description = f"{regime_emoji} {regime_kr} (S&P500: {current_price:.0f}, 3개월: {trend_3m*100:+.1f}%, ADX: {adx_value:.0f})"

            return regime, details, description

        except Exception as e:
            print(f"Market regime detection error: {e}")
            return 'neutral', {}, "감지 실패"

    def _apply_regime_adjustment(self, tech_score, fund_score, regime, is_downtrend=False, tech_breakdown=None):
        """시장 상태에 따른 점수 비율 재설계 + 추세 필터 (펀더멘털 차등)"""
        # ==================== 1. 추세 필터 페널티 (펀더멘털 품질 차등) ====================
        trend_penalty_applied = False
        if is_downtrend and tech_score > 0:
            # 펀더멘털 점수에 따라 페널티 차등 적용
            # 우량주 눌림목 = 기회, 약한 종목 하락 = 위험
            if fund_score >= 40:
                # 우량주: 페널티 최소화 (저가매수 기회)
                penalty = 0.9 if regime == 'bear' else 0.85
                trend_penalty_msg = f"하락추세 페널티 -{int((1-penalty)*100)}% (우량주 경감)"
            elif fund_score >= 30:
                # 보통: 기존 수준
                penalty = 0.8 if regime == 'bear' else 0.7
                trend_penalty_msg = f"하락추세 페널티 -{int((1-penalty)*100)}%"
            else:
                # 약한 종목: 페널티 강화
                penalty = 0.7 if regime == 'bear' else 0.5
                trend_penalty_msg = f"하락추세 페널티 -{int((1-penalty)*100)}% (펀더 약세 강화)"
            tech_score = int(tech_score * penalty)
            trend_penalty_applied = True
        else:
            trend_penalty_msg = ""

        # ==================== 2. 시장 상태별 가중치 재설계 ====================
        # 기존: 멀티플라이어 방식 → 신규: 비율 재분배 방식
        if regime == 'bull':
            tech_score = int(tech_score * 1.2)
            fund_score = int(fund_score * 0.8)
            adjustment = "상승장: 기술60% : 펀더40% (모멘텀 중시)"

        elif regime == 'bear':
            tech_score = int(tech_score * 0.8)
            fund_score = int(fund_score * 1.2)
            adjustment = "하락장: 기술40% : 펀더60% (안전성 중시)"

        elif regime == 'sideways':
            adjustment = "횡보장: 기술50% : 펀더50% (균형)"

        else:  # neutral
            adjustment = "중립: 조정 없음"

        # ==================== 3. 점수 상한선 적용 (인플레이션 방지) ====================
        if regime == 'bull':
            tech_score = min(tech_score, 60)  # 상승장에서 기술 점수 상한
            fund_score = min(fund_score, 50)
        elif regime == 'bear':
            tech_score = min(tech_score, 50)
            fund_score = min(fund_score, 65)  # 하락장에서 펀더 점수 상한
        else:
            tech_score = min(tech_score, 55)
            fund_score = min(fund_score, 55)

        # 조정 메시지 통합
        if trend_penalty_applied:
            adjustment = f"{trend_penalty_msg} + {adjustment}"

        return tech_score, fund_score, adjustment

    # ===== 스윙매매 헬퍼 메서드 =====

    def _find_swing_lows(self, hist, lookback=60, order=5):
        """최근 N일 로우에서 스윙 저점(지지선) 탐지"""
        lows = hist['Low'].iloc[-lookback:]
        swing_lows = []
        for i in range(order, len(lows) - order):
            if all(lows.iloc[i] <= lows.iloc[i - j] for j in range(1, order + 1)) and \
               all(lows.iloc[i] <= lows.iloc[i + j] for j in range(1, order + 1)):
                swing_lows.append(float(lows.iloc[i]))
        return sorted(set(swing_lows))

    def _find_swing_highs(self, hist, lookback=60, order=5):
        """최근 N일 하이에서 스윙 고점(저항선) 탐지"""
        highs = hist['High'].iloc[-lookback:]
        swing_highs = []
        for i in range(order, len(highs) - order):
            if all(highs.iloc[i] >= highs.iloc[i - j] for j in range(1, order + 1)) and \
               all(highs.iloc[i] >= highs.iloc[i + j] for j in range(1, order + 1)):
                swing_highs.append(float(highs.iloc[i]))
        return sorted(set(swing_highs))

    @staticmethod
    def _nearest_below(levels, price):
        """현재가 아래 가장 가까운 레벨"""
        candidates = [l for l in levels if l < price]
        return max(candidates) if candidates else None

    @staticmethod
    def _nearest_above(levels, price):
        """현재가 위 가장 가까운 레벨"""
        candidates = [l for l in levels if l > price]
        return min(candidates) if candidates else None

    def _validate_risk_reward(self, buy_price, target_price, stop_loss, atr, swing_highs):
        """R:R >= 1.5 보장, 최대 손절 8%"""
        # 최대 손절 거리 8%
        max_stop = buy_price * 0.92
        if stop_loss < max_stop:
            stop_loss = max_stop

        # R:R 최소 1.5:1
        risk = buy_price - stop_loss
        reward = target_price - buy_price
        if risk > 0 and reward / risk < 1.5:
            farther = [r for r in swing_highs if r > target_price]
            if farther:
                target_price = min(farther)
            elif atr > 0:
                target_price = buy_price + (2.5 * atr)
            else:
                target_price = buy_price * 1.10

        return target_price, stop_loss

    def _calculate_smart_entry_exit(self, current_price, contrarian_adj, hist, tech_breakdown):
        """🎯 스윙매매 특화 진입/청산 전략 (기술적 레벨 기반)"""
        try:
            if len(hist) < 20:
                return None, None, None, "데이터 부족"

            # --- 기술적 데이터 추출 ---
            ma20 = tech_breakdown.get('ma20', 0)
            ma60 = tech_breakdown.get('ma60', 0)
            bb_upper = tech_breakdown.get('bb_upper', 0)
            bb_lower = tech_breakdown.get('bb_lower', 0)
            atr = tech_breakdown.get('atr_value', 0)

            # --- 스윙 구조 탐지 ---
            swing_lows = self._find_swing_lows(hist)
            swing_highs = self._find_swing_highs(hist)
            nearest_support = self._nearest_below(swing_lows, current_price)
            nearest_resistance = self._nearest_above(swing_highs, current_price)

            # ========== Tier 1: 역발상 매수 (과매도 우량주) ==========
            if contrarian_adj > 0:
                # 매수: BB 하단이 현재가 -3% 이내면 BB 하단, 아니면 현재가
                if bb_lower > 0 and bb_lower >= current_price * 0.97:
                    buy_price = bb_lower
                else:
                    buy_price = current_price

                # 목표: 스윙 고점 > BB 상단 > 1.5×ATR
                if nearest_resistance and nearest_resistance > buy_price * 1.03:
                    target_price = nearest_resistance
                elif bb_upper > 0 and bb_upper > buy_price * 1.03:
                    target_price = bb_upper
                else:
                    target_price = buy_price + (1.5 * atr) if atr > 0 else buy_price * 1.08

                # 손절: 스윙 저점 -1% 또는 2×ATR 중 타이트한 쪽
                atr_stop = buy_price - (2.0 * atr) if atr > 0 else buy_price * 0.95
                struct_stop = nearest_support * 0.99 if nearest_support else atr_stop
                stop_loss = max(atr_stop, struct_stop)
                if stop_loss > buy_price * 0.98:
                    stop_loss = buy_price * 0.98
                if stop_loss >= buy_price:
                    stop_loss = buy_price * 0.95

                target_price, stop_loss = self._validate_risk_reward(
                    buy_price, target_price, stop_loss, atr, swing_highs)

                strategy = "🎯 역발상매수(기술적지지)"

            # ========== Tier 2: 조정대기 (과열주) ==========
            elif contrarian_adj < 0:
                # 진입조건가: MA20, 스윙 저점, 2×ATR 풀백 중 가장 높은 값
                candidates = []
                if ma20 > 0 and ma20 < current_price:
                    candidates.append(ma20)
                if nearest_support and nearest_support < current_price:
                    candidates.append(nearest_support)
                if atr > 0:
                    candidates.append(current_price - (2.0 * atr))

                buy_price = max(candidates) if candidates else current_price * 0.95

                # 조건충족시 목표/손절
                if nearest_resistance and nearest_resistance > buy_price * 1.03:
                    target_price = nearest_resistance
                elif bb_upper > 0:
                    target_price = bb_upper
                else:
                    target_price = buy_price * 1.08

                atr_stop = buy_price - (2.0 * atr) if atr > 0 else buy_price * 0.95
                struct_stop = nearest_support * 0.99 if nearest_support else atr_stop
                stop_loss = max(atr_stop, struct_stop)
                if stop_loss >= buy_price:
                    stop_loss = buy_price * 0.95

                target_price, stop_loss = self._validate_risk_reward(
                    buy_price, target_price, stop_loss, atr, swing_highs)

                strategy = "⚠️ 조정대기(진입조건가)"

            # ========== Tier 3: 세분화 전략 (일반종목) ==========
            else:
                rsi = tech_breakdown.get('rsi_value', 50)
                ma120 = tech_breakdown.get('ma120', 0)

                # --- 시장 구조 판별 ---
                uptrend = (ma20 > 0 and ma60 > 0 and ma20 > ma60)
                price_above_ma20 = (ma20 > 0 and current_price > ma20)
                sideways = (ma20 > 0 and ma60 > 0 and abs(ma20 - ma60) / ma60 < 0.02)
                weak = (ma60 > 0 and current_price < ma60) or rsi < 40

                # --- Tier 3A: 📈 추세추종 (강한 상승추세 편승) ---
                if uptrend and price_above_ma20 and rsi >= 50:
                    buy_price = current_price
                    # 목표: 스윙고점 > BB상단 > 2×ATR
                    if nearest_resistance and nearest_resistance > current_price * 1.02:
                        target_price = nearest_resistance
                    elif bb_upper > 0 and bb_upper > current_price * 1.02:
                        target_price = bb_upper
                    else:
                        target_price = current_price + (2.0 * atr) if atr > 0 else current_price * 1.08
                    # 손절: MA20 or 2×ATR 중 타이트한 쪽
                    atr_stop = current_price - (2.0 * atr) if atr > 0 else current_price * 0.95
                    ma20_stop = ma20 * 0.99 if ma20 > 0 else atr_stop
                    stop_loss = max(atr_stop, ma20_stop)
                    if stop_loss > current_price * 0.98:
                        stop_loss = current_price * 0.98
                    if stop_loss >= current_price:
                        stop_loss = current_price * 0.95
                    target_price, stop_loss = self._validate_risk_reward(
                        buy_price, target_price, stop_loss, atr, swing_highs)
                    strategy = "📈 추세추종(MA20↑)"

                # --- Tier 3B: 📊 풀백매수 (상승추세 눌림목) ---
                elif uptrend and not price_above_ma20:
                    support_candidates = []
                    if ma20 > 0 and ma20 < current_price * 1.03:
                        support_candidates.append(('MA20', ma20))
                    if bb_lower > 0 and bb_lower < current_price:
                        support_candidates.append(('BB하단', bb_lower))
                    if nearest_support and nearest_support < current_price:
                        support_candidates.append(('스윙저점', nearest_support))
                    if support_candidates:
                        best_label, best_support = max(support_candidates, key=lambda x: x[1])
                        buy_price = best_support
                        strategy_suffix = best_label
                    else:
                        buy_price = ma20 if ma20 > 0 else current_price
                        strategy_suffix = "MA20"
                    # 목표: 최근 고점 복귀
                    if nearest_resistance and nearest_resistance > current_price:
                        target_price = nearest_resistance
                    elif bb_upper > 0 and bb_upper > current_price:
                        target_price = bb_upper
                    else:
                        target_price = buy_price + (2.0 * atr) if atr > 0 else buy_price * 1.08
                    # 손절
                    supports_below = [l for l in swing_lows if l < buy_price]
                    struct_stop = max(supports_below) * 0.99 if supports_below else buy_price * 0.95
                    atr_stop = buy_price - (2.0 * atr) if atr > 0 else buy_price * 0.95
                    stop_loss = max(atr_stop, struct_stop)
                    if stop_loss > buy_price * 0.98:
                        stop_loss = buy_price * 0.98
                    if stop_loss >= buy_price:
                        stop_loss = buy_price * 0.95
                    target_price, stop_loss = self._validate_risk_reward(
                        buy_price, target_price, stop_loss, atr, swing_highs)
                    strategy = f"📊 풀백매수({strategy_suffix})"

                # --- Tier 3C: 📦 박스권하단 (횡보장 지지선 매수) ---
                elif sideways or (not uptrend and not weak):
                    support_candidates = []
                    if bb_lower > 0 and bb_lower < current_price:
                        support_candidates.append(('BB하단', bb_lower))
                    if nearest_support and nearest_support < current_price:
                        support_candidates.append(('스윙저점', nearest_support))
                    if ma60 > 0 and ma60 < current_price:
                        support_candidates.append(('MA60', ma60))
                    if support_candidates:
                        best_label, best_support = max(support_candidates, key=lambda x: x[1])
                        buy_price = best_support
                        strategy_suffix = best_label
                    else:
                        buy_price = current_price * 0.97
                        strategy_suffix = "지지선"
                    # 목표: 박스 상단 (BB상단 or 스윙고점)
                    if nearest_resistance and nearest_resistance > current_price:
                        target_price = nearest_resistance
                    elif bb_upper > 0 and bb_upper > current_price:
                        target_price = bb_upper
                    else:
                        target_price = buy_price + (1.5 * atr) if atr > 0 else buy_price * 1.06
                    # 손절: 박스 하단 이탈
                    supports_below = [l for l in swing_lows if l < buy_price]
                    struct_stop = max(supports_below) * 0.99 if supports_below else buy_price * 0.95
                    atr_stop = buy_price - (2.0 * atr) if atr > 0 else buy_price * 0.95
                    stop_loss = max(atr_stop, struct_stop)
                    if stop_loss > buy_price * 0.98:
                        stop_loss = buy_price * 0.98
                    if stop_loss >= buy_price:
                        stop_loss = buy_price * 0.95
                    target_price, stop_loss = self._validate_risk_reward(
                        buy_price, target_price, stop_loss, atr, swing_highs)
                    strategy = f"📦 박스권하단({strategy_suffix})"

                # --- Tier 3D: 🔄 반등대기 (약세, 확인 후 진입) ---
                else:
                    # 강한 지지선에서만 진입
                    support_candidates = []
                    if nearest_support and nearest_support < current_price:
                        support_candidates.append(('스윙저점', nearest_support))
                    if ma120 > 0 and ma120 < current_price:
                        support_candidates.append(('MA120', ma120))
                    if bb_lower > 0 and bb_lower < current_price:
                        support_candidates.append(('BB하단', bb_lower))
                    if support_candidates:
                        best_label, best_support = max(support_candidates, key=lambda x: x[1])
                        buy_price = best_support
                        strategy_suffix = best_label
                    else:
                        buy_price = current_price * 0.95
                        strategy_suffix = "지지확인"
                    # 목표: 보수적 (MA60 복귀 or 1.5×ATR)
                    if ma60 > 0 and ma60 > current_price:
                        target_price = ma60
                    elif nearest_resistance and nearest_resistance > current_price:
                        target_price = nearest_resistance
                    else:
                        target_price = buy_price + (1.5 * atr) if atr > 0 else buy_price * 1.06
                    # 손절: 타이트하게
                    supports_below = [l for l in swing_lows if l < buy_price]
                    struct_stop = max(supports_below) * 0.99 if supports_below else buy_price * 0.95
                    atr_stop = buy_price - (1.5 * atr) if atr > 0 else buy_price * 0.95
                    stop_loss = max(atr_stop, struct_stop)
                    if stop_loss > buy_price * 0.97:
                        stop_loss = buy_price * 0.97
                    if stop_loss >= buy_price:
                        stop_loss = buy_price * 0.95
                    target_price, stop_loss = self._validate_risk_reward(
                        buy_price, target_price, stop_loss, atr, swing_highs)
                    strategy = f"🔄 반등대기({strategy_suffix})"

            return buy_price, target_price, stop_loss, strategy

        except Exception:
            return None, None, None, "계산 실패"

    def _get_current_price(self, info, hist):
        """현재가 추출"""
        return info.get('currentPrice') or info.get('regularMarketPrice') or hist['Close'].iloc[-1]

    def _get_market_status_and_prices(self, info, stock_obj=None):
        """시장 상태 및 가격 정보 추출 - 프리/정규/애프터/폐장 정확히 구분"""
        try:
            et_tz = pytz.timezone('America/New_York')
            now_et = datetime.now(et_tz)
            hour = now_et.hour
            minute = now_et.minute
            weekday = now_et.weekday()  # 0=Mon, 6=Sun

            # 시장 시간대 판단
            # Pre-market: 4:00 AM - 9:30 AM ET (월-금)
            # Regular: 9:30 AM - 4:00 PM ET (월-금)
            # After-hours: 4:00 PM - 8:00 PM ET (월-금)
            # 그 외: closed

            market_status = 'closed'
            if weekday < 5:  # 월-금만
                if (hour == 4 and minute >= 0) or (4 < hour < 9) or (hour == 9 and minute < 30):
                    market_status = 'pre'
                elif (hour == 9 and minute >= 30) or (9 < hour < 16):
                    market_status = 'regular'
                elif (hour >= 16 and hour < 20):
                    market_status = 'after'

            # 가격 정보
            regular_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            pre_market_price = info.get('preMarketPrice')
            post_market_price = info.get('postMarketPrice')
            previous_close = info.get('regularMarketPreviousClose') or info.get('previousClose', 0)

            # Extended hours에서 가격 없으면 history(prepost=True)로 실시간 가격 시도
            if market_status in ('pre', 'after') and stock_obj is not None:
                target_price = pre_market_price if market_status == 'pre' else post_market_price
                if not target_price:
                    try:
                        ext = stock_obj.history(period='5d', interval='5m', prepost=True)
                        if not ext.empty:
                            latest = float(ext['Close'].iloc[-1])
                            if market_status == 'pre':
                                pre_market_price = latest
                            else:
                                post_market_price = latest
                    except Exception:
                        pass

            # 시장 상태별 표시용 가격 결정
            if market_status == 'pre':
                display_price = pre_market_price or regular_price
            elif market_status == 'after':
                display_price = post_market_price or regular_price
            else:
                display_price = regular_price

            return {
                'status': market_status,
                'current_price': regular_price,
                'display_price': display_price,
                'pre_market_price': pre_market_price,
                'post_market_price': post_market_price,
                'previous_close': previous_close
            }
        except Exception:
            fallback_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            return {
                'status': 'unknown',
                'current_price': fallback_price,
                'display_price': fallback_price,
                'pre_market_price': None,
                'post_market_price': None,
                'previous_close': info.get('regularMarketPreviousClose') or info.get('previousClose', 0)
            }

    def _apply_contrarian_adjustment(self, fund_score, tech_breakdown, sector_name):
        """하이브리드 전략: 과매도 우량주 보너스, 과열주 감점"""
        adjustment = 0
        contrarian_comment = ""

        rsi = tech_breakdown.get('rsi_value', 50)

        # 우량 성장 섹터 리스트
        quality_growth_sectors = [
            'AI/반도체', '클라우드', '사이버보안', '국방/항공',
            '소프트웨어', '바이오텍', '디지털인프라'
        ]

        # 🎯 과매도 우량주 = 황금 매수 기회
        if rsi < self.RSI_OVERSOLD:
            # 펀더멘털이 우수하고 (30점 이상)
            if fund_score >= 30:
                # 성장 섹터면 큰 보너스
                if sector_name in quality_growth_sectors:
                    adjustment = self.SCORE_OVERSOLD_QUALITY_BONUS
                    contrarian_comment = "🎯저가매수기회"
                # 기타 섹터는 작은 보너스
                else:
                    adjustment = self.SCORE_OVERSOLD_QUALITY_BONUS // 2
                    contrarian_comment = "💎저평가"

        # ⚠️ 과열 = 위험 신호
        elif rsi > self.RSI_OVERBOUGHT:
            adjustment = self.SCORE_OVERBOUGHT_PENALTY
            contrarian_comment = "⚠️과열주의"

        return adjustment, contrarian_comment

    def _generate_analyst_comment(self, stock_data, analyst_data):
        """Titan 분석 데이터 + 월가 데이터를 조합한 애널리스트 톤 코멘트 생성"""
        parts = []
        fund_bd = stock_data.get('fund_breakdown', {})
        tech_bd = stock_data.get('tech_breakdown', {})

        # 1) 펀더멘털 요약
        roe = fund_bd.get('roe_value', 0)
        opm = fund_bd.get('opm_value', 0)
        rev_growth = fund_bd.get('revenue_growth_value')

        fund_parts = []
        if roe >= 20:
            fund_parts.append(f"ROE {roe:.1f}%로 수익성 최상위권")
        elif roe >= 10:
            fund_parts.append(f"ROE {roe:.1f}%로 양호한 수익성")
        elif roe > 0:
            fund_parts.append(f"ROE {roe:.1f}%로 수익성 보통")

        if opm >= 25:
            fund_parts.append(f"영업이익률 {opm:.1f}%의 고마진 구조")
        elif opm >= 15:
            fund_parts.append(f"영업이익률 {opm:.1f}%로 안정적")

        if rev_growth is not None:
            if rev_growth >= 30:
                fund_parts.append(f"매출 YoY +{rev_growth:.0f}% 고성장")
            elif rev_growth >= 10:
                fund_parts.append(f"매출 YoY +{rev_growth:.0f}% 성장세")

        if fund_parts:
            parts.append(". ".join(fund_parts) + ".")

        # 2) 기술적 요약
        rsi = tech_bd.get('rsi_value', 50)
        ma20 = tech_bd.get('ma20', 0)
        ma60 = tech_bd.get('ma60', 0)
        price = stock_data.get('price', 0)

        tech_parts = []
        if ma20 and ma60:
            if ma20 > ma60 and price > ma20:
                tech_parts.append("MA20>MA60 정배열 상태로 상승 추세 진행 중")
            elif ma20 > ma60:
                tech_parts.append("MA20>MA60 정배열이나 단기 조정 구간")
            elif ma20 < ma60 and price < ma20:
                tech_parts.append("MA20<MA60 역배열로 약세 흐름")
            else:
                tech_parts.append("이동평균 수렴 구간으로 방향성 탐색 중")

        if rsi <= 30:
            tech_parts.append(f"RSI {rsi:.0f}으로 과매도 영역 → 반등 가능성")
        elif rsi >= 70:
            tech_parts.append(f"RSI {rsi:.0f}으로 과매수 영역 → 단기 조정 유의")
        elif rsi >= 50:
            tech_parts.append(f"RSI {rsi:.0f}으로 매수세 우위")
        else:
            tech_parts.append(f"RSI {rsi:.0f}으로 매도세 우위")

        if tech_parts:
            parts.append(". ".join(tech_parts) + ".")

        # 3) 월가 컨센서스
        buy_cnt = analyst_data.get('buy_count', 0)
        hold_cnt = analyst_data.get('hold_count', 0)
        sell_cnt = analyst_data.get('sell_count', 0)
        total_cnt = buy_cnt + hold_cnt + sell_cnt
        target_mean = analyst_data.get('target_mean')

        if total_cnt > 0:
            buy_ratio = buy_cnt / total_cnt * 100
            ws_parts = []
            if buy_ratio >= 70:
                ws_parts.append(f"월가 {total_cnt}명 중 {buy_cnt}명 매수 의견(Strong Buy)")
            elif buy_ratio >= 50:
                ws_parts.append(f"월가 {total_cnt}명 중 {buy_cnt}명 매수 의견(Buy)")
            else:
                ws_parts.append(f"월가 매수 {buy_cnt} / 보유 {hold_cnt} / 매도 {sell_cnt}")

            if target_mean and price > 0:
                upside = (target_mean - price) / price * 100
                if upside > 0:
                    ws_parts.append(f"평균 목표가 ${target_mean:.0f} (현재가 대비 +{upside:.0f}% 상승여력)")
                else:
                    ws_parts.append(f"평균 목표가 ${target_mean:.0f} (현재가 대비 {upside:.0f}%)")

            if ws_parts:
                parts.append(". ".join(ws_parts) + ".")

        # 4) 전략 제안
        strategy = stock_data.get('buy_strategy', '')
        contrarian = stock_data.get('contrarian_adjustment', 0)

        if contrarian > 0:
            parts.append("역발상 매수 시그널 감지 → 저가 매수 기회로 판단.")
        elif '추세추종' in strategy:
            parts.append("상승 추세 지속 중으로 추세 추종 매매가 유효.")
        elif '풀백매수' in strategy:
            parts.append("상승 추세 내 조정 구간으로 분할 매수 접근 권장.")
        elif '박스권' in strategy:
            parts.append("횡보 구간 하단 접근 중으로 지지선 확인 후 매수 검토.")
        elif '반등대기' in strategy:
            parts.append("하락 추세로 반등 신호 확인 전까지 관망 권장.")
        elif '⚠️' in strategy:
            parts.append("과열 구간으로 신규 진입보다 조정 후 재진입 권장.")

        return " ".join(parts) if parts else ""

    def _analyze_single_stock(self, ticker):
        """개별 종목 분석"""
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period='1y')  # 전문가급 분석용 1년 데이터

        if hist.empty or len(hist) < 20:
            return None

        # 현재가
        current_price = self._get_current_price(info, hist)

        # 점수 계산
        fund_score, fund_comments, fund_breakdown = self._get_fundamental_score(info)
        tech_score, tech_comments, tech_breakdown = self._get_technical_score(hist, current_price)

        # 🔥 하이브리드 전략: 역발상 조정
        contrarian_adj, contrarian_comment = self._apply_contrarian_adjustment(
            fund_score,
            tech_breakdown,
            fund_breakdown.get('sector_name', '')
        )

        # 최종 점수 (역발상 조정 반영)
        total_score = fund_score + tech_score + contrarian_adj

        # 🎯 스윙매매 특화 진입/청산 전략
        buy_price, target, stop_loss, strategy = self._calculate_smart_entry_exit(
            current_price, contrarian_adj, hist, tech_breakdown
        )

        # 시장 상태 및 가격 정보
        market_info = self._get_market_status_and_prices(info, stock)

        # Verdict
        verdict = self._get_verdict(total_score)

        # 코멘트 조합 (역발상 코멘트 우선 표시)
        all_comments = fund_comments + tech_comments
        if contrarian_comment:
            all_comments.insert(0, contrarian_comment)
        comment = ", ".join(all_comments[:3]) if all_comments else "-"

        # 📊 월가 애널리스트 데이터 수집
        analyst_data = {}
        try:
            rec = stock.recommendations
            if rec is not None and not rec.empty:
                latest = rec.tail(3)
                analyst_data['buy_count'] = int(latest[['strongBuy', 'buy']].sum().sum())
                analyst_data['hold_count'] = int(latest['hold'].sum())
                analyst_data['sell_count'] = int(latest[['sell', 'strongSell']].sum().sum())
        except Exception:
            pass
        try:
            targets = stock.analyst_price_targets
            if targets is not None:
                analyst_data['target_low'] = targets.get('low')
                analyst_data['target_mean'] = targets.get('mean')
                analyst_data['target_high'] = targets.get('high')
        except Exception:
            pass
        try:
            news_list = stock.news
            if news_list:
                analyst_data['news'] = [
                    {'title': n.get('title', ''), 'publisher': n.get('publisher', '')}
                    for n in news_list[:2]
                ]
        except Exception:
            pass

        result = {
            'ticker': ticker,
            'company_name': info.get('shortName', ''),
            'score': total_score,
            'fund_score': fund_score,
            'tech_score': tech_score,
            'contrarian_adjustment': contrarian_adj,
            'fund_breakdown': fund_breakdown,
            'tech_breakdown': tech_breakdown,
            'verdict': verdict,
            'price': current_price,
            'avg_volume': info.get('averageVolume', 0),
            'market_cap': info.get('marketCap', 0),
            'sector': info.get('sector', ''),
            'liquidity_bonus': 0,
            'liquidity_tier': 'N/A',
            'daily_trading_value': 0,
            'market_info': market_info,
            'buy_price': buy_price,
            'buy_strategy': strategy,
            'target': target,
            'stop_loss': stop_loss,
            'comment': comment,
            'analyst_data': analyst_data,
        }

        # 📝 애널리스트 뷰 코멘트 생성
        result['analyst_comment'] = self._generate_analyst_comment(result, analyst_data)

        return result

    def stage2_deep_analysis(self, tickers):
        """2단계: 정밀 분석 (Titan 알고리즘)"""
        print("=" * 70)
        print("📊 STAGE 2: 정밀 분석 (Fundamental + Technical)")
        print("=" * 70)

        # 🌍 시장 상태 감지
        print("\n🌍 시장 상태 감지 중...")
        market_regime, regime_details, regime_desc = self._detect_market_regime()
        print(f"   {regime_desc}\n")

        # 🔄 섹터 순환매 분석
        print("🔄 섹터 순환매 분석 중...")
        self.sector_rotation = self._analyze_sector_rotation()
        if self.sector_rotation:
            phases = {}
            for sector, info in self.sector_rotation.items():
                phase = info.get('phase', '중립')
                if phase not in phases:
                    phases[phase] = []
                phases[phase].append(f"{sector}({info['week_return']:+.1f}%)")

            icons = {'수급유입': '🔥', '과열주의': '⚠️', '순환매 기대': '⚡', '소외 지속': '❄️', '관심': '👀', '중립': '➖'}
            for phase in ['수급유입', '순환매 기대', '관심', '중립', '과열주의', '소외 지속']:
                if phase in phases:
                    print(f"   {icons.get(phase, '')} {phase}: {', '.join(phases[phase])}")
            print()

        results = []
        total = len(tickers)

        for i, ticker in enumerate(tickers, 1):
            try:
                print(f"분석 중: {i}/{total} - {ticker}")

                result = self._analyze_single_stock(ticker)
                if result:
                    # 시장 상태에 따른 점수 조정 (추세 필터 포함)
                    is_downtrend = result.get('tech_breakdown', {}).get('is_downtrend', False)
                    tech_adjusted, fund_adjusted, adjustment_msg = self._apply_regime_adjustment(
                        result['tech_score'],
                        result['fund_score'],
                        market_regime,
                        is_downtrend=is_downtrend,
                        tech_breakdown=result.get('tech_breakdown', {})
                    )

                    # 🔥 거래대금 유동성 티어 보너스
                    avg_vol = result.get('avg_volume', 0)
                    cur_price = result.get('price', 0)
                    daily_value = avg_vol * cur_price
                    if daily_value >= 1_000_000_000:
                        liq_bonus, liq_tier = 5, 'Hot'
                    elif daily_value >= 300_000_000:
                        liq_bonus, liq_tier = 3, 'Active'
                    elif daily_value >= 100_000_000:
                        liq_bonus, liq_tier = 0, 'Normal'
                    else:
                        liq_bonus, liq_tier = -3, 'Thin'

                    result['liquidity_bonus'] = liq_bonus
                    result['liquidity_tier'] = liq_tier
                    result['daily_trading_value'] = daily_value

                    # 모드별 펀더멘털/기술적 가중치 적용
                    if self.analysis_mode == 'value':
                        fund_w, tech_w = 1.3, 0.7   # 가치주: 펀더 65 : 기술 35
                    else:
                        fund_w, tech_w = 0.8, 1.2    # 성장주: 펀더 40 : 기술 60

                    # 🔄 섹터 순환매 보너스
                    sector = result.get('sector', '')
                    rotation_info = self.sector_rotation.get(sector, {})
                    rotation_bonus = rotation_info.get('rotation_bonus', 0)
                    rotation_phase = rotation_info.get('phase', '중립')
                    result['rotation_bonus'] = rotation_bonus
                    result['rotation_phase'] = rotation_phase

                    # 조정된 점수로 총점 재계산 (가중치 + 거래대금 + 순환매 보너스 포함)
                    total_score_adjusted = round(fund_adjusted * fund_w + tech_adjusted * tech_w) + result['contrarian_adjustment'] + liq_bonus + rotation_bonus

                    # 결과에 시장 상태 정보 추가
                    result['market_regime'] = market_regime
                    result['regime_description'] = regime_desc
                    result['regime_adjustment'] = adjustment_msg
                    result['tech_score_original'] = result['tech_score']
                    result['fund_score_original'] = result['fund_score']
                    result['tech_score'] = tech_adjusted
                    result['fund_score'] = fund_adjusted
                    result['score'] = total_score_adjusted
                    result['verdict'] = self._get_verdict(total_score_adjusted, market_regime)

                    results.append(result)

                # API 제한 회피
                time.sleep(0.5)

            except Exception as e:
                print(f"  ⚠️  {ticker} 분석 실패: {e}")
                continue

        print(f"\n✅ 2단계 완료: {len(results)}개 종목 분석 완료")
        print(f"📊 시장 상태: {regime_desc}\n")
        return results

    def display_results(self, results, min_score=60):
        """결과 테이블 출력"""
        print("=" * 100)
        print(f"🎯 PROJECT TITAN - 최종 결과 (Score >= {min_score})")
        print(f"📅 분석 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)

        # 필터링 및 정렬
        filtered = [r for r in results if r['score'] >= min_score]
        filtered.sort(key=lambda x: x['score'], reverse=True)

        if not filtered:
            print(f"⚠️  Score >= {min_score} 이상인 종목이 없습니다.")
            return

        # 테이블 데이터 준비
        table_data = []
        for r in filtered:
            table_data.append([
                r['ticker'],
                r['score'],
                r['verdict'],
                f"${r['price']:.2f}",
                f"${r['buy_price']:.2f}" if r.get('buy_price') else "N/A",
                f"${r['stop_loss']:.2f}" if r['stop_loss'] else "N/A",
                r['comment']
            ])

        headers = ['Ticker', 'Score', 'Verdict', 'Price', '매수신호가', '손절가', 'Comment']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        print(f"\n📊 총 {len(filtered)}개 유망 종목 발견")

    def _get_current_market_status(self):
        """리포트 생성 시점 기준 시장 상태 판별 (경계 시간 여유 포함)"""
        try:
            et_tz = pytz.timezone('America/New_York')
            now_et = datetime.now(et_tz)
            hour = now_et.hour
            minute = now_et.minute
            weekday = now_et.weekday()
            # 분 단위로 변환하여 경계 판별 (10분 여유)
            time_min = hour * 60 + minute
            if weekday >= 5:
                return 'closed'
            if time_min >= 230 and time_min < 570:      # 3:50 AM ~ 9:30 AM
                return 'pre'
            elif time_min >= 570 and time_min < 960:     # 9:30 AM ~ 4:00 PM
                return 'regular'
            elif time_min >= 960 and time_min < 1210:    # 4:00 PM ~ 8:10 PM
                return 'after'
            else:
                return 'closed'
        except Exception:
            return 'unknown'

    def generate_html_report(self, results, report_type="NASDAQ 100", filename="report.html", min_score=50):
        """HTML 리포트 생성"""
        filtered = [r for r in results if r['score'] >= min_score]
        filtered.sort(key=lambda x: x['score'], reverse=True)

        import pytz as _pytz
        _kst = _pytz.timezone('Asia/Seoul')
        now = datetime.now(_kst)

        # 리포트 전체에 적용할 시장 상태 (생성 시점 기준 1회 판별)
        report_market_status = self._get_current_market_status()

        # 시장 상태 및 기준 점수 결정
        market_regime = filtered[0].get('market_regime', 'neutral') if filtered else 'neutral'
        if market_regime == 'bull':
            strong_buy_threshold = 85
            buy_threshold = 75
        elif market_regime == 'bear':
            strong_buy_threshold = 75
            buy_threshold = 65
        else:
            strong_buy_threshold = 80
            buy_threshold = 70

        # 리포트 타입에 따른 색상 설정
        if "NASDAQ" in report_type:
            primary_color = "#5BA3E0"
        elif "Value" in report_type:
            primary_color = "#E8A838"
        else:
            primary_color = "#7B68EE"

        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_type} - Titan Analysis - {now.strftime("%Y-%m-%d")}</title>
    <link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
    <link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" rel="stylesheet">
    <style>
        :root {{
            --bg: #f7f8fa;
            --surface: #ffffff;
            --text: #191f28;
            --text-sub: #8b95a1;
            --text-muted: #b0b8c1;
            --border: #e5e8eb;
            --accent: {primary_color};
            --accent-light: {('#edf2ff' if '5BA3E0' in primary_color else '#fff8e1' if 'E8A838' in primary_color else '#f3f0ff')};
            --green: #20c997;
            --red: #f06595;
            --radius: 16px;
            --shadow: 0 2px 8px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
            --shadow-hover: 0 8px 24px rgba(0,0,0,0.08);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Pretendard Variable', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 20px;
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{ max-width: 960px; margin: 0 auto; }}
        .market-switcher {{
            display: flex; justify-content: center; gap: 4px; margin-bottom: 20px;
            background: var(--surface); border-radius: 12px; padding: 4px;
            box-shadow: var(--shadow); width: fit-content; margin-left: auto; margin-right: auto;
        }}
        .market-btn {{
            padding: 10px 24px; font-size: 0.9em; font-weight: 600; font-family: inherit;
            border: none; border-radius: 10px; cursor: pointer; transition: all 0.2s;
            text-decoration: none; color: var(--text-sub); display: flex; align-items: center; gap: 6px; background: transparent;
        }}
        .market-btn.active {{ background: var(--accent); color: white; }}
        .market-btn:not(.active):hover {{ background: var(--accent-light); color: var(--accent); }}
        .back-link {{
            display: block; text-align: center; margin-bottom: 16px;
            color: var(--text-sub); text-decoration: none; font-weight: 600; font-size: 0.9em;
        }}
        .back-link:hover {{ color: var(--accent); }}
        .header {{
            background: var(--surface);
            border-radius: var(--radius);
            padding: 32px;
            margin-bottom: 20px;
            box-shadow: var(--shadow);
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        .header::before {{
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
            background: linear-gradient(90deg, var(--accent), {('#7c3aed' if '5BA3E0' in primary_color else '#f59f00' if 'E8A838' in primary_color else '#9775fa')});
        }}
        .header h1 {{ color: var(--text); font-size: 1.6em; font-weight: 800; margin-top: 8px; letter-spacing: -0.02em; }}
        .header .subtitle {{ color: var(--text-sub); margin-top: 8px; font-size: 0.95em; }}
        .header .date {{ color: var(--text-muted); margin-top: 8px; font-size: 0.85em; }}
        .titan-badge {{
            display: inline-block; background: var(--accent); color: white;
            padding: 4px 12px; border-radius: 8px; font-size: 0.7em; margin-left: 8px; font-weight: 700;
        }}
        .summary {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px; margin-bottom: 20px;
        }}
        .summary-card {{
            background: var(--surface); border-radius: var(--radius); padding: 18px;
            box-shadow: var(--shadow); text-align: center;
        }}
        .summary-card .label {{ color: var(--text-sub); margin-bottom: 6px; font-size: 0.85em; }}
        .summary-card .value {{ color: var(--accent); font-size: 1.5em; font-weight: 700; }}
        .stock-card {{
            background: var(--surface); border-radius: var(--radius); padding: 24px;
            margin-bottom: 12px; box-shadow: var(--shadow); position: relative;
            transition: box-shadow 0.2s;
        }}
        .stock-card:hover {{ box-shadow: var(--shadow-hover); }}
        .stock-card .rank {{
            position: absolute; top: 12px; left: 12px;
            background: var(--accent); color: white;
            width: 36px; height: 36px; border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 0.9em;
        }}
        .stock-card h2 {{ color: var(--text); margin-bottom: 8px; padding-left: 48px; font-size: 1.2em; font-weight: 700; }}
        .stock-card .ticker {{ color: var(--accent); font-weight: 700; font-size: 1.05em; }}
        .stock-card .info {{ margin-top: 14px; display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px; }}
        .stock-card .info-item {{ padding: 10px; background: var(--bg); border-radius: 12px; }}
        .stock-card .info-label {{ font-size: 0.8em; color: var(--text-sub); }}
        .stock-card .info-value {{ font-weight: 700; color: var(--text); margin-top: 2px; }}
        .score-badge {{
            background: var(--accent); color: white; padding: 6px 16px; border-radius: 10px;
            float: right; font-weight: 700; font-size: 1em;
        }}
        .score-badge.high {{ background: var(--green); }}
        .score-badge.strong {{ background: #f76707; }}
        .verdict {{
            display: inline-block; padding: 4px 14px; border-radius: 8px;
            font-size: 0.85em; font-weight: 700; margin-top: 8px;
        }}
        .verdict.strong-buy {{ background: #e6fcf5; color: #0ca678; }}
        .verdict.buy {{ background: #e6fcf5; color: var(--green); }}
        .verdict.hold {{ background: #fff9db; color: #e67700; }}
        .comment {{
            margin-top: 12px; padding: 12px 14px; background: var(--bg);
            border-left: 3px solid var(--accent); border-radius: 8px;
            font-size: 0.88em; color: var(--text); line-height: 1.6;
        }}
        .analyst-view {{
            margin-top: 14px; padding: 18px 20px;
            background: var(--bg); border: 1px solid var(--border); border-radius: 12px;
        }}
        .analyst-header {{
            font-weight: 700; font-size: 0.92em; color: var(--text);
            margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid var(--border);
        }}
        .analyst-comment {{
            font-size: 0.86em; color: var(--text); line-height: 1.8;
            margin-bottom: 14px; padding: 12px 14px; background: var(--surface);
            border-radius: 10px; border-left: 3px solid var(--accent);
        }}
        .wall-street {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }}
        .ws-tag {{ padding: 6px 12px; border-radius: 8px; font-size: 0.82em; font-weight: 700; }}
        .ws-consensus {{ background: #e6fcf5; color: #0ca678; }}
        .ws-target {{ background: #edf2ff; color: #4263eb; }}
        .ws-news {{
            font-size: 0.82em; color: var(--text-sub); line-height: 1.6;
            padding: 10px 14px; background: var(--surface); border-radius: 10px; border: 1px solid var(--border);
        }}
        .ws-news-item {{ padding: 4px 0; }}
        .ws-news-item + .ws-news-item {{ border-top: 1px solid var(--border); margin-top: 4px; padding-top: 8px; }}
        .ws-news-pub {{ color: var(--text-muted); font-size: 0.9em; }}
        .detail-toggle {{
            display: inline-block; margin-top: 10px; padding: 6px 16px;
            background: var(--bg); color: var(--text-sub); border: 1px solid var(--border);
            border-radius: 10px; font-size: 0.84em; font-weight: 600;
            cursor: pointer; transition: all 0.2s; font-family: inherit;
        }}
        .detail-toggle:hover {{ background: var(--accent-light); color: var(--accent); border-color: var(--accent); }}
        .score-breakdown {{ margin: 14px 0; padding: 16px; background: var(--bg); border-radius: 12px; border: 1px solid var(--border); display: none; }}
        .score-breakdown.open {{ display: block; }}
        .score-breakdown h3 {{ color: var(--text); margin-bottom: 12px; font-size: 0.95em; }}
        .breakdown-section {{ margin-bottom: 12px; }}
        .breakdown-title {{ font-weight: 700; color: var(--accent); margin-bottom: 8px; font-size: 0.9em; }}
        .breakdown-items {{ display: grid; gap: 4px; }}
        .breakdown-item {{
            display: grid; grid-template-columns: 1fr auto auto; gap: 10px;
            padding: 8px 12px; background: var(--surface); border-radius: 8px;
            align-items: center; font-size: 0.84em;
        }}
        .breakdown-item .criterion {{ color: var(--text); font-weight: 500; }}
        .breakdown-item .criterion-value {{ color: var(--text-sub); text-align: right; }}
        .breakdown-item .criterion-score {{ color: var(--accent); font-weight: 700; text-align: right; min-width: 50px; }}
        .highlight-price {{ background: var(--accent-light) !important; font-weight: bold; }}
        .scoring-btn {{
            display: inline-block; margin-top: 12px; padding: 8px 20px;
            background: var(--text); color: white; border: none; border-radius: 10px;
            font-size: 0.85em; font-weight: 600; cursor: pointer; transition: all 0.2s; font-family: inherit;
        }}
        .scoring-btn:hover {{ opacity: 0.85; transform: translateY(-1px); }}
        .scoring-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999; justify-content: center; align-items: center; backdrop-filter: blur(4px); }}
        .scoring-overlay.active {{ display: flex; }}
        .scoring-modal {{ width: 95%; max-width: 1200px; height: 90vh; border-radius: var(--radius); overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.3); position: relative; }}
        .scoring-modal iframe {{ width: 100%; height: 100%; border: none; }}
        .scoring-close {{ position: absolute; top: 12px; right: 16px; width: 36px; height: 36px; background: rgba(0,0,0,0.6); color: #fff; border: none; border-radius: 10px; font-size: 1.2em; cursor: pointer; z-index: 10; display: flex; align-items: center; justify-content: center; }}
        .scoring-close:hover {{ background: rgba(240,101,149,0.8); }}
        .footer {{
            background: var(--surface); border-radius: var(--radius); padding: 20px;
            text-align: center; color: var(--text-muted); margin-top: 24px;
            box-shadow: var(--shadow); font-size: 0.85em; line-height: 1.7;
        }}
        @media (max-width: 768px) {{
            body {{ padding: 12px; }}
            .header {{ padding: 24px 16px; }}
            .header h1 {{ font-size: 1.25em; }}
            .titan-badge {{ display: block; margin: 8px auto 0; width: fit-content; }}
            .summary {{ grid-template-columns: repeat(2, 1fr); gap: 8px; }}
            .summary-card {{ padding: 14px 8px; }}
            .summary-card .value {{ font-size: 1.2em; }}
            .stock-card {{ padding: 18px 14px; }}
            .stock-card .rank {{ width: 30px; height: 30px; font-size: 0.85em; border-radius: 8px; }}
            .stock-card h2 {{ padding-left: 40px; font-size: 1.05em; padding-right: 70px; }}
            .score-badge {{ padding: 5px 12px; font-size: 0.9em; }}
            .stock-card .info {{ grid-template-columns: repeat(2, 1fr); gap: 6px; }}
            .breakdown-item {{ grid-template-columns: 1fr auto; gap: 4px; font-size: 0.8em; }}
            .breakdown-item .criterion-value {{ display: none; }}
            .comment {{ font-size: 0.82em; }}
            .analyst-view {{ padding: 14px; }}
            .analyst-comment {{ font-size: 0.82em; padding: 10px 12px; margin-bottom: 12px; }}
            .wall-street {{ gap: 6px; }}
            .ws-tag {{ font-size: 0.78em; padding: 5px 10px; }}
            .ws-news {{ padding: 8px 10px; font-size: 0.8em; }}
            .verdict {{ font-size: 0.8em; padding: 4px 12px; }}
            .scoring-modal {{ width: 100%; height: 95vh; border-radius: 10px; }}
        }}
        @media (max-width: 400px) {{
            .header h1 {{ font-size: 1.1em; }}
            .summary {{ grid-template-columns: 1fr 1fr; gap: 6px; }}
            .stock-card h2 {{ font-size: 0.95em; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="market-switcher">
            <span class="market-btn active">US</span>
            <a href="https://redchoeng.github.io/stock-recommendation_kr/" class="market-btn">KR</a>
        </div>
        <a href="index.html" class="back-link">&larr; 메인으로</a>
        <div class="header">
            <h1>{report_type} Recommendations <span class="titan-badge">TITAN v2.0</span></h1>
            <div class="subtitle">Fundamental + Technical + Volatility Breakout Analysis</div>
            <div class="date">{now.strftime("%Y-%m-%d %H:%M")} KST 업데이트</div>
            <button class="scoring-btn" onclick="document.getElementById('scoringOverlay').classList.add('active')">📐 점수 체계 보기</button>
        </div>
        <!-- 점수 체계 모달 -->
        <div id="scoringOverlay" class="scoring-overlay" onclick="if(event.target===this)this.classList.remove('active')">
            <div class="scoring-modal">
                <button class="scoring-close" onclick="document.getElementById('scoringOverlay').classList.remove('active')">&times;</button>
                <iframe src="scoring_system.html"></iframe>
            </div>
        </div>
        <div class="summary">
            <div class="summary-card">
                <div class="label">분석 종목</div>
                <div class="value">{len(results)}개</div>
            </div>
            <div class="summary-card">
                <div class="label">추천 종목 (≥{min_score}점)</div>
                <div class="value">{len(filtered)}개</div>
            </div>
            <div class="summary-card">
                <div class="label">Strong Buy (≥{strong_buy_threshold}점)</div>
                <div class="value">{len([r for r in filtered if r['score'] >= strong_buy_threshold])}개</div>
            </div>
            <div class="summary-card">
                <div class="label">평균 점수</div>
                <div class="value">{sum(r['score'] for r in filtered) / len(filtered) if filtered else 0:.0f}점</div>
            </div>
            <div class="summary-card" style="grid-column: 1 / -1; background: var(--accent); color: white;">
                <div class="label" style="color: rgba(255,255,255,0.8);">시장 상태 및 평가 기준</div>
                <div class="value" style="font-size: 1em; color: white;">{filtered[0].get('regime_description', 'N/A') if filtered else 'N/A'}<br>
                <span style="font-size: 0.8em; opacity: 0.85;">Strong Buy ≥{strong_buy_threshold}점 | Buy ≥{buy_threshold}점</span></div>
            </div>
        </div>
'''

        for i, stock in enumerate(filtered, 1):
            score_class = 'strong' if stock['score'] >= strong_buy_threshold else ('high' if stock['score'] >= buy_threshold else '')
            verdict_class = stock['verdict'].lower().replace(' ', '-').replace('★', '').strip()

            # 점수 상세 정보
            fund_bd = stock.get('fund_breakdown', {})
            tech_bd = stock.get('tech_breakdown', {})

            # 매출성장률 표시 (None이면 N/A)
            rg_value = fund_bd.get('revenue_growth_value')
            rg_display = f"{rg_value:.1f}%" if rg_value is not None else "N/A"

            # 가치주 여부 판별 (dividend_yield_value가 있으면 가치주 모드)
            is_value_mode = fund_bd.get('dividend_yield_value') is not None or 'Value' in report_type

            # 정책 보너스 HTML (중첩 f-string 회피 - Python 3.11 호환)
            policy_bonus = fund_bd.get('policy_bonus', 0)
            if policy_bonus != 0:
                p_color = '76,175,80' if policy_bonus > 0 else '244,67,54'
                p_label = '수혜' if policy_bonus > 0 else '역풍'
                p_sign = '+' if policy_bonus > 0 else ''
                policy_html = f'''<div class="breakdown-item" style="background: rgba({p_color}, 0.08);">
                            <span class="criterion">[Policy] 정책</span>
                            <span class="criterion-value">트럼프 정부 {p_label}</span>
                            <span class="criterion-score">{p_sign}{policy_bonus}점</span>
                        </div>'''
            else:
                policy_html = ""

            # === 가격 블록을 먼저 빌드 (카드 상단에 표시) ===
            market_info = stock.get('market_info', {})
            market_status = report_market_status  # 리포트 생성 시점 기준 통일
            prev_close = market_info.get('previous_close', 0)
            regular_price = stock['price']
            display_price = market_info.get('display_price', regular_price)

            if market_status == 'pre':
                status_color = '#FF9800'
                status_label = '🌅 프리마켓'
                base_price = prev_close
            elif market_status == 'after':
                status_color = '#9C27B0'
                status_label = '🌙 애프터장'
                base_price = regular_price
            elif market_status == 'regular':
                status_color = '#4CAF50'
                status_label = '☀️ 정규장'
                base_price = prev_close
            else:
                status_color = '#607D8B'
                status_label = '🌙 폐장'
                base_price = prev_close

            change_pct = ((display_price - base_price) / base_price * 100) if base_price > 0 else 0
            change_color = '#4CAF50' if change_pct >= 0 else '#F44336'
            change_sign = '+' if change_pct >= 0 else ''

            price_html = f'''
            <div class="info">
                <div class="info-item" style="background: {status_color}; color: white;">
                    <div class="info-label" style="color: rgba(255,255,255,0.9);">{status_label}</div>
                    <div class="info-value" style="font-size: 1.2em;">${display_price:.2f}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">전일대비</div>
                    <div class="info-value" style="color: {change_color}; font-weight: bold;">{change_sign}{change_pct:.2f}%</div>
                </div>'''

            buy_strategy = stock.get('buy_strategy', '')
            if stock.get('buy_price') is not None and buy_strategy.startswith('⚠️'):
                price_html += f'''
                <div class="info-item" style="background: rgba(244, 67, 54, 0.1); border-left: 3px solid #F44336;">
                    <div class="info-label">⚠️ 투자전략</div>
                    <div class="info-value" style="color: #F44336;">조정 대기</div>
                </div>
                <div class="info-item" style="background: rgba(255, 152, 0, 0.1);">
                    <div class="info-label">진입 조건가</div>
                    <div class="info-value" style="color: #E67E22;">${stock['buy_price']:.2f}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">조건충족시 목표</div>
                    <div class="info-value">${stock['target']:.2f}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">조건충족시 손절</div>
                    <div class="info-value">${stock['stop_loss']:.2f}</div>
                </div>'''
            elif stock.get('buy_price') is not None:
                price_html += f'''
                <div class="info-item">
                    <div class="info-label">매수가 {buy_strategy}</div>
                    <div class="info-value">${stock['buy_price']:.2f}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">목표가</div>
                    <div class="info-value">${stock['target']:.2f}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">손절가</div>
                    <div class="info-value">${stock['stop_loss']:.2f}</div>
                </div>'''
            else:
                price_html += f'''
                <div class="info-item" style="background: rgba(244, 67, 54, 0.1);">
                    <div class="info-label">⚠️ 투자전략</div>
                    <div class="info-value" style="color: #F44336;">데이터 부족</div>
                </div>'''

            price_html += '''
            </div>'''

            # 코멘트
            comment_html = ''
            if stock['comment'] and stock['comment'] != '-':
                comment_html = f'<div class="comment">💡 {stock["comment"]}</div>'

            # 📝 애널리스트 뷰
            analyst_view_html = ''
            analyst_comment = stock.get('analyst_comment', '')
            a_data = stock.get('analyst_data', {})
            if analyst_comment or a_data:
                analyst_view_html = '<div class="analyst-view">'
                analyst_view_html += '<div class="analyst-header">📝 Titan 애널리스트 뷰</div>'
                if analyst_comment:
                    analyst_view_html += f'<div class="analyst-comment">{analyst_comment}</div>'

                # 월가 컨센서스 태그
                ws_tags = []
                a_buy = a_data.get('buy_count', 0)
                a_hold = a_data.get('hold_count', 0)
                a_sell = a_data.get('sell_count', 0)
                a_total = a_buy + a_hold + a_sell
                if a_total > 0:
                    buy_ratio = a_buy / a_total * 100
                    if buy_ratio >= 70:
                        consensus_label = 'Strong Buy'
                    elif buy_ratio >= 50:
                        consensus_label = 'Buy'
                    else:
                        consensus_label = 'Hold'
                    ws_tags.append(f'<span class="ws-tag ws-consensus">월가: {consensus_label} ({a_buy}/{a_total})</span>')

                a_target_mean = a_data.get('target_mean')
                a_target_low = a_data.get('target_low')
                a_target_high = a_data.get('target_high')
                if a_target_mean:
                    target_str = f'목표가 ${a_target_mean:.0f}'
                    if a_target_low and a_target_high:
                        target_str = f'목표가 ${a_target_low:.0f}~${a_target_high:.0f} (avg ${a_target_mean:.0f})'
                    ws_tags.append(f'<span class="ws-tag ws-target">{target_str}</span>')

                if ws_tags:
                    analyst_view_html += '<div class="wall-street">' + ''.join(ws_tags) + '</div>'

                # 뉴스 헤드라인
                news_items = a_data.get('news', [])
                if news_items:
                    news_html = '<div class="ws-news">'
                    for n in news_items[:2]:
                        title = n.get('title', '')
                        publisher = n.get('publisher', '')
                        if title:
                            pub_str = f' <span class="ws-news-pub">— {publisher}</span>' if publisher else ''
                            news_html += f'<div class="ws-news-item">📰 {title}{pub_str}</div>'
                    news_html += '</div>'
                    analyst_view_html += news_html

                analyst_view_html += '</div>'

            html += f'''
        <div class="stock-card">
            <div class="rank">#{i}</div>
            <span class="score-badge {score_class}">{stock['score']}점</span>
            <h2><span class="ticker">{stock['ticker']}</span> <span style="font-size:0.55em; color:#7B6B4F; font-weight:normal;">{stock.get('company_name', '')}</span></h2>
            <span class="verdict {verdict_class}">{stock['verdict']}</span>

            {price_html}
            {comment_html}
            {analyst_view_html}

            <button class="detail-toggle" onclick="toggleDetail({i})">상세 분석 ▼</button>

            <!-- 점수 상세 분석 (접힌 상태) -->
            <div class="score-breakdown" id="detail-{i}">
                <h3>📊 점수 상세 분석</h3>
                <div class="breakdown-section">
                    <div class="breakdown-title">펀더멘털 점수: {stock.get('fund_score', 0)}점 / 50점</div>
                    <div class="breakdown-items">''' + (f'''
                        <div class="breakdown-item">
                            <span class="criterion">배당수익률</span>
                            <span class="criterion-value">{fund_bd.get('dividend_yield_value', 0):.2f}%</span>
                            <span class="criterion-score">+{fund_bd.get('dividend_yield_score', 0)}점</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">PER (저평가)</span>
                            <span class="criterion-value">{fund_bd.get('per_value', 0):.1f}x</span>
                            <span class="criterion-score">+{fund_bd.get('per_score', 0)}점</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">ROE (수익성)</span>
                            <span class="criterion-value">{fund_bd.get('roe_value', 0):.1f}%</span>
                            <span class="criterion-score">+{fund_bd.get('roe_score', 0)}점</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">부채비율 (D/E)</span>
                            <span class="criterion-value">{"N/A" if fund_bd.get('debt_equity_value') is None else f"{fund_bd.get('debt_equity_value', 0):.0f}%"}</span>
                            <span class="criterion-score">+{fund_bd.get('debt_equity_score', 0)}점</span>
                        </div>''' if is_value_mode else f'''
                        <div class="breakdown-item">
                            <span class="criterion">ROE (자기자본이익률)</span>
                            <span class="criterion-value">{fund_bd.get('roe_value', 0):.1f}%</span>
                            <span class="criterion-score">+{fund_bd.get('roe_score', 0)}점</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">OPM (영업이익률)</span>
                            <span class="criterion-value">{fund_bd.get('opm_value', 0):.1f}%</span>
                            <span class="criterion-score">+{fund_bd.get('opm_score', 0)}점</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">매출성장률</span>
                            <span class="criterion-value">{rg_display}</span>
                            <span class="criterion-score">+{fund_bd.get('revenue_growth_score', 0)}점</span>
                        </div>''') + f'''
                        <div class="breakdown-item">
                            <span class="criterion">섹터</span>
                            <span class="criterion-value">{fund_bd.get('sector_name', 'N/A')}</span>
                            <span class="criterion-score">+{fund_bd.get('sector_score', 0)}점</span>
                        </div>
                        {policy_html}
                    </div>
                </div>
                <div class="breakdown-section">
                    <div class="breakdown-title">기술적 점수: {stock.get('tech_score', 0)}점 / 50점</div>
                    <div class="breakdown-items">
                        <!-- 추세 분석 -->
                        <div class="breakdown-item" style="background: rgba(103, 126, 234, 0.05);">
                            <span class="criterion">📈 추세 분석</span>
                            <span class="criterion-value">MA5/20/60/120, MACD, 일목균형표, ADX</span>
                            <span class="criterion-score">+{tech_bd.get('trend_score', 0)}점 /20</span>
                        </div>
                        <!-- 모멘텀 -->
                        <div class="breakdown-item" style="background: rgba(76, 175, 80, 0.05);">
                            <span class="criterion">⚡ 모멘텀</span>
                            <span class="criterion-value">RSI:{tech_bd.get('rsi_value', 0):.0f}, Stoch</span>
                            <span class="criterion-score">+{tech_bd.get('momentum_score', 0)}점 /10</span>
                        </div>
                        <!-- 거래량 -->
                        <div class="breakdown-item" style="background: rgba(255, 152, 0, 0.05);">
                            <span class="criterion">📊 거래량</span>
                            <span class="criterion-value">{tech_bd.get('volume_ratio', 0):.1f}x, OBV</span>
                            <span class="criterion-score">+{tech_bd.get('volume_score', 0)}점 /8</span>
                        </div>
                        <!-- 변동성 -->
                        <div class="breakdown-item" style="background: rgba(156, 39, 176, 0.05);">
                            <span class="criterion">🌊 변동성</span>
                            <span class="criterion-value">BB, ATR</span>
                            <span class="criterion-score">+{tech_bd.get('volatility_score', 0)}점 /7</span>
                        </div>
                        <!-- 가격 패턴 -->
                        <div class="breakdown-item" style="background: rgba(244, 67, 54, 0.05);">
                            <span class="criterion">🎯 가격 패턴</span>
                            <span class="criterion-value">52주 {tech_bd.get('price_position', 0):.0%}</span>
                            <span class="criterion-score">+{tech_bd.get('pattern_score', 0)}점 /5</span>
                        </div>
                    </div>
                </div>'''

            # 시장 상태 조정 표시
            regime_adjustment = stock.get('regime_adjustment', '')
            if regime_adjustment and regime_adjustment != '중립: 조정 없음':
                html += f'''
                <div class="breakdown-section" style="border-top: 2px dashed #667eea; padding-top: 10px; margin-top: 10px;">
                    <div class="breakdown-title" style="color: #667eea;">🌍 {regime_adjustment}</div>
                    <div class="breakdown-items">
                        <div class="breakdown-item" style="background: rgba(102, 126, 234, 0.05);">
                            <span class="criterion">원래 기술 점수</span>
                            <span class="criterion-value">{stock.get('tech_score_original', 0)}점</span>
                            <span class="criterion-score">→ {stock.get('tech_score', 0)}점</span>
                        </div>
                        <div class="breakdown-item" style="background: rgba(102, 126, 234, 0.05);">
                            <span class="criterion">원래 펀더 점수</span>
                            <span class="criterion-value">{stock.get('fund_score_original', 0)}점</span>
                            <span class="criterion-score">→ {stock.get('fund_score', 0)}점</span>
                        </div>
                    </div>
                </div>'''

            # 역발상 조정 표시 (보너스/페널티가 있을 때만)
            contrarian_adj = stock.get('contrarian_adjustment', 0)
            if contrarian_adj != 0:
                adj_sign = '+' if contrarian_adj > 0 else ''
                adj_color = '#4CAF50' if contrarian_adj > 0 else '#F44336'
                adj_label = '🎯 역발상 보너스' if contrarian_adj > 0 else '⚠️ 과열 감점'
                html += f'''
                <div class="breakdown-section" style="border-top: 2px solid {primary_color}; padding-top: 10px; margin-top: 10px;">
                    <div class="breakdown-title" style="color: {adj_color};">{adj_label}: {adj_sign}{contrarian_adj}점</div>
                    <div class="breakdown-items">
                        <div class="breakdown-item" style="background: rgba(76, 175, 80, 0.1);">
                            <span class="criterion">최종 점수</span>
                            <span class="criterion-value">{stock.get('fund_score', 0)} + {stock.get('tech_score', 0)} {adj_sign}{contrarian_adj}</span>
                            <span class="criterion-score" style="color: {adj_color}; font-size: 1.1em;">{stock['score']}점</span>
                        </div>
                    </div>
                </div>'''

            # 💧 거래대금 유동성 티어 표시
            liq_bonus = stock.get('liquidity_bonus', 0)
            liq_tier = stock.get('liquidity_tier', 'N/A')
            daily_val = stock.get('daily_trading_value', 0)
            daily_val_m = daily_val / 1e6  # 백만 달러 단위
            liq_sign = '+' if liq_bonus >= 0 else ''
            tier_colors = {'Hot': '#FF6B35', 'Active': '#27AE60', 'Normal': '#7B6B4F', 'Thin': '#E74C3C'}
            liq_color = tier_colors.get(liq_tier, '#7B6B4F')
            html += f'''
                <div class="breakdown-section" style="border-top: 2px dashed #3498DB; padding-top: 10px; margin-top: 10px;">
                    <div class="breakdown-title" style="color: {liq_color};">💧 거래대금 유동성: {liq_tier} ({liq_sign}{liq_bonus}점)</div>
                    <div class="breakdown-items">
                        <div class="breakdown-item" style="background: rgba(52, 152, 219, 0.05);">
                            <span class="criterion">일 거래대금</span>
                            <span class="criterion-value">${daily_val_m:,.0f}M</span>
                            <span class="criterion-score" style="color: {liq_color};">{liq_sign}{liq_bonus}점</span>
                        </div>
                    </div>
                </div>'''

            # 🔄 섹터 순환매 표시
            rot_bonus = stock.get('rotation_bonus', 0)
            rot_phase = stock.get('rotation_phase', '')
            if rot_phase and rot_phase != '중립':
                rot_sign = '+' if rot_bonus >= 0 else ''
                phase_colors = {'수급유입': '#FF6B35', '순환매 기대': '#27AE60', '관심': '#3498DB', '과열주의': '#E67E22', '소외 지속': '#E74C3C'}
                phase_icons = {'수급유입': '🔥', '순환매 기대': '⚡', '관심': '👀', '과열주의': '⚠️', '소외 지속': '❄️'}
                rot_color = phase_colors.get(rot_phase, '#7B6B4F')
                rot_icon = phase_icons.get(rot_phase, '🔄')
                html += f'''
                <div class="breakdown-section" style="border-top: 2px dashed {rot_color}; padding-top: 10px; margin-top: 10px;">
                    <div class="breakdown-title" style="color: {rot_color};">{rot_icon} 섹터 순환매: {rot_phase} ({rot_sign}{rot_bonus}점)</div>
                    <div class="breakdown-items">
                        <div class="breakdown-item" style="background: rgba(52, 152, 219, 0.05);">
                            <span class="criterion">섹터 동향</span>
                            <span class="criterion-value">{stock.get('sector', '')} {rot_phase}</span>
                            <span class="criterion-score" style="color: {rot_color};">{rot_sign}{rot_bonus}점</span>
                        </div>
                    </div>
                </div>'''

            # score-breakdown 닫기 + stock-card 닫기
            html += '''
            </div>
        </div>'''

        html += f'''
        <div class="footer">
            <p>Project Titan v2.0 &middot; Fundamental + Technical + Contrarian Hybrid Strategy</p>
            <p style="margin-top: 4px;">본 리포트는 알고리즘 기반 투자 참고 자료이며, 투자 손실에 대한 책임은 본인에게 있습니다.</p>
        </div>
    </div>
<script>
function toggleDetail(id) {{
    var el = document.getElementById('detail-' + id);
    var btn = el.previousElementSibling;
    if (el.classList.contains('open')) {{
        el.classList.remove('open');
        btn.textContent = '상세 분석 ▼';
    }} else {{
        el.classList.add('open');
        btn.textContent = '상세 분석 ▲';
    }}
}}
</script>
</body>
</html>'''

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)

        # 점수 체계 HTML을 리포트와 같은 디렉토리에 복사
        try:
            import shutil
            scoring_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scoring_system.html')
            scoring_dst = os.path.join(os.path.dirname(os.path.abspath(filename)), 'scoring_system.html')
            if os.path.exists(scoring_src) and scoring_src != scoring_dst:
                shutil.copy2(scoring_src, scoring_dst)
        except Exception:
            pass

        print(f"✅ HTML 리포트 생성 완료: {filename} ({len(filtered)}개 추천)")
        return filtered

    def run_analysis_with_tickers(self, tickers, report_type="Analysis", html_filename=None, min_score=50, skip_stage1=True):
        """특정 티커 리스트로 분석 실행"""
        start_time = time.time()

        print(f"\n{'='*70}")
        print(f"🎯 {report_type} Analysis Started")
        print(f"📊 Analyzing {len(tickers)} stocks")
        print(f"{'='*70}\n")

        if skip_stage1:
            # Stage 1 스킵하고 바로 Stage 2 분석
            results = self.stage2_deep_analysis(tickers)
        else:
            # Stage 1 필터링 후 Stage 2 분석
            filtered_tickers = self.stage1_quick_filter(tickers)
            if not filtered_tickers:
                print("❌ 1단계 필터를 통과한 종목이 없습니다.")
                return []
            results = self.stage2_deep_analysis(filtered_tickers)

        # 결과 출력
        self.display_results(results, min_score=min_score)

        # HTML 리포트 생성
        if html_filename:
            self.generate_html_report(results, report_type=report_type, filename=html_filename, min_score=min_score)

        # Titan 점수 캐시 저장 (ML 포트폴리오에서 동일 점수 사용)
        self._save_score_cache(results, report_type)

        # 보유종목 알림 (Web Push / 텔레그램 폴백)
        send_push_alert(results, market='us')

        # 마지막 업데이트 시간 저장 (index.html에서 표시용, KST)
        import json as _json
        import pytz as _pytz
        kst_tz = _pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst_tz)
        with open('last_updated.json', 'w', encoding='utf-8') as _f:
            _json.dump({
                'timestamp': now_kst.strftime('%Y-%m-%d %H:%M'),
                'timezone': 'KST',
                'mode': report_type
            }, _f)

        elapsed = time.time() - start_time
        print(f"\n⏱️  총 소요 시간: {elapsed/60:.1f}분")

        return results

    def _save_score_cache(self, results, report_type):
        """Titan 분석 점수를 JSON 캐시로 저장"""
        import json
        cache_type = 'growth' if 'Growth' in report_type else 'value'
        cache_file = f"titan_scores_{cache_type}.json"
        cache = {}
        for r in results:
            fund_bd = r.get('fund_breakdown', {})
            tech_bd = r.get('tech_breakdown', {})
            cache[r['ticker']] = {
                'score': r.get('score', 0),
                'fund_score': r.get('fund_score', 0),
                'tech_score': r.get('tech_score', 0),
                'price': r.get('price', 0),
                'avg_volume': r.get('avg_volume', 0),
                'market_cap': r.get('market_cap', 0),
                'sector': r.get('sector', ''),
                'company_name': r.get('company_name', ''),
                'verdict': r.get('verdict', ''),
                'buy_price': r.get('buy_price'),
                'target_price': r.get('target'),
                'stop_loss': r.get('stop_loss'),
                'strategy': r.get('buy_strategy', ''),
                'comment': r.get('comment', ''),
                'contrarian_adjustment': r.get('contrarian_adjustment', 0),
                'liquidity_bonus': r.get('liquidity_bonus', 0),
                'liquidity_tier': r.get('liquidity_tier', ''),
                'rotation_bonus': r.get('rotation_bonus', 0),
                'rotation_phase': r.get('rotation_phase', ''),
                'sector_name': fund_bd.get('sector_name', ''),
                'roe_value': fund_bd.get('roe_value'),
                'opm_value': fund_bd.get('opm_value'),
                'revenue_growth_value': fund_bd.get('revenue_growth_value'),
                'dividend_yield_value': fund_bd.get('dividend_yield_value'),
                'per_value': fund_bd.get('per_value'),
                'debt_equity_value': fund_bd.get('debt_equity_value'),
                'rsi_value': tech_bd.get('rsi_value'),
                'ma5': tech_bd.get('ma5'),
                'ma20': tech_bd.get('ma20'),
                'ma60': tech_bd.get('ma60'),
                'ma120': tech_bd.get('ma120'),
                'analyst_comment': r.get('analyst_comment', ''),
                'analyst_data': r.get('analyst_data', {}),
            }
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
        print(f"💾 Titan 점수 캐시 저장: {cache_file} ({len(cache)}개 종목)")

    def generate_portfolio_html(self, filename="portfolio.html"):
        """포트폴리오 구성 HTML 페이지 생성 (Titan + Liquidity Tier, ML 없음)"""
        import json as _json

        # 1. 양쪽 캐시 로드
        growth_cache, value_cache = {}, {}
        try:
            with open('titan_scores_growth.json', 'r') as f:
                growth_cache = _json.load(f)
        except FileNotFoundError:
            print("⚠️ titan_scores_growth.json 없음")
        try:
            with open('titan_scores_value.json', 'r') as f:
                value_cache = _json.load(f)
        except FileNotFoundError:
            print("⚠️ titan_scores_value.json 없음")

        if not growth_cache and not value_cache:
            print("❌ 캐시 파일 없음. growth/value 분석을 먼저 실행하세요.")
            return

        # 2. 유동성 티어 계산
        def calc_tier(avg_vol, price):
            dv = avg_vol * price
            if dv >= 1_000_000_000: return 5, 'Hot'
            elif dv >= 300_000_000: return 3, 'Active'
            elif dv >= 100_000_000: return 0, 'Normal'
            else: return -3, 'Thin'

        # 3. 후보 생성
        def process_cache(cache, category):
            candidates = []
            for ticker, d in cache.items():
                if d.get('score', 0) >= 75 and d.get('price', 0) > 0:
                    bonus, tier = calc_tier(d.get('avg_volume', 0), d.get('price', 0))
                    dv = d.get('avg_volume', 0) * d.get('price', 0) / 1e6
                    candidates.append({
                        'ticker': ticker,
                        'name': d.get('company_name', ticker),
                        'titan': d.get('score', 0),
                        'fund': d.get('fund_score', 0),
                        'tech': d.get('tech_score', 0),
                        'tier_bonus': bonus,
                        'tier_name': tier,
                        'final': d.get('score', 0) + bonus,
                        'price': round(d.get('price', 0), 2),
                        'daily_val': round(dv, 0),
                        'sector': d.get('sector', ''),
                        'category': category
                    })
            candidates.sort(key=lambda x: x['final'], reverse=True)
            return candidates

        growth_list = process_cache(growth_cache, 'Growth')
        value_list = process_cache(value_cache, 'Value')

        # 상위 5개씩 (JS에서 사용자가 3개 선택 가능)
        top_growth = growth_list[:5]
        top_value = value_list[:5]
        all_candidates = top_growth + top_value

        portfolio_json = _json.dumps(all_candidates, ensure_ascii=False)
        import pytz as _ptz
        now = datetime.now(_ptz.timezone('Asia/Seoul'))
        timestamp = now.strftime("%Y-%m-%d %H:%M KST")

        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portfolio Builder - Titan v2.0</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" rel="stylesheet">
<style>
:root {{
    --bg: #f7f8fa; --surface: #ffffff; --text: #191f28; --text-sub: #8b95a1;
    --text-muted: #b0b8c1; --border: #e5e8eb; --accent: #20c997;
    --accent-dark: #0ca678; --radius: 16px;
    --shadow: 0 2px 8px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
    --shadow-hover: 0 8px 24px rgba(0,0,0,0.08);
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    font-family: 'Pretendard Variable', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
    min-height: 100vh; background: var(--bg); color: var(--text);
    padding: 20px; -webkit-font-smoothing: antialiased;
}}
.container {{ max-width:780px; margin:0 auto; }}
.market-switcher {{
    display:flex; justify-content:center; gap:4px; margin-bottom:20px;
    background:var(--surface); border-radius:12px; padding:4px;
    box-shadow:var(--shadow); width:fit-content; margin-left:auto; margin-right:auto;
}}
.market-btn {{
    padding:10px 24px; font-size:0.9em; font-weight:600; font-family:inherit;
    border:none; border-radius:10px; cursor:pointer; transition:all 0.2s;
    text-decoration:none; color:var(--text-sub); display:flex; align-items:center; gap:6px; background:transparent;
}}
.market-btn.active {{ background:var(--accent); color:white; }}
.market-btn:not(.active):hover {{ background:#e6fcf5; color:var(--accent-dark); }}
.back-link {{
    display:block; text-align:center; margin-bottom:16px;
    color:var(--text-sub); text-decoration:none; font-weight:600; font-size:0.9em;
}}
.back-link:hover {{ color:var(--accent); }}
.header-card {{
    background:var(--surface); border-radius:var(--radius); padding:28px;
    margin-bottom:20px; box-shadow:var(--shadow); text-align:center;
    position:relative; overflow:hidden;
}}
.header-card::before {{ content:''; position:absolute; top:0; left:0; right:0; height:4px; background:linear-gradient(90deg, #20c997, #12b886); }}
h1 {{ color:var(--text); font-size:1.5em; font-weight:800; margin-bottom:6px; letter-spacing:-0.02em; }}
.subtitle {{ color:var(--text-sub); font-size:0.9em; }}
.timestamp {{ color:var(--text-muted); font-size:0.8em; margin-top:6px; }}

/* 입력 섹션 */
.input-section {{
    background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
    padding:24px; margin-bottom:20px; box-shadow:var(--shadow);
}}
.input-row {{ display:flex; gap:16px; align-items:center; justify-content:center; flex-wrap:wrap; margin-bottom:16px; }}
.input-group {{ display:flex; flex-direction:column; align-items:center; }}
.input-group label {{ color:var(--text); font-weight:700; margin-bottom:6px; font-size:0.88em; }}
.seed-input {{
    width:200px; padding:12px 15px; border:1px solid var(--border); border-radius:12px;
    font-size:1.1em; font-family:inherit; text-align:center; background:var(--bg);
}}
.seed-input:focus {{ outline:none; border-color:var(--accent); box-shadow:0 0 0 3px rgba(32,201,151,0.15); }}
.slider-group {{ display:flex; align-items:center; gap:10px; }}
.slider-group input[type=range] {{ width:180px; accent-color:var(--accent); }}
.slider-label {{ font-weight:700; color:var(--text); min-width:120px; text-align:center; font-size:0.88em; }}
.calc-btn {{
    background:var(--accent); color:white; padding:12px 32px; border:none;
    border-radius:12px; font-size:1em; font-weight:700; cursor:pointer;
    transition:all 0.2s; font-family:inherit;
}}
.calc-btn:hover {{ background:var(--accent-dark); transform:translateY(-1px); }}
.calc-btn:active {{ transform:translateY(1px); }}

/* 결과 테이블 */
.result-section {{ display:none; }}
.result-card {{
    background:var(--surface); border-radius:var(--radius); padding:20px;
    margin-bottom:20px; box-shadow:var(--shadow);
}}
.result-card h2 {{ color:var(--text); font-size:1.2em; font-weight:700; margin-bottom:16px; text-align:center; }}
table {{ width:100%; border-collapse:collapse; font-size:0.85em; }}
th {{ background:var(--accent); color:white; padding:10px 8px; text-align:center; font-weight:700; }}
th:first-child {{ border-radius:10px 0 0 0; }}
th:last-child {{ border-radius:0 10px 0 0; }}
td {{ padding:10px 8px; text-align:center; border-bottom:1px solid var(--border); }}
tr:hover {{ background:#f0fdf9; }}
.cat-growth {{ background:#edf2ff; color:#4263eb; padding:3px 10px; border-radius:8px; font-size:0.82em; font-weight:700; }}
.cat-value {{ background:#fff4e6; color:#fd7e14; padding:3px 10px; border-radius:8px; font-size:0.82em; font-weight:700; }}
.tier-hot {{ color:#f76707; font-weight:700; }}
.tier-active {{ color:var(--accent-dark); font-weight:700; }}
.tier-normal {{ color:var(--text-sub); }}
.tier-thin {{ color:#f06595; font-weight:700; }}
.summary-box {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:12px; margin-top:16px; }}
.summary-item {{ background:var(--bg); border-radius:12px; padding:14px; text-align:center; }}
.summary-value {{ font-size:1.2em; font-weight:800; color:var(--accent-dark); }}
.summary-label {{ font-size:0.8em; color:var(--text-sub); margin-top:3px; }}
.cash-note {{ text-align:center; margin-top:12px; color:#fd7e14; font-weight:700; font-size:0.88em; }}

/* 내 자산에 추가 버튼 */
.add-to-assets {{
    display:block; width:100%; padding:14px; margin-top:20px;
    background:#7c3aed; color:white; border:none;
    border-radius:12px; font-size:1em; font-weight:700; cursor:pointer;
    font-family:inherit; transition:all 0.2s; text-align:center;
}}
.add-to-assets:hover {{ background:#6c2bd9; transform:translateY(-1px); }}
.add-to-assets:disabled {{ background:var(--text-muted); cursor:not-allowed; }}
.add-msg {{ text-align:center; margin-top:10px; padding:10px; border-radius:10px; font-size:0.88em; display:none; }}
.add-msg.success {{ display:block; background:#e6fcf5; color:var(--accent-dark); }}
.add-msg.error {{ display:block; background:#fff0f6; color:#f06595; }}
.add-msg.info {{ display:block; background:#edf2ff; color:#4263eb; }}

/* 푸터 */
.footer {{
    background:var(--surface); border-radius:var(--radius); padding:20px;
    color:var(--text-muted); font-size:0.85em; text-align:center;
    box-shadow:var(--shadow); line-height:1.7;
}}
@media (max-width:768px) {{
    body {{ padding:12px; }}
    .header-card {{ padding:20px 16px; }}
    h1 {{ font-size:1.25em; }}
    .input-section {{ padding:16px 12px; }}
    .input-row {{ flex-direction:column; gap:10px; }}
    .seed-input {{ width:100%; font-size:1em; }}
    .slider-group input[type=range] {{ width:140px; }}
    .slider-label {{ min-width:100px; font-size:0.82em; }}
    .calc-btn {{ width:100%; padding:14px; }}
    .result-card {{ padding:14px 10px; }}
    .result-card h2 {{ font-size:1.05em; }}
    table {{ font-size:0.72em; display:block; overflow-x:auto; white-space:nowrap; -webkit-overflow-scrolling:touch; }}
    th,td {{ padding:6px 4px; }}
    .summary-box {{ grid-template-columns:repeat(2,1fr); gap:8px; }}
    .summary-value {{ font-size:1em; }}
    .add-to-assets {{ font-size:0.95em; padding:12px; }}
}}
@media (max-width:400px) {{
    h1 {{ font-size:1.1em; }}
    table {{ font-size:0.65em; }}
    .summary-box {{ grid-template-columns:1fr 1fr; }}
}}
</style>
</head>
<body>

<div class="container">
    <div class="market-switcher">
        <span class="market-btn active">US</span>
        <a href="https://redchoeng.github.io/stock-recommendation_kr/" class="market-btn">KR</a>
    </div>
    <a href="index.html" class="back-link">&larr; 메인으로</a>

    <div class="header-card">
        <h1>Portfolio Builder</h1>
        <p class="subtitle">Titan 점수 + 유동성 등급 기반 포트폴리오 구성</p>
        <p class="timestamp">{timestamp}</p>
    </div>

    <div class="input-section">
        <div class="input-row">
            <div class="input-group">
                <label>💵 투자금 (USD)</label>
                <input type="text" id="seedInput" class="seed-input" placeholder="10,000" value="10000">
            </div>
            <div class="input-group">
                <label>⚖️ Growth / Value 비율</label>
                <div class="slider-group">
                    <input type="range" id="ratioSlider" min="0" max="100" value="60" step="5">
                    <span class="slider-label" id="ratioLabel">Growth 60% / Value 40%</span>
                </div>
            </div>
        </div>
        <div style="text-align:center">
            <button class="calc-btn" onclick="calculatePortfolio()">📊 포트폴리오 계산</button>
        </div>
    </div>

    <div class="result-section" id="resultSection">
        <div class="result-card">
            <h2>🏆 추천 포트폴리오</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>종목</th>
                        <th>분류</th>
                        <th>Titan</th>
                        <th>유동성</th>
                        <th>최종</th>
                        <th>비중</th>
                        <th>금액</th>
                        <th>주수</th>
                    </tr>
                </thead>
                <tbody id="portfolioTable"></tbody>
            </table>
            <div class="cash-note" id="cashNote"></div>
            <div class="summary-box" id="summaryBox"></div>
            <button class="add-to-assets" id="addToAssetsBtn" onclick="addToMyAssets()">🏦 내 자산에 전체 추가</button>
            <div class="add-msg" id="addMsg"></div>
        </div>
    </div>

    <div class="footer">
        <p>본 포트폴리오는 Titan 알고리즘 기반 참고 자료이며, 투자 손실에 대한 책임은 본인에게 있습니다.</p>
        <p style="margin-top:4px;">Titan v2.0 &middot; Hot($1B+/일) &middot; Active($300M+) &middot; Normal($100M+) &middot; Thin(&lt;$100M)</p>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script src="supabase_config.js"></script>
<script>
let sbClient = null;
let currentUser = null;
let lastPortfolio = [];

// Supabase 초기화 + 인증 체크
(async () => {{
    try {{
        const {{ createClient }} = supabase;
        sbClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
        const {{ data: {{ session }} }} = await sbClient.auth.getSession();
        if (!session) {{
            window.location.href = 'login.html';
            return;
        }}
        currentUser = session.user;
    }} catch(e) {{
        window.location.href = 'login.html';
    }}
}})();

const ALL_DATA = {portfolio_json};
const GROWTH = ALL_DATA.filter(s => s.category === 'Growth');
const VALUE = ALL_DATA.filter(s => s.category === 'Value');

const slider = document.getElementById('ratioSlider');
const ratioLabel = document.getElementById('ratioLabel');
slider.addEventListener('input', () => {{
    const g = slider.value;
    ratioLabel.textContent = 'Growth ' + g + '% / Value ' + (100 - g) + '%';
}});

// 시드 입력에 콤마 자동 포맷
document.getElementById('seedInput').addEventListener('input', function(e) {{
    let v = e.target.value.replace(/[^0-9]/g, '');
    if (v) e.target.value = parseInt(v).toLocaleString('en-US');
}});

function calculatePortfolio() {{
    const seedStr = document.getElementById('seedInput').value.replace(/,/g, '');
    const seed = parseFloat(seedStr);
    if (isNaN(seed) || seed <= 0) {{ alert('투자금을 입력하세요'); return; }}

    const growthRatio = parseInt(slider.value) / 100;
    const valueRatio = 1 - growthRatio;

    // 상위 3개씩 선택
    const gPicks = GROWTH.slice(0, 3);
    const vPicks = VALUE.slice(0, 3);

    // 카테고리 내 점수 비례 비중
    const gTotal = gPicks.reduce((s, x) => s + x.final, 0) || 1;
    const vTotal = vPicks.reduce((s, x) => s + x.final, 0) || 1;

    let portfolio = [];
    gPicks.forEach(s => {{
        const w = growthRatio * (s.final / gTotal);
        portfolio.push({{...s, weight: w}});
    }});
    vPicks.forEach(s => {{
        const w = valueRatio * (s.final / vTotal);
        portfolio.push({{...s, weight: w}});
    }});

    // 계산 결과 저장 (내 자산 추가용)
    lastPortfolio = portfolio.map(s => ({{
        ...s,
        calcShares: Math.floor(seed * s.weight / s.price)
    }}));

    // 테이블 렌더링
    const tbody = document.getElementById('portfolioTable');
    tbody.innerHTML = '';
    let totalUsed = 0;
    let totalShares = 0;

    portfolio.forEach((s, i) => {{
        const amount = seed * s.weight;
        const shares = Math.floor(amount / s.price);
        const actual = shares * s.price;
        totalUsed += actual;
        totalShares += shares;

        const catClass = s.category === 'Growth' ? 'cat-growth' : 'cat-value';
        const tierClass = 'tier-' + s.tier_name.toLowerCase();
        const bonusStr = s.tier_bonus >= 0 ? '+' + s.tier_bonus : s.tier_bonus;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${{i+1}}</strong></td>
            <td style="text-align:left"><strong>${{s.ticker}}</strong><br><span style="font-size:0.8em;color:#999">${{s.name}}</span></td>
            <td><span class="${{catClass}}">${{s.category}}</span></td>
            <td>${{s.titan}}</td>
            <td><span class="${{tierClass}}">${{s.tier_name}}(${{bonusStr}})</span></td>
            <td><strong>${{s.final}}</strong></td>
            <td>${{(s.weight * 100).toFixed(1)}}%</td>
            <td>$${{actual.toLocaleString('en-US', {{minimumFractionDigits:0}})}}</td>
            <td>${{shares}}주</td>
        `;
        tbody.appendChild(tr);
    }});

    // 잔액
    const remainder = seed - totalUsed;
    document.getElementById('cashNote').textContent =
        remainder > 0 ? '💰 미배분 현금: $' + remainder.toLocaleString('en-US', {{minimumFractionDigits:2}}) + ' (주수 내림 처리)' : '';

    // 요약
    const avgScore = portfolio.reduce((s, x) => s + x.final, 0) / portfolio.length;
    document.getElementById('summaryBox').innerHTML = `
        <div class="summary-item">
            <div class="summary-value">$${{seed.toLocaleString('en-US')}}</div>
            <div class="summary-label">총 투자금</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">${{portfolio.length}}종목</div>
            <div class="summary-label">포트폴리오</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">${{avgScore.toFixed(1)}}</div>
            <div class="summary-label">평균 최종점수</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">${{parseInt(slider.value)}}:${{100-parseInt(slider.value)}}</div>
            <div class="summary-label">Growth:Value</div>
        </div>
    `;

    document.getElementById('resultSection').style.display = 'block';
    document.getElementById('resultSection').scrollIntoView({{behavior:'smooth'}});
}}

// ===== 내 자산에 추가 =====
async function addToMyAssets() {{
    const msgEl = document.getElementById('addMsg');
    const btn = document.getElementById('addToAssetsBtn');

    if (!currentUser) {{
        msgEl.className = 'add-msg info';
        msgEl.textContent = '로그인이 필요합니다. 로그인 페이지로 이동합니다...';
        setTimeout(() => {{ window.location.href = 'login.html'; }}, 1500);
        return;
    }}

    if (lastPortfolio.length === 0) {{
        msgEl.className = 'add-msg error';
        msgEl.textContent = '먼저 포트폴리오를 계산해주세요.';
        return;
    }}

    const validItems = lastPortfolio.filter(s => s.calcShares > 0);
    if (validItems.length === 0) {{
        msgEl.className = 'add-msg error';
        msgEl.textContent = '투자금이 부족하여 추가할 종목이 없습니다.';
        return;
    }}

    btn.disabled = true;
    btn.textContent = '추가 중...';

    let success = 0, fail = 0;
    for (const s of validItems) {{
        const {{ error }} = await sbClient.from('assets').insert({{
            user_id: currentUser.id,
            asset_type: 'stock',
            ticker: s.ticker,
            name: s.name,
            shares: s.calcShares,
            buy_price: s.price,
            amount: s.calcShares * s.price,
            note: `Titan ${{s.titan}}점, ${{s.category}}, ${{s.tier_name}}`
        }});
        if (error) fail++; else success++;
    }}

    btn.disabled = false;
    btn.textContent = '🏦 내 자산에 전체 추가';

    if (success > 0) {{
        msgEl.className = 'add-msg success';
        msgEl.textContent = `${{success}}종목 자산 추가 완료!` + (fail > 0 ? ` (${{fail}}건 실패)` : '') + ' 대시보드에서 확인하세요.';
    }} else {{
        msgEl.className = 'add-msg error';
        msgEl.textContent = '추가에 실패했습니다.';
    }}

    setTimeout(() => {{ msgEl.className = 'add-msg'; }}, 8000);
}}

// 페이지 로드 시 자동 계산
window.addEventListener('load', () => {{ calculatePortfolio(); }});

</script>
</body>
</html>'''

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"📊 포트폴리오 페이지 생성: {filename} (Growth {len(top_growth)}개 + Value {len(top_value)}개)")

    def generate_changelog_html(self, md_file="CHANGELOG.md", filename="changelog.html"):
        """CHANGELOG.md → changelog.html 변환 (카와이 스타일)"""
        import re

        md_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), md_file)
        if not os.path.exists(md_path):
            print(f"⚠️ {md_file} 없음 - changelog 생성 스킵")
            return

        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # 마크다운 → HTML 변환
        sections_html = ""
        current_version = ""
        current_subtitle = ""
        current_items = []

        # 버전별 색상 매핑
        version_colors = ['#E74C3C', '#E67E22', '#F1C40F', '#2ECC71', '#3498DB', '#9B59B6', '#1ABC9C', '#E91E63']
        color_idx = 0

        for line in md_content.split('\n'):
            line = line.rstrip()

            if line.startswith('## '):
                # 이전 버전 섹션 마무리
                if current_version:
                    color = version_colors[color_idx % len(version_colors)]
                    color_idx += 1
                    items_html = ""
                    for item in current_items:
                        # **bold** 처리
                        item = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item)
                        items_html += f'<li>{item}</li>\n'
                    sections_html += f'''
        <div class="version-card" style="border-left-color: {color};">
            <div class="version-header">
                <span class="version-tag" style="background: {color};">{current_version}</span>
                <span class="version-subtitle">{current_subtitle}</span>
            </div>
            <ul class="change-list">{items_html}</ul>
        </div>'''
                    current_items = []

                # 새 버전 파싱: ## v2.4.0 (2026-02-19)
                match = re.match(r'##\s+(.+?)(?:\s+\(.+?\))?\s*$', line)
                if match:
                    current_version = match.group(1).strip()
                current_subtitle = ""

            elif line.startswith('### '):
                current_subtitle = line[4:].strip()

            elif line.startswith('- '):
                item = line[2:].strip()
                current_items.append(item)

            elif line.startswith('  - '):
                item = line[4:].strip()
                current_items.append(f'&nbsp;&nbsp;&nbsp;&nbsp;{item}')

        # 마지막 버전
        if current_version:
            color = version_colors[color_idx % len(version_colors)]
            items_html = ""
            for item in current_items:
                item = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item)
                items_html += f'<li>{item}</li>\n'
            sections_html += f'''
        <div class="version-card" style="border-left-color: {color};">
            <div class="version-header">
                <span class="version-tag" style="background: {color};">{current_version}</span>
                <span class="version-subtitle">{current_subtitle}</span>
            </div>
            <ul class="change-list">{items_html}</ul>
        </div>'''

        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Patch Notes - Titan v2.0</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" rel="stylesheet">
<style>
:root {{
    --bg: #f7f8fa; --surface: #ffffff; --text: #191f28; --text-sub: #8b95a1;
    --text-muted: #b0b8c1; --border: #e5e8eb; --red: #f06595;
    --radius: 16px; --shadow: 0 2px 8px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    font-family: 'Pretendard Variable', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
    min-height: 100vh; background: var(--bg); color: var(--text);
    padding: 20px; -webkit-font-smoothing: antialiased;
}}
.container {{ max-width:720px; margin:0 auto; }}
.market-switcher {{
    display:flex; justify-content:center; gap:4px; margin-bottom:20px;
    background:var(--surface); border-radius:12px; padding:4px;
    box-shadow:var(--shadow); width:fit-content; margin-left:auto; margin-right:auto;
}}
.market-btn {{
    padding:10px 24px; font-size:0.9em; font-weight:600; font-family:inherit;
    border:none; border-radius:10px; cursor:pointer; transition:all 0.2s;
    text-decoration:none; color:var(--text-sub); display:flex; align-items:center; gap:6px; background:transparent;
}}
.market-btn.active {{ background:var(--red); color:white; }}
.market-btn:not(.active):hover {{ background:#fff0f6; color:var(--red); }}
.back-link {{
    display:block; text-align:center; margin-bottom:16px;
    color:var(--text-sub); text-decoration:none; font-weight:600; font-size:0.9em;
}}
.back-link:hover {{ color:var(--red); }}
.header-card {{
    background:var(--surface); border-radius:var(--radius); padding:28px;
    margin-bottom:20px; box-shadow:var(--shadow); text-align:center;
    position:relative; overflow:hidden;
}}
.header-card::before {{ content:''; position:absolute; top:0; left:0; right:0; height:4px; background:linear-gradient(90deg, #f06595, #e64980); }}
h1 {{ color:var(--text); font-size:1.5em; font-weight:800; margin-bottom:6px; letter-spacing:-0.02em; }}
.subtitle {{ color:var(--text-sub); font-size:0.9em; }}

.version-card {{
    background: var(--surface); border-radius: var(--radius);
    padding: 20px 24px; margin-bottom: 12px;
    border-left: 4px solid var(--red);
    box-shadow: var(--shadow); transition: all 0.2s;
}}
.version-card:hover {{ transform: translateX(4px); box-shadow: 0 4px 16px rgba(0,0,0,0.06); }}
.version-header {{ display:flex; align-items:center; gap:10px; margin-bottom:10px; flex-wrap:wrap; }}
.version-tag {{
    display:inline-block; padding:4px 14px; border-radius:8px;
    color:white; font-weight:700; font-size:0.85em;
}}
.version-subtitle {{ color:var(--text); font-weight:700; font-size:0.95em; }}
.change-list {{ list-style:none; padding:0; }}
.change-list li {{
    color:var(--text-sub); font-size:0.88em; line-height:1.7;
    padding:2px 0 2px 18px; position:relative;
}}
.change-list li::before {{
    content:''; position:absolute; left:0; top:10px;
    width:6px; height:6px; border-radius:50%; background:var(--text-muted);
}}
.change-list li strong {{ color:var(--text); }}

.footer {{
    background:var(--surface); border-radius:var(--radius); padding:20px;
    color:var(--text-muted); font-size:0.85em; text-align:center;
    box-shadow:var(--shadow); margin-top:16px; line-height:1.7;
}}
@media (max-width:768px) {{
    body {{ padding:12px; }}
    .header-card {{ padding:20px 16px; }}
    h1 {{ font-size:1.25em; }}
    .version-card {{ padding:16px; border-left-width:3px; }}
    .version-tag {{ font-size:0.8em; padding:3px 10px; }}
    .change-list li {{ font-size:0.82em; padding-left:14px; }}
}}
</style>
</head>
<body>

<div class="container">
    <div class="market-switcher">
        <span class="market-btn active">US</span>
        <a href="https://redchoeng.github.io/stock-recommendation_kr/" class="market-btn">KR</a>
    </div>
    <a href="index.html" class="back-link">&larr; 메인으로</a>

    <div class="header-card">
        <h1>Patch Notes</h1>
        <p class="subtitle">Project Titan 버전 히스토리</p>
    </div>

    {sections_html}

    <div class="footer">
        <p>Titan v2.0 &middot; CHANGELOG.md 기반 자동 생성</p>
    </div>
</div>
</body>
</html>'''

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"📋 패치노트 생성: {filename}")

    def run_ml_predictions(self, results, ml_min_score):
        """ML 예측 실행 (특정 점수 이상 종목만)"""
        try:
            from ml_predictor import EnsemblePredictor
        except ImportError:
            print("⚠️ ML Predictor 미설치 - ML 예측 스킵")
            return results

        # ml_min_score 이상 종목 필터링
        ml_targets = [r for r in results if r.get('score', 0) >= ml_min_score]

        if not ml_targets:
            print(f"ℹ️ {ml_min_score}점 이상 종목 없음 - ML 예측 스킵")
            return results

        print(f"\n{'='*70}")
        print(f"🤖 ML 예측 시작 ({ml_min_score}점 이상 {len(ml_targets)}개 종목)")
        print(f"{'='*70}")

        predictor = EnsemblePredictor(sequence_length=20)

        for stock in ml_targets:
            ticker = stock['ticker']
            try:
                print(f"\n📊 {ticker} ML 분석 중...")

                # 데이터 준비
                df, features, target = predictor.prepare_data(ticker, period='2y')
                if df is None:
                    stock['ml_signal'] = '❓ 데이터 부족'
                    stock['ml_confidence'] = 0
                    continue

                # Train/Val 분할
                split_idx = int(len(features) * 0.8)
                X_train = features.iloc[:split_idx]
                y_train = target.iloc[:split_idx]
                X_val = features.iloc[split_idx:]
                y_val = target.iloc[split_idx:]

                # 모델 학습
                predictor.train_xgboost(X_train, y_train, X_val, y_val)
                predictor.train_lstm(X_train, y_train, X_val, y_val, epochs=30)

                # 예측
                recent_features = features.iloc[-30:]
                predictions, probabilities = predictor.predict(recent_features)

                if 'ensemble' in probabilities:
                    latest_prob = probabilities['ensemble'][-1]
                elif 'xgboost' in probabilities:
                    latest_prob = probabilities['xgboost'][-1]
                else:
                    stock['ml_signal'] = '❓ 예측 실패'
                    stock['ml_confidence'] = 0
                    continue

                signal, confidence = predictor.get_signal(latest_prob)

                stock['ml_signal'] = signal
                stock['ml_confidence'] = confidence
                stock['ml_prob_up'] = latest_prob[2]
                stock['ml_prob_down'] = latest_prob[0]

                print(f"   ✅ {ticker}: {signal} (신뢰도: {confidence:.1%})")

            except Exception as e:
                print(f"   ❌ {ticker} ML 예측 실패: {e}")
                stock['ml_signal'] = '❓ 오류'
                stock['ml_confidence'] = 0

        return results



# ============================================================================
# 텔레그램 알림
# ============================================================================
def send_push_alert(results, market='us'):
    """Supabase에서 사용자별 보유종목 조회 후 Web Push 알림 전송"""
    import requests as _req
    import json as _json
    from collections import defaultdict
    import time

    sb_url = os.environ.get('SUPABASE_URL', '')
    sb_key = os.environ.get('SUPABASE_SERVICE_KEY', '')
    vapid_private = os.environ.get('VAPID_PRIVATE_KEY', '')
    vapid_email = os.environ.get('VAPID_EMAIL', 'mailto:admin@titan.com')

    if not sb_url or not sb_key or not vapid_private:
        # Supabase 미설정 시 텔레그램 폴백
        _send_telegram_fallback(results, market)
        return

    headers = {
        'apikey': sb_key,
        'Authorization': f'Bearer {sb_key}',
        'Content-Type': 'application/json'
    }

    # 1) alert_holdings 조회
    try:
        resp = _req.get(
            f'{sb_url}/rest/v1/alert_holdings?market=eq.{market}&select=*',
            headers=headers, timeout=15
        )
        all_holdings = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        print(f"⚠️  보유종목 조회 실패: {e}")
        _send_telegram_fallback(results, market)
        return

    all_holdings = [h for h in all_holdings if float(h.get('qty', 0)) > 0]
    if not all_holdings:
        print("ℹ️  등록된 보유종목 없음")
        return

    # 2) push_subscriptions 조회
    user_ids = list(set(h['user_id'] for h in all_holdings))
    user_id_csv = ','.join(user_ids)
    try:
        resp2 = _req.get(
            f'{sb_url}/rest/v1/push_subscriptions?user_id=in.({user_id_csv})&select=*',
            headers=headers, timeout=15
        )
        subs = resp2.json() if resp2.status_code == 200 else []
    except Exception:
        subs = []

    # user_id → subscriptions 매핑
    user_subs = defaultdict(list)
    for s in subs:
        user_subs[s['user_id']].append(s)

    # 3) user_id → holdings 매핑
    user_holdings = defaultdict(list)
    for h in all_holdings:
        user_holdings[h['user_id']].append(h)

    # 4) 분석 결과 lookup
    lookup = {r['ticker']: r for r in results}
    is_kr = (market == 'kr')
    kst = pytz.timezone('Asia/Seoul')
    now_str = datetime.now(kst).strftime('%m/%d %H:%M')

    def fmt(v):
        if not v:
            return '-'
        return f"₩{int(v):,}" if is_kr else f"${v:,.2f}"

    tag = 'KR' if is_kr else 'US'
    total_alerts = 0

    # 5) 사용자별 알림 체크 + 전송
    for user_id, holdings in user_holdings.items():
        subscriptions = user_subs.get(user_id, [])
        if not subscriptions:
            continue

        alerts = []
        for h in holdings:
            r = lookup.get(h['ticker'])
            if not r:
                continue

            price = r.get('price', 0)
            target = r.get('target') or r.get('target_price', 0)
            stop = r.get('stop_loss', 0)
            avg = float(h.get('avg_price', 0))
            qty = float(h.get('qty', 0))
            name = h.get('name', h['ticker'])
            pnl_pct = ((price - avg) / avg * 100) if avg else 0

            if price and target and price >= target:
                alerts.append({
                    'title': f'🟢 목표가 도달: {name}',
                    'body': f'{fmt(price)} ≥ 목표 {fmt(target)} | {pnl_pct:+.1f}%',
                    'tag': f'target-{h["ticker"]}'
                })

            if price and stop and price <= stop:
                alerts.append({
                    'title': f'🔴 손절가 도달: {name}',
                    'body': f'{fmt(price)} ≤ 손절 {fmt(stop)} | {pnl_pct:+.1f}%',
                    'tag': f'stop-{h["ticker"]}'
                })

        if not alerts:
            continue

        # 각 구독 기기에 푸시 전송
        for alert in alerts:
            for sub_info in subscriptions:
                _send_webpush(sub_info, alert, vapid_private, vapid_email, sb_url, sb_key, headers)
                time.sleep(0.05)
            total_alerts += 1

    print(f"📨 [{tag}] Web Push 알림 {total_alerts}건 전송 ({len(user_holdings)}명)")


def _send_webpush(sub_info, payload, vapid_private, vapid_email, sb_url, sb_key, headers):
    """단일 Web Push 전송"""
    try:
        from pywebpush import webpush, WebPushException
        import json as _json

        subscription_info = {
            'endpoint': sub_info['endpoint'],
            'keys': {
                'p256dh': sub_info['p256dh'],
                'auth': sub_info['auth']
            }
        }

        webpush(
            subscription_info=subscription_info,
            data=_json.dumps(payload),
            vapid_private_key=vapid_private,
            vapid_claims={'sub': vapid_email}
        )
    except Exception as e:
        err_str = str(e)
        # 410 Gone = 구독 만료 → DB에서 삭제
        if '410' in err_str or 'Gone' in err_str:
            try:
                import requests as _req
                _req.delete(
                    f'{sb_url}/rest/v1/push_subscriptions?id=eq.{sub_info["id"]}',
                    headers=headers, timeout=10
                )
                print(f"🗑️  만료된 구독 삭제: {sub_info['endpoint'][:50]}...")
            except Exception:
                pass
        else:
            print(f"⚠️  Push 전송 실패: {err_str[:80]}")


def _send_telegram_fallback(results, market='us'):
    """Supabase 미설정 시 기존 텔레그램 폴백"""
    import json as _json
    import requests as _req

    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        print("⚠️  텔레그램/Supabase 설정 없음 — 알림 건너뜀")
        return

    try:
        with open('my_holdings.json', 'r', encoding='utf-8') as f:
            holdings = _json.load(f).get('holdings', [])
    except (FileNotFoundError, _json.JSONDecodeError):
        return

    holdings = [h for h in holdings if h.get('qty', 0) > 0]
    if not holdings:
        return

    lookup = {r['ticker']: r for r in results}
    is_kr = (market == 'kr')
    kst = pytz.timezone('Asia/Seoul')
    now_str = datetime.now(kst).strftime('%m/%d %H:%M')

    def fmt(v):
        if not v:
            return '-'
        return f"₩{int(v):,}" if is_kr else f"${v:,.2f}"

    alerts = []
    summary_lines = []

    for h in holdings:
        r = lookup.get(h['ticker'])
        if not r:
            continue

        price = r.get('price', 0)
        target = r.get('target') or r.get('target_price', 0)
        stop = r.get('stop_loss', 0)
        avg = h.get('avg_price', 0)
        qty = h.get('qty', 0)
        name = h.get('name', h['ticker'])
        pnl_pct = ((price - avg) / avg * 100) if avg else 0

        if price and target and price >= target:
            alerts.append(f"🟢 목표가 도달: {name} ({h['ticker']})\n현재 {fmt(price)} ≥ 목표 {fmt(target)}\n보유 {qty}주 · 평단 {fmt(avg)} · 수익 {pnl_pct:+.1f}%")
        if price and stop and price <= stop:
            alerts.append(f"🔴 손절가 도달: {name} ({h['ticker']})\n현재 {fmt(price)} ≤ 손절 {fmt(stop)}\n보유 {qty}주 · 평단 {fmt(avg)} · 손실 {pnl_pct:+.1f}%")
        summary_lines.append(f"  {name}: {fmt(price)} ({pnl_pct:+.1f}%)\n    목표 {fmt(target)} | 손절 {fmt(stop)}")

    def send_tg(text):
        try:
            _req.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={'chat_id': chat_id, 'text': text}, timeout=10)
        except Exception:
            pass

    for a in alerts:
        send_tg(a)
    if summary_lines:
        tag = 'KR' if is_kr else 'US'
        send_tg(f"📊 [{tag}] 보유종목 현황 ({now_str} KST)\n\n" + "\n\n".join(summary_lines))


def _fetch_user_holding_tickers(market='us'):
    """Supabase에서 사용자 보유종목 티커를 가져와 분석 대상에 추가"""
    import requests as _req
    sb_url = os.environ.get('SUPABASE_URL', '')
    sb_key = os.environ.get('SUPABASE_SERVICE_KEY', '')
    if not sb_url or not sb_key:
        return []
    try:
        headers = {'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}
        resp = _req.get(
            f"{sb_url}/rest/v1/alert_holdings?market=eq.{market}&select=ticker",
            headers=headers, timeout=10
        )
        if resp.status_code == 200:
            tickers = list(set(h['ticker'] for h in resp.json()))
            if tickers:
                print(f"📌 보유종목 {len(tickers)}개 추가 분석 대상에 포함")
            return tickers
    except Exception as e:
        print(f"⚠️  보유종목 조회 실패: {e}")
    return []


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                   PROJECT TITAN v2.0                     ║
    ║          Advanced Stock Decision Support System          ║
    ║                                                           ║
    ║  Strategy: Fundamental + Technical + Volatility Breakout  ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    analyzer = TitanAnalyzer()

    # 명령줄 인자 처리
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

        if mode == "growth":
            analyzer.analysis_mode = 'growth'
            holding_tickers = _fetch_user_holding_tickers(market='us')
            tickers = list(dict.fromkeys(GROWTH_TICKERS + holding_tickers))
            analyzer.run_analysis_with_tickers(
                tickers=tickers,
                report_type="Growth Stocks",
                html_filename="growth_report.html",
                min_score=70,
                skip_stage1=True,
            )
        elif mode == "value":
            analyzer.analysis_mode = 'value'
            holding_tickers = _fetch_user_holding_tickers(market='us')
            tickers = list(dict.fromkeys(VALUE_TICKERS + holding_tickers))
            analyzer.run_analysis_with_tickers(
                tickers=tickers,
                report_type="Value Stocks",
                html_filename="value_report.html",
                min_score=85,
                skip_stage1=True,
            )
        elif mode == "portfolio":
            analyzer.generate_portfolio_html(filename="portfolio.html")
        elif mode == "changelog":
            analyzer.generate_changelog_html()
        else:
            print(f"❌ 알 수 없는 모드: {mode}")
            print("사용법: python project_titan.py [growth|value|portfolio|changelog]")
    else:
        print("사용법: python project_titan.py [growth|value|portfolio|changelog]")