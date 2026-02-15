#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROJECT TITAN - Rolling Backtest Engine
매월 리밸런싱 백테스팅 시스템
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
from project_titan import TitanAnalyzer, NASDAQ100_TICKERS, VALUE_TICKERS


class TitanBacktester:
    """Titan 전략 Rolling 백테스팅"""

    def __init__(self, start_date='2023-01-01', end_date=None, top_n=10, rebalance_freq='M'):
        """
        Args:
            start_date: 백테스트 시작일 (YYYY-MM-DD)
            end_date: 백테스트 종료일 (None이면 현재)
            top_n: 매 리밸런싱마다 선정할 종목 수
            rebalance_freq: 리밸런싱 주기 ('M': 월, 'Q': 분기)
        """
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date) if end_date else pd.Timestamp.now()
        self.top_n = top_n
        self.rebalance_freq = rebalance_freq
        self.analyzer = TitanAnalyzer()

        # 결과 저장
        self.trades = []
        self.portfolio_values = []
        self.benchmark_values = []

    def _get_rebalance_dates(self):
        """리밸런싱 날짜 리스트 생성"""
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

    def _analyze_at_date(self, tickers, analysis_date):
        """특정 날짜 시점의 데이터로 분석"""
        print(f"\n📅 분석 시점: {analysis_date.strftime('%Y-%m-%d')}")
        results = []

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)

                # 해당 날짜 이전 60일 데이터
                hist = stock.history(
                    start=analysis_date - timedelta(days=80),
                    end=analysis_date + timedelta(days=1)
                )

                if hist.empty or len(hist) < 20:
                    continue

                # 해당 시점의 info (최신 데이터 사용)
                info = stock.info

                # 분석 실행
                current_price = hist['Close'].iloc[-1]

                fund_score, fund_comments, fund_breakdown = self.analyzer._get_fundamental_score(info)
                tech_score, tech_comments, tech_breakdown = self.analyzer._get_technical_score(hist, current_price)

                contrarian_adj, contrarian_comment = self.analyzer._apply_contrarian_adjustment(
                    fund_score,
                    tech_breakdown,
                    fund_breakdown.get('sector_name', '')
                )

                total_score = fund_score + tech_score + contrarian_adj

                results.append({
                    'ticker': ticker,
                    'score': total_score,
                    'price': current_price,
                    'contrarian_adj': contrarian_adj,
                    'fund_score': fund_score,
                    'tech_score': tech_score
                })

                time.sleep(0.3)  # API 제한 회피

            except Exception as e:
                print(f"  ⚠️  {ticker} 분석 실패: {e}")
                continue

        # 점수순 정렬
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:self.top_n]

    def _calculate_period_returns(self, picks, start_date, end_date):
        """기간별 수익률 계산"""
        returns = []

        for pick in picks:
            try:
                stock = yf.Ticker(pick['ticker'])
                hist = stock.history(
                    start=start_date,
                    end=end_date + timedelta(days=1)
                )

                if len(hist) < 2:
                    returns.append(0.0)
                    continue

                start_price = hist['Close'].iloc[0]
                end_price = hist['Close'].iloc[-1]
                ret = (end_price - start_price) / start_price * 100

                returns.append(ret)

            except Exception:
                returns.append(0.0)

        return returns

    def _get_benchmark_return(self, start_date, end_date, benchmark='QQQ'):
        """벤치마크 수익률 계산"""
        try:
            bench = yf.Ticker(benchmark)
            hist = bench.history(start=start_date, end=end_date + timedelta(days=1))

            if len(hist) < 2:
                return 0.0

            start_price = hist['Close'].iloc[0]
            end_price = hist['Close'].iloc[-1]

            return (end_price - start_price) / start_price * 100

        except Exception:
            return 0.0

    def run_backtest(self, tickers):
        """백테스트 실행"""
        print("=" * 80)
        print("🔬 PROJECT TITAN - ROLLING BACKTEST")
        print("=" * 80)
        print(f"📊 종목 풀: {len(tickers)}개 (NASDAQ 100 + VALUE)")
        print(f"📅 기간: {self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}")
        print(f"🔄 리밸런싱: {self.rebalance_freq} (매월)")
        print(f"💼 포트폴리오 크기: TOP {self.top_n}")
        print("=" * 80)

        rebalance_dates = self._get_rebalance_dates()
        portfolio_value = 100.0  # 초기 자본 $100
        benchmark_value = 100.0

        for i in range(len(rebalance_dates) - 1):
            period_start = rebalance_dates[i]
            period_end = rebalance_dates[i + 1]

            print(f"\n{'='*80}")
            print(f"📊 Period {i+1}: {period_start.strftime('%Y-%m-%d')} → {period_end.strftime('%Y-%m-%d')}")
            print(f"{'='*80}")

            # 1. 해당 시점 분석 및 TOP N 선정
            picks = self._analyze_at_date(tickers, period_start)

            if not picks:
                print("⚠️  선정된 종목 없음")
                continue

            print(f"\n🎯 선정 종목 (TOP {len(picks)}):")
            for j, pick in enumerate(picks, 1):
                adj_icon = "🎯" if pick['contrarian_adj'] > 0 else "⚠️" if pick['contrarian_adj'] < 0 else "📊"
                print(f"  {j}. {pick['ticker']:6s} - {pick['score']:3.0f}점 {adj_icon} (${pick['price']:.2f})")

            # 2. 다음 리밸런싱까지 수익률 계산
            returns = self._calculate_period_returns(picks, period_start, period_end)
            avg_return = np.mean(returns) if returns else 0.0

            # 3. 포트폴리오 가치 업데이트
            portfolio_value *= (1 + avg_return / 100)

            # 4. 벤치마크 수익률
            bench_return = self._get_benchmark_return(period_start, period_end, 'QQQ')
            benchmark_value *= (1 + bench_return / 100)

            # 5. 결과 저장
            trade_record = {
                'date': period_start,
                'picks': [p['ticker'] for p in picks],
                'returns': returns,
                'avg_return': avg_return,
                'portfolio_value': portfolio_value,
                'benchmark_value': benchmark_value,
                'contrarian_count': sum(1 for p in picks if p['contrarian_adj'] > 0),
                'overheated_count': sum(1 for p in picks if p['contrarian_adj'] < 0)
            }
            self.trades.append(trade_record)

            print(f"\n📈 기간 수익률: {avg_return:+.2f}%")
            print(f"💰 포트폴리오 가치: ${portfolio_value:.2f}")
            print(f"📊 QQQ 벤치마크: ${benchmark_value:.2f}")
            print(f"🎯 역발상 종목: {trade_record['contrarian_count']}개")

            time.sleep(1)  # API 제한 회피

        # 최종 결과 계산
        return self._calculate_final_metrics()

    def _calculate_final_metrics(self):
        """최종 성과 지표 계산"""
        if not self.trades:
            return None

        # 수익률 리스트
        returns = [t['avg_return'] for t in self.trades]
        portfolio_values = [t['portfolio_value'] for t in self.trades]
        benchmark_values = [t['benchmark_value'] for t in self.trades]

        # 총 수익률
        total_return = portfolio_values[-1] - 100
        bench_return = benchmark_values[-1] - 100

        # 연환산 수익률
        years = (self.end_date - self.start_date).days / 365.25
        annual_return = ((portfolio_values[-1] / 100) ** (1 / years) - 1) * 100 if years > 0 else 0

        # 최대 낙폭 (MDD)
        peak = 100
        max_dd = 0
        for val in portfolio_values:
            if val > peak:
                peak = val
            dd = (val - peak) / peak * 100
            if dd < max_dd:
                max_dd = dd

        # 변동성 & Sharpe Ratio
        volatility = np.std(returns) if len(returns) > 1 else 0
        sharpe = (np.mean(returns) / volatility * np.sqrt(12)) if volatility > 0 else 0

        # 승률
        win_rate = sum(1 for r in returns if r > 0) / len(returns) * 100 if returns else 0

        metrics = {
            'total_return': total_return,
            'annual_return': annual_return,
            'benchmark_return': bench_return,
            'outperformance': total_return - bench_return,
            'max_drawdown': max_dd,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'win_rate': win_rate,
            'total_trades': len(self.trades),
            'avg_return_per_period': np.mean(returns),
            'final_value': portfolio_values[-1],
            'benchmark_final': benchmark_values[-1]
        }

        return metrics

    def print_summary(self, metrics):
        """결과 요약 출력"""
        if not metrics:
            print("⚠️  백테스트 결과 없음")
            return

        print("\n" + "=" * 80)
        print("📊 BACKTEST RESULTS SUMMARY")
        print("=" * 80)
        print(f"\n💰 수익률:")
        print(f"  총 수익률:        {metrics['total_return']:+.2f}%")
        print(f"  연환산 수익률:    {metrics['annual_return']:+.2f}%")
        print(f"  벤치마크 (QQQ):   {metrics['benchmark_return']:+.2f}%")
        print(f"  초과 수익:        {metrics['outperformance']:+.2f}%")

        print(f"\n📉 리스크 지표:")
        print(f"  최대 낙폭 (MDD):  {metrics['max_drawdown']:.2f}%")
        print(f"  변동성:           {metrics['volatility']:.2f}%")
        print(f"  샤프 비율:        {metrics['sharpe_ratio']:.2f}")

        print(f"\n🎯 성과 지표:")
        print(f"  승률:             {metrics['win_rate']:.1f}%")
        print(f"  총 리밸런싱:      {metrics['total_trades']}회")
        print(f"  평균 기간수익:    {metrics['avg_return_per_period']:+.2f}%")

        print(f"\n💵 최종 가치:")
        print(f"  Titan 전략:       ${metrics['final_value']:.2f} (초기 $100)")
        print(f"  QQQ 벤치마크:     ${metrics['benchmark_final']:.2f}")

        print("\n" + "=" * 80)

    def generate_html_report(self, metrics, output_file='backtest_report.html'):
        """백테스트 결과 HTML 리포트 생성"""
        if not metrics:
            print("⚠️  리포트 생성 실패: 데이터 없음")
            return

        # 성과 색상
        perf_color = '#4CAF50' if metrics['outperformance'] > 0 else '#F44336'

        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PROJECT TITAN - Backtest Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            color: #667eea;
            font-size: 2.5em;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid #667eea;
        }}
        .metric-card.highlight {{
            background: linear-gradient(135deg, {perf_color}22 0%, {perf_color}44 100%);
            border-left-color: {perf_color};
        }}
        .metric-label {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .trades-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 30px 0;
        }}
        .trades-table th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        .trades-table td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        .trades-table tr:hover {{
            background: #f5f5f5;
        }}
        .positive {{ color: #4CAF50; font-weight: bold; }}
        .negative {{ color: #F44336; font-weight: bold; }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #eee;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔬 PROJECT TITAN</h1>
            <h2>Rolling Backtest Report</h2>
            <h3>통합 포트폴리오 (NASDAQ 100 + VALUE)</h3>
            <p>{self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}</p>
        </div>

        <div class="summary">
            <div class="metric-card highlight">
                <div class="metric-label">총 수익률</div>
                <div class="metric-value" style="color: {perf_color};">{metrics['total_return']:+.2f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">연환산 수익률</div>
                <div class="metric-value">{metrics['annual_return']:+.2f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">QQQ 대비 초과수익</div>
                <div class="metric-value" style="color: {perf_color};">{metrics['outperformance']:+.2f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">샤프 비율</div>
                <div class="metric-value">{metrics['sharpe_ratio']:.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">최대 낙폭 (MDD)</div>
                <div class="metric-value">{metrics['max_drawdown']:.2f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">승률</div>
                <div class="metric-value">{metrics['win_rate']:.1f}%</div>
            </div>
        </div>

        <h3>📈 리밸런싱 내역</h3>
        <table class="trades-table">
            <thead>
                <tr>
                    <th>날짜</th>
                    <th>선정 종목</th>
                    <th>기간 수익률</th>
                    <th>누적 가치</th>
                    <th>🎯역발상</th>
                </tr>
            </thead>
            <tbody>'''

        for trade in self.trades:
            ret_class = 'positive' if trade['avg_return'] > 0 else 'negative'
            picks_str = ', '.join(trade['picks'][:5])
            if len(trade['picks']) > 5:
                picks_str += f" +{len(trade['picks'])-5}개"

            html += f'''
                <tr>
                    <td>{trade['date'].strftime('%Y-%m-%d')}</td>
                    <td>{picks_str}</td>
                    <td class="{ret_class}">{trade['avg_return']:+.2f}%</td>
                    <td>${trade['portfolio_value']:.2f}</td>
                    <td>{trade['contrarian_count']}개</td>
                </tr>'''

        html += f'''
            </tbody>
        </table>

        <div class="footer">
            <strong>PROJECT TITAN v2.0 - Backtest Engine</strong><br>
            <small>Contrarian Hybrid Strategy | Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</small>
        </div>
    </div>
</body>
</html>'''

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"\n✅ 백테스트 리포트 생성: {output_file}")


def main():
    """메인 실행 함수"""
    import sys

    # 백테스터 초기화
    backtester = TitanBacktester(
        start_date='2023-01-01',
        end_date=None,  # 현재까지
        top_n=10,
        rebalance_freq='M'
    )

    # 전체 종목 통합 (NASDAQ 100 + VALUE)
    tickers = list(set(NASDAQ100_TICKERS + VALUE_TICKERS))  # 중복 제거

    nasdaq_count = len(NASDAQ100_TICKERS)
    value_count = len(VALUE_TICKERS)
    total_count = len(tickers)

    print(f"📊 백테스트 대상: 통합 포트폴리오")
    print(f"   - NASDAQ 100: {nasdaq_count}개")
    print(f"   - VALUE: {value_count}개")
    print(f"   - 총 종목 (중복제거): {total_count}개")

    # 백테스트 실행
    metrics = backtester.run_backtest(tickers)

    # 결과 출력
    backtester.print_summary(metrics)

    # HTML 리포트 생성
    backtester.generate_html_report(metrics, 'backtest_report.html')


if __name__ == '__main__':
    main()
