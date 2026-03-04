# -*- coding: utf-8 -*-
"""
균형 포트폴리오 ML 분석
Titan 리포트의 캐시된 점수를 사용하여 ML 예측 실행
(리포트와 동일한 Titan 점수 보장)
"""
import sys
import os
import json
sys.stdout.reconfigure(encoding='utf-8')

from ml_predictor import EnsemblePredictor, train_and_predict
from project_titan import TitanAnalyzer, GROWTH_TICKERS, VALUE_TICKERS

BASE_MIN_SCORE = 75

def _get_dynamic_min_score():
    """시장 상태에 따른 동적 임계값 (Titan 캐시에서 regime 확인)"""
    try:
        with open("titan_scores_growth.json", 'r') as f:
            g_cache = json.load(f)
        # 첫 번째 종목에서 market_regime 확인
        first = next(iter(g_cache.values()), {})
        regime = first.get('market_regime', 'neutral')
        adj = {'bull': 0, 'neutral': -5, 'sideways': -5, 'bear': -10}.get(regime, 0)
        effective = BASE_MIN_SCORE + adj
        if adj != 0:
            print(f"📊 시장 상태({regime}) 반영: ML 임계값 {BASE_MIN_SCORE} → {effective}")
        return effective
    except Exception:
        return BASE_MIN_SCORE

MIN_SCORE = _get_dynamic_min_score()

def load_titan_cache(min_score=MIN_SCORE):
    """Titan 리포트에서 저장된 캐시 점수 로드 (캐시 없으면 실시간 스캔 폴백)"""
    growth_cache_file = "titan_scores_growth.json"
    value_cache_file = "titan_scores_value.json"

    titan_scores = {}
    growth_list = []
    value_list = []

    has_growth_cache = os.path.exists(growth_cache_file)
    has_value_cache = os.path.exists(value_cache_file)

    if has_growth_cache and has_value_cache:
        print("📂 Titan 캐시 로드 (리포트와 동일한 점수 사용)")

        with open(growth_cache_file, 'r') as f:
            g_cache = json.load(f)
        with open(value_cache_file, 'r') as f:
            v_cache = json.load(f)

        for t, data in g_cache.items():
            score = data['score']
            titan_scores[t] = score
            if score >= min_score:
                growth_list.append((t, score))

        for t, data in v_cache.items():
            score = data['score']
            titan_scores[t] = score
            if score >= min_score:
                value_list.append((t, score))

        growth_list.sort(key=lambda x: x[1], reverse=True)
        value_list.sort(key=lambda x: x[1], reverse=True)

        g_tickers = [t for t, s in growth_list]
        v_tickers = [t for t, s in value_list]

        print(f"\n✅ Titan 캐시 로드 완료:")
        print(f"   Growth {min_score}+: {len(g_tickers)}개 - {[f'{t}({titan_scores[t]})' for t in g_tickers[:10]]}{'...' if len(g_tickers) > 10 else ''}")
        print(f"   Value  {min_score}+: {len(v_tickers)}개 - {[f'{t}({titan_scores[t]})' for t in v_tickers[:10]]}{'...' if len(v_tickers) > 10 else ''}")

        return g_tickers, v_tickers, titan_scores
    else:
        print("⚠️ Titan 캐시 없음 - 리포트를 먼저 생성하세요:")
        print("   python project_titan.py growth")
        print("   python project_titan.py value")
        print("   그 후 다시 실행하면 캐시된 점수를 사용합니다.")
        print("\n🔄 실시간 스캔으로 폴백...")
        return _scan_titan_live(min_score)

