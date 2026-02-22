# -*- coding: utf-8 -*-
"""
project_titan.py — TitanAnalyzer 핵심 파이프라인
(펀더멘탈/기술/전략/리포터는 각 Mixin 모듈에서 로드)
"""
import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import pytz
import yfinance as yf

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None

from config import GROWTH_TICKERS, VALUE_TICKERS
from fundamental import FundamentalMixin
from technical import TechnicalMixin
from strategy import StrategyMixin
from reporter import ReporterMixin
from notifier import send_push_alert, _fetch_user_holding_tickers


class TitanAnalyzer(FundamentalMixin, TechnicalMixin, StrategyMixin, ReporterMixin):
    """Titan 주식 분석 엔진 — Mixin 패턴으로 기능 분리"""

    MIN_MARKET_CAP = 10_000_000_000   # 최소 시총 $10B
    MIN_PRICE = 5.0                    # 최소 주가
    MIN_AVG_VOLUME = 1_000_000         # 최소 평균 거래량

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
    def _meets_stage1_criteria(self, info, min_market_cap=None):
        """1단계 필터 조건 충족 여부 확인"""
        threshold = min_market_cap if min_market_cap is not None else self.MIN_MARKET_CAP
        market_cap = info.get('marketCap', 0)
        current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
        avg_volume = info.get('averageVolume', 0)

        return (market_cap and market_cap > threshold and
                current_price and current_price > self.MIN_PRICE and
                avg_volume and avg_volume > self.MIN_AVG_VOLUME)

    def _print_progress(self, current, total, interval=50):
        """진행 상황 출력"""
        if current % interval == 0 or current == total:
            print(f"진행: {current}/{total} ({current/total*100:.1f}%)")

    def stage1_quick_filter(self, tickers, min_market_cap=None):
        """1단계: 빠른 스크리닝 (시가총액, 거래량, 가격)"""
        threshold = min_market_cap if min_market_cap is not None else self.MIN_MARKET_CAP
        print("=" * 70)
        print(f"🔍 STAGE 1: 빠른 스크리닝 (시가총액 > ${threshold/1e9:.0f}B, "
              f"거래량 > {self.MIN_AVG_VOLUME/1e6:.0f}M, 가격 > ${self.MIN_PRICE})")
        print("=" * 70)

        filtered = []
        total = len(tickers)

        for i, ticker in enumerate(tickers, 1):
            try:
                self._print_progress(i, total)

                stock = yf.Ticker(ticker)
                info = stock.info

                if self._meets_stage1_criteria(info, min_market_cap=threshold):
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

    def _analyze_single_stock(self, ticker, spy_hist=None):
        """개별 종목 분석"""
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period='1y')  # 전문가급 분석용 1년 데이터

        if hist.empty or len(hist) < 20:
            return None

        # 현재가
        current_price = self._get_current_price(info, hist)

        # 점수 계산 (SPY 히스토리 전달하여 상대강도 계산)
        fund_score, fund_comments, fund_breakdown = self._get_fundamental_score(info)
        tech_score, tech_comments, tech_breakdown = self._get_technical_score(hist, current_price, spy_hist=spy_hist)

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

        # 🌍 시장 상태 감지 (VIX 포함)
        print("\n🌍 시장 상태 감지 중...")
        market_regime, regime_details, regime_desc, spy_hist = self._detect_market_regime()
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

                result = self._analyze_single_stock(ticker, spy_hist=spy_hist)
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

    def run_analysis_with_tickers(self, tickers, report_type="Analysis", html_filename=None, min_score=50, skip_stage1=True, min_market_cap=0):
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
            filtered_tickers = self.stage1_quick_filter(tickers, min_market_cap=min_market_cap)
            if not filtered_tickers:
                print("❌ 1단계 필터를 통과한 종목이 없습니다.")
                return []
            results = self.stage2_deep_analysis(filtered_tickers)

        # 시총 필터 (skip_stage1=True일 때도 적용)
        if min_market_cap and min_market_cap > 0:
            before = len(results)
            results = [r for r in results if r.get('market_cap', 0) >= min_market_cap]
            print(f"🏦 시총 필터 (≥${min_market_cap/1e9:.0f}B): {before}개 → {len(results)}개")

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
                'peg_value': fund_bd.get('peg_value'),
                'fcf_margin_value': fund_bd.get('fcf_margin_value'),
                'fcf_score': fund_bd.get('fcf_score', 0),
                'rs_score': tech_bd.get('rs_score', 0),
                'rs_ratio': tech_bd.get('rs_ratio', 0),
                'dividend_yield_value': fund_bd.get('dividend_yield_value'),
                'per_value': fund_bd.get('per_value'),
                'ev_ebitda_value': fund_bd.get('ev_ebitda_value'),
                'valuation_method': fund_bd.get('valuation_method', 'PER'),
                'debt_equity_value': fund_bd.get('debt_equity_value'),
                'rsi_value': tech_bd.get('rsi_value'),
                'ma5': tech_bd.get('ma5'),
                'ma20': tech_bd.get('ma20'),
                'ma60': tech_bd.get('ma60'),
                'ma120': tech_bd.get('ma120'),
                'atr_value': tech_bd.get('atr_value'), # [추가] 리스크 패리티용 ATR
                'mfi_value': tech_bd.get('mfi_value'),
                'analyst_comment': r.get('analyst_comment', ''),
                'analyst_data': r.get('analyst_data', {}),
            }
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
        print(f"💾 Titan 점수 캐시 저장: {cache_file} ({len(cache)}개 종목)")

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
                min_score=80,
                skip_stage1=False,  # Stage 1 활성화 (분석 시간 단축)
                min_market_cap=50_000_000_000,  # $50B 이상만 (헤징 안정성 강화)
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