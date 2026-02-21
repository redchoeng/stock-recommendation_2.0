# Project Titan v2.0 — AI 가이드

> 다른 AI가 이 프로젝트를 이어받을 때 참고하는 문서입니다.

---

## 개요

미국 주식 자동 분석 시스템. GitHub Actions로 하루 10회 자동 실행 → GitHub Pages에 HTML 리포트 배포.

- **GitHub**: `redchoeng/stock-recommendation_2.0`
- **Pages URL**: `https://redchoeng.github.io/stock-recommendation_2.0/`
- **KR 버전**: `redchoeng/stock-recommendation_kr` (별도 레포, 구조 동일)
- **DB**: Supabase (보유종목, 유저 인증)

---

## 파일 구조

```
project_titan.py       ← 핵심 분석 엔진 (전부 여기에)
backtest_titan.py      ← 백테스트 (독립 실행)
ml_predictor.py        ← ML 예측 모듈
portfolio_manager.py   ← 포트폴리오 계산
check_stocks.py        ← 단일 종목 빠른 체크

index.html             ← 메인 페이지 (정적, 수동 편집)
login.html             ← 로그인 (Supabase Auth)
growth_report.html     ← 성장주 리포트 (Actions가 자동 생성)
value_report.html      ← 가치주 리포트 (Actions가 자동 생성)
portfolio.html         ← 포트폴리오 (Actions가 자동 생성)
changelog.html         ← 업데이트 내역 (CHANGELOG.md → 자동 변환)
search.html            ← 종목 검색 (정적, 수동 편집)
dashboard.html         ← 자산 관리 (정적, 수동 편집)
my_holdings.html       ← 보유종목 알림 설정 (정적)
scoring_system.html    ← 점수체계 설명 (정적)
admin_setup.html       ← 관리자 설정 (정적)

supabase_config.js     ← Supabase URL/KEY (GitHub Secret에서 주입)
manifest.json          ← PWA 설정
service-worker.js      ← PWA 오프라인 캐싱

titan_scores_growth.json  ← 성장주 점수 캐시 (Actions가 자동 생성)
titan_scores_value.json   ← 가치주 점수 캐시 (Actions가 자동 생성)
last_updated.json         ← 마지막 업데이트 시각 (Actions가 자동 생성)
CHANGELOG.md              ← 수동 관리 변경 이력

.github/workflows/deploy.yml   ← 메인 배포 워크플로
.github/workflows/backtest.yml ← 백테스트 워크플로
requirements.txt               ← Python 의존성
```

---

## 핵심 클래스: `TitanAnalyzer` (project_titan.py)

### 주요 메서드

| 메서드 | 역할 |
|--------|------|
| `stage1_quick_filter()` | 시총/가격/거래량 빠른 필터 (성장주만 사용) |
| `stage2_deep_analysis()` | 펀더멘탈 + 기술적 분석 (전체 파이프라인) |
| `_get_fundamental_score()` | 펀더멘탈 점수 계산 (성장주/가치주 분기) |
| `_get_technical_score()` | 기술적 점수 계산 (MA, RSI, MACD 등) |
| `_analyze_sector_rotation()` | ETF 모멘텀 기반 섹터 순환매 분석 |
| `_get_trump_policy_bonus()` | 트럼프 정책 보너스/페널티 |
| `generate_html_report()` | HTML 리포트 생성 (growth/value 분기 렌더링) |
| `generate_portfolio_html()` | 포트폴리오 HTML 생성 |
| `generate_changelog_html()` | CHANGELOG.md → HTML 변환 |
| `run_analysis_with_tickers()` | 분석 실행 진입점 |
| `_save_score_cache()` | 점수를 JSON 캐시로 저장 |
| `run_ml_predictions()` | ML 예측 (별도 모듈 호출) |

### 실행 모드

```bash
python project_titan.py growth     # 성장주 분석 → growth_report.html
python project_titan.py value      # 가치주 분석 → value_report.html
python project_titan.py portfolio  # 포트폴리오 → portfolio.html
python project_titan.py changelog  # 변경이력 → changelog.html
```