def _scan_titan_live(min_score=MIN_SCORE):
    """캐시 없을 때 실시간 Titan 스캔 (폴백)"""
    analyzer = TitanAnalyzer()
    growth_list = []
    value_list = []
    titan_scores = {}

    print(f"📊 Titan 성장주 스캔 중... ({len(GROWTH_TICKERS)}개)")
    analyzer.analysis_mode = 'growth'
    for i, t in enumerate(GROWTH_TICKERS):
        try:
            r = analyzer._analyze_single_stock(t)
            if r and r['score'] >= min_score:
                growth_list.append((t, r['score']))
                titan_scores[t] = r['score']
        except:
            pass
        if i % 50 == 0 and i > 0:
            print(f"   ... {i}/{len(GROWTH_TICKERS)} 스캔 완료")

    print(f"📊 Titan 가치주 스캔 중... ({len(VALUE_TICKERS)}개)")
    analyzer.analysis_mode = 'value'
    for i, t in enumerate(VALUE_TICKERS):
        try:
            r = analyzer._analyze_single_stock(t)
            if r and r['score'] >= min_score:
                value_list.append((t, r['score']))
                titan_scores[t] = r['score']
        except:
            pass
        if i % 50 == 0 and i > 0:
            print(f"   ... {i}/{len(VALUE_TICKERS)} 스캔 완료")

    growth_list.sort(key=lambda x: x[1], reverse=True)
    value_list.sort(key=lambda x: x[1], reverse=True)

    g_tickers = [t for t, s in growth_list]
    v_tickers = [t for t, s in value_list]

    print(f"\n✅ 실시간 스캔 완료:")
    print(f"   Growth {min_score}+: {len(g_tickers)}개 - {[f'{t}({titan_scores[t]})' for t in g_tickers[:10]]}{'...' if len(g_tickers) > 10 else ''}")
    print(f"   Value  {min_score}+: {len(v_tickers)}개 - {[f'{t}({titan_scores[t]})' for t in v_tickers[:10]]}{'...' if len(v_tickers) > 10 else ''}")

    return g_tickers, v_tickers, titan_scores

# === Titan 점수 로드 (캐시 우선, 없으면 실시간 스캔) ===
GROWTH_75_PLUS, VALUE_75_PLUS, TITAN_SCORES = load_titan_cache()
ALL_75_PLUS = GROWTH_75_PLUS + VALUE_75_PLUS

print("\n" + "=" * 70)
print("🚀 균형 포트폴리오 ML 분석 (Titan 자동 연동)")
print(f"📊 분석 대상: {len(ALL_75_PLUS)}개 종목 (75점+)")
print(f"   - Growth: {len(GROWTH_75_PLUS)}개 (기술적 분석)")
print(f"   - Value: {len(VALUE_75_PLUS)}개 (펀더멘털 + 기술적 분석)")
print("=" * 70)

# ML 예측 실행 - 성장주와 가치주 분리
print("\n📈 성장주 ML 분석 중...")
growth_results = train_and_predict(GROWTH_75_PLUS, value_mode=False)

print("\n💎 가치주 ML 분석 중 (펀더멘털 피처 포함)...")
value_results = train_and_predict(VALUE_75_PLUS, value_mode=True)

# 결과 병합
results = growth_results + value_results

# === 복합 스코어 계산 (Titan 60% + ML 방향조정 40%) ===
# Titan 점수: 0~100, ML 신뢰도: 방향에 따라 조정 후 0~100 스케일
TITAN_WEIGHT = 0.8
ML_WEIGHT = 0.2

for r in results:
    ticker = r['ticker']
    titan_score = TITAN_SCORES.get(ticker, 75)  # 기본 75

    # ML 방향조정: 상승확률을 직접 사용 (가장 정확한 지표)
    # Sell 63.5%라도 prob_up이 8%면 adj_ml=8 (실제 상승 기대값 반영)
    adj_ml = r.get('prob_up', 0.33) * 100  # 0~100 스케일

    r['titan_score'] = titan_score
    r['adj_ml'] = adj_ml
    r['combined_score'] = titan_score * TITAN_WEIGHT + adj_ml * ML_WEIGHT

    # 배당률 정규화 (yfinance 데이터 에러 필터링)
    dy = r.get('dividend_yield', 0) or 0
    if dy > 1:  # yfinance가 % 형태로 반환하는 경우 (2.7 → 0.027)
        dy = dy / 100
    if dy > 0.20:  # 20% 초과는 데이터 에러
        dy = 0
    r['dividend_yield'] = dy

    # 거래대금 티어 보너스 (실제 매수세/유동성 반영)
    avg_vol = r.get('avg_volume', 0) or 0
    price = r.get('price', 0) or 0
    daily_value = avg_vol * price / 1e6  # 일평균 거래대금 (백만달러)
    if daily_value >= 1000:
        tier_bonus, tier_label = 5, "Hot"      # $1B+/일
    elif daily_value >= 300:
        tier_bonus, tier_label = 3, "Active"   # $300M-$1B/일
    elif daily_value >= 100:
        tier_bonus, tier_label = 0, "Normal"   # $100M-$300M/일
    else:
        tier_bonus, tier_label = -3, "Thin"    # $100M 미만/일
    r['liquidity_tier'] = tier_label
    r['daily_value_m'] = daily_value
    r['tier_bonus'] = tier_bonus
    r['combined_score'] = r['combined_score'] + tier_bonus

