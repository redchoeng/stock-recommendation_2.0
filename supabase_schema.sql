-- ============================================
-- PROJECT TITAN - Portfolio Management Schema
-- Supabase SQL Editor에서 실행하세요
-- ============================================

-- 1. 사용자 프로필
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
    display_name TEXT,
    target_stocks INTEGER DEFAULT 40,    -- 목표 주식 비율 %
    target_etf INTEGER DEFAULT 40,       -- 목표 ETF 비율 %
    target_cash INTEGER DEFAULT 20,      -- 목표 예금 비율 %
    monthly_budget NUMERIC DEFAULT 0,    -- 월 투자 가능 금액 (USD)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 자산 목록
CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    asset_type TEXT NOT NULL CHECK (asset_type IN ('stock', 'etf', 'deposit')),
    ticker TEXT,                          -- 주식/ETF 티커 (예금은 NULL)
    name TEXT NOT NULL,                   -- 자산명
    shares NUMERIC DEFAULT 0,            -- 주수
    buy_price NUMERIC DEFAULT 0,         -- 매수 평단가
    amount NUMERIC DEFAULT 0,            -- 투자 원금
    interest_rate NUMERIC DEFAULT 0,     -- 예금 이자율 (%)
    maturity_date DATE,                  -- 예금 만기일
    note TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 월별 스냅샷
CREATE TABLE monthly_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    month TEXT NOT NULL,                  -- "2026-02" 형식
    total_value NUMERIC DEFAULT 0,
    stocks_value NUMERIC DEFAULT 0,
    etf_value NUMERIC DEFAULT 0,
    cash_value NUMERIC DEFAULT 0,
    growth_rate NUMERIC DEFAULT 0,       -- 전월 대비 %
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, month)
);

-- 4. 거래 내역
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    asset_id UUID REFERENCES assets(id) ON DELETE SET NULL,
    type TEXT NOT NULL CHECK (type IN ('buy', 'sell', 'deposit', 'withdraw', 'interest')),
    amount NUMERIC NOT NULL,
    shares NUMERIC DEFAULT 0,
    price NUMERIC DEFAULT 0,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    note TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Row Level Security (RLS) - 본인 데이터만 접근
-- ============================================

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- user_profiles: 본인 프로필만
CREATE POLICY "Users can view own profile" ON user_profiles FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own profile" ON user_profiles FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own profile" ON user_profiles FOR UPDATE USING (auth.uid() = user_id);

-- assets: 본인 자산만
CREATE POLICY "Users can view own assets" ON assets FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own assets" ON assets FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own assets" ON assets FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own assets" ON assets FOR DELETE USING (auth.uid() = user_id);

-- monthly_snapshots: 본인 스냅샷만
CREATE POLICY "Users can view own snapshots" ON monthly_snapshots FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own snapshots" ON monthly_snapshots FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own snapshots" ON monthly_snapshots FOR UPDATE USING (auth.uid() = user_id);

-- transactions: 본인 거래만
CREATE POLICY "Users can view own transactions" ON transactions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own transactions" ON transactions FOR INSERT WITH CHECK (auth.uid() = user_id);

-- ============================================
-- 자동 프로필 생성 트리거
-- ============================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (user_id, display_name)
    VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'name', NEW.email));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
