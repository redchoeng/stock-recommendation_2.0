# -*- coding: utf-8 -*-
"""
reporter.py — HTML 리포트 생성 Mixin
ReporterMixin: display_results, _get_current_market_status,
               generate_html_report, generate_portfolio_html, generate_changelog_html
"""
import os
import json
import re
from datetime import datetime
from tabulate import tabulate


class ReporterMixin:
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

        # 이전 순위 로드 (순위 변화 표시용)
        import json as _jcache
        _cache_type = 'growth' if 'Growth' in report_type else 'value'
        _prev_cache_file = f"titan_scores_{_cache_type}.json"
        prev_ranks = {}
        try:
            with open(_prev_cache_file) as _f:
                _prev_data = _jcache.load(_f)
            _prev_sorted = sorted(_prev_data.items(), key=lambda x: x[1].get('score', 0), reverse=True)
            for _ri, (_tk, _) in enumerate(_prev_sorted, 1):
                prev_ranks[_tk] = _ri
        except Exception:
            pass

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
    <script>(function(){{const t=localStorage.getItem('titan_theme');if(t==='dark')document.documentElement.setAttribute('data-theme','dark');}})()</script>
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
            --green-bg: #e6fcf5;
            --red: #f06595;
            --red-bg: #fff0f6;
            --orange: #fd7e14;
            --radius: 16px;
            --shadow: 0 2px 8px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
            --shadow-hover: 0 8px 24px rgba(0,0,0,0.08);
        }}
        [data-theme="dark"] {{
            --bg: #0f1117;
            --surface: #1a1d27;
            --text: #e4e8f0;
            --text-sub: #7a8494;
            --text-muted: #4a5060;
            --border: #252836;
            --accent-light: {('#0d1f3a' if '5BA3E0' in primary_color else '#2a1f08' if 'E8A838' in primary_color else '#1e1730')};
            --green-bg: #0b2520;
            --red-bg: #2b0e1c;
            --shadow: 0 2px 8px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2);
            --shadow-hover: 0 8px 24px rgba(0,0,0,0.45);
        }}
        .theme-toggle {{
            background: var(--surface); border: none; border-radius: 10px;
            box-shadow: var(--shadow); cursor: pointer; font-size: 1.05em;
            width: 34px; height: 34px; display: flex; align-items: center;
            justify-content: center; transition: box-shadow 0.2s; flex-shrink: 0;
        }}
        .theme-toggle:hover {{ box-shadow: var(--shadow-hover); }}
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
        .rank-change {{
            position: absolute; top: 52px; left: 12px;
            font-size: 0.72em; font-weight: 700; border-radius: 6px;
            padding: 1px 6px; white-space: nowrap;
        }}
        .rank-change.up {{ color: #2f9e44; background: #d3f9d8; }}
        .rank-change.down {{ color: #c92a2a; background: #ffe3e3; }}
        .rank-change.new {{ color: #1971c2; background: #dbe4ff; }}
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
        <div style="display:flex; align-items:center; justify-content:center; gap:8px; margin-bottom:20px;">
            <div class="market-switcher" style="margin-bottom:0;">
                <span class="market-btn active">US</span>
                <a href="https://redchoeng.github.io/stock-recommendation_kr/" class="market-btn">KR</a>
            </div>
            <button class="theme-toggle" id="themeToggle" onclick="toggleTheme()" title="다크모드 전환">🌙</button>
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
            prev_close = market_info.get('previous_close', 0)
            regular_price = stock['price']
            pre_market_price = market_info.get('pre_market_price') or 0
            post_market_price = market_info.get('post_market_price') or 0
            display_price = market_info.get('display_price', regular_price)

            # 변동률은 폐장 기준(전일대비)으로 기본 계산, JS가 시장 상태별로 재계산
            change_pct = ((regular_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
            change_color = '#4CAF50' if change_pct >= 0 else '#F44336'
            change_sign = '+' if change_pct >= 0 else ''

            _pre_attr = f'data-pre-market="{pre_market_price:.2f}"' if pre_market_price else ''
            _post_attr = f'data-post-market="{post_market_price:.2f}"' if post_market_price else ''

            price_html = f'''
            <div class="info">
                <div class="info-item market-status-box" style="background: #607D8B; color: white;"
                     data-regular="{regular_price:.2f}"
                     data-prev-close="{prev_close:.2f}"
                     {_pre_attr} {_post_attr}>
                    <div class="info-label market-status-label" style="color: rgba(255,255,255,0.9);">🌙 폐장</div>
                    <div class="info-value market-status-price" style="font-size: 1.2em;">${regular_price:.2f}</div>
                </div>
                <div class="info-item market-change-box">
                    <div class="info-label">전일대비</div>
                    <div class="info-value market-change-value" style="color: {change_color}; font-weight: bold;">{change_sign}{change_pct:.2f}%</div>
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

            _prev_rank = prev_ranks.get(stock['ticker'])
            if _prev_rank is None:
                _rank_change_html = '<span class="rank-change new">NEW</span>'
            else:
                _diff = _prev_rank - i
                if _diff > 0:
                    _rank_change_html = f'<span class="rank-change up">▲{_diff}</span>'
                elif _diff < 0:
                    _rank_change_html = f'<span class="rank-change down">▼{abs(_diff)}</span>'
                else:
                    _rank_change_html = ''

            html += f'''
        <div class="stock-card">
            <div class="rank">#{i}</div>
            {_rank_change_html}
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
                            <span class="criterion-value">{(fund_bd.get('dividend_yield_value') or 0):.2f}%</span>
                            <span class="criterion-score">+{fund_bd.get('dividend_yield_score', 0)}점</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">{"EV/EBITDA" if fund_bd.get("valuation_method") == "EV/EBITDA" else "PER"} (저평가)</span>
                            <span class="criterion-value">{fund_bd.get("valuation_method")} 지표 사용</span>
                            <span class="criterion-score">+{fund_bd.get('per_score', 0)}점</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">ROE (수익성)</span>
                            <span class="criterion-value">{(fund_bd.get('roe_value') or 0):.1f}%</span>
                            <span class="criterion-score">+{fund_bd.get('roe_score', 0)}점</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">부채비율 (D/E)</span>
                            <span class="criterion-value">{"N/A" if fund_bd.get('debt_equity_value') is None else f"{(fund_bd.get('debt_equity_value') or 0):.0f}%"}</span>
                            <span class="criterion-score">+{fund_bd.get('debt_equity_score', 0)}점</span>
                        </div>''' if is_value_mode else f'''
                        <div class="breakdown-item">
                            <span class="criterion">Beta (시장민감도)</span>
                            <span class="criterion-value">{(fund_bd.get('beta_value') or 0):.2f}</span>
                            <span class="criterion-score">+{fund_bd.get('beta_score', 0)}점</span>
                        </div>''' if is_value_mode else f'''
                        <div class="breakdown-item">
                            <span class="criterion">ROE (자기자본이익률)</span>
                            <span class="criterion-value">{(fund_bd.get('roe_value') or 0):.1f}%</span>
                            <span class="criterion-score">+{fund_bd.get('roe_score', 0)}점</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">OPM (영업이익률)</span>
                            <span class="criterion-value">{(fund_bd.get('opm_value') or 0):.1f}%</span>
                            <span class="criterion-score">+{fund_bd.get('opm_score', 0)}점</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">매출성장률</span>
                            <span class="criterion-value">{rg_display}</span>
                            <span class="criterion-score">+{fund_bd.get('revenue_growth_score', 0)}점</span>
                        </div>''') + f'''
                        <div class="breakdown-item">
                            <span class="criterion">PEG (성장가치)</span>
                            <span class="criterion-value">{(fund_bd.get('peg_value') or 0):.2f}</span>
                            <span class="criterion-score">+{fund_bd.get('peg_score', 0)}점</span>
                        </div>
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
                            <span class="criterion-value">RSI:{(tech_bd.get('rsi_value') or 0):.0f}, MFI:{(tech_bd.get('mfi_value') or 0):.0f}</span>
                            <span class="criterion-score">+{tech_bd.get('momentum_score', 0)}점</span>
                        </div>
                        <!-- 거래량 -->
                        <div class="breakdown-item" style="background: rgba(255, 152, 0, 0.05);">
                            <span class="criterion">📊 거래량</span>
                            <span class="criterion-value">{(tech_bd.get('volume_ratio') or 0):.1f}x, OBV</span>
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
    (function(){{
    const saved = localStorage.getItem('titan_theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
    const btn = document.getElementById('themeToggle');
    if (btn) btn.textContent = saved === 'dark' ? '☀️' : '🌙';
    }})();
    function toggleTheme() {{
    const cur = document.documentElement.getAttribute('data-theme') || 'light';
    const next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('titan_theme', next);
    document.getElementById('themeToggle').textContent = next === 'dark' ? '☀️' : '🌙';
    }}

    // 시장 상태 동적 판별 (클라이언트 ET 시간 기준)
    (function updateMarketStatus() {{
        var now = new Date();
        // ET 시간 계산 (UTC offset: EST=-5, EDT=-4)
        var utc = now.getTime() + now.getTimezoneOffset() * 60000;
        // US Eastern: 1월~3월 둘째 일요일 = EST(-5), 이후~11월 첫째 일요일 = EDT(-4)
        var jan1 = new Date(now.getFullYear(), 0, 1);
        var jul1 = new Date(now.getFullYear(), 6, 1);
        var stdOff = Math.max(jan1.getTimezoneOffset(), jul1.getTimezoneOffset());
        // ET offset in ms: -5h (EST) or -4h (EDT)
        var etNow = new Date(utc + (-5) * 3600000);
        // DST check: 3월 둘째 일요일 ~ 11월 첫째 일요일
        var mar = new Date(now.getFullYear(), 2, 1);
        var marSun2 = new Date(mar.getTime() + ((14 - mar.getDay()) % 7 + 7) * 86400000);
        var nov = new Date(now.getFullYear(), 10, 1);
        var novSun1 = new Date(nov.getTime() + ((7 - nov.getDay()) % 7) * 86400000);
        var utcDate = new Date(utc);
        if (utcDate >= marSun2 && utcDate < novSun1) {{
            etNow = new Date(utc + (-4) * 3600000);
        }}

        var day = etNow.getDay(); // 0=Sun, 6=Sat
        var h = etNow.getHours();
        var m = etNow.getMinutes();
        var timeMin = h * 60 + m;

        var status;
        if (day === 0 || day === 6) {{
            status = 'closed';
        }} else if (timeMin >= 240 && timeMin < 570) {{
            status = 'pre';       // 4:00 AM ~ 9:30 AM ET
        }} else if (timeMin >= 570 && timeMin < 960) {{
            status = 'regular';   // 9:30 AM ~ 4:00 PM ET
        }} else if (timeMin >= 960 && timeMin < 1200) {{
            status = 'after';     // 4:00 PM ~ 8:00 PM ET
        }} else {{
            status = 'closed';
        }}

        var statusMap = {{
            pre:     {{ color: '#FF9800', label: '🌅 프리마켓' }},
            regular: {{ color: '#4CAF50', label: '☀️ 정규장' }},
            after:   {{ color: '#9C27B0', label: '🌙 애프터장' }},
            closed:  {{ color: '#607D8B', label: '🌙 폐장' }}
        }};
        var info = statusMap[status];

        var boxes = document.querySelectorAll('.market-status-box');
        boxes.forEach(function(box) {{
            box.style.background = info.color;
            var label = box.querySelector('.market-status-label');
            var priceEl = box.querySelector('.market-status-price');
            if (label) label.textContent = info.label;

            var regular = parseFloat(box.dataset.regular) || 0;
            var prevClose = parseFloat(box.dataset.prevClose) || 0;
            var preMkt = parseFloat(box.dataset.preMarket) || 0;
            var postMkt = parseFloat(box.dataset.postMarket) || 0;

            var displayPrice = regular;
            var basePrice = prevClose;
            if (status === 'pre' && preMkt > 0) {{
                displayPrice = preMkt;
                basePrice = prevClose;
            }} else if (status === 'after' && postMkt > 0) {{
                displayPrice = postMkt;
                basePrice = regular;
            }} else if (status === 'after') {{
                basePrice = regular;
            }}

            if (priceEl) priceEl.textContent = '$' + displayPrice.toFixed(2);

            var changeBox = box.parentElement.querySelector('.market-change-box');
            if (changeBox && basePrice > 0) {{
                var pct = ((displayPrice - basePrice) / basePrice * 100);
                var sign = pct >= 0 ? '+' : '';
                var color = pct >= 0 ? '#4CAF50' : '#F44336';
                var valEl = changeBox.querySelector('.market-change-value');
                if (valEl) {{
                    valEl.textContent = sign + pct.toFixed(2) + '%';
                    valEl.style.color = color;
                }}
            }}
        }});
    }})();
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