---

## 점수 체계 (100점 만점)

### 성장주 (Fund 0.8 : Tech 1.2 가중치)

| 항목 | 배점 | 기준 |
|------|------|------|
| ROE | 15 | 섹터별 차등 임계값 |
| OPM (영업이익률) | 15 | 섹터/업종별 차등 |
| 매출성장률 | 10 | 섹터별 차등 |
| 섹터 적합도 | 10 | Tier1~4 (AI/반도체=10, 전통산업=1~3) |
| **펀더멘탈 소계** | **50** | |
| 추세 (MA/MACD/일목) | 20 | |
| 모멘텀 (RSI/Stoch) | 10 | |
| 거래량 (OBV 등) | 8 | |
| 변동성 (BB/ATR) | 7 | |
| 가격 패턴 | 5 | |
| **기술적 소계** | **50** | |

### 가치주 (Fund 1.3 : Tech 0.7 가중치)

| 항목 | 배점 | 기준 |
|------|------|------|
| 배당수익률 | 12 | dividendRate/price 직접 계산 |
| 밸류에이션 | 12 | PER vs EV/EBITDA 중 높은 쪽 채택 |
| ROE | 8 | 섹터별 차등 |
| 부채비율 D/E | 8 | 역방향 (낮을수록 좋음) |
| 섹터 적합도 | 10 | 가치주 섹터 기준 |
| **펀더멘탈 소계** | **50** | |
| 기술적 점수 | **50** | 성장주와 동일 구조 |

### 보정 항목

| 항목 | 범위 |
|------|------|
| contrarian (역발상) | ±10 |
| liquidity (유동성 등급) | ±5 |
| policy (트럼프 정책) | ±3 |
| rotation (섹터 순환매) | -3 ~ +5 |
| 배당귀족 보너스 | +4 (고정) |
| 과매도 우량주 보너스 | +10 |
| 과열 페널티 | -5 |

### 판정 기준 (시장 상태별)

| 시장 | Strong Buy | Buy |
|------|-----------|-----|
| Bull | ≥85점 | ≥75점 |
| Bear | ≥75점 | ≥65점 |
| Neutral | ≥80점 | ≥70점 |

---

## 주요 상수 (수정 가능 여부)

### ✅ 수정해도 되는 것

| 상수/파라미터 | 위치 | 설명 |
|--------------|------|------|
| `GROWTH_TICKERS` | line 20 | 성장주 분석 대상 종목 리스트 |
| `VALUE_TICKERS` | line 69 | 가치주 분석 대상 종목 리스트 |
| `DIVIDEND_ARISTOCRATS` | line 338 | 배당귀족 목록 (보너스 +4점) |
| `VALUE_DIVIDEND_THRESHOLDS` | line 265 | 섹터별 배당수익률 기준 |
| `VALUE_PER_THRESHOLDS` | line 281 | 섹터별 PER 기준 |
| `VALUE_DE_THRESHOLDS` | line 297 | 섹터별 D/E 기준 |
| `VALUE_EVEBITDA_THRESHOLDS` | line 314 | 섹터별 EV/EBITDA 기준 |
| `SECTOR_ROE_THRESHOLDS` | line 205 | 섹터별 ROE 기준 |
| `SECTOR_OPM_THRESHOLDS` | line 237 | 섹터별 OPM 기준 |
| `SECTOR_ETF_MAP` | line 184 | 순환매 분석용 ETF 매핑 |
| `ROTATION_BONUS_*` | line 197 | 순환매 보너스 점수 |
| `min_score` (run 호출) | line 4128/4139 | 리포트 노출 최소 점수 |
| `min_market_cap` (value) | line 4139 | 가치주 최소 시총 ($20B) |
| `SCORE_SECTOR_TIER*` | line 166 | 섹터 티어별 점수 |

### ⚠️ 신중하게 수정해야 하는 것

| 항목 | 이유 |
|------|------|
| `_get_fundamental_score()` 내부 로직 | 점수 체계 전체에 영향 |
| `_get_technical_score()` 내부 로직 | 기술적 분석 전체에 영향 |
| `_calc_gradient_score()` | 모든 정방향 점수 계산에 사용 |
| `_calc_inverse_gradient_score()` | PER/D/E 역방향 점수에 사용 |
| `generate_html_report()` | HTML 생성 템플릿 전체 (매우 긺) |
| `_save_score_cache()` | 캐시 필드 추가 시 HTML 렌더링도 함께 수정 필요 |

### ❌ 수정하면 안 되는 것

| 항목 | 이유 |
|------|------|
| `supabase_config.js` | GitHub Secret에서 Actions가 주입, 로컬 파일은 더미 |
| `service-worker.js` | PWA 캐싱 로직, 건드리면 앱 오프라인 기능 깨짐 |
| `manifest.json` | PWA 설정, 함부로 변경 시 앱 등록 깨짐 |
| `.github/workflows/deploy.yml` | CI/CD 파이프라인, 깨지면 자동배포 중단 |
| `titan_scores_*.json` | Actions가 덮어씀, 수동 수정 의미 없음 |
| `growth_report.html` / `value_report.html` | Actions가 덮어씀, 수동 수정 의미 없음 |
| `last_updated.json` | Actions가 덮어씀 |

---

## GitHub Actions 배포 흐름

```
push to main  또는  cron 스케줄 (하루 10회)
        ↓
deploy.yml 실행
        ↓
1. python project_titan.py growth  → growth_report.html 생성
2. python project_titan.py value   → value_report.html 생성
3. python project_titan.py portfolio → portfolio.html 생성
4. python project_titan.py changelog → changelog.html 생성
5. 결과물 전체 → GitHub Pages 배포
```

**스케줄 (KST 기준)**: 06:30 / 08:00 / 09:00 / 10:00 / 18:00 / 21:00 / 23:30 / 00:30 / 03:30 / 05:30

**주의**: push 시 분석 재실행 조건 = `analysis_changed == 'true'` (project_titan.py 변경 감지)

---

## Supabase 연동

- **인증**: 로그인/로그아웃 (Supabase Auth)
- **보유종목**: `holdings` 테이블 → 분석 시 자동 포함
- **유저 프로필**: `user_profiles` 테이블 (role: admin/user)
- **키**: GitHub Secret `SUPABASE_URL`, `SUPABASE_ANON_KEY` → Actions에서 `supabase_config.js`로 주입

---

## 섹터 순환매 분석

`_analyze_sector_rotation()` 메서드:
- 11개 섹터 ETF (XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLRE, XLU, XLC, XLB) 모멘텀 계산
- 1주 수익률 + 최근5일 vs 이전5일 가속도 비교
- 국면 판별 → 보너스 적용

| 국면 | 조건 | 보너스 |
|------|------|--------|
| 수급유입 | 상위 + 가속 | +3 |
| 순환매 기대 | 하위 + 반등 | +5 |
| 관심 | 중위 + 가속 | +1 |
| 과열주의 | 상위 + 감속 | -2 |
| 소외 지속 | 하위 + 감속 | -3 |

---

## 배당수익률 계산 방식

yfinance `dividendYield` 필드가 종목마다 포맷이 달라서 (0.019 vs 1.9 vs 0.93) 직접 계산:

```python
div_pct = dividendRate / currentPrice * 100  # 우선
# fallback: dividendYield <= 15이면 그대로, 초과 시 /100
```

---

## 알려진 주의사항

- **KR 레포 push 전** `git pull --rebase` 필수 (Actions가 자주 커밋)
- **금융주 D/E**: yfinance가 null 반환 → Financial Services/Real Estate는 중간 점수(4점) 자동 부여
- **COST/WMT 같은 프리미엄 우량주**: PER 높아도 EV/EBITDA로 구제됨
- `generate_html_report()`는 매우 긺 (약 700줄) — 수정 시 `is_value_mode` 분기 주의
- `analysis_mode` 속성이 `'growth'` / `'value'`에 따라 `_get_fundamental_score()` 전체가 분기됨
