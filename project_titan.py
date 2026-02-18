"""
Project Titan - US Stock Decision Support System
Advanced 2-Stage Filtering Analysis for NASDAQ 100, Value Stocks, and S&P 500
"""

import yfinance as yf
import pandas as pd
import time
from datetime import datetime, timezone
from tabulate import tabulate
from ta.momentum import RSIIndicator
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

    # ========== Technology - AI & Data (8) ==========
    'PLTR', 'AI', 'PATH', 'U', 'SNPS', 'CDNS',

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

    # 점수 임계값
    SCORE_STRONG_BUY = 80
    SCORE_BUY = 60
    SCORE_HOLD = 40

    # 펀더멘털 점수 가중치
    SCORE_ROE_EXCELLENT = 15
    SCORE_ROE_GOOD = 5
    SCORE_OPM_EXCELLENT = 15
    SCORE_OPM_GOOD = 5

    # 매출 성장률 점수 (신규 - 섹터 비중 축소분 이동)
    SCORE_REVENUE_GROWTH_HIGH = 10   # 매출 성장률 20% 이상
    SCORE_REVENUE_GROWTH_GOOD = 5    # 매출 성장률 10-20%

    # 섹터별 점수 - 성장주 (비중 축소: 20% → 10%)
    SCORE_SECTOR_TIER1 = 10  # AI, 반도체, 클라우드, 사이버보안, 국방, 원자력
    SCORE_SECTOR_TIER2 = 8   # 소프트웨어, EV, 바이오텍, 신재생에너지, 희토류
    SCORE_SECTOR_TIER3 = 5   # 헬스케어, 산업자동화, 핀테크
    SCORE_SECTOR_TIER4 = 3   # 전통 에너지, 소비재, 유틸리티

    # 섹터별 점수 - 가치주 (비중 축소: 20% → 10%)
    VALUE_SECTOR_TIER1 = 10  # 필수소비재, 헬스케어 (배당귀족)
    VALUE_SECTOR_TIER2 = 8   # 유틸리티, 금융 (안정적 배당)
    VALUE_SECTOR_TIER3 = 5   # 산업재, 에너지, 부동산 (가치 섹터)
    VALUE_SECTOR_TIER4 = 3   # 기술주, 경기민감 소비재 (성장주 영역)

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

    # 업종(industry) 레벨 매출성장률 오버라이드
    INDUSTRY_REVENUE_GROWTH_OVERRIDES = {
        'Semiconductors': (15, 5),                       # 반도체 사이클 (QCOM 5%, INTC -4%)
        'Semiconductor Equipment & Materials': (15, 5),  # 장비 사이클 (AMAT -2%, LRCX 22%)
    }

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

    # 기술적 점수 재설계 (전문가급, 총 50점)
    # 1. 추세 분석 (15점)
    SCORE_MA200 = 3
    SCORE_MA50 = 3
    SCORE_MA20 = 2
    SCORE_MACD_BULLISH = 4
    SCORE_MACD_SIGNAL = 2
    SCORE_ADX_STRONG = 3

    # 2. 모멘텀 (12점)
    SCORE_RSI_OPTIMAL = 6
    SCORE_RSI_GOOD = 4
    SCORE_RSI_OVERSOLD = 2
    SCORE_STOCH_OPTIMAL = 6
    SCORE_STOCH_GOOD = 3

    # 3. 거래량 (10점)
    SCORE_VOLUME_EXTREME = 6    # 3배 이상
    SCORE_VOLUME_HIGH = 4       # 2-3배
    SCORE_VOLUME_MODERATE = 3   # 1.5-2배
    SCORE_VOLUME_NORMAL = 2     # 1.2-1.5배
    SCORE_OBV_RISING = 4

    # 4. 변동성 (8점)
    SCORE_BB_POSITION = 5
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
    VOLUME_SURGE_MULTIPLIER = 1.2
    STOP_LOSS_RATIO = 0.97

    def __init__(self):
        self.K_FACTOR = 0.5  # Volatility breakout factor
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

    def _get_fundamental_score(self, info):
        """기본적 분석 점수 (최대 50점)"""
        score = 0
        comments = []
        breakdown = {
            'roe_score': 0,
            'roe_value': 0,
            'opm_score': 0,
            'opm_value': 0,
            'revenue_growth_score': 0,
            'revenue_growth_value': None,  # None이면 N/A 표시
            'sector_score': 0,
            'sector_name': ''
        }

        try:
            sector = info.get('sector', '')
            industry = info.get('industry', '')

            # 1. ROE (섹터별 차등 기준)
            roe = info.get('returnOnEquity')
            roe_excellent, roe_good = self.SECTOR_ROE_THRESHOLDS.get(
                sector, self.DEFAULT_ROE_THRESHOLD)
            if roe:
                roe_pct = roe * 100
                breakdown['roe_value'] = roe_pct
                if roe_pct > roe_excellent:
                    score += self.SCORE_ROE_EXCELLENT
                    breakdown['roe_score'] = self.SCORE_ROE_EXCELLENT
                    comments.append(f"ROE:{roe_pct:.1f}%")
                elif roe_pct > roe_good:
                    score += self.SCORE_ROE_GOOD
                    breakdown['roe_score'] = self.SCORE_ROE_GOOD
                    comments.append(f"ROE:{roe_pct:.1f}%")

            # 2. Operating Margin (업종/섹터별 차등 기준)
            opm = info.get('operatingMargins')
            # industry 오버라이드 우선, 없으면 섹터 기준
            opm_excellent, opm_good = self.INDUSTRY_OPM_OVERRIDES.get(
                industry, self.SECTOR_OPM_THRESHOLDS.get(
                    sector, self.DEFAULT_OPM_THRESHOLD))
            if opm:
                opm_pct = opm * 100
                breakdown['opm_value'] = opm_pct
                if opm_pct > opm_excellent:
                    score += self.SCORE_OPM_EXCELLENT
                    breakdown['opm_score'] = self.SCORE_OPM_EXCELLENT
                    comments.append(f"OPM:{opm_pct:.1f}%")
                elif opm_pct > opm_good:
                    score += self.SCORE_OPM_GOOD
                    breakdown['opm_score'] = self.SCORE_OPM_GOOD

            # 3. Revenue Growth (매출 성장률 - 업종/섹터별 차등 기준)
            revenue_growth = info.get('revenueGrowth')
            rg_high, rg_good = self.INDUSTRY_REVENUE_GROWTH_OVERRIDES.get(
                industry, self.SECTOR_REVENUE_GROWTH_THRESHOLDS.get(
                    sector, self.DEFAULT_REVENUE_GROWTH_THRESHOLD))
            if revenue_growth:
                rg_pct = revenue_growth * 100
                breakdown['revenue_growth_value'] = rg_pct
                if rg_pct > rg_high:
                    score += self.SCORE_REVENUE_GROWTH_HIGH
                    breakdown['revenue_growth_score'] = self.SCORE_REVENUE_GROWTH_HIGH
                elif rg_pct > rg_good:
                    score += self.SCORE_REVENUE_GROWTH_GOOD
                    breakdown['revenue_growth_score'] = self.SCORE_REVENUE_GROWTH_GOOD

            # 3-1. 고성장 투자기업 보정 (매출 30%+ & ROE/OPM 적자)
            # SNOW, NET, CRWD 등 성장 투자 중인 기업은 적자가 구조적
            if revenue_growth and revenue_growth > 0.30:
                roe_val = roe * 100 if roe else 0
                opm_val = opm * 100 if opm else 0
                if roe_val < 0 and breakdown['roe_score'] == 0:
                    score += self.SCORE_ROE_GOOD  # 성장 투자 인정 +5
                    breakdown['roe_score'] = self.SCORE_ROE_GOOD
                    comments.append("성장투자")
                if opm_val < 0 and breakdown['opm_score'] == 0:
                    score += self.SCORE_OPM_GOOD  # 성장 투자 인정 +5
                    breakdown['opm_score'] = self.SCORE_OPM_GOOD

            # 4. Sector & Industry (세분화된 분류)
            breakdown['sector_name'] = f"{sector}"

            # ===== 가치주 모드: 배당/안정성 중심 점수 체계 =====
            if self.analysis_mode == 'value':
                sector_score, sector_name, sector_comment = self._get_value_sector_score(sector, industry)
                score += sector_score
                breakdown['sector_score'] = sector_score
                breakdown['sector_name'] = sector_name
                if sector_comment:
                    comments.append(sector_comment)

            # ===== 성장주 모드: 기술/성장 중심 점수 체계 =====
            else:
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

        except Exception:
            pass

        return score, comments, breakdown

    def _get_value_sector_score(self, sector, industry):
        """가치주 모드용 섹터 점수 (배당/안정성 중심)"""
        industry_lower = industry.lower()

        # Tier 1 (20점): 필수소비재, 헬스케어 (배당귀족 다수 포함)
        # 필수소비재 - 경기 방어적, 안정적 배당
        if sector == 'Consumer Defensive':
            if any(kw in industry_lower for kw in ['household', 'personal', 'packaged food', 'beverage', 'tobacco']):
                return self.VALUE_SECTOR_TIER1, "필수소비재", "필수소비재"
            return self.VALUE_SECTOR_TIER1, "필수소비재", "필수소비재"
        # 헬스케어 - 제약/의료기기 (바이오텍 제외한 안정적 헬스케어)
        if sector == 'Healthcare' and 'biotech' not in industry_lower:
            if any(kw in industry_lower for kw in ['drug', 'pharmaceutical', 'medical device', 'health care plan', 'diagnostics']):
                return self.VALUE_SECTOR_TIER1, "헬스케어", "헬스케어"
            return self.VALUE_SECTOR_TIER1, "헬스케어", "헬스케어"

        # Tier 2 (15점): 유틸리티, 금융 (안정적 배당)
        if sector == 'Utilities':
            return self.VALUE_SECTOR_TIER2, "유틸리티", "유틸리티"
        if sector == 'Financial Services':
            if any(kw in industry_lower for kw in ['bank', 'insurance', 'asset management', 'capital market']):
                return self.VALUE_SECTOR_TIER2, "금융", "금융"
            return self.VALUE_SECTOR_TIER2, "금융", "금융"
        # 부동산 - REITs
        if sector == 'Real Estate':
            return self.VALUE_SECTOR_TIER2, "부동산/REITs", "부동산/REITs"

        # Tier 3 (10점): 산업재, 에너지, 통신
        if sector == 'Industrials':
            if any(kw in industry_lower for kw in ['aerospace', 'defense', 'railroad', 'logistics', 'machinery']):
                return self.VALUE_SECTOR_TIER3, "산업재", "산업재"
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

        # 기타 섹터
        return 5, sector if sector else "기타", sector if sector else ""

    def _get_technical_score(self, hist, current_price):
        """전문가급 기술적 분석 (최대 50점)"""
        from ta.trend import MACD, ADXIndicator
        from ta.momentum import RSIIndicator, StochasticOscillator
        from ta.volatility import BollingerBands, AverageTrueRange
        from ta.volume import OnBalanceVolumeIndicator

        score = 0
        comments = []
        breakdown = {
            # 추세 (15점)
            'trend_score': 0, 'ma20': 0, 'ma50': 0, 'ma200': 0,
            'macd_score': 0, 'adx_score': 0,
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
            if len(hist) < 200:
                return 0, ["데이터부족"], breakdown

            close = hist['Close']
            volume = hist['Volume']

            # ==================== 1. 추세 분석 (15점) ====================
            trend_score = 0

            # 다층 이동평균
            ma20 = close.rolling(window=20).mean().iloc[-1]
            ma50 = close.rolling(window=50).mean().iloc[-1]
            ma200 = close.rolling(window=200).mean().iloc[-1]

            breakdown['ma20'] = ma20
            breakdown['ma50'] = ma50
            breakdown['ma200'] = ma200

            if current_price > ma200:
                trend_score += self.SCORE_MA200
                comments.append("MA200↑")
            if current_price > ma50:
                trend_score += self.SCORE_MA50
            if current_price > ma20:
                trend_score += self.SCORE_MA20

            # MACD
            macd = MACD(close=close)
            macd_line = macd.macd().iloc[-1]
            macd_signal = macd.macd_signal().iloc[-1]

            if macd_line > macd_signal:
                if macd_line > 0:
                    trend_score += self.SCORE_MACD_BULLISH  # 강한 상승
                    comments.append("MACD골든")
                else:
                    trend_score += self.SCORE_MACD_SIGNAL
                breakdown['macd_score'] = self.SCORE_MACD_BULLISH if macd_line > 0 else self.SCORE_MACD_SIGNAL

            # ADX (추세 강도)
            adx = ADXIndicator(high=hist['High'], low=hist['Low'], close=close)
            adx_value = adx.adx().iloc[-1]

            if adx_value > 25:  # 강한 추세
                trend_score += self.SCORE_ADX_STRONG
                breakdown['adx_score'] = self.SCORE_ADX_STRONG
                comments.append(f"ADX:{adx_value:.0f}")

            breakdown['trend_score'] = trend_score
            score += trend_score

            # ==================== 추세 필터 ====================
            # 추세 점수가 낮으면 하락 추세로 판단
            is_downtrend = trend_score < 8  # 15점 만점의 절반 이하

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

    def _detect_market_regime(self):
        """시장 상태 감지 (Bull/Bear/Sideways)"""
        try:
            import yfinance as yf
            from ta.trend import ADXIndicator

            # S&P 500 분석
            spy = yf.Ticker('^GSPC')
            hist = spy.history(period='1y')

            if len(hist) < 200:
                return 'neutral', {}, "데이터 부족"

            close = hist['Close']
            current_price = close.iloc[-1]

            # 이동평균
            ma50 = close.rolling(window=50).mean().iloc[-1]
            ma200 = close.rolling(window=200).mean().iloc[-1]

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

            # 1. 가격 vs MA200
            if current_price > ma200:
                bull_signals += 1
            else:
                bear_signals += 1

            # 2. MA50 vs MA200
            if ma50 > ma200:
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
                'ma50': ma50,
                'ma200': ma200,
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
        """시장 상태에 따른 점수 비율 재설계 + 추세 필터"""
        original_tech = tech_score
        original_fund = fund_score

        # ==================== 1. 추세 필터 페널티 (시장 상태 고려) ====================
        trend_penalty_applied = False
        if is_downtrend and tech_score > 0:
            if regime == 'bear':
                # 하락장에서는 모든 종목이 하락 추세이므로 페널티 완화
                tech_score = int(tech_score * 0.8)  # 20% 페널티만
                trend_penalty_msg = f"하락추세 페널티 -20% (하락장 완화)"
            else:
                # 상승장/횡보장에서는 하락 추세가 비정상이므로 강한 페널티
                tech_score = int(tech_score * 0.6)  # 40% 페널티
                trend_penalty_msg = f"하락추세 페널티 -40%"
            trend_penalty_applied = True
        else:
            trend_penalty_msg = ""

        # ==================== 2. 시장 상태별 가중치 재설계 ====================
        # 기존: 멀티플라이어 방식 → 신규: 비율 재분배 방식
        if regime == 'bull':
            # 상승장: 기술 60 : 펀더 40
            tech_weight = 0.6
            fund_weight = 0.4
            tech_score = int(tech_score * 1.2)  # 60/50 = 1.2
            fund_score = int(fund_score * 0.8)  # 40/50 = 0.8
            adjustment = "상승장: 기술60% : 펀더40% (모멘텀 중시)"

        elif regime == 'bear':
            # 하락장: 기술 40 : 펀더 60
            tech_weight = 0.4
            fund_weight = 0.6
            tech_score = int(tech_score * 0.8)  # 40/50 = 0.8
            fund_score = int(fund_score * 1.2)  # 60/50 = 1.2
            adjustment = "하락장: 기술40% : 펀더60% (안전성 중시)"

        elif regime == 'sideways':
            # 횡보장: 기술 50 : 펀더 50 (균형)
            tech_weight = 0.5
            fund_weight = 0.5
            tech_score = int(tech_score * 1.0)
            fund_score = int(fund_score * 1.0)
            adjustment = "횡보장: 기술50% : 펀더50% (균형)"

        else:  # neutral
            tech_weight = 0.5
            fund_weight = 0.5
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

    def _calculate_volatility_breakout(self, hist):
        """변동성 돌파 전략 가격 계산 (레거시 - 호환성 유지)"""
        try:
            if len(hist) < 2:
                return None, None, None

            # 전일 데이터
            prev_high = hist['High'].iloc[-2]
            prev_low = hist['Low'].iloc[-2]
            today_open = hist['Open'].iloc[-1]

            # 계산
            range_val = prev_high - prev_low
            breakout_price = today_open + (range_val * self.K_FACTOR)
            target_price = breakout_price + range_val
            stop_loss = breakout_price * self.STOP_LOSS_RATIO

            return breakout_price, target_price, stop_loss

        except Exception:
            return None, None, None

    def _calculate_smart_entry_exit(self, current_price, contrarian_adj, hist, ma20):
        """🎯 스마트 진입/청산 전략 (역발상 하이브리드)"""
        try:
            if len(hist) < 2:
                return None, None, None, "데이터 부족"

            # Tier 1: 🎯 역발상 매수 (과매도 우량주)
            if contrarian_adj > 0:
                buy_price = current_price  # 즉시 매수
                target_price = current_price * 1.10  # +10%
                stop_loss = current_price * 0.95     # -5%
                strategy = "🎯 즉시매수"

            # Tier 2: ⚠️ 매수 보류 (과열주)
            elif contrarian_adj < 0:
                buy_price = None  # 매수 보류
                target_price = None
                stop_loss = None
                strategy = "⚠️ 조정대기"

            # Tier 3: 📊 기술적 매수 (일반 종목)
            else:
                # MA20 풀백 전략: MA20 + 1%
                if ma20 and ma20 > 0:
                    buy_price = ma20 * 1.01
                    target_price = buy_price * 1.08  # +8%
                    stop_loss = ma20 * 0.97          # MA20 -3% (추세 이탈)
                    strategy = "📊 MA20풀백"
                else:
                    # MA20 없으면 현재가
                    buy_price = current_price
                    target_price = current_price * 1.08
                    stop_loss = current_price * 0.97
                    strategy = "📊 현재가"

            return buy_price, target_price, stop_loss, strategy

        except Exception:
            return None, None, None, "계산 실패"

    def _get_current_price(self, info, hist):
        """현재가 추출"""
        return info.get('currentPrice') or info.get('regularMarketPrice') or hist['Close'].iloc[-1]

    def _get_market_status_and_prices(self, info):
        """시장 상태 및 가격 정보 추출"""
        try:
            # 현재 ET 시간
            et_tz = pytz.timezone('America/New_York')
            now_et = datetime.now(et_tz)
            hour = now_et.hour
            minute = now_et.minute

            # 시장 시간대 판단
            # Pre-market: 4:00 AM - 9:30 AM ET
            # Regular: 9:30 AM - 4:00 PM ET
            # After-hours: 4:00 PM - 8:00 PM ET

            market_status = 'closed'
            if (hour == 4 and minute >= 0) or (4 < hour < 9) or (hour == 9 and minute < 30):
                market_status = 'pre'
            elif (hour == 9 and minute >= 30) or (9 < hour < 16):
                market_status = 'regular'
            elif (hour >= 16 and hour < 20):
                market_status = 'after'

            # 가격 정보
            current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            pre_market_price = info.get('preMarketPrice')
            post_market_price = info.get('postMarketPrice')
            regular_market_previous_close = info.get('regularMarketPreviousClose') or info.get('previousClose', 0)

            return {
                'status': market_status,
                'current_price': current_price,
                'pre_market_price': pre_market_price,
                'post_market_price': post_market_price,
                'previous_close': regular_market_previous_close
            }
        except Exception:
            return {
                'status': 'unknown',
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice', 0),
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

        # 🎯 스마트 진입/청산 전략
        ma20 = tech_breakdown.get('ma20_value', 0)
        buy_price, target, stop_loss, strategy = self._calculate_smart_entry_exit(
            current_price, contrarian_adj, hist, ma20
        )

        # 레거시 호환성: breakout 가격도 유지
        breakout, _, _ = self._calculate_volatility_breakout(hist)

        # 시장 상태 및 가격 정보
        market_info = self._get_market_status_and_prices(info)

        # Verdict
        verdict = self._get_verdict(total_score)

        # 코멘트 조합 (역발상 코멘트 우선 표시)
        all_comments = fund_comments + tech_comments
        if contrarian_comment:
            all_comments.insert(0, contrarian_comment)
        comment = ", ".join(all_comments[:3]) if all_comments else "-"

        return {
            'ticker': ticker,
            'score': total_score,
            'fund_score': fund_score,
            'tech_score': tech_score,
            'contrarian_adjustment': contrarian_adj,
            'fund_breakdown': fund_breakdown,
            'tech_breakdown': tech_breakdown,
            'verdict': verdict,
            'price': current_price,
            'market_info': market_info,
            'buy_price': buy_price,           # 🎯 스마트 매수가
            'buy_strategy': strategy,          # 전략 설명
            'breakout': breakout,              # 레거시 호환
            'target': target,
            'stop_loss': stop_loss,
            'comment': comment
        }

    def stage2_deep_analysis(self, tickers):
        """2단계: 정밀 분석 (Titan 알고리즘)"""
        print("=" * 70)
        print("📊 STAGE 2: 정밀 분석 (Fundamental + Technical)")
        print("=" * 70)

        # 🌍 시장 상태 감지
        print("\n🌍 시장 상태 감지 중...")
        market_regime, regime_details, regime_desc = self._detect_market_regime()
        print(f"   {regime_desc}\n")

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

                    # 조정된 점수로 총점 재계산
                    total_score_adjusted = fund_adjusted + tech_adjusted + result['contrarian_adjustment']

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
                f"${r['breakout']:.2f}" if r['breakout'] else "N/A",
                f"${r['stop_loss']:.2f}" if r['stop_loss'] else "N/A",
                r['comment']
            ])

        headers = ['Ticker', 'Score', 'Verdict', 'Price', '매수신호가', '손절가', 'Comment']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        print(f"\n📊 총 {len(filtered)}개 유망 종목 발견")

    def generate_html_report(self, results, report_type="NASDAQ 100", filename="report.html", min_score=50):
        """HTML 리포트 생성"""
        filtered = [r for r in results if r['score'] >= min_score]
        filtered.sort(key=lambda x: x['score'], reverse=True)

        now = datetime.now()

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

        # 리포트 타입에 따른 색상 및 아이콘 설정
        if "NASDAQ" in report_type:
            primary_color = "#5BA3E0"
            emoji = "🚀"
        elif "Value" in report_type:
            primary_color = "#E8A838"
            emoji = "💰"
        else:
            primary_color = "#7B68EE"
            emoji = "⭐"

        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_type} - Titan Analysis - {now.strftime("%Y-%m-%d")}</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Noto Sans KR', sans-serif;
            background: linear-gradient(180deg, #87CEEB 0%, #98D8C8 30%, #F7DC6F 70%, #FADBD8 100%);
            background-attachment: fixed;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            background: white;
            border-radius: 30px;
            padding: 35px;
            margin-bottom: 25px;
            box-shadow: 0 8px 0 {primary_color};
            border: 4px solid #5D4E37;
            text-align: center;
        }}
        .header h1 {{ color: #5D4E37; font-size: 2em; margin-top: 10px; }}
        .header .subtitle {{ color: {primary_color}; margin-top: 10px; font-size: 1.1em; }}
        .header .date {{ color: #7B6B4F; margin-top: 10px; font-size: 0.9em; }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .summary-card {{
            background: linear-gradient(180deg, #FFF8DC, #FAEBD7);
            border-radius: 20px;
            padding: 20px;
            border: 3px solid #5D4E37;
            text-align: center;
        }}
        .summary-card .label {{ color: #7B6B4F; margin-bottom: 8px; }}
        .summary-card .value {{ color: #FF6B35; font-size: 1.8em; font-weight: bold; }}
        .stock-card {{
            background: white;
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 15px;
            border: 3px solid #5D4E37;
            box-shadow: 0 5px 0 {primary_color};
            position: relative;
        }}
        .stock-card .rank {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: #FFD700;
            color: #5D4E37;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 1.2em;
            border: 2px solid #5D4E37;
        }}
        .stock-card h2 {{ color: #5D4E37; margin-bottom: 10px; padding-left: 50px; }}
        .stock-card .ticker {{ color: {primary_color}; font-weight: bold; font-size: 1.1em; }}
        .stock-card .info {{ margin-top: 15px; display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }}
        .stock-card .info-item {{ padding: 8px; background: #F5F5F5; border-radius: 10px; }}
        .stock-card .info-label {{ font-size: 0.85em; color: #7B6B4F; }}
        .stock-card .info-value {{ font-weight: bold; color: #5D4E37; margin-top: 3px; }}
        .score-badge {{
            background: {primary_color};
            color: white;
            padding: 8px 20px;
            border-radius: 20px;
            float: right;
            font-weight: bold;
            font-size: 1.1em;
        }}
        .score-badge.high {{ background: #4CAF50; }}
        .score-badge.strong {{ background: #FF6B35; }}
        .verdict {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 15px;
            font-size: 0.9em;
            font-weight: bold;
            margin-top: 10px;
        }}
        .verdict.strong-buy {{ background: #4CAF50; color: white; }}
        .verdict.buy {{ background: #8BC34A; color: white; }}
        .verdict.hold {{ background: #FFC107; color: #5D4E37; }}
        .comment {{
            margin-top: 10px;
            padding: 10px;
            background: #FFF9E6;
            border-left: 4px solid {primary_color};
            border-radius: 5px;
            font-size: 0.9em;
            color: #5D4E37;
        }}
        .back-link {{
            display: block;
            text-align: center;
            margin-bottom: 20px;
            color: #5D4E37;
            text-decoration: none;
            font-weight: bold;
        }}
        .back-link:hover {{ color: {primary_color}; }}
        .footer {{
            background: rgba(255,255,255,0.9);
            border-radius: 20px;
            padding: 20px;
            text-align: center;
            color: #7B6B4F;
            margin-top: 30px;
        }}
        .titan-badge {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 5px 15px;
            border-radius: 15px;
            font-size: 0.8em;
            margin-left: 10px;
            font-weight: bold;
        }}
        .score-breakdown {{
            margin: 15px 0;
            padding: 15px;
            background: #F8F9FA;
            border-radius: 10px;
            border: 2px solid #E0E0E0;
        }}
        .score-breakdown h3 {{
            color: #5D4E37;
            margin-bottom: 12px;
            font-size: 1em;
        }}
        .breakdown-section {{
            margin-bottom: 12px;
        }}
        .breakdown-title {{
            font-weight: bold;
            color: {primary_color};
            margin-bottom: 8px;
            font-size: 0.95em;
        }}
        .breakdown-items {{
            display: grid;
            gap: 6px;
        }}
        .breakdown-item {{
            display: grid;
            grid-template-columns: 1fr auto auto;
            gap: 10px;
            padding: 6px 10px;
            background: white;
            border-radius: 6px;
            align-items: center;
            font-size: 0.85em;
        }}
        .breakdown-item .criterion {{
            color: #5D4E37;
            font-weight: 500;
        }}
        .breakdown-item .criterion-value {{
            color: #7B6B4F;
            text-align: right;
        }}
        .breakdown-item .criterion-score {{
            color: {primary_color};
            font-weight: bold;
            text-align: right;
            min-width: 50px;
        }}
        .highlight-price {{
            background: linear-gradient(135deg, #FFF3CD, #FFE5B4) !important;
            border: 2px solid {primary_color} !important;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-link">← 메인으로</a>
        <div class="header">
            <div style="font-size: 3em;">{emoji}</div>
            <h1>{report_type} Recommendations <span class="titan-badge">TITAN v2.0</span></h1>
            <div class="subtitle">Advanced Fundamental + Technical Analysis</div>
            <div class="date">{now.strftime("%Y-%m-%d %H:%M")} UTC 업데이트</div>
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
            <div class="summary-card" style="grid-column: 1 / -1; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                <div class="label" style="color: rgba(255,255,255,0.9);">🌍 시장 상태 및 평가 기준</div>
                <div class="value" style="font-size: 1.1em;">{filtered[0].get('regime_description', 'N/A') if filtered else 'N/A'}<br>
                <span style="font-size: 0.85em; opacity: 0.9;">Strong Buy ≥{strong_buy_threshold}점 | Buy ≥{buy_threshold}점</span></div>
            </div>
        </div>
'''

        for i, stock in enumerate(filtered[:20], 1):
            score_class = 'strong' if stock['score'] >= strong_buy_threshold else ('high' if stock['score'] >= buy_threshold else '')
            verdict_class = stock['verdict'].lower().replace(' ', '-').replace('★', '').strip()

            # 점수 상세 정보
            fund_bd = stock.get('fund_breakdown', {})
            tech_bd = stock.get('tech_breakdown', {})
            market_info = stock.get('market_info', {})

            # 매출성장률 표시 (None이면 N/A)
            rg_value = fund_bd.get('revenue_growth_value')
            rg_display = f"{rg_value:.1f}%" if rg_value is not None else "N/A"

            html += f'''
        <div class="stock-card">
            <div class="rank">#{i}</div>
            <span class="score-badge {score_class}">{stock['score']}점</span>
            <h2><span class="ticker">{stock['ticker']}</span></h2>
            <span class="verdict {verdict_class}">{stock['verdict']}</span>

            <!-- 점수 상세 분석 -->
            <div class="score-breakdown">
                <h3>📊 점수 상세 분석</h3>
                <div class="breakdown-section">
                    <div class="breakdown-title">펀더멘털 점수: {stock.get('fund_score', 0)}점 / 50점</div>
                    <div class="breakdown-items">
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
                            <span class="criterion">섹터</span>
                            <span class="criterion-value">{fund_bd.get('sector_name', 'N/A')}</span>
                            <span class="criterion-score">+{fund_bd.get('sector_score', 0)}점</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">매출성장률</span>
                            <span class="criterion-value">{rg_display}</span>
                            <span class="criterion-score">+{fund_bd.get('revenue_growth_score', 0)}점</span>
                        </div>
                    </div>
                </div>
                <div class="breakdown-section">
                    <div class="breakdown-title">기술적 점수: {stock.get('tech_score', 0)}점 / 50점 (전문가급)</div>
                    <div class="breakdown-items">
                        <!-- 추세 분석 -->
                        <div class="breakdown-item" style="background: rgba(103, 126, 234, 0.05);">
                            <span class="criterion">📈 추세 분석</span>
                            <span class="criterion-value">MA20/50/200, MACD, ADX</span>
                            <span class="criterion-score">+{tech_bd.get('trend_score', 0)}점 /15</span>
                        </div>
                        <!-- 모멘텀 -->
                        <div class="breakdown-item" style="background: rgba(76, 175, 80, 0.05);">
                            <span class="criterion">⚡ 모멘텀</span>
                            <span class="criterion-value">RSI:{tech_bd.get('rsi_value', 0):.0f}, Stoch</span>
                            <span class="criterion-score">+{tech_bd.get('momentum_score', 0)}점 /12</span>
                        </div>
                        <!-- 거래량 -->
                        <div class="breakdown-item" style="background: rgba(255, 152, 0, 0.05);">
                            <span class="criterion">📊 거래량</span>
                            <span class="criterion-value">{tech_bd.get('volume_ratio', 0):.1f}x, OBV</span>
                            <span class="criterion-score">+{tech_bd.get('volume_score', 0)}점 /10</span>
                        </div>
                        <!-- 변동성 -->
                        <div class="breakdown-item" style="background: rgba(156, 39, 176, 0.05);">
                            <span class="criterion">🌊 변동성</span>
                            <span class="criterion-value">BB, ATR</span>
                            <span class="criterion-score">+{tech_bd.get('volatility_score', 0)}점 /8</span>
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

            html += '''
            </div>

            <!-- 가격 정보 -->
            <div class="info">'''

            # 시장 상태에 따른 가격 표시
            market_status = market_info.get('status', 'unknown')
            prev_close = market_info.get('previous_close', 0)
            current_price = stock['price']
            pre_price = market_info.get('pre_market_price')
            post_price = market_info.get('post_market_price')

            # 시장 상태별 설정
            if market_status == 'pre' and pre_price:
                # 프리마켓: 프리마켓 가격 표시
                display_price = pre_price
                status_color = '#FF9800'
                status_label = '🌅 프리마켓'
                base_price = prev_close
            elif market_status == 'after' and post_price:
                # 애프터장: 애프터장 가격 표시
                display_price = post_price
                status_color = '#9C27B0'
                status_label = '🌙 애프터장'
                base_price = current_price  # 정규장 종가 대비
            else:
                # 정규장 또는 기타: 정규장 가격 표시
                display_price = current_price
                status_color = '#4CAF50'
                status_label = '☀️ 정규장'
                base_price = prev_close

            # 변동률 계산
            change_pct = ((display_price - base_price) / base_price * 100) if base_price > 0 else 0
            change_color = '#4CAF50' if change_pct >= 0 else '#F44336'
            change_sign = '+' if change_pct >= 0 else ''

            # 시장 상태 + 가격 표시
            html += f'''
                <div class="info-item" style="background: {status_color}; color: white;">
                    <div class="info-label" style="color: rgba(255,255,255,0.9);">{status_label}</div>
                    <div class="info-value" style="font-size: 1.2em;">${display_price:.2f}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">전일대비</div>
                    <div class="info-value" style="color: {change_color}; font-weight: bold;">{change_sign}{change_pct:.2f}%</div>
                </div>'''

            # 🎯 스마트 매수/매도 가격 표시
            if stock.get('buy_price') is not None:
                html += f'''
                <div class="info-item">
                    <div class="info-label">매수가 {stock.get('buy_strategy', '')}</div>
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
                # ⚠️ 과열주 - 매수 보류
                html += f'''
                <div class="info-item" style="background: rgba(244, 67, 54, 0.1); border-left: 3px solid #F44336;">
                    <div class="info-label">⚠️ 투자전략</div>
                    <div class="info-value" style="color: #F44336;">조정 대기</div>
                </div>
                <div class="info-item">
                    <div class="info-label">진입 조건</div>
                    <div class="info-value" style="font-size: 0.85em;">RSI 60 이하 또는 MA20 도달</div>
                </div>'''

            # 🤖 ML 예측 결과 표시
            if stock.get('ml_signal'):
                ml_signal = stock['ml_signal']
                ml_conf = stock.get('ml_confidence', 0)
                ml_prob_up = stock.get('ml_prob_up', 0)

                # 신호에 따른 색상
                if 'Buy' in ml_signal or '상승' in ml_signal:
                    ml_color = '#4CAF50'
                elif 'Sell' in ml_signal or '하락' in ml_signal:
                    ml_color = '#F44336'
                else:
                    ml_color = '#FF9800'

                html += f'''
                <div class="info-item" style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border: 1px solid {ml_color};">
                    <div class="info-label" style="color: #888;">🤖 AI 예측</div>
                    <div class="info-value" style="color: {ml_color}; font-weight: bold;">{ml_signal}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">AI 신뢰도</div>
                    <div class="info-value">{ml_conf:.0%}</div>
                </div>'''

            if stock['comment'] and stock['comment'] != '-':
                html += f'''
            </div>
            <div class="comment">💡 {stock['comment']}</div>'''
            else:
                html += '''
            </div>'''

            html += '''
        </div>'''

        html += f'''
        <div class="footer">
            <strong>⚠️ 투자 유의사항</strong><br>
            본 리포트는 PROJECT TITAN 알고리즘 기반 투자 참고 자료이며, 투자 손실에 대한 책임은 투자자 본인에게 있습니다.<br>
            <small>Powered by Titan v2.0 | Fundamental (ROE, OPM, Sector) + Technical (MA20, RSI, Volume) + Contrarian Hybrid Strategy</small><br>
            <small>🎯 과매도 우량주 즉시매수 | 📊 일반주 MA20풀백 | ⚠️ 과열주 조정대기</small>
        </div>
    </div>
</body>
</html>'''

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✅ HTML 리포트 생성 완료: {filename} ({len(filtered)}개 추천)")
        return filtered

    def run_analysis_with_tickers(self, tickers, report_type="Analysis", html_filename=None, min_score=50, skip_stage1=True, ml_min_score=None):
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

        # ML 예측 (ml_min_score 이상 종목만)
        if ml_min_score is not None:
            results = self.run_ml_predictions(results, ml_min_score)

        # 결과 출력
        self.display_results(results, min_score=min_score)

        # HTML 리포트 생성
        if html_filename:
            self.generate_html_report(results, report_type=report_type, filename=html_filename, min_score=min_score)

        elapsed = time.time() - start_time
        print(f"\n⏱️  총 소요 시간: {elapsed/60:.1f}분")

        return results

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

    def run_full_analysis(self):
        """전체 분석 실행 (S&P 500)"""
        start_time = time.time()

        # S&P 500 다운로드
        sp500_tickers = self.get_sp500_tickers()
        if not sp500_tickers:
            print("❌ 티커 리스트를 가져올 수 없습니다.")
            return

        # Stage 1: 빠른 필터링
        filtered_tickers = self.stage1_quick_filter(sp500_tickers)

        if not filtered_tickers:
            print("❌ 1단계 필터를 통과한 종목이 없습니다.")
            return

        # Stage 2: 정밀 분석
        results = self.stage2_deep_analysis(filtered_tickers)

        # 결과 출력
        self.display_results(results, min_score=60)

        elapsed = time.time() - start_time
        print(f"\n⏱️  총 소요 시간: {elapsed/60:.1f}분")

        return results


if __name__ == "__main__":
    import sys

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
            analyzer.analysis_mode = 'growth'  # 성장주 섹터 점수 체계
            analyzer.run_analysis_with_tickers(
                tickers=GROWTH_TICKERS,
                report_type="Growth Stocks",
                html_filename="growth_report.html",
                min_score=50,
                skip_stage1=True,
                ml_min_score=75  # ML 예측은 75점 이상만
            )
        elif mode == "value":
            analyzer.analysis_mode = 'value'  # 가치주 섹터 점수 체계
            analyzer.run_analysis_with_tickers(
                tickers=VALUE_TICKERS,
                report_type="Value Stocks",
                html_filename="value_report.html",
                min_score=45,
                skip_stage1=True,
                ml_min_score=75  # ML 예측은 75점 이상만
            )
        elif mode == "sp500":
            analyzer.run_full_analysis()
        else:
            print(f"❌ 알 수 없는 모드: {mode}")
            print("사용법: python project_titan.py [growth|value|sp500]")
    else:
        # 기본: S&P 500 전체 분석
        analyzer.run_full_analysis()