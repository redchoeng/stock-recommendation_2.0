# -*- coding: utf-8 -*-
"""
notifier.py — Web Push / Telegram 알림 전역 함수
send_push_alert, _send_webpush, _send_telegram_fallback, _fetch_user_holding_tickers
"""
import os
import pytz

def send_push_alert(results, market='us'):
    """Supabase에서 사용자별 보유종목 조회 후 Web Push 알림 전송"""
    import requests as _req
    import json as _json
    from collections import defaultdict
    import time

    sb_url = os.environ.get('SUPABASE_URL', '')
    sb_key = os.environ.get('SUPABASE_SERVICE_KEY', '')
    vapid_private = os.environ.get('VAPID_PRIVATE_KEY', '')
    vapid_email = os.environ.get('VAPID_EMAIL', 'mailto:admin@titan.com')

    if not sb_url or not sb_key or not vapid_private:
        # Supabase 미설정 시 텔레그램 폴백
        _send_telegram_fallback(results, market)
        return

    headers = {
        'apikey': sb_key,
        'Authorization': f'Bearer {sb_key}',
        'Content-Type': 'application/json'
    }

    # 1) alert_holdings 조회
    try:
        resp = _req.get(
            f'{sb_url}/rest/v1/alert_holdings?market=eq.{market}&select=*',
            headers=headers, timeout=15
        )
        all_holdings = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        print(f"⚠️  보유종목 조회 실패: {e}")
        _send_telegram_fallback(results, market)
        return

    all_holdings = [h for h in all_holdings if float(h.get('qty', 0)) > 0]
    if not all_holdings:
        print("ℹ️  등록된 보유종목 없음")
        return

    # 2) push_subscriptions 조회
    user_ids = list(set(h['user_id'] for h in all_holdings))
    user_id_csv = ','.join(user_ids)
    try:
        resp2 = _req.get(
            f'{sb_url}/rest/v1/push_subscriptions?user_id=in.({user_id_csv})&select=*',
            headers=headers, timeout=15
        )
        subs = resp2.json() if resp2.status_code == 200 else []
    except Exception:
        subs = []

    # user_id → subscriptions 매핑
    user_subs = defaultdict(list)
    for s in subs:
        user_subs[s['user_id']].append(s)

    # 3) user_id → holdings 매핑
    user_holdings = defaultdict(list)
    for h in all_holdings:
        user_holdings[h['user_id']].append(h)

    # 4) 분석 결과 lookup
    lookup = {r['ticker']: r for r in results}
    is_kr = (market == 'kr')
    kst = pytz.timezone('Asia/Seoul')
    now_str = datetime.now(kst).strftime('%m/%d %H:%M')

    def fmt(v):
        if not v:
            return '-'
        return f"₩{int(v):,}" if is_kr else f"${v:,.2f}"

    tag = 'KR' if is_kr else 'US'
    total_alerts = 0

    # 5) 사용자별 알림 체크 + 전송
    for user_id, holdings in user_holdings.items():
        subscriptions = user_subs.get(user_id, [])
        if not subscriptions:
            continue

        alerts = []
        for h in holdings:
            r = lookup.get(h['ticker'])
            if not r:
                continue

            price = r.get('price', 0)
            target = r.get('target') or r.get('target_price', 0)
            stop = r.get('stop_loss', 0)
            avg = float(h.get('avg_price', 0))
            qty = float(h.get('qty', 0))
            name = h.get('name', h['ticker'])
            pnl_pct = ((price - avg) / avg * 100) if avg else 0

            if price and target and price >= target:
                alerts.append({
                    'title': f'🟢 목표가 도달: {name}',
                    'body': f'{fmt(price)} ≥ 목표 {fmt(target)} | {pnl_pct:+.1f}%',
                    'tag': f'target-{h["ticker"]}'
                })

            if price and stop and price <= stop:
                alerts.append({
                    'title': f'🔴 손절가 도달: {name}',
                    'body': f'{fmt(price)} ≤ 손절 {fmt(stop)} | {pnl_pct:+.1f}%',
                    'tag': f'stop-{h["ticker"]}'
                })

        if not alerts:
            continue

        # 각 구독 기기에 푸시 전송
        for alert in alerts:
            for sub_info in subscriptions:
                _send_webpush(sub_info, alert, vapid_private, vapid_email, sb_url, sb_key, headers)
                time.sleep(0.05)
            total_alerts += 1

    print(f"📨 [{tag}] Web Push 알림 {total_alerts}건 전송 ({len(user_holdings)}명)")


def _send_webpush(sub_info, payload, vapid_private, vapid_email, sb_url, sb_key, headers):
    """단일 Web Push 전송"""
    try:
        from pywebpush import webpush, WebPushException
        import json as _json

        subscription_info = {
            'endpoint': sub_info['endpoint'],
            'keys': {
                'p256dh': sub_info['p256dh'],
                'auth': sub_info['auth']
            }
        }

        webpush(
            subscription_info=subscription_info,
            data=_json.dumps(payload),
            vapid_private_key=vapid_private,
            vapid_claims={'sub': vapid_email}
        )
    except Exception as e:
        err_str = str(e)
        # 410 Gone = 구독 만료 → DB에서 삭제
        if '410' in err_str or 'Gone' in err_str:
            try:
                import requests as _req
                _req.delete(
                    f'{sb_url}/rest/v1/push_subscriptions?id=eq.{sub_info["id"]}',
                    headers=headers, timeout=10
                )
                print(f"🗑️  만료된 구독 삭제: {sub_info['endpoint'][:50]}...")
            except Exception:
                pass
        else:
            print(f"⚠️  Push 전송 실패: {err_str[:80]}")


def _send_telegram_fallback(results, market='us'):
    """Supabase 미설정 시 기존 텔레그램 폴백"""
    import json as _json
    import requests as _req

    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        print("⚠️  텔레그램/Supabase 설정 없음 — 알림 건너뜀")
        return

    try:
        with open('my_holdings.json', 'r', encoding='utf-8') as f:
            holdings = _json.load(f).get('holdings', [])
    except (FileNotFoundError, _json.JSONDecodeError):
        return

    holdings = [h for h in holdings if h.get('qty', 0) > 0]
    if not holdings:
        return

    lookup = {r['ticker']: r for r in results}
    is_kr = (market == 'kr')
    kst = pytz.timezone('Asia/Seoul')
    now_str = datetime.now(kst).strftime('%m/%d %H:%M')

    def fmt(v):
        if not v:
            return '-'
        return f"₩{int(v):,}" if is_kr else f"${v:,.2f}"

    alerts = []
    summary_lines = []

    for h in holdings:
        r = lookup.get(h['ticker'])
        if not r:
            continue

        price = r.get('price', 0)
        target = r.get('target') or r.get('target_price', 0)
        stop = r.get('stop_loss', 0)
        avg = h.get('avg_price', 0)
        qty = h.get('qty', 0)
        name = h.get('name', h['ticker'])
        pnl_pct = ((price - avg) / avg * 100) if avg else 0

        if price and target and price >= target:
            alerts.append(f"🟢 목표가 도달: {name} ({h['ticker']})\n현재 {fmt(price)} ≥ 목표 {fmt(target)}\n보유 {qty}주 · 평단 {fmt(avg)} · 수익 {pnl_pct:+.1f}%")
        if price and stop and price <= stop:
            alerts.append(f"🔴 손절가 도달: {name} ({h['ticker']})\n현재 {fmt(price)} ≤ 손절 {fmt(stop)}\n보유 {qty}주 · 평단 {fmt(avg)} · 손실 {pnl_pct:+.1f}%")
        summary_lines.append(f"  {name}: {fmt(price)} ({pnl_pct:+.1f}%)\n    목표 {fmt(target)} | 손절 {fmt(stop)}")

    def send_tg(text):
        try:
            _req.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={'chat_id': chat_id, 'text': text}, timeout=10)
        except Exception:
            pass

    for a in alerts:
        send_tg(a)
    if summary_lines:
        tag = 'KR' if is_kr else 'US'
        send_tg(f"📊 [{tag}] 보유종목 현황 ({now_str} KST)\n\n" + "\n\n".join(summary_lines))


def _fetch_user_holding_tickers(market='us'):
    """Supabase에서 사용자 보유종목 티커를 가져와 분석 대상에 추가"""
    import requests as _req
    sb_url = os.environ.get('SUPABASE_URL', '')
    sb_key = os.environ.get('SUPABASE_SERVICE_KEY', '')
    if not sb_url or not sb_key:
        return []
    try:
        headers = {'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}
        resp = _req.get(
            f"{sb_url}/rest/v1/alert_holdings?market=eq.{market}&select=ticker",
            headers=headers, timeout=10
        )
        if resp.status_code == 200:
            tickers = list(set(h['ticker'] for h in resp.json()))
            if tickers:
                print(f"📌 보유종목 {len(tickers)}개 추가 분석 대상에 포함")
            return tickers
    except Exception as e:
        print(f"⚠️  보유종목 조회 실패: {e}")
    return []


