# -*- coding: utf-8 -*-
"""
fundamental.py — 펀더멘탈 점수 계산 Mixin
FundamentalMixin: _get_fundamental_score, _get_trump_policy_bonus, _get_value_sector_score
"""


class FundamentalMixin:
    # ===== 섹터별 점수 - 성장주 =====
    SCORE_SECTOR_TIER1 = 10  # AI, 반도체, 클라우드, 사이버보안, 국방, 원자력
    SCORE_SECTOR_TIER2 = 8   # 소프트웨어, EV, 바이오텍, 신재생에너지, 희토류
    SCORE_SECTOR_TIER3 = 5   # 헬스케어, 산업자동화, 핀테크
    SCORE_SECTOR_TIER4 = 3   # 전통 에너지, 소비재, 유틸리티
    SCORE_SECTOR_DEFAULT = 1 # 분류 미매칭 (최소 보장)

    # ===== 섹터별 점수 - 가치주 =====
    VALUE_SECTOR_TIER1 = 10  # 필수소비재, 헬스케어 (배당귀족)
    VALUE_SECTOR_TIER2 = 8   # 유틸리티, 금융 (안정적 배당)
    VALUE_SECTOR_TIER3 = 5   # 산업재, 에너지, 부동산 (가치 섹터)
    VALUE_SECTOR_TIER4 = 3   # 기술주, 경기민감 소비재 (성장주 영역)
    VALUE_SECTOR_DEFAULT = 1 # 분류 미매칭 (최소 보장)

    # ===== 트럼프 정부 정책 방향 =====
    POLICY_BONUS = 3
    POLICY_PENALTY = -3

    # ===== 섹터별 ROE 기준 =====
    SECTOR_ROE_THRESHOLDS = {
        'Utilities': (12, 6),
        'Real Estate': (12, 5),
        'Energy': (15, 8),
        'Consumer Defensive': (20, 10),
        'Industrials': (20, 10),
        'Technology': (20, 10),
        'Healthcare': (20, 10),
        'Financial Services': (20, 10),
    }
    DEFAULT_ROE_THRESHOLD = (20, 10)

    # ===== 섹터별 매출성장률 기준 =====
    SECTOR_REVENUE_GROWTH_THRESHOLDS = {
        'Consumer Defensive': (8, 3),
        'Energy': (10, 3),
        'Utilities': (10, 5),
        'Financial Services': (10, 3),
        'Healthcare': (12, 5),
        'Industrials': (15, 8),
        'Real Estate': (10, 3),
        'Communication Services': (15, 8),
        'Consumer Cyclical': (15, 8),
        'Technology': (20, 10),
        'Basic Materials': (15, 8),
    }
    DEFAULT_REVENUE_GROWTH_THRESHOLD = (20, 10)

    # ===== 섹터별 OPM 기준 =====
    SECTOR_OPM_THRESHOLDS = {
        'Consumer Defensive': (7, 3),
        'Consumer Cyclical': (12, 6),
        'Industrials': (15, 8),
        'Energy': (15, 8),
        'Basic Materials': (15, 8),
        'Real Estate': (15, 8),
        'Communication Services': (15, 8),
        'Utilities': (15, 8),
        'Financial Services': (20, 10),
        'Healthcare': (20, 10),
        'Technology': (20, 10),
    }
    DEFAULT_OPM_THRESHOLD = (20, 10)

    # ===== 업종(industry) 레벨 OPM 오버라이드 =====
    INDUSTRY_OPM_OVERRIDES = {
        'Aerospace & Defense': (10, 5),
        'Computer Hardware': (10, 3),
        'Scientific & Technical Instruments': (10, 5),
        'Healthcare Plans': (5, 1),
    }

    # ===== 가치주 모드 전용 기준 =====
    VALUE_DIVIDEND_THRESHOLDS = {
        'Utilities': (4.0, 2.5),
        'Real Estate': (4.5, 2.5),
        'Energy': (4.0, 2.0),
        'Consumer Defensive': (3.2, 1.8),
        'Financial Services': (3.2, 1.5),
        'Industrials': (2.8, 1.2),
        'Healthcare': (2.8, 1.2),
        'Communication Services': (2.8, 1.2),
        'Consumer Cyclical': (2.5, 1.0),
        'Basic Materials': (3.5, 1.8),
        'Technology': (1.8, 0.5),
    }
    DEFAULT_VALUE_DIVIDEND_THRESHOLD = (3.5, 1.5)

    VALUE_PER_THRESHOLDS = {
        'Technology': (20, 35),
        'Healthcare': (18, 30),
        'Consumer Cyclical': (15, 25),
        'Consumer Defensive': (22, 42),
        'Financial Services': (12, 20),
        'Utilities': (18, 28),
        'Real Estate': (18, 30),
        'Energy': (12, 20),
        'Industrials': (20, 36),
        'Communication Services': (15, 25),
        'Basic Materials': (12, 20),
    }
    DEFAULT_VALUE_PER_THRESHOLD = (15, 25)

    VALUE_DE_THRESHOLDS = {
        'Financial Services': (300, 600),
        'Real Estate': (150, 300),
        'Utilities': (150, 250),
        'Communication Services': (100, 200),
        'Energy': (80, 150),
        'Healthcare': (100, 220),
        'Consumer Defensive': (150, 320),
        'Consumer Cyclical': (80, 150),
        'Industrials': (120, 260),
        'Basic Materials': (80, 150),
        'Technology': (50, 100),
    }
    DEFAULT_VALUE_DE_THRESHOLD = (80, 150)

    VALUE_EVEBITDA_THRESHOLDS = {
        'Technology':              (18, 30),
        'Healthcare':              (14, 22),
        'Consumer Defensive':      (14, 24),
        'Consumer Cyclical':       (12, 20),
        'Financial Services':      (10, 16),
        'Utilities':               (10, 16),
        'Real Estate':             (14, 22),
        'Energy':                  (7,  12),
        'Industrials':             (13, 22),
        'Communication Services':  (8,  14),
        'Basic Materials':         (8,  13),
    }
    DEFAULT_VALUE_EVEBITDA_THRESHOLD = (12, 20)

    VALUE_PB_THRESHOLDS = {
        'Financial Services': (1.2, 1.8),
        'Basic Materials': (1.8, 2.8),
        'Energy': (1.8, 2.8),
        'default': (2.5, 4.5)
    }

    # ===== 배당 귀족 (25년 이상 연속 배당 증가) =====
    DIVIDEND_ARISTOCRATS = {
        'KO', 'PEP', 'PG', 'CL', 'KMB', 'WMT', 'MCD', 'GPC',
        'JNJ', 'ABT', 'ABBV', 'MDT', 'BDX', 'SYY',
        'CAT', 'EMR', 'ITW', 'MMM', 'DOV', 'SWK', 'PH', 'GWW',
        'XOM', 'CVX',
        'AFL', 'AXP', 'MCO',
        'NUE', 'APD', 'SHW',
        'TGT', 'LOW', 'SPGI',
    }

    VALUE_BETA_THRESHOLDS = (0.8, 1.2)

    # =========================================================================

    @staticmethod
    def _calc_gradient_score(value, excellent, good, max_pts):
        """선형 보간 점수 계산 (커트라인 점프 제거)

        구간별 점수:
        - value > excellent*1.3: max_pts (만점, 확실한 우수)
        - excellent ~ excellent*1.3: max_pts*0.8 ~ max_pts (우수 구간 보간)
        - good ~ excellent: max_pts*0.4 ~ max_pts*0.8 (양호 구간 보간)
        - good*0.5 ~ good: 1 ~ max_pts*0.4 (미달이지만 인정)
        - < good*0.5: 0
        """
        if value <= 0:
            return 0

        fair = good * 0.5
        top = excellent * 1.3  # 확실한 우수 기준

        if value >= top:
            return max_pts
        elif value >= excellent:
            ratio = (value - excellent) / (top - excellent) if top > excellent else 1
            pts = max_pts * (0.8 + 0.2 * ratio)
        elif value >= good:
            ratio = (value - good) / (excellent - good) if excellent > good else 1
            pts = max_pts * (0.4 + 0.4 * ratio)
        elif value >= fair:
            ratio = (value - fair) / (good - fair) if good > fair else 1
            pts = max_pts * (0.05 + 0.35 * ratio)
        else:
            return 0

        return round(pts)

    @staticmethod
    def _calc_inverse_gradient_score(value, good_upper, fair_upper, max_pts):
        """역방향 선형 보간 (낮을수록 좋은 지표: PER, 부채비율)

        구간별 점수:
        - value <= good_upper * 0.6: max_pts (만점, 확실한 저평가)
        - good_upper*0.6 ~ good_upper: max_pts*0.8 ~ max_pts
        - good_upper ~ fair_upper: max_pts*0.4 ~ max_pts*0.8
        - fair_upper ~ fair_upper*1.5: max_pts*0.05 ~ max_pts*0.4
        - > fair_upper*1.5: 0
        """
        if value <= 0:
            return 0

        excellent = good_upper * 0.6
        poor = fair_upper * 1.5

        if value <= excellent:
            return max_pts
        elif value <= good_upper:
            ratio = (good_upper - value) / (good_upper - excellent) if good_upper > excellent else 1
            pts = max_pts * (0.8 + 0.2 * ratio)
        elif value <= fair_upper:
            ratio = (fair_upper - value) / (fair_upper - good_upper) if fair_upper > good_upper else 1
            pts = max_pts * (0.4 + 0.4 * ratio)
        elif value <= poor:
            ratio = (poor - value) / (poor - fair_upper) if poor > fair_upper else 1
            pts = max_pts * (0.05 + 0.35 * ratio)
        else:
            return 0

        return round(pts)

    def _get_fundamental_score(self, info):
        """기본적 분석 점수 (최대 50점 + 보너스)

        [가치주(Value) 평가 기준 - 총 50점 + α]
        1. 💰 배당수익률 (12점): 섹터별 기준, 배당성향(Payout Ratio) 과다 시 감점
        2. 💎 밸류에이션 (12점): PER, EV/EBITDA, PBR 중 가장 유리한 지표 채택 (우량주 프리미엄 적용)
        3. 📈 ROE (8점): 자본 효율성 (가치주는 성장주보다 비중 낮음)
        4. ⚖️ 부채비율 (8점): 재무 안정성 (낮을수록 좋음, 우량주 기준 완화)
        5. 🛡️ 섹터 (10점): 필수소비재, 헬스케어 등 방어주 우대

        [보너스 항목]
        + 📉 Beta (최대 5점): 시장 민감도 0.8 이하 시 만점 (헤징 효과)
        + 💵 FCF Yield (3점): 잉여현금흐름 5% 이상 시
        + 👑 배당귀족 (4점): 25년 이상 연속 배당 증가
        + 🏛️ 정책 수혜 (3점): 트럼프 정책 등 거시 환경 수혜"""
        score = 0
        comments = []
        breakdown = {
            'roe_score': 0, 'roe_value': 0,
            'opm_score': 0, 'opm_value': 0,
            'revenue_growth_score': 0, 'revenue_growth_value': None,
            'sector_score': 0, 'sector_name': '',
            # 가치주 전용 필드
            'dividend_yield_score': 0, 'dividend_yield_value': None,
            'per_score': 0, 'per_value': None,
            'ev_ebitda_value': None, 'valuation_method': 'PER',
            'debt_equity_score': 0, 'debt_equity_value': None,
            'fcf_score': 0,  # FCF 보너스
            'beta_score': 0, 'beta_value': None,
            'peg_score': 0, 'peg_value': None,
        }

        try:
            sector = info.get('sector', '')
            industry = info.get('industry', '')
            ticker_sym = info.get('symbol', '')

            # 주요 지표 미리 추출 (우량주 판별용)
            market_cap = info.get('marketCap', 0)
            roe = info.get('returnOnEquity')
            opm = info.get('operatingMargins')
            is_aristocrat = ticker_sym in self.DIVIDEND_ARISTOCRATS

            # ===== 가치주 모드: 배당/저평가/안정성 중심 (50점) =====
            if self.analysis_mode == 'value':

                # [우량주 프리미엄 산정] KO, PEP, COST 등 고평가 우량주 구제 로직
                premium_multiplier = 1.0
                moat_factors = []

                if market_cap >= 100_000_000_000:
                    premium_multiplier += 0.2
                    moat_factors.append("MegaCap")

                if roe and roe >= 0.20:
                    premium_multiplier += 0.2
                    moat_factors.append("HighROE")

                if is_aristocrat:
                    premium_multiplier += 0.1

                premium_multiplier = min(premium_multiplier, 1.6)

                # 1. 배당수익률 (12점)
                div_pct = None
                div_rate = info.get('dividendRate')
                price_now = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
                if div_rate and div_rate > 0 and price_now and price_now > 0:
                    div_pct = div_rate / price_now * 100
                else:
                    div_yield = info.get('dividendYield') or info.get('trailingAnnualDividendYield')
                    if div_yield and div_yield > 0:
                        div_pct = div_yield if div_yield <= 15 else div_yield / 100

                if div_pct and div_pct > 0:
                    breakdown['dividend_yield_value'] = round(div_pct, 2)
                    dy_exc, dy_good = self.VALUE_DIVIDEND_THRESHOLDS.get(
                        sector, self.DEFAULT_VALUE_DIVIDEND_THRESHOLD)
                    dy_pts = self._calc_gradient_score(div_pct, dy_exc, dy_good, 12)

                    if dy_pts < 5 and (is_aristocrat or 'MegaCap' in moat_factors):
                        dy_pts = 5

                    payout = info.get('payoutRatio')
                    if payout and payout > 1.0 and sector != 'Real Estate':
                        dy_pts = int(dy_pts * 0.7)
                        comments.append(f"배당성향{payout*100:.0f}%⚠️")

                    score += dy_pts
                    breakdown['dividend_yield_score'] = dy_pts
                    if dy_pts >= 6:
                        comments.append(f"배당{div_pct:.1f}%")

                # 2. 밸류에이션 (12점): PER vs EV/EBITDA 중 높은 쪽 채택
                per = info.get('trailingPE')
                ev_ebitda = info.get('enterpriseToEbitda')

                per_pts = 0
                if per and per > 0:
                    breakdown['per_value'] = per
                    per_good, per_fair = self.VALUE_PER_THRESHOLDS.get(
                        sector, self.DEFAULT_VALUE_PER_THRESHOLD)
                    per_good *= premium_multiplier
                    per_fair *= premium_multiplier
                    per_pts = self._calc_inverse_gradient_score(per, per_good, per_fair, 12)

                ev_pts = 0
                if ev_ebitda and ev_ebitda > 0 and sector != 'Financial Services':
                    breakdown['ev_ebitda_value'] = ev_ebitda
                    ev_good, ev_fair = self.VALUE_EVEBITDA_THRESHOLDS.get(
                        sector, self.DEFAULT_VALUE_EVEBITDA_THRESHOLD)
                    ev_good *= premium_multiplier
                    ev_fair *= premium_multiplier
                    ev_pts = self._calc_inverse_gradient_score(ev_ebitda, ev_good, ev_fair, 12)

                pb_pts = 0
                if sector in ['Financial Services', 'Basic Materials', 'Energy']:
                    pb = info.get('priceToBook')
                    if pb and pb > 0:
                        pb_good, pb_fair = self.VALUE_PB_THRESHOLDS.get(sector, self.VALUE_PB_THRESHOLDS['default'])
                        pb_good *= premium_multiplier
                        pb_fair *= premium_multiplier
                        pb_pts = self._calc_inverse_gradient_score(pb, pb_good, pb_fair, 12)

                val_pts = max(per_pts, ev_pts, pb_pts)

                if val_pts == pb_pts and pb_pts > 0:
                    breakdown['valuation_method'] = 'P/B'
                elif val_pts == ev_pts and ev_pts > 0:
                    breakdown['valuation_method'] = 'EV/EBITDA'
                else:
                    breakdown['valuation_method'] = 'PER'

                score += val_pts
                breakdown['per_score'] = val_pts
                if val_pts >= 6:
                    if ev_pts > per_pts and ev_ebitda:
                        comments.append(f"EV/EBITDA:{ev_ebitda:.1f}x")
                    elif per and per > 0:
                        comments.append(f"PER:{per:.1f}")

                # 3. ROE (8점)
                roe = info.get('returnOnEquity')
                roe_excellent, roe_good = self.SECTOR_ROE_THRESHOLDS.get(
                    sector, self.DEFAULT_ROE_THRESHOLD)
                if roe:
                    roe_pct = roe * 100
                    breakdown['roe_value'] = roe_pct
                    roe_pts = self._calc_gradient_score(roe_pct, roe_excellent, roe_good, 8)
                    score += roe_pts
                    breakdown['roe_score'] = roe_pts
                    if roe_pts >= 4:
                        comments.append(f"ROE:{roe_pct:.1f}%")

                # 4. 부채비율 D/E (8점)
                de = info.get('debtToEquity')
                if de is not None and de >= 0:
                    breakdown['debt_equity_value'] = de
                    de_good, de_fair = self.VALUE_DE_THRESHOLDS.get(
                        sector, self.DEFAULT_VALUE_DE_THRESHOLD)
                    de_good = int(de_good * premium_multiplier)
                    de_fair = int(de_fair * premium_multiplier)
                    de_pts = self._calc_inverse_gradient_score(de, de_good, de_fair, 8)
                    score += de_pts
                    breakdown['debt_equity_score'] = de_pts
                    if de_pts >= 4:
                        comments.append(f"D/E:{de:.0f}")
                elif sector in ('Financial Services', 'Real Estate'):
                    de_pts = round(8 * 0.5)
                    score += de_pts
                    breakdown['debt_equity_score'] = de_pts

                # FCF 보너스 (최대 3점)
                fcf = info.get('freeCashflow')
                if fcf and market_cap and market_cap > 0:
                    fcf_yield = fcf / market_cap
                    if fcf_yield > 0.05:
                        score += 3
                        breakdown['fcf_score'] = 3
                        if fcf_yield > 0.07:
                            comments.append("현금흐름우수")

                # 베타(Beta) 점수 (5점)
                beta = info.get('beta')
                if beta is not None:
                    breakdown['beta_value'] = beta
                    if beta <= 0.8:
                        beta_pts = 5
                        comments.append(f"LowBeta({beta:.2f})")
                    elif beta <= 1.0:
                        beta_pts = 4
                    elif beta <= 1.2:
                        beta_pts = 2
                    else:
                        beta_pts = 0
                    score += beta_pts
                    breakdown['beta_score'] = beta_pts

                # 5. 섹터 (10점)
                breakdown['sector_name'] = sector
                sector_score, sector_name, sector_comment = self._get_value_sector_score(sector, industry)
                score += sector_score
                breakdown['sector_score'] = sector_score
                breakdown['sector_name'] = sector_name
                if sector_comment:
                    comments.append(sector_comment)

                # 배당 귀족 보너스 (+4점)
                ticker_sym = info.get('symbol', '')
                if ticker_sym in self.DIVIDEND_ARISTOCRATS:
                    score += 4
                    breakdown['aristocrat_bonus'] = 4
                    comments.append("배당귀족")

                # 트럼프 정책 보너스/페널티
                policy_bonus, policy_comment = self._get_trump_policy_bonus(
                    sector, industry, sector_name)
                if policy_bonus != 0:
                    score += policy_bonus
                    breakdown['policy_bonus'] = policy_bonus
                    comments.append(policy_comment)

            # ===== 성장주 모드: ROE/OPM/매출성장 중심 (50점) =====
            else:
                # 1. ROE (15점)
                roe = info.get('returnOnEquity')
                roe_excellent, roe_good = self.SECTOR_ROE_THRESHOLDS.get(
                    sector, self.DEFAULT_ROE_THRESHOLD)
                if roe:
                    roe_pct = roe * 100
                    breakdown['roe_value'] = roe_pct
                    roe_pts = self._calc_gradient_score(roe_pct, roe_excellent, roe_good, 15)
                    score += roe_pts
                    breakdown['roe_score'] = roe_pts
                    if roe_pts >= 8:
                        comments.append(f"ROE:{roe_pct:.1f}%")

                # 2. Operating Margin (15점)
                opm = info.get('operatingMargins')
                opm_excellent, opm_good = self.INDUSTRY_OPM_OVERRIDES.get(
                    industry, self.SECTOR_OPM_THRESHOLDS.get(
                        sector, self.DEFAULT_OPM_THRESHOLD))
                if opm:
                    opm_pct = opm * 100
                    breakdown['opm_value'] = opm_pct
                    opm_pts = self._calc_gradient_score(opm_pct, opm_excellent, opm_good, 15)
                    score += opm_pts
                    breakdown['opm_score'] = opm_pts
                    if opm_pts >= 8:
                        comments.append(f"OPM:{opm_pct:.1f}%")

                # 3. Revenue Growth (10점)
                revenue_growth = info.get('revenueGrowth')
                rg_high, rg_good = self.SECTOR_REVENUE_GROWTH_THRESHOLDS.get(
                        sector, self.DEFAULT_REVENUE_GROWTH_THRESHOLD)
                if revenue_growth:
                    rg_pct = revenue_growth * 100
                    breakdown['revenue_growth_value'] = rg_pct
                    rg_pts = self._calc_gradient_score(rg_pct, rg_high, rg_good, 10)
                    score += rg_pts
                    breakdown['revenue_growth_score'] = rg_pts

                # PEG Ratio (GARP 전략)
                peg = info.get('pegRatio')
                if peg and peg > 0:
                    breakdown['peg_value'] = peg
                    if peg < 1.0:
                        score += 5
                        breakdown['peg_score'] = 5
                        comments.append(f"PEG저평가({peg:.2f})")
                    elif peg < 1.5:
                        score += 3
                        breakdown['peg_score'] = 3

                # 고성장 투자기업 보정 (매출 30%+ & ROE/OPM 적자)
                if revenue_growth and revenue_growth > 0.30:
                    roe_val = roe * 100 if roe else 0
                    opm_val = opm * 100 if opm else 0
                    if roe_val < 0 and breakdown['roe_score'] == 0:
                        growth_credit = round(15 * 0.4)
                        score += growth_credit
                        breakdown['roe_score'] = growth_credit
                        comments.append("성장투자")
                    if opm_val < 0 and breakdown['opm_score'] == 0:
                        growth_credit = round(15 * 0.4)
                        score += growth_credit
                        breakdown['opm_score'] = growth_credit

                # 4. Sector & Industry (세분화된 분류)
                breakdown['sector_name'] = f"{sector}"
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

                # Tier 3: 전통 에너지
                elif sector == 'Energy' and 'renewable' not in industry.lower():
                    score += self.SCORE_SECTOR_TIER3
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER3
                    breakdown['sector_name'] = "에너지"
                    comments.append("에너지")
                # 원자력 유틸리티 (CEG, VST 등) → TIER2
                elif sector == 'Utilities' and 'independent power' in industry.lower():
                    score += self.SCORE_SECTOR_TIER2
                    breakdown['sector_score'] = self.SCORE_SECTOR_TIER2
                    breakdown['sector_name'] = "원자력발전"
                    comments.append("원자력발전")

                # Tier 4: 소비재, 일반 유틸리티
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

                # Default
                else:
                    score += self.SCORE_SECTOR_DEFAULT
                    breakdown['sector_score'] = self.SCORE_SECTOR_DEFAULT
                    breakdown['sector_name'] = sector or "기타"

                # 트럼프 정책 보너스/페널티
                policy_bonus, policy_comment = self._get_trump_policy_bonus(
                    sector, industry, breakdown.get('sector_name', ''))
                if policy_bonus != 0:
                    score += policy_bonus
                    breakdown['policy_bonus'] = policy_bonus
                    comments.append(policy_comment)

                # 성장주 모드 섹터 적합도 스케일링
                sector_tier = breakdown.get('sector_score', 0)
                if sector_tier <= self.SCORE_SECTOR_TIER3:
                    base_scores = breakdown.get('roe_score', 0) + breakdown.get('opm_score', 0) + breakdown.get('revenue_growth_score', 0)
                    scale = 0.7 + 0.3 * (sector_tier / self.SCORE_SECTOR_TIER1)
                    scaled_base = int(base_scores * scale)
                    score -= (base_scores - scaled_base)
                    comments.append(f"비핵심섹터 조정")

        except Exception:
            pass

        return score, comments, breakdown

    def _get_trump_policy_bonus(self, sector, industry, sector_name=""):
        """트럼프 정부 거시 정책 방향에 따른 섹터 보너스/페널티"""
        ind_lower = industry.lower() if industry else ""

        # === 수혜 섹터 ===
        if sector == 'Energy' and 'renewable' not in ind_lower and 'solar' not in ind_lower:
            return self.POLICY_BONUS, "[Policy]트럼프 에너지정책 수혜"
        if any(kw in ind_lower for kw in ['aerospace', 'defense', 'military']):
            return self.POLICY_BONUS, "[Policy]트럼프 국방비증액 수혜"
        if sector == 'Financial Services' and any(kw in ind_lower for kw in ['bank', 'insurance', 'asset management', 'capital market', 'financial exchange']):
            return self.POLICY_BONUS, "[Policy]트럼프 금융규제완화 수혜"
        if sector == 'Industrials':
            return self.POLICY_BONUS, "[AIRR]인프라/리쇼어링 수혜"
        if any(kw in ind_lower for kw in ['nuclear', 'uranium', 'reactor', 'enrichment', 'smr']):
            return self.POLICY_BONUS, "[AIRR]AI전력/원자력 수혜"
        if sector == 'Utilities' and 'independent power' in ind_lower:
            return self.POLICY_BONUS, "[AIRR]AI전력/원자력 수혜"
        if any(kw in ind_lower for kw in ['rare earth', 'critical mineral', 'cobalt', 'nickel']):
            return self.POLICY_BONUS, "[Policy]트럼프 공급망안보 수혜"

        # === 역풍 섹터 ===
        if any(kw in ind_lower for kw in ['solar', 'wind', 'renewable', 'clean energy', 'hydrogen']):
            return self.POLICY_PENALTY, "[Policy]트럼프 IRA축소 역풍"
        if any(kw in ind_lower for kw in ['electric vehicle', 'ev ', 'battery', 'lithium']):
            return self.POLICY_PENALTY, "[Policy]트럼프 EV보조금삭감 역풍"

        return 0, ""

    def _get_value_sector_score(self, sector, industry):
        """가치주 모드용 섹터 점수 (배당/안정성 중심)"""
        industry_lower = industry.lower()

        # Tier 1: 필수소비재, 헬스케어
        if sector == 'Consumer Defensive':
            return self.VALUE_SECTOR_TIER1, "필수소비재", "필수소비재"
        if sector == 'Healthcare' and 'biotech' not in industry_lower:
            return self.VALUE_SECTOR_TIER1, "헬스케어", "헬스케어"

        # Tier 2: 유틸리티, 금융, 부동산
        if sector == 'Utilities':
            return self.VALUE_SECTOR_TIER2, "유틸리티", "유틸리티"
        if sector == 'Financial Services':
            return self.VALUE_SECTOR_TIER2, "금융", "금융"
        if sector == 'Real Estate':
            return self.VALUE_SECTOR_TIER2, "부동산/REITs", "부동산/REITs"

        # Tier 3: 산업재, 에너지, 통신, 소재
        if sector == 'Industrials':
            return self.VALUE_SECTOR_TIER3, "산업재", "산업재"
        if sector == 'Energy':
            return self.VALUE_SECTOR_TIER3, "에너지", "에너지"
        if sector == 'Communication Services' and any(kw in industry_lower for kw in ['telecom', 'wireless']):
            return self.VALUE_SECTOR_TIER3, "통신", "통신"
        if sector == 'Basic Materials':
            return self.VALUE_SECTOR_TIER3, "소재", "소재"

        # Tier 4: 기술주, 경기소비재
        if sector == 'Technology':
            return self.VALUE_SECTOR_TIER4, "기술주", "기술주"
        if sector == 'Consumer Cyclical':
            return self.VALUE_SECTOR_TIER4, "경기소비재", "경기소비재"
        if sector == 'Communication Services':
            return self.VALUE_SECTOR_TIER4, "미디어/엔터", "미디어/엔터"

        # 기타
        return self.VALUE_SECTOR_DEFAULT, sector if sector else "기타", sector if sector else ""
