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

# 사전 정의된 티커 리스트
NASDAQ100_TICKERS = [
    'AAPL', 'MSFT', 'NVDA', 'AVGO', 'ADBE', 'CSCO', 'QCOM', 'TXN', 'AMD', 'INTC',
    'GOOGL', 'META', 'AMZN', 'TSLA', 'NFLX', 'CRM', 'ORCL', 'INTU', 'NOW', 'SNOW',
    'COST', 'PEP', 'AMGN', 'GILD', 'ISRG', 'HON', 'PYPL', 'ABNB', 'MELI', 'ARM'
]

VALUE_TICKERS = [
    'JPM', 'BAC', 'WFC', 'GS', 'BRK-B', 'V', 'MA',
    'JNJ', 'UNH', 'PFE', 'ABBV', 'MRK', 'LLY',
    'PG', 'KO', 'PEP', 'WMT', 'COST',
    'XOM', 'CVX', 'COP',
    'LMT', 'RTX', 'CAT', 'UNP', 'UPS', 'HON',
    'NEE', 'DUK', 'SO'
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

    # 섹터별 점수 (2026 거시 경제 트렌드 반영)
    SCORE_SECTOR_TIER1 = 20  # AI, 반도체, 클라우드, 사이버보안, 국방
    SCORE_SECTOR_TIER2 = 15  # 소프트웨어, EV, 바이오텍, 신재생에너지
    SCORE_SECTOR_TIER3 = 10  # 헬스케어, 산업자동화, 핀테크
    SCORE_SECTOR_TIER4 = 5   # 전통 에너지, 소비재, 유틸리티

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
            'sector_score': 0,
            'sector_name': ''
        }

        try:
            # 1. ROE
            roe = info.get('returnOnEquity')
            if roe:
                roe_pct = roe * 100
                breakdown['roe_value'] = roe_pct
                if roe_pct > 20:
                    score += self.SCORE_ROE_EXCELLENT
                    breakdown['roe_score'] = self.SCORE_ROE_EXCELLENT
                    comments.append(f"ROE:{roe_pct:.1f}%")
                elif roe_pct > 10:
                    score += self.SCORE_ROE_GOOD
                    breakdown['roe_score'] = self.SCORE_ROE_GOOD
                    comments.append(f"ROE:{roe_pct:.1f}%")

            # 2. Operating Margin
            opm = info.get('operatingMargins')
            if opm:
                opm_pct = opm * 100
                breakdown['opm_value'] = opm_pct
                if opm_pct > 20:
                    score += self.SCORE_OPM_EXCELLENT
                    breakdown['opm_score'] = self.SCORE_OPM_EXCELLENT
                    comments.append(f"OPM:{opm_pct:.1f}%")
                elif opm_pct > 10:
                    score += self.SCORE_OPM_GOOD
                    breakdown['opm_score'] = self.SCORE_OPM_GOOD

            # 3. Sector & Industry (세분화된 분류)
            sector = info.get('sector', '')
            industry = info.get('industry', '')
            breakdown['sector_name'] = f"{sector}"

            # Tier 1: AI, 반도체, 클라우드, 사이버보안, 국방 (20점)
            if any(keyword in industry.lower() for keyword in ['semiconductor', 'chip', 'ai', 'artificial intelligence']):
                score += self.SCORE_SECTOR_TIER1
                breakdown['sector_score'] = self.SCORE_SECTOR_TIER1
                breakdown['sector_name'] = "AI/반도체"
                comments.append("AI/반도체")
            elif any(keyword in industry.lower() for keyword in ['cloud', 'data center', 'infrastructure software']):
                score += self.SCORE_SECTOR_TIER1
                breakdown['sector_score'] = self.SCORE_SECTOR_TIER1
                breakdown['sector_name'] = "클라우드"
                comments.append("클라우드")
            elif any(keyword in industry.lower() for keyword in ['cybersecurity', 'security software', 'information security']):
                score += self.SCORE_SECTOR_TIER1
                breakdown['sector_score'] = self.SCORE_SECTOR_TIER1
                breakdown['sector_name'] = "사이버보안"
                comments.append("사이버보안")
            elif any(keyword in industry.lower() for keyword in ['aerospace', 'defense', 'military']):
                score += self.SCORE_SECTOR_TIER1
                breakdown['sector_score'] = self.SCORE_SECTOR_TIER1
                breakdown['sector_name'] = "국방/항공"
                comments.append("국방/항공")

            # Tier 2: 소프트웨어, EV, 바이오텍, 신재생 (15점)
            elif sector == 'Technology' and any(keyword in industry.lower() for keyword in ['software', 'application', 'saas']):
                score += self.SCORE_SECTOR_TIER2
                breakdown['sector_score'] = self.SCORE_SECTOR_TIER2
                breakdown['sector_name'] = "소프트웨어"
                comments.append("소프트웨어")
            elif any(keyword in industry.lower() for keyword in ['electric vehicle', 'ev ', 'battery', 'lithium']):
                score += self.SCORE_SECTOR_TIER2
                breakdown['sector_score'] = self.SCORE_SECTOR_TIER2
                breakdown['sector_name'] = "전기차/배터리"
                comments.append("전기차/배터리")
            elif any(keyword in industry.lower() for keyword in ['biotech', 'genomic', 'gene therapy', 'crispr']):
                score += self.SCORE_SECTOR_TIER2
                breakdown['sector_score'] = self.SCORE_SECTOR_TIER2
                breakdown['sector_name'] = "바이오텍"
                comments.append("바이오텍")
            elif any(keyword in industry.lower() for keyword in ['solar', 'wind', 'renewable', 'clean energy', 'hydrogen']):
                score += self.SCORE_SECTOR_TIER2
                breakdown['sector_score'] = self.SCORE_SECTOR_TIER2
                breakdown['sector_name'] = "신재생에너지"
                comments.append("신재생에너지")
            elif sector == 'Communication Services':
                score += self.SCORE_SECTOR_TIER2
                breakdown['sector_score'] = self.SCORE_SECTOR_TIER2
                breakdown['sector_name'] = "디지털인프라"
                comments.append("디지털인프라")

            # Tier 3: 헬스케어, 산업자동화, 핀테크 (10점)
            elif sector == 'Healthcare' and 'biotech' not in industry.lower():
                score += self.SCORE_SECTOR_TIER3
                breakdown['sector_score'] = self.SCORE_SECTOR_TIER3
                breakdown['sector_name'] = "헬스케어"
                comments.append("헬스케어")
            elif sector == 'Industrials' and any(keyword in industry.lower() for keyword in ['automation', 'robot', 'machinery']):
                score += self.SCORE_SECTOR_TIER3
                breakdown['sector_score'] = self.SCORE_SECTOR_TIER3
                breakdown['sector_name'] = "산업자동화"
                comments.append("산업자동화")
            elif any(keyword in industry.lower() for keyword in ['fintech', 'payment', 'financial technology']):
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

            # Tier 4: 전통 에너지, 소비재, 유틸리티 (5점)
            elif sector == 'Energy' and 'renewable' not in industry.lower():
                score += self.SCORE_SECTOR_TIER4
                breakdown['sector_score'] = self.SCORE_SECTOR_TIER4
                breakdown['sector_name'] = "전통에너지"
                comments.append("전통에너지")
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
                momentum_score += self.SCORE_RSI_OVERSOLD
                breakdown['rsi_score'] = self.SCORE_RSI_OVERSOLD
                comments.append(f"RSI:{rsi:.0f}↓")

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
                volatility_score += 3  # 하단 (반등 기대)
                comments.append("BB하단")

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

        except Exception as e:
            print(f"Technical analysis error: {e}")
            pass

        return score, comments, breakdown

    def _get_verdict(self, total_score):
        """점수에 따른 투자 판단"""
        if total_score >= self.SCORE_STRONG_BUY:
            return "Strong Buy ★"
        elif total_score >= self.SCORE_BUY:
            return "Buy"
        elif total_score >= self.SCORE_HOLD:
            return "Hold"
        else:
            return "Avoid"

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

        results = []
        total = len(tickers)

        for i, ticker in enumerate(tickers, 1):
            try:
                print(f"분석 중: {i}/{total} - {ticker}")

                result = self._analyze_single_stock(ticker)
                if result:
                    results.append(result)

                # API 제한 회피
                time.sleep(0.5)

            except Exception as e:
                print(f"  ⚠️  {ticker} 분석 실패: {e}")
                continue

        print(f"\n✅ 2단계 완료: {len(results)}개 종목 분석 완료\n")
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
                <div class="label">Strong Buy</div>
                <div class="value">{len([r for r in filtered if r['score'] >= self.SCORE_STRONG_BUY])}개</div>
            </div>
            <div class="summary-card">
                <div class="label">평균 점수</div>
                <div class="value">{sum(r['score'] for r in filtered) / len(filtered) if filtered else 0:.0f}점</div>
            </div>
        </div>