# 결과 정렬 (복합 스코어 기준)
results_sorted = sorted(results, key=lambda x: x.get('combined_score', 0), reverse=True)

print("\n" + "=" * 70)
print(f"📊 ML 예측 결과 (복합 스코어 = Titan {TITAN_WEIGHT:.0%} + ML {ML_WEIGHT:.0%})")
print("=" * 70)
print(f"{'Ticker':<8} {'Price':>10} {'Signal':<18} {'Conf':>8} {'AdjML':>6} {'Titan':>6} {'Tier':<7} {'Bonus':>5} {'Score':>7} {'Type':<7} {'DailyVal':>10}")
print("-" * 100)

strong_buy = []
buy = []
hold = []
avoid = []

for r in results_sorted:
    ticker = r['ticker']
    price = r.get('price', 0)
    signal = r.get('signal', 'N/A')
    conf = r.get('confidence', 0)
    category = "Growth" if ticker in GROWTH_75_PLUS else "Value"

    titan_s = r.get('titan_score', 0)
    adj_ml = r.get('adj_ml', 0)
    combined = r.get('combined_score', 0)
    tier = r.get('liquidity_tier', '?')
    bonus = r.get('tier_bonus', 0)
    dv_m = r.get('daily_value_m', 0)
    bonus_str = f"+{bonus}" if bonus >= 0 else f"{bonus}"
    dv_str = f"${dv_m:,.0f}M" if dv_m >= 1 else f"${dv_m:.1f}M"
    print(f"{ticker:<8} ${price:>9.2f} {signal:<18} {conf:>7.1%} {adj_ml:>5.1f} {titan_s:>5} {tier:<7} {bonus_str:>5} {combined:>6.1f} {category:<7} {dv_str:>10}")

    # 분류
    if 'Strong' in signal or 'Buy' in signal:
        if conf >= 0.7:
            strong_buy.append(r)
        elif conf >= 0.5:
            buy.append(r)
        else:
            hold.append(r)
    elif 'Hold' in signal:
        hold.append(r)
    else:
        avoid.append(r)

print("\n" + "=" * 70)
print("🎯 공격적 포트폴리오 추천 (ML 기반)")
print("=" * 70)

print(f"\n✅ Strong Buy (신뢰도 70%+): {len(strong_buy)}개")
for r in strong_buy:
    print(f"   - {r['ticker']}: ${r['price']:.2f} | {r['signal']} | 신뢰도 {r['confidence']:.1%}")

print(f"\n📈 Buy (신뢰도 50-70%): {len(buy)}개")
for r in buy:
    print(f"   - {r['ticker']}: ${r['price']:.2f} | {r['signal']} | 신뢰도 {r['confidence']:.1%}")

print(f"\n⏸️ Hold: {len(hold)}개")
for r in hold:
    print(f"   - {r['ticker']}: ${r['price']:.2f} | {r['signal']} | 신뢰도 {r['confidence']:.1%}")

print(f"\n❌ Avoid: {len(avoid)}개")
for r in avoid:
    print(f"   - {r['ticker']}: ${r['price']:.2f} | {r['signal']} | 신뢰도 {r['confidence']:.1%}")

# 포트폴리오 구성 제안
print("\n" + "=" * 70)
print("💼 균형 포트폴리오 구성 제안 (Growth + Value)")
print("=" * 70)

# 후보군: Strong Buy + Buy (Sell/Weak 제외)
portfolio_candidates = strong_buy + buy

# 섹터별 분류 (모든 종목 포함 - Titan 점수가 높으면 ML Sell이라도 후보)
growth_all = [r for r in results if r['ticker'] in GROWTH_75_PLUS]
value_all = [r for r in results if r['ticker'] in VALUE_75_PLUS]

# 복합 스코어 순 정렬 (Titan 60% + ML 40%)
growth_all.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
value_all.sort(key=lambda x: x.get('combined_score', 0), reverse=True)

print(f"\n📈 Growth 후보 ({len(growth_all)}개) [복합 스코어 순]:")
for r in growth_all[:7]:
    signal_emoji = "🚀" if r.get('adj_ml', 0) >= 65 else "📈" if r.get('adj_ml', 0) >= 50 else "➡️"
    tier = r.get('liquidity_tier', '?')
    dv_m = r.get('daily_value_m', 0)
    print(f"   {signal_emoji} {r['ticker']}: ${r['price']:.2f} | Titan {r['titan_score']} | ML {r['adj_ml']:.1f} | {tier}(${dv_m:,.0f}M/일) | 복합 {r['combined_score']:.1f}")

print(f"\n💎 Value 후보 ({len(value_all)}개) [복합 스코어 순]:")
for r in value_all[:7]:
    div_yield = r.get('dividend_yield', 0) or 0
    pe_ratio = r.get('pe_ratio', 0) or 0
    div_pct = div_yield * 100
    signal_emoji = "🚀" if r.get('adj_ml', 0) >= 65 else "📈" if r.get('adj_ml', 0) >= 50 else "➡️"
    tier = r.get('liquidity_tier', '?')
    dv_m = r.get('daily_value_m', 0)
    extra = f"PER:{pe_ratio:.1f} DIV:{div_pct:.1f}%" if pe_ratio > 0 else ""
    print(f"   {signal_emoji} {r['ticker']}: ${r['price']:.2f} | Titan {r['titan_score']} | ML {r['adj_ml']:.1f} | {tier}(${dv_m:,.0f}M/일) | 복합 {r['combined_score']:.1f} | {extra}")

# === 균형 포트폴리오 구성 ===
# Growth 2개 + Value 2개 (총 4종목)
# 안정성을 위해 Value는 최소 2개 필수 포함
growth_picks = growth_all[:2]  # Growth 상위 2개
value_picks = value_all[:2]     # Value 상위 2개

final_picks = growth_picks + value_picks

if final_picks:
    print(f"\n🏆 최종 균형 포트폴리오 (Growth 2 + Value 2):")
    print("-" * 60)

    # 비중 계산 (Growth 50%, Value 50%)
    growth_weight = 50 / len(growth_picks) if growth_picks else 0
    value_weight = 50 / len(value_picks) if value_picks else 0

    total_combined = sum(r.get('combined_score', 0) for r in final_picks)

    for r in final_picks:
        is_value = r['ticker'] in VALUE_75_PLUS
        base_weight = value_weight if is_value else growth_weight

        # 복합 스코어 기반 미세 조정 (±5%)
        combined = r.get('combined_score', 0)
        score_adj = (combined / total_combined * len(final_picks) - 1) * 5 if total_combined > 0 else 0
        weight = base_weight + score_adj

        if is_value:
            div_yield = r.get('dividend_yield', 0) or 0
            pe_ratio = r.get('pe_ratio', 0) or 0
            div_pct = div_yield * 100
            extra = f"[Value] PER:{pe_ratio:.1f} DIV:{div_pct:.1f}%"
        else:
            extra = "[Growth]"

        signal_emoji = "🚀" if r['confidence'] >= 0.65 else "📈" if r['confidence'] >= 0.5 else "➡️"
        print(f"   ⭐ {r['ticker']}: 비중 {weight:.1f}% | ${r['price']:.2f} | Titan {r['titan_score']} | ML {r['confidence']:.1%} | 복합 {combined:.1f} {extra}")

    # 포트폴리오 요약
    print(f"\n📊 포트폴리오 요약:")
    avg_combined = sum(r.get('combined_score', 0) for r in final_picks) / len(final_picks)
    avg_conf = sum(r['confidence'] for r in final_picks) / len(final_picks)
    avg_titan = sum(r.get('titan_score', 0) for r in final_picks) / len(final_picks)
    avg_div = sum((r.get('dividend_yield', 0) or 0) for r in value_picks) / len(value_picks) if value_picks else 0
    avg_div_pct = avg_div * 100
    print(f"   평균 복합 스코어: {avg_combined:.1f} (Titan {avg_titan:.0f} + ML {avg_conf:.1%})")
    print(f"   Value 평균 배당률: {avg_div_pct:.2f}%")
    print(f"   Growth/Value 비율: {len(growth_picks)*25}% / {len(value_picks)*25}%")
else:
    print("\n⚠️ 추천 가능한 종목이 없습니다. 시장 타이밍을 기다리세요.")
