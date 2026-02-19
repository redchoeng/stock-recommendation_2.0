-- ============================================
-- PROJECT TITAN - Admin Role Setup
-- Supabase SQL Editor에서 실행하세요
-- ============================================

-- 1. user_profiles에 role 컬럼 추가
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user';

-- 2. 관리자 승격 RPC 함수 (서버사이드 코드 검증)
-- 기본 관리자 코드: 'titan-admin-2024' (아래에서 변경 가능)
CREATE OR REPLACE FUNCTION promote_to_admin(admin_code TEXT)
RETURNS JSON AS $$
DECLARE
    correct_code TEXT := 'titan-admin-2024';
BEGIN
    IF admin_code != correct_code THEN
        RETURN json_build_object('success', false, 'message', '잘못된 관리자 코드입니다');
    END IF;

    UPDATE user_profiles SET role = 'admin' WHERE user_id = auth.uid();
    RETURN json_build_object('success', true, 'message', '관리자 권한이 부여되었습니다');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3. 관리자 코드 변경하려면 위 함수에서 correct_code 값을 수정하세요
-- 예: correct_code TEXT := 'my-secret-code-123';