'''

        for i, stock in enumerate(filtered[:20], 1):
            score_class = 'strong' if stock['score'] >= self.SCORE_STRONG_BUY else ('high' if stock['score'] >= self.SCORE_BUY else '')
            verdict_class = stock['verdict'].lower().replace(' ', '-').replace('★', '').strip()

            # 점수 상세 정보
            fund_bd = stock.get('fund_breakdown', {})
            tech_bd = stock.get('tech_breakdown', {})
            market_info = stock.get('market_info', {})

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
            if market_status == 'pre':
                # 프리마켓: 전날 마감가 + 프리마켓 가격
                html += f'''
                <div class="info-item">
                    <div class="info-label">전날 마감가</div>
                    <div class="info-value">${market_info.get('previous_close', 0):.2f}</div>
                </div>'''
                if market_info.get('pre_market_price'):
                    html += f'''
                <div class="info-item highlight-price">
                    <div class="info-label">프리마켓 가격</div>
                    <div class="info-value">${market_info.get('pre_market_price', 0):.2f}</div>
                </div>'''
            elif market_status == 'regular':
                # 정규장: 현재가만
                html += f'''
                <div class="info-item highlight-price">
                    <div class="info-label">현재가</div>
                    <div class="info-value">${stock['price']:.2f}</div>
                </div>'''
            elif market_status == 'after':
                # 애프터장: 정규장 마감가 + 애프터장 가격
                html += f'''
                <div class="info-item">
                    <div class="info-label">정규장 마감가</div>
                    <div class="info-value">${market_info.get('previous_close', 0):.2f}</div>
                </div>'''
                if market_info.get('post_market_price'):
                    html += f'''
                <div class="info-item highlight-price">
                    <div class="info-label">애프터장 가격</div>
                    <div class="info-value">${market_info.get('post_market_price', 0):.2f}</div>
                </div>'''
            else:
                # 장 마감 또는 알 수 없음: 현재가
                html += f'''
                <div class="info-item">
                    <div class="info-label">현재가</div>
                    <div class="info-value">${stock['price']:.2f}</div>
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

        elapsed = time.time() - start_time
        print(f"\n⏱️  총 소요 시간: {elapsed/60:.1f}분")

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

        if mode == "nasdaq":
            analyzer.run_analysis_with_tickers(
                tickers=NASDAQ100_TICKERS,
                report_type="NASDAQ 100",
                html_filename="nasdaq100_report.html",
                min_score=50,
                skip_stage1=True
            )
        elif mode == "value":
            analyzer.run_analysis_with_tickers(
                tickers=VALUE_TICKERS,
                report_type="Value Stocks",
                html_filename="value_report.html",
                min_score=45,
                skip_stage1=True
            )
        elif mode == "sp500":
            analyzer.run_full_analysis()
        else:
            print(f"❌ 알 수 없는 모드: {mode}")
            print("사용법: python project_titan.py [nasdaq|value|sp500]")
    else:
        # 기본: S&P 500 전체 분석
        analyzer.run_full_analysis()