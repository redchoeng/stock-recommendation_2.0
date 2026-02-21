# -*- coding: utf-8 -*-
"""
technical.py — 기술적 분석 + 시장 분석 Mixin
TechnicalMixin: _get_technical_score, _get_verdict, _analyze_sector_rotation,
                _detect_market_regime, _apply_regime_adjustment
"""
import yfinance as yf


class TechnicalMixin:
    # ===== 섹터 순환매 분석용 ETF 매핑 =====
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
    ROTATION_BONUS_INFLOW = 3
    ROTATION_BONUS_TURNING = 5
    ROTATION_BONUS_WATCHING = 1
    ROTATION_PENALTY_OVERHEAT = -2
    ROTATION_PENALTY_COLD = -3

    # ===== 기술적 점수 상수 (총 50점) =====
    # 1. 추세 분석 (20점) - MA5/20/60/120 + MACD + 일목균형표 + ADX
    SCORE_MA120 = 2
    SCORE_MA60 = 2
    SCORE_MA20 = 3
    SCORE_MA5 = 2
    SCORE_MACD_BULLISH = 4
    SCORE_MACD_SIGNAL = 2
    SCORE_ICHIMOKU = 3
    SCORE_ADX_STRONG = 2

    # 2. 모멘텀 (10점)
    SCORE_RSI_OPTIMAL = 5
    SCORE_RSI_GOOD = 3
    SCORE_RSI_OVERSOLD = 2
    SCORE_STOCH_OPTIMAL = 5
    SCORE_STOCH_GOOD = 2

    # 3. 거래량 (8점)
    SCORE_VOLUME_EXTREME = 4
    SCORE_VOLUME_HIGH = 3
    SCORE_VOLUME_MODERATE = 2
    SCORE_VOLUME_NORMAL = 1
    SCORE_OBV_RISING = 4

    # 4. 변동성 (7점)
    SCORE_BB_POSITION = 4
    SCORE_ATR_EXPANSION = 3

    # 5. 가격 패턴 (5점)
    SCORE_PRICE_POSITION = 5

    # ===== RSI 임계값 =====
    RSI_OVERSOLD = 30
    RSI_OPTIMAL_MIN = 40
    RSI_OPTIMAL_MAX = 60
    RSI_GOOD_MAX = 70
    RSI_OVERBOUGHT = 70

    # =========================================================================

    def _get_technical_score(self, hist, current_price):
        """전문가급 기술적 분석 (최대 50점)"""
        from ta.trend import MACD, ADXIndicator
        from ta.momentum import RSIIndicator, StochasticOscillator
        from ta.volatility import BollingerBands, AverageTrueRange
        from ta.volume import OnBalanceVolumeIndicator, MFIIndicator

        score = 0
        comments = []
        breakdown = {
            'trend_score': 0, 'ma5': 0, 'ma20': 0, 'ma60': 0, 'ma120': 0,
            'macd_score': 0, 'ichimoku_score': 0, 'adx_score': 0,
            'momentum_score': 0, 'rsi_value': 0, 'rsi_score': 0,
            'stoch_score': 0, 'stoch_k': 0, 'stoch_d': 0,
            'volume_score': 0, 'volume_ratio': 0, 'obv_score': 0,
            'volatility_score': 0, 'bb_position': 0, 'atr_score': 0,
            'pattern_score': 0, 'price_position': 0
        }

        try:
            if len(hist) < 120:
                return 0, ["데이터부족"], breakdown

            close = hist['Close']
            volume = hist['Volume']

            # ==================== 1. 추세 분석 (16점) ====================
            trend_score = 0

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

            tenkan = (high_9 + low_9) / 2
            kijun = (high_26 + low_26) / 2
            senkou_a = ((tenkan + kijun) / 2).shift(26)
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

            # ADX
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
                if not is_downtrend:
                    momentum_score += self.SCORE_RSI_OVERSOLD
                    breakdown['rsi_score'] = self.SCORE_RSI_OVERSOLD
                    comments.append(f"RSI:{rsi:.0f}↓")
                else:
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

            # MFI
            mfi = MFIIndicator(high=hist['High'], low=hist['Low'], close=close, volume=volume, window=14)
            mfi_val = mfi.money_flow_index().iloc[-1]
            breakdown['mfi_value'] = mfi_val

            if mfi_val < 20:
                momentum_score += 2
                comments.append("MFI바닥")
            elif mfi_val > 80 and is_downtrend:
                comments.append("MFI과열")

            breakdown['momentum_score'] = momentum_score
            score += momentum_score

            # ==================== 3. 거래량 (10점) ====================
            volume_score = 0

            avg_volume = volume.rolling(window=20).mean().iloc[-1]
            current_volume = volume.iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            breakdown['volume_ratio'] = volume_ratio

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

            # OBV
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

            bb = BollingerBands(close=close)
            bb_high = bb.bollinger_hband().iloc[-1]
            bb_low = bb.bollinger_lband().iloc[-1]
            bb_mid = bb.bollinger_mavg().iloc[-1]

            bb_position = (current_price - bb_low) / (bb_high - bb_low) if (bb_high - bb_low) > 0 else 0.5
            breakdown['bb_position'] = bb_position
            breakdown['bb_upper'] = float(bb_high)
            breakdown['bb_lower'] = float(bb_low)
            breakdown['bb_mid'] = float(bb_mid)

            if 0.3 <= bb_position <= 0.7:
                volatility_score += self.SCORE_BB_POSITION
            elif bb_position < 0.3:
                if not is_downtrend:
                    volatility_score += 3
                    comments.append("BB하단")

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

            # 하락 추세 플래그 저장
            breakdown['is_downtrend'] = is_downtrend
            if is_downtrend:
                comments.append(f"⚠하락추세")

        except Exception as e:
            print(f"Technical analysis error: {e}")
            pass

        return score, comments, breakdown

    def _get_verdict(self, total_score, market_regime='neutral'):
        """시장 상태에 따른 적응형 투자 판단"""
        if market_regime == 'bull':
            strong_buy_threshold = 85
            buy_threshold = 75
            hold_threshold = 65
        elif market_regime == 'bear':
            strong_buy_threshold = 75
            buy_threshold = 65
            hold_threshold = 55
        else:
            strong_buy_threshold = 80
            buy_threshold = 70
            hold_threshold = 60

        if total_score >= strong_buy_threshold:
            return "Strong Buy ★"
        elif total_score >= buy_threshold:
            return "Buy"
        elif total_score >= hold_threshold:
            return "Hold"
        else:
            return "Avoid"

    def _analyze_sector_rotation(self):
        """섹터 순환매 분석 — ETF 모멘텀 기반"""
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

                    week_return = (close.iloc[-1] / close.iloc[-5] - 1) * 100
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

            sorted_sectors = sorted(results.items(), key=lambda x: x[1]['week_return'], reverse=True)
            total = len(sorted_sectors)
            top_cutoff = max(total // 3, 1)
            bottom_cutoff = total - top_cutoff

            for rank, (sector, info) in enumerate(sorted_sectors):
                info['rank'] = rank + 1
                acc = info['acceleration']

                if rank < top_cutoff:
                    if acc > 0:
                        info['rotation_bonus'] = self.ROTATION_BONUS_INFLOW
                        info['phase'] = '수급유입'
                    else:
                        info['rotation_bonus'] = self.ROTATION_PENALTY_OVERHEAT
                        info['phase'] = '과열주의'
                elif rank >= bottom_cutoff:
                    if acc > 0:
                        info['rotation_bonus'] = self.ROTATION_BONUS_TURNING
                        info['phase'] = '순환매 기대'
                    else:
                        info['rotation_bonus'] = self.ROTATION_PENALTY_COLD
                        info['phase'] = '소외 지속'
                else:
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

            spy = yf.Ticker('^GSPC')
            hist = spy.history(period='1y')

            if len(hist) < 120:
                return 'neutral', {}, "데이터 부족"

            close = hist['Close']
            current_price = close.iloc[-1]

            ma60 = close.rolling(window=60).mean().iloc[-1]
            ma120 = close.rolling(window=120).mean().iloc[-1]

            price_3m_ago = close.iloc[-63] if len(close) >= 63 else close.iloc[0]
            trend_3m = (current_price - price_3m_ago) / price_3m_ago

            price_6m_ago = close.iloc[-126] if len(close) >= 126 else close.iloc[0]
            trend_6m = (current_price - price_6m_ago) / price_6m_ago

            adx = ADXIndicator(high=hist['High'], low=hist['Low'], close=close)
            adx_value = adx.adx().iloc[-1]

            bull_signals = 0
            bear_signals = 0

            if current_price > ma120:
                bull_signals += 1
            else:
                bear_signals += 1

            if ma60 > ma120:
                bull_signals += 1
            else:
                bear_signals += 1

            if trend_3m > 0.05:
                bull_signals += 1
            elif trend_3m < -0.05:
                bear_signals += 1

            if trend_6m > 0.10:
                bull_signals += 1
            elif trend_6m < -0.10:
                bear_signals += 1

            if adx_value < 20:
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
                'trend_3m': trend_3m * 100,
                'trend_6m': trend_6m * 100,
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
        trend_penalty_applied = False
        if is_downtrend and tech_score > 0:
            if fund_score >= 40:
                penalty = 0.9 if regime == 'bear' else 0.85
                trend_penalty_msg = f"하락추세 페널티 -{int((1-penalty)*100)}% (우량주 경감)"
            elif fund_score >= 30:
                penalty = 0.8 if regime == 'bear' else 0.7
                trend_penalty_msg = f"하락추세 페널티 -{int((1-penalty)*100)}%"
            else:
                penalty = 0.7 if regime == 'bear' else 0.5
                trend_penalty_msg = f"하락추세 페널티 -{int((1-penalty)*100)}% (펀더 약세 강화)"
            tech_score = int(tech_score * penalty)
            trend_penalty_applied = True
        else:
            trend_penalty_msg = ""

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
        else:
            adjustment = "중립: 조정 없음"

        if regime == 'bull':
            tech_score = min(tech_score, 60)
            fund_score = min(fund_score, 50)
        elif regime == 'bear':
            tech_score = min(tech_score, 50)
            fund_score = min(fund_score, 65)
        else:
            tech_score = min(tech_score, 55)
            fund_score = min(fund_score, 55)

        if trend_penalty_applied:
            adjustment = f"{trend_penalty_msg} + {adjustment}"

        return tech_score, fund_score, adjustment
