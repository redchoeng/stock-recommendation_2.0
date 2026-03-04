# -*- coding: utf-8 -*-
"""
strategy.py — 진입/청산 전략 + 역발상 조정 Mixin
StrategyMixin: _find_swing_lows/highs, _calculate_smart_entry_exit,
               _apply_contrarian_adjustment, _generate_analyst_comment
"""
import pytz
from datetime import datetime


class StrategyMixin:
    # ===== 역발상 보너스/페널티 (강화) =====
    SCORE_OVERSOLD_QUALITY_BONUS = 10
    SCORE_OVERBOUGHT_PENALTY = -8     # 기존 -5 → -8 강화

    # =========================================================================

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
        """R:R 검증: 비율 부족 시 목표가 강제 상향 대신 진입 보류 플래그 반환"""
        max_stop = buy_price * 0.93   # 최대 손절 7%
        if stop_loss < max_stop:
            stop_loss = max_stop

        risk = buy_price - stop_loss
        reward = target_price - buy_price

        # R:R < 1.5 → 진입 부적합 (avoid 플래그)
        if risk > 0 and reward / risk < 1.5:
            # 현실적 저항선이 있으면 목표가만 소폭 조정 시도
            realistic = [r for r in swing_highs if r > target_price and r <= buy_price * 1.15]
            if realistic:
                target_price = min(realistic)
                # 재검증: 여전히 부족하면 avoid
                if (target_price - buy_price) / risk < 1.5:
                    return target_price, stop_loss, True  # avoid=True
            else:
                return target_price, stop_loss, True  # avoid=True
        # R:R 1.5~2.0 → 비중 축소 권장
        elif risk > 0 and reward / risk < 2.0:
            return target_price, stop_loss, False  # 통과하되 비중 축소는 전략 텍스트에서 표현

        return target_price, stop_loss, False

    def _calculate_smart_entry_exit(self, current_price, contrarian_adj, hist, tech_breakdown):
        """🎯 스윙매매 특화 진입/청산 전략 (기술적 레벨 기반)"""
        try:
            if len(hist) < 20:
                return None, None, None, "데이터 부족"

            ma20 = tech_breakdown.get('ma20', 0)
            ma60 = tech_breakdown.get('ma60', 0)
            bb_upper = tech_breakdown.get('bb_upper', 0)
            bb_lower = tech_breakdown.get('bb_lower', 0)
            atr = tech_breakdown.get('atr_value', 0)

            swing_lows = self._find_swing_lows(hist)
            swing_highs = self._find_swing_highs(hist)
            nearest_support = self._nearest_below(swing_lows, current_price)
            nearest_resistance = self._nearest_above(swing_highs, current_price)

            # ========== Tier 1: 역발상 매수 (과매도 우량주) ==========
            if contrarian_adj > 0:
                if bb_lower > 0 and bb_lower >= current_price * 0.97:
                    buy_price = bb_lower
                else:
                    buy_price = current_price

                if nearest_resistance and nearest_resistance > buy_price * 1.03:
                    target_price = nearest_resistance
                elif bb_upper > 0 and bb_upper > buy_price * 1.03:
                    target_price = bb_upper
                else:
                    target_price = buy_price + (1.5 * atr) if atr > 0 else buy_price * 1.08

                atr_stop = buy_price - (2.0 * atr) if atr > 0 else buy_price * 0.95
                struct_stop = nearest_support * 0.99 if nearest_support else atr_stop
                stop_loss = max(atr_stop, struct_stop)
                if stop_loss > buy_price * 0.98:
                    stop_loss = buy_price * 0.98
                if stop_loss >= buy_price:
                    stop_loss = buy_price * 0.95

                target_price, stop_loss, _rr_avoid = self._validate_risk_reward(
                    buy_price, target_price, stop_loss, atr, swing_highs)
                strategy = "🎯 역발상매수(기술적지지)"

            # ========== Tier 2: 조정대기 (과열주) ==========
            elif contrarian_adj < 0:
                candidates = []
                if ma20 > 0 and ma20 < current_price:
                    candidates.append(ma20)
                if nearest_support and nearest_support < current_price:
                    candidates.append(nearest_support)
                if atr > 0:
                    candidates.append(current_price - (2.0 * atr))

                buy_price = max(candidates) if candidates else current_price * 0.95

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

                target_price, stop_loss, _rr_avoid = self._validate_risk_reward(
                    buy_price, target_price, stop_loss, atr, swing_highs)
                strategy = "⚠️ 조정대기(진입조건가)"

            # ========== Tier 3: 세분화 전략 (일반종목) ==========
            else:
                rsi = tech_breakdown.get('rsi_value', 50)
                ma120 = tech_breakdown.get('ma120', 0)

                uptrend = (ma20 > 0 and ma60 > 0 and ma20 > ma60)
                price_above_ma20 = (ma20 > 0 and current_price > ma20)
                sideways = (ma20 > 0 and ma60 > 0 and abs(ma20 - ma60) / ma60 < 0.02)
                weak = (ma60 > 0 and current_price < ma60) or rsi < 40

                # --- Tier 3A: 추세추종 ---
                if uptrend and price_above_ma20 and rsi >= 50:
                    buy_price = current_price
                    if nearest_resistance and nearest_resistance > current_price * 1.02:
                        target_price = nearest_resistance
                    elif bb_upper > 0 and bb_upper > current_price * 1.02:
                        target_price = bb_upper
                    else:
                        target_price = current_price + (2.0 * atr) if atr > 0 else current_price * 1.08
                    atr_stop = current_price - (2.0 * atr) if atr > 0 else current_price * 0.95
                    ma20_stop = ma20 * 0.99 if ma20 > 0 else atr_stop
                    stop_loss = max(atr_stop, ma20_stop)
                    if stop_loss > current_price * 0.98:
                        stop_loss = current_price * 0.98
                    if stop_loss >= current_price:
                        stop_loss = current_price * 0.95
                    target_price, stop_loss, _rr_avoid = self._validate_risk_reward(
                        buy_price, target_price, stop_loss, atr, swing_highs)
                    strategy = "📈 추세추종(MA20↑)"

                # --- Tier 3B: 풀백매수 ---
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
                    if nearest_resistance and nearest_resistance > current_price:
                        target_price = nearest_resistance
                    elif bb_upper > 0 and bb_upper > current_price:
                        target_price = bb_upper
                    else:
                        target_price = buy_price + (2.0 * atr) if atr > 0 else buy_price * 1.08
                    supports_below = [l for l in swing_lows if l < buy_price]
                    struct_stop = max(supports_below) * 0.99 if supports_below else buy_price * 0.95
                    atr_stop = buy_price - (2.0 * atr) if atr > 0 else buy_price * 0.95
                    stop_loss = max(atr_stop, struct_stop)
                    if stop_loss > buy_price * 0.98:
                        stop_loss = buy_price * 0.98
                    if stop_loss >= buy_price:
                        stop_loss = buy_price * 0.95
                    target_price, stop_loss, _rr_avoid = self._validate_risk_reward(
                        buy_price, target_price, stop_loss, atr, swing_highs)
                    strategy = f"📊 풀백매수({strategy_suffix})"

                # --- Tier 3C: 박스권하단 ---
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
                    if nearest_resistance and nearest_resistance > current_price:
                        target_price = nearest_resistance
                    elif bb_upper > 0 and bb_upper > current_price:
                        target_price = bb_upper
                    else:
                        target_price = buy_price + (1.5 * atr) if atr > 0 else buy_price * 1.06
                    supports_below = [l for l in swing_lows if l < buy_price]
                    struct_stop = max(supports_below) * 0.99 if supports_below else buy_price * 0.95
                    atr_stop = buy_price - (2.0 * atr) if atr > 0 else buy_price * 0.95
                    stop_loss = max(atr_stop, struct_stop)
                    if stop_loss > buy_price * 0.98:
                        stop_loss = buy_price * 0.98
                    if stop_loss >= buy_price:
                        stop_loss = buy_price * 0.95
                    target_price, stop_loss, _rr_avoid = self._validate_risk_reward(
                        buy_price, target_price, stop_loss, atr, swing_highs)
                    strategy = f"📦 박스권하단({strategy_suffix})"

                # --- Tier 3D: 반등대기 ---
                else:
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
                    if ma60 > 0 and ma60 > current_price:
                        target_price = ma60
                    elif nearest_resistance and nearest_resistance > current_price:
                        target_price = nearest_resistance
                    else:
                        target_price = buy_price + (1.5 * atr) if atr > 0 else buy_price * 1.06
                    supports_below = [l for l in swing_lows if l < buy_price]
                    struct_stop = max(supports_below) * 0.99 if supports_below else buy_price * 0.95
                    atr_stop = buy_price - (1.5 * atr) if atr > 0 else buy_price * 0.95
                    stop_loss = max(atr_stop, struct_stop)
                    if stop_loss > buy_price * 0.97:
                        stop_loss = buy_price * 0.97
                    if stop_loss >= buy_price:
                        stop_loss = buy_price * 0.95
                    target_price, stop_loss, _rr_avoid = self._validate_risk_reward(
                        buy_price, target_price, stop_loss, atr, swing_highs)
                    strategy = f"🔄 반등대기({strategy_suffix})"

            # R:R 부족 시 경고 표시 + 감점 (완전 차단 대신)
            rr_penalty = 0
            if _rr_avoid:
                strategy = f"⚠️ {strategy}(R:R주의)"
                rr_penalty = -5

            return buy_price, target_price, stop_loss, strategy, rr_penalty

        except (KeyError, TypeError, ValueError, ZeroDivisionError) as e:
            print(f"  ⚠️ 진입/청산 계산 에러: {type(e).__name__}: {e}")
            return None, None, None, "계산 실패", 0

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
            weekday = now_et.weekday()

            market_status = 'closed'
            if weekday < 5:
                if (hour == 4 and minute >= 0) or (4 < hour < 9) or (hour == 9 and minute < 30):
                    market_status = 'pre'
                elif (hour == 9 and minute >= 30) or (9 < hour < 16):
                    market_status = 'regular'
                elif (hour >= 16 and hour < 20):
                    market_status = 'after'

            regular_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            pre_market_price = info.get('preMarketPrice')
            post_market_price = info.get('postMarketPrice')
            previous_close = info.get('regularMarketPreviousClose') or info.get('previousClose', 0)

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
        """하이브리드 전략: 과매도/조정구간 우량주 보너스, 과열주 감점"""
        adjustment = 0
        contrarian_comment = ""

        rsi = tech_breakdown.get('rsi_value', 50)
        mfi = tech_breakdown.get('mfi_value', 50)
        volume_ratio = tech_breakdown.get('volume_ratio', 1.0)
        bb_lower = tech_breakdown.get('bb_lower', 0)
        current_price = tech_breakdown.get('current_price', 0)

        quality_growth_sectors = [
            'AI/반도체', '클라우드', '사이버보안', '국방/항공',
            '소프트웨어', '바이오텍', '디지털인프라',
            '필수소비재', '헬스케어', '유틸리티', '금융',
        ]

        # BB하단 근접 여부 (현재가가 BB하단의 102% 이내)
        near_bb_lower = (bb_lower > 0 and current_price > 0
                         and current_price <= bb_lower * 1.02)

        # === 구간 1: 강한 과매도 (RSI < 30) ===
        if rsi < self.RSI_OVERSOLD:
            if fund_score >= 35:
                if sector_name in quality_growth_sectors:
                    adjustment = self.SCORE_OVERSOLD_QUALITY_BONUS  # +10
                    if volume_ratio >= 2.0:
                        adjustment += 2  # 항복매도(Capitulation) 거래량 동반
                    contrarian_comment = "🎯저가매수기회"
                else:
                    adjustment = self.SCORE_OVERSOLD_QUALITY_BONUS // 2  # +5
                    contrarian_comment = "💎저평가"
            elif fund_score >= 25:
                adjustment = 3
                contrarian_comment = "💎약한저평가"

        # === 구간 2: 조정매수 구간 (RSI 30~45 + 추가 조건) ===
        elif rsi < 45 and fund_score >= 30:
            # 조건: BB하단 근접 OR MFI 과매도 OR 거래량 급증
            dip_signals = sum([
                near_bb_lower,
                mfi < 30,
                volume_ratio >= 1.5,
            ])
            if dip_signals >= 1:
                if fund_score >= 40:
                    adjustment = 8  # 펀더멘탈 최우량 조정 = 강한 매수 신호
                    contrarian_comment = "📉우량주조정매수"
                else:
                    adjustment = 5  # 펀더멘탈 양호 조정
                    contrarian_comment = "📉조정매수구간"
            elif rsi < 35 and fund_score >= 35:
                # RSI 30~35: 신호 없어도 펀더 우량이면 소폭 보너스
                adjustment = 3
                contrarian_comment = "💎눌림목"

        # === 구간 3: 과열 경계 (RSI 70~75) ===
        elif rsi > self.RSI_OVERBOUGHT and rsi <= 75:
            adjustment = -3
            contrarian_comment = "⚡과열경계"

        # === 구간 4: 강한 과열 (RSI > 75) ===
        elif rsi > 75:
            adjustment = self.SCORE_OVERBOUGHT_PENALTY  # -8
            if volume_ratio < 1.0:
                adjustment -= 2  # 거래량 감소 동반 과열 = 추가 감점
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

        fcf_margin = fund_bd.get('fcf_margin_value')
        if fcf_margin is not None:
            if fcf_margin >= 25:
                fund_parts.append(f"FCF Margin {fcf_margin:.0f}%로 현금창출력 최상위")
            elif fcf_margin >= 15:
                fund_parts.append(f"FCF Margin {fcf_margin:.0f}%로 우수한 현금흐름")

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
