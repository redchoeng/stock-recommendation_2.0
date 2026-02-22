#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROJECT TITAN - Rolling Backtest Engine (Claude 이상안 호환)
매월 리밸런싱 백테스팅 시스템
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
import sys

from project_titan import TitanAnalyzer
from config import GROWTH_TICKERS


class TitanBacktester:
    """Titan 전략 Rolling 백테스팅"""

    def __init__(self, start_date='2024-06-01', end_date=None, top_n=10, rebalance_freq='M'):
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date) if end_date else pd.Timestamp.now()
        self.top_n = top_n
        self.rebalance_freq = rebalance_freq
        self.analyzer = TitanAnalyzer()
        self.trades = []

    def _get_rebalance_dates(self):
        dates = []
        current = self.start_date
        while current <= self.end_date:
            dates.append(current)
            if self.rebalance_freq == 'M':
                current += relativedelta(months=1)
            elif self.rebalance_freq == 'Q':
                current += relativedelta(months=3)
            else:
                current += relativedelta(months=1)
        return dates

    def _get_spy_hist(self, analysis_date):
        """SPY 히스토리 가져오기 (상대강도 계산용)"""
        try:
            spy = yf.Ticker('^GSPC')
            hist = spy.history(
                start=analysis_date - timedelta(days=400),
                end=analysis_date + timedelta(days=1)
            )
            return hist if not hist.empty else None
        except Exception:
            return None

    def _analyze_at_date(self, tickers, analysis_date, spy_hist=None):
        """특정 날짜 시점의 데이터로 분석"""
        print(f"\n  📅 분석 시점: {analysis_date.strftime('%Y-%m-%d')}")
        results = []
        analyzed = 0

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)

                # 1년치 데이터 (MA120, 52주 고저 등에 필요)
                hist = stock.history(
                    start=analysis_date - timedelta(days=400),
                    end=analysis_date + timedelta(days=1)
                )

                if hist.empty or len(hist) < 120:
                    continue

                info = stock.info
                current_price = hist['Close'].iloc[-1]

                fund_score, fund_comments, fund_breakdown = self.analyzer._get_fundamental_score(info)
                tech_score, tech_comments, tech_breakdown = self.analyzer._get_technical_score(
                    hist, current_price, spy_hist=spy_hist
                )

                contrarian_adj, _ = self.analyzer._apply_contrarian_adjustment(
                    fund_score,
                    tech_breakdown,
                    fund_breakdown.get('sector_name', '')
                )

                total_score = fund_score + tech_score + contrarian_adj

                # 섹터 순환매 보너스는 현재 시점 기준으로만 적용 가능 (과거 ETF 데이터 한계)
                sector = info.get('sector', '')
                rotation_info = getattr(self.analyzer, 'sector_rotation', {}).get(sector, {})
                rotation_bonus = rotation_info.get('rotation_bonus', 0)
                total_score += rotation_bonus

                # 유동성 보너스
                avg_vol = info.get('averageVolume', 0)
                daily_value = avg_vol * current_price
                if daily_value >= 1_000_000_000:
                    liq_bonus = 5
                elif daily_value >= 300_000_000:
                    liq_bonus = 3
                elif daily_value >= 100_000_000:
                    liq_bonus = 0
                else:
                    liq_bonus = -3
                total_score += liq_bonus

                results.append({
                    'ticker': ticker,
                    'score': total_score,
                    'price': current_price,
                    'contrarian_adj': contrarian_adj,
                    'fund_score': fund_score,
                    'tech_score': tech_score,
                    'sector': fund_breakdown.get('sector_name', ''),
                })

                analyzed += 1
                if analyzed % 20 == 0:
                    print(f"    진행: {analyzed}/{len(tickers)}")

                time.sleep(0.3)

            except Exception as e:
                continue

        results.sort(key=lambda x: x['score'], reverse=True)
        print(f"    분석 완료: {analyzed}개 → TOP {min(self.top_n, len(results))} 선정")
        return results[:self.top_n]

    def _calculate_period_returns(self, picks, start_date, end_date):
        """기간별 수익률 계산"""
        returns = []
        for pick in picks:
            try:
                stock = yf.Ticker(pick['ticker'])
                hist = stock.history(start=start_date, end=end_date + timedelta(days=1))
                if len(hist) < 2:
                    returns.append(0.0)
                    continue
                ret = (hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0] * 100
                returns.append(ret)
            except Exception:
                returns.append(0.0)
        return returns

    def _get_benchmark_return(self, start_date, end_date, benchmark='QQQ'):
        try:
            bench = yf.Ticker(benchmark)
            hist = bench.history(start=start_date, end=end_date + timedelta(days=1))
            if len(hist) < 2:
                return 0.0
            return (hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0] * 100
        except Exception:
            return 0.0

    def run_backtest(self, tickers):
        """백테스트 실행"""
        print("=" * 80)
        print("🔬 PROJECT TITAN - ROLLING BACKTEST (Claude 이상안)")
        print("=" * 80)
        print(f"📊 종목 풀: {len(tickers)}개")
        print(f"📅 기간: {self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}")
        print(f"🔄 리밸런싱: 매월")
        print(f"💼 포트폴리오: TOP {self.top_n}")
        print("=" * 80)

        # 섹터 순환매 분석 (현재 시점 기준 1회)
        print("\n🔄 섹터 순환매 분석 중...")
        self.analyzer.sector_rotation = self.analyzer._analyze_sector_rotation()

        rebalance_dates = self._get_rebalance_dates()
        portfolio_value = 100.0
        benchmark_value = 100.0

        for i in range(len(rebalance_dates) - 1):
            period_start = rebalance_dates[i]
            period_end = rebalance_dates[i + 1]

            print(f"\n{'='*80}")
            print(f"📊 Period {i+1}/{len(rebalance_dates)-1}: "
                  f"{period_start.strftime('%Y-%m-%d')} → {period_end.strftime('%Y-%m-%d')}")

            # SPY 히스토리 가져오기
            spy_hist = self._get_spy_hist(period_start)

            # TOP N 선정
            picks = self._analyze_at_date(tickers, period_start, spy_hist=spy_hist)
            if not picks:
                print("  ⚠️ 선정 종목 없음")
                continue

            print(f"\n  🎯 선정 종목:")
            for j, pick in enumerate(picks, 1):
                icon = "🎯" if pick['contrarian_adj'] > 0 else "⚠️" if pick['contrarian_adj'] < 0 else "📊"
                print(f"    {j}. {pick['ticker']:6s} {pick['score']:3.0f}점 {icon} "
                      f"(${pick['price']:.2f}) [{pick['sector']}]")

            # 수익률 계산
            returns = self._calculate_period_returns(picks, period_start, period_end)
            avg_return = np.mean(returns) if returns else 0.0
            portfolio_value *= (1 + avg_return / 100)

            bench_return = self._get_benchmark_return(period_start, period_end, 'QQQ')
            benchmark_value *= (1 + bench_return / 100)

            # 개별 종목 수익률 출력
            print(f"\n  📈 개별 수익률:")
            for pick, ret in zip(picks, returns):
                ret_icon = "🟢" if ret > 0 else "🔴"
                print(f"    {ret_icon} {pick['ticker']:6s} {ret:+.1f}%")

            self.trades.append({
                'date': period_start,
                'picks': [p['ticker'] for p in picks],
                'scores': [p['score'] for p in picks],
                'returns': returns,
                'avg_return': avg_return,
                'portfolio_value': portfolio_value,
                'benchmark_value': benchmark_value,
                'bench_return': bench_return,
                'contrarian_count': sum(1 for p in picks if p['contrarian_adj'] > 0),
            })

            print(f"\n  💰 기간수익: Titan {avg_return:+.2f}% vs QQQ {bench_return:+.2f}%")
            print(f"  💵 누적가치: Titan ${portfolio_value:.2f} vs QQQ ${benchmark_value:.2f}")

            time.sleep(1)

        return self._calculate_final_metrics()

    def _calculate_final_metrics(self):
        if not self.trades:
            return None

        returns = [t['avg_return'] for t in self.trades]
        p_vals = [t['portfolio_value'] for t in self.trades]
        b_vals = [t['benchmark_value'] for t in self.trades]

        total_return = p_vals[-1] - 100
        bench_return = b_vals[-1] - 100

        years = (self.end_date - self.start_date).days / 365.25
        annual_return = ((p_vals[-1] / 100) ** (1 / years) - 1) * 100 if years > 0 else 0

        # MDD
        peak = 100
        max_dd = 0
        for val in p_vals:
            if val > peak:
                peak = val
            dd = (val - peak) / peak * 100
            if dd < max_dd:
                max_dd = dd

        volatility = np.std(returns) if len(returns) > 1 else 0
        sharpe = (np.mean(returns) / volatility * np.sqrt(12)) if volatility > 0 else 0
        win_rate = sum(1 for r in returns if r > 0) / len(returns) * 100 if returns else 0

        # 벤치마크 대비 승률
        outperform_months = sum(1 for t in self.trades if t['avg_return'] > t['bench_return'])
        outperform_rate = outperform_months / len(self.trades) * 100 if self.trades else 0

        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'benchmark_return': bench_return,
            'outperformance': total_return - bench_return,
            'max_drawdown': max_dd,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'win_rate': win_rate,
            'outperform_rate': outperform_rate,
            'total_trades': len(self.trades),
            'avg_return_per_period': np.mean(returns),
            'final_value': p_vals[-1],
            'benchmark_final': b_vals[-1]
        }

    def print_summary(self, metrics):
        if not metrics:
            print("⚠️  백테스트 결과 없음")
            return

        alpha = metrics['outperformance']
        verdict = "OUTPERFORM ✅" if alpha > 0 else "UNDERPERFORM ❌"

        print("\n" + "=" * 80)
        print("📊 BACKTEST RESULTS — Claude 이상안 (고정티어 제거 + 순환매 확대)")
        print("=" * 80)

        print(f"\n💰 수익률:")
        print(f"  Titan 총수익:     {metrics['total_return']:+.2f}%")
        print(f"  QQQ 벤치마크:     {metrics['benchmark_return']:+.2f}%")
        print(f"  초과수익(Alpha):  {metrics['outperformance']:+.2f}% → {verdict}")
        print(f"  연환산 수익률:    {metrics['annual_return']:+.2f}%")

        print(f"\n📉 리스크:")
        print(f"  최대낙폭(MDD):    {metrics['max_drawdown']:.2f}%")
        print(f"  월간 변동성:      {metrics['volatility']:.2f}%")
        print(f"  샤프비율:         {metrics['sharpe_ratio']:.2f}")

        print(f"\n🎯 성과:")
        print(f"  월간 승률:        {metrics['win_rate']:.1f}%")
        print(f"  QQQ 대비 승률:    {metrics['outperform_rate']:.1f}%")
        print(f"  총 리밸런싱:      {metrics['total_trades']}회")
        print(f"  평균 월수익:      {metrics['avg_return_per_period']:+.2f}%")

        print(f"\n💵 최종 ($100 시작):")
        print(f"  Titan:  ${metrics['final_value']:.2f}")
        print(f"  QQQ:    ${metrics['benchmark_final']:.2f}")

        print("\n" + "=" * 80)


def main():
    sys.stdout.reconfigure(encoding='utf-8')

    # 최근 8개월 백테스트 (2024-06 ~ 2025-02)
    backtester = TitanBacktester(
        start_date='2024-06-01',
        end_date='2025-02-01',
        top_n=10,
        rebalance_freq='M'
    )

    # 성장주 풀에서 대표 50개로 제한 (속도)
    # 시총 상위 + 다양한 섹터 커버
    test_tickers = [
        # 반도체
        'NVDA', 'AMD', 'AVGO', 'LRCX', 'AMAT', 'KLAC', 'QCOM', 'MU',
        # 소프트웨어/클라우드
        'MSFT', 'ORCL', 'CRM', 'NOW', 'ADBE', 'PANW', 'CRWD', 'FTNT',
        # 빅테크/플랫폼
        'AAPL', 'GOOGL', 'META', 'AMZN', 'NFLX',
        # 핀테크
        'V', 'MA', 'PYPL',
        # AI/데이터
        'PLTR', 'SNOW', 'DDOG',
        # 하드웨어
        'ANET', 'DELL', 'SMCI', 'WDC', 'PSTG',
        # 헬스케어
        'LLY', 'ISRG', 'VRTX', 'REGN', 'DXCM',
        # 이커머스/소비재
        'TSLA', 'ABNB', 'BKNG', 'MELI', 'SHOP',
        # 산업재/에너지
        'GEV', 'VRSK',
        # 기타
        'INTU', 'CDNS', 'SNPS', 'TTD',
    ]

    print(f"📊 백테스트 대상: 성장주 대표 {len(test_tickers)}개")
    metrics = backtester.run_backtest(test_tickers)
    backtester.print_summary(metrics)


if __name__ == '__main__':
    main()
