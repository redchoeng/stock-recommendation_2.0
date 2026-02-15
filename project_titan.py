"""
Project Titan - US Stock Decision Support System
Advanced 2-Stage Filtering Analysis for NASDAQ 100, Value Stocks, and S&P 500
"""

import yfinance as yf
import pandas as pd
import time
from datetime import datetime
from tabulate import tabulate
from ta.momentum import RSIIndicator

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
    SCORE_SECTOR_PRIMARY = 20
    SCORE_SECTOR_SECONDARY = 10

    # 기술적 점수 가중치
    SCORE_MA20 = 20
    SCORE_VOLUME_SURGE = 15
    SCORE_RSI_OPTIMAL = 15
    SCORE_RSI_OVERSOLD = 5

    # RSI 임계값
    RSI_OVERSOLD = 30
    RSI_OPTIMAL_MAX = 60
    RSI_OVERBOUGHT = 70

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

        try:
            # 1. ROE
            roe = info.get('returnOnEquity')
            if roe:
                roe_pct = roe * 100
                if roe_pct > 20:
                    score += self.SCORE_ROE_EXCELLENT
                    comments.append(f"ROE:{roe_pct:.1f}%")
                elif roe_pct > 10:
                    score += self.SCORE_ROE_GOOD
                    comments.append(f"ROE:{roe_pct:.1f}%")

            # 2. Operating Margin
            opm = info.get('operatingMargins')
            if opm:
                opm_pct = opm * 100
                if opm_pct > 20:
                    score += self.SCORE_OPM_EXCELLENT
                    comments.append(f"OPM:{opm_pct:.1f}%")
                elif opm_pct > 10:
                    score += self.SCORE_OPM_GOOD

            # 3. Sector
            sector = info.get('sector', '')
            if sector in ['Technology', 'Communication Services']:
                score += self.SCORE_SECTOR_PRIMARY
                comments.append("Tech/AI섹터")
            elif sector in ['Industrials', 'Energy']:
                score += self.SCORE_SECTOR_PRIMARY
                comments.append("인프라/에너지")
            elif sector in ['Healthcare', 'Consumer Cyclical']:
                score += self.SCORE_SECTOR_SECONDARY
                comments.append("헬스케어/소비")

        except Exception:
            pass

        return score, comments

    def _get_technical_score(self, hist, current_price):
        """기술적 분석 점수 (최대 50점)"""
        score = 0
        comments = []

        try:
            if len(hist) < 20:
                return 0, ["데이터부족"]

            # 1. MA20
            ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
            if current_price > ma20:
                score += self.SCORE_MA20
                comments.append("Price>MA20")

            # 2. Volume
            avg_volume_20 = hist['Volume'].rolling(window=20).mean().iloc[-1]
            current_volume = hist['Volume'].iloc[-1]
            if current_volume > avg_volume_20 * self.VOLUME_SURGE_MULTIPLIER:
                score += self.SCORE_VOLUME_SURGE
                comments.append("고거래량")

            # 3. RSI
            rsi_indicator = RSIIndicator(close=hist['Close'], window=14)
            rsi = rsi_indicator.rsi().iloc[-1]

            if self.RSI_OVERSOLD <= rsi <= self.RSI_OPTIMAL_MAX:
                score += self.SCORE_RSI_OPTIMAL
                comments.append(f"RSI:{rsi:.0f}")
            elif rsi < self.RSI_OVERSOLD:
                score += self.SCORE_RSI_OVERSOLD
                comments.append(f"RSI:{rsi:.0f}(과매도)")
            elif rsi > self.RSI_OVERBOUGHT:
                comments.append(f"RSI:{rsi:.0f}(과열)")

        except Exception:
            pass

        return score, comments

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
        """변동성 돌파 전략 가격 계산"""
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

    def _get_current_price(self, info, hist):
        """현재가 추출"""
        return info.get('currentPrice') or info.get('regularMarketPrice') or hist['Close'].iloc[-1]

    def _analyze_single_stock(self, ticker):
        """개별 종목 분석"""
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period='60d')

        if hist.empty or len(hist) < 20:
            return None

        # 현재가
        current_price = self._get_current_price(info, hist)

        # 점수 계산
        fund_score, fund_comments = self._get_fundamental_score(info)
        tech_score, tech_comments = self._get_technical_score(hist, current_price)
        total_score = fund_score + tech_score

        # 가격 계산
        breakout, target, stop_loss = self._calculate_volatility_breakout(hist)

        # Verdict
        verdict = self._get_verdict(total_score)

        # 코멘트 조합
        all_comments = fund_comments + tech_comments
        comment = ", ".join(all_comments[:3]) if all_comments else "-"

        return {
            'ticker': ticker,
            'score': total_score,
            'verdict': verdict,
            'price': current_price,
            'breakout': breakout,
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

            html += f'''
        <div class="stock-card">
            <div class="rank">#{i}</div>
            <span class="score-badge {score_class}">{stock['score']}점</span>
            <h2><span class="ticker">{stock['ticker']}</span></h2>
            <span class="verdict {verdict_class}">{stock['verdict']}</span>
            <div class="info">
                <div class="info-item">
                    <div class="info-label">현재가</div>
                    <div class="info-value">${stock['price']:.2f}</div>
                </div>'''

            if stock['breakout']:
                html += f'''
                <div class="info-item">
                    <div class="info-label">매수 신호가</div>
                    <div class="info-value">${stock['breakout']:.2f}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">목표가</div>
                    <div class="info-value">${stock['target']:.2f}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">손절가</div>
                    <div class="info-value">${stock['stop_loss']:.2f}</div>
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
            <small>Powered by Titan v2.0 | Fundamental (ROE, OPM, Sector) + Technical (MA20, RSI, Volume) + Volatility Breakout</small>
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