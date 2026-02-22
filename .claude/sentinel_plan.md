# Sentinel 실시간 주가 알림 시스템 구현 계획

## Context
현재 시스템은 ~1시간 간격으로 전체 분석을 재실행하여 리포트를 갱신한다.
그 사이 시장이 급변하면 (패닉 급락, 목표가 도달 등) 사용자가 대응하지 못하는 문제가 있다.
**해결**: 전체 재분석 없이, 캐시된 Titan 점수 + 실시간 가격만 비교하는 경량 경보 시스템(Sentinel)을 5분 간격으로 실행.

## 아키텍처

```
[1시간 간격] deploy.yml → project_titan.py → titan_scores_*.json 갱신
[5분 간격]   sentinel.yml → sentinel.py → 캐시 로드 → 가격 비교 → 알림
```

## 파일 변경 목록

### 1. NEW: `sentinel.py` (~200줄)
- `main()`: 개장 확인 → 캐시 로드 → 가격 조회 → 감지 → 알림
- `is_market_open()`: `pandas_market_calendars`로 NYSE 거래일+시간 확인 (공휴일 포함)
- `load_cached_scores()`: `titan_scores_growth.json` + `titan_scores_value.json` 병합 로드
- `fetch_user_holdings()`: Supabase `alert_holdings` REST API (기존 notifier.py 패턴 재사용)
- `build_monitor_list()`: 고점수(≥70) 종목 + 사용자 보유종목 합집합
- `fetch_live_prices()`: **`yf.download(tickers, period='1d', interval='5m', prepost=True)`** — 일괄 조회 ~3-5초
- `fetch_vix()`: `yf.Ticker('^VIX')` — VIX 공포지수
- `detect_alerts()`: 5가지 조건 감지
  - **(a) 급락 매수기회**: 점수 ≥70 종목이 캐시 대비 -5% 이상 하락
  - **(b) 매수구간 진입**: 현재가 ≤ 캐시의 `buy_price`
  - **(c) 손절선 이탈**: 보유종목이 `stop_loss` 아래로
  - **(d) 목표가 도달**: 보유종목이 `target_price` 위로
  - **(e) 시장 패닉**: VIX ≥ 30 + 우량주 5개 이상 동시 하락
- `filter_cooldown()`: Supabase `sentinel_alerts` 테이블로 동일 알림 4시간 쿨다운
- `send_alerts()`: `notifier.send_sentinel_alert()` 호출
- `record_sent_alerts()`: Supabase에 발송 기록 저장

### 2. MODIFY: `notifier.py`
- **bugfix**: `from datetime import datetime` import 추가 (기존 누락)
- **신규 함수**: `send_sentinel_alert(alerts, user_holdings)` 추가
  - 브로드캐스트 알림 (급락/매수구간/시장패닉) → 전체 구독자
  - 타겟 알림 (손절/목표가) → 해당 보유 유저만
  - 기존 `_send_webpush()` 재사용
- **신규 함수**: `_send_sentinel_telegram_fallback(alerts)` — 텔레그램 폴백

### 3. NEW: `.github/workflows/sentinel.yml`
- 5분 간격 cron (UTC 09:00~01:00 = ET 04:00~20:00, 월~금)
- `concurrency: sentinel-alerts` + `cancel-in-progress: true`
- `timeout-minutes: 2`
- `permissions: contents: read` (읽기 전용, git push 없음)
- 기존 deploy.yml과 동일한 secrets 사용

### 4. Supabase `sentinel_alerts` 테이블 (SQL 1회 실행)
```sql
CREATE TABLE sentinel_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_tag TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    ticker TEXT NOT NULL,
    title TEXT NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_sentinel_alerts_sent_at ON sentinel_alerts(sent_at DESC);
CREATE INDEX idx_sentinel_alerts_tag ON sentinel_alerts(alert_tag);
```

## 실행 시간 예산 (<15초 목표)
| 단계 | 시간 |
|------|------|
| JSON 캐시 로드 | <0.1초 |
| Supabase 보유종목 조회 | ~1초 |
| yf.download 일괄 가격 | ~3-5초 |
| VIX 조회 | ~1초 |
| Supabase 쿨다운 조회 | ~1초 |
| 감지 로직 | <0.1초 |
| 알림 전송 | ~2초 |
| **총합** | **~8-11초** |

## GitHub Actions 비용
- 공개 저장소: 무제한 무료
- 비공개 저장소: 5분 간격 시 월 ~4,200분 (무료 2,000분 초과)
  → 비공개라면 15분 간격(`*/15`)으로 조정 가능

## 검증 방법
1. `python -c "from sentinel import main"` — 구문 검증
2. `python sentinel.py` — 로컬 실행 (Supabase 없으면 텔레그램 폴백)
3. GitHub Actions에서 수동 실행(`workflow_dispatch`)으로 확인
4. Actions 로그에서 감지 건수 및 실행 시간 확인
