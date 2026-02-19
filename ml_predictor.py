# -*- coding: utf-8 -*-
"""
ML Predictor v2.0 - AI/ML 기반 주가 예측 모델
풀링 학습 (종목 합산) + 시장 상대강도 + 적응형 타겟

변경 이력:
- v1: 종목별 개별 학습 (데이터 부족, 느림)
- v2: 풀링 학습 + SPY 상대강도 + 적응형 타겟 + 모델 캐시
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import os
import pickle
import hashlib
warnings.filterwarnings('ignore')

# CPU: XGBoost
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("XGBoost not installed: pip install xgboost")

# GPU: PyTorch + ONNX Runtime (CUDA / DirectML / CPU)
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    PYTORCH_AVAILABLE = True
    TORCH_DEVICE = torch.device('cpu')

    if torch.cuda.is_available():
        TORCH_DEVICE = torch.device('cuda')
        print(f"NVIDIA GPU: {torch.cuda.get_device_name(0)}")

except ImportError:
    PYTORCH_AVAILABLE = False
    TORCH_DEVICE = 'cpu'
    print("PyTorch not installed: pip install torch")

# ONNX Runtime with DirectML (AMD GPU)
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True

    providers = ort.get_available_providers()
    if 'DmlExecutionProvider' in providers:
        ONNX_PROVIDERS = ['DmlExecutionProvider', 'CPUExecutionProvider']
        print("DirectML GPU acceleration enabled")
    elif 'CUDAExecutionProvider' in providers:
        ONNX_PROVIDERS = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        print("CUDA GPU acceleration enabled")
    else:
        ONNX_PROVIDERS = ['CPUExecutionProvider']
except ImportError:
    ONNX_AVAILABLE = False
    ONNX_PROVIDERS = []

# 기술 지표 라이브러리
from ta.trend import MACD, ADXIndicator, SMAIndicator, EMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator


# ============================================================
# 모델 캐시 디렉토리 (ASCII 경로 → ONNX utf-8 에러 방지)
# ============================================================
CACHE_DIR = os.path.join(os.environ.get('TEMP', '/tmp'), 'ml_predictor_cache')
os.makedirs(CACHE_DIR, exist_ok=True)


class FeatureEngineer:
    """기술 지표 + 시장 상대강도 + 가치투자 피처"""

    _spy_cache = None  # SPY 데이터 캐시 (세션 내 재사용)

    @classmethod
    def get_spy_data(cls, period='5y'):
        """SPY 데이터 캐시"""
        if cls._spy_cache is None:
            print("📥 SPY (시장 벤치마크) 다운로드...")
            cls._spy_cache = yf.Ticker('SPY').history(period=period)
        return cls._spy_cache

    @staticmethod
    def create_features(df, ticker_info=None, value_mode=False, spy_df=None):
        """ML 피처 생성 (시장 상대강도 포함)"""
        features = pd.DataFrame(index=df.index)

        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']

        # 1. 가격 기반 피처 (수익률)
        for d in [1, 3, 5, 10, 20]:
            features[f'return_{d}d'] = close.pct_change(d)

        # 2. 이동평균 (가격 대비 위치)
        for w in [5, 10, 20, 50, 200]:
            sma = SMAIndicator(close, window=w).sma_indicator()
            features[f'sma_{w}_dist'] = close / sma - 1

        features['ema_12_dist'] = EMAIndicator(close, window=12).ema_indicator() / close - 1
        features['ema_26_dist'] = EMAIndicator(close, window=26).ema_indicator() / close - 1

        # 골든크로스/데드크로스 신호
        sma20 = SMAIndicator(close, window=20).sma_indicator()
        sma50 = SMAIndicator(close, window=50).sma_indicator()
        features['golden_cross'] = (sma20 > sma50).astype(float)

        # 3. 모멘텀 지표
        features['rsi'] = RSIIndicator(close, window=14).rsi() / 100
        stoch = StochasticOscillator(high, low, close)
        features['stoch_k'] = stoch.stoch() / 100
        features['stoch_d'] = stoch.stoch_signal() / 100

        # 4. MACD
        macd = MACD(close)
        features['macd'] = macd.macd() / close
        features['macd_signal'] = macd.macd_signal() / close
        features['macd_hist'] = macd.macd_diff() / close

        # 5. 볼린저 밴드
        bb = BollingerBands(close)
        features['bb_position'] = (close - bb.bollinger_lband()) / \
                                  (bb.bollinger_hband() - bb.bollinger_lband() + 1e-10)
        features['bb_width'] = (bb.bollinger_hband() - bb.bollinger_lband()) / close

        # 6. ATR (변동성) - 정규화
        atr = AverageTrueRange(high, low, close)
        features['atr_pct'] = atr.average_true_range() / close

        # 7. ADX (추세 강도)
        adx = ADXIndicator(high, low, close)
        features['adx'] = adx.adx() / 100
        features['adx_pos'] = adx.adx_pos() / 100
        features['adx_neg'] = adx.adx_neg() / 100

        # 8. 거래량 지표
        features['volume_change'] = volume.pct_change(1)
        vol_ma = volume.rolling(20).mean()
        features['volume_ma_ratio'] = volume / (vol_ma + 1)
        obv = OnBalanceVolumeIndicator(close, volume)
        features['obv_change'] = obv.on_balance_volume().pct_change(5)

        # 9. 가격 위치
        features['close_to_20d_high'] = close / high.rolling(20).max() - 1
        features['close_to_20d_low'] = close / low.rolling(20).min() - 1

        # 10. 52주 가격 위치
        high_52w = close.rolling(252, min_periods=60).max()
        low_52w = close.rolling(252, min_periods=60).min()
        features['price_52w_position'] = (close - low_52w) / (high_52w - low_52w + 1e-10)

        # 11. 변동성 레짐 (최근 20일 vs 60일)
        vol_20 = close.pct_change().rolling(20).std()
        vol_60 = close.pct_change().rolling(60).std()
        features['vol_regime'] = vol_20 / (vol_60 + 1e-10)

        # ===== 12. 시장 상대강도 (SPY 대비) =====
        if spy_df is not None and len(spy_df) > 0:
            spy_close = spy_df['Close'].reindex(df.index, method='ffill')
            # 상대 수익률
            for d in [5, 10, 20]:
                stock_ret = close.pct_change(d)
                spy_ret = spy_close.pct_change(d)
                features[f'rel_strength_{d}d'] = stock_ret - spy_ret

            # 상대강도지수 (RS ratio)
            rs_20 = (close / close.shift(20)) / (spy_close / spy_close.shift(20) + 1e-10)
            features['rs_ratio'] = rs_20

            # 시장 추세 (SPY RSI)
            spy_rsi = RSIIndicator(spy_close.dropna(), window=14).rsi() / 100
            features['market_rsi'] = spy_rsi.reindex(df.index, method='ffill')

            # 시장 변동성 (SPY ATR)
            spy_atr = spy_close.pct_change().rolling(20).std()
            features['market_vol'] = spy_atr.reindex(df.index, method='ffill')

        # ===== 가치투자 피처 (value_mode) =====
        if value_mode and ticker_info:
            div_yield = ticker_info.get('dividendYield', 0) or 0
            features['dividend_yield'] = div_yield
            features['dividend_attractive'] = min(div_yield / 0.03, 1.0) if div_yield > 0 else 0

            pe_ratio = ticker_info.get('trailingPE', 0) or ticker_info.get('forwardPE', 0) or 30
            features['pe_ratio'] = min(pe_ratio / 100, 1.0)
            features['pe_attractive'] = max(0, 1 - pe_ratio / 30) if pe_ratio > 0 else 0

            pb_ratio = ticker_info.get('priceToBook', 0) or 3
            features['pb_ratio'] = min(pb_ratio / 10, 1.0)
            features['pb_attractive'] = max(0, 1 - pb_ratio / 3) if pb_ratio > 0 else 0

            payout = ticker_info.get('payoutRatio', 0) or 0
            features['payout_ratio'] = min(payout, 1.0)
            features['payout_healthy'] = 1.0 if 0.3 <= payout <= 0.6 else (0.5 if 0.2 <= payout <= 0.8 else 0.0)

            roe = ticker_info.get('returnOnEquity', 0) or 0
            features['roe'] = min(max(roe, 0), 0.5)
            features['roe_attractive'] = min(roe / 0.15, 1.0) if roe > 0 else 0

            debt_equity = ticker_info.get('debtToEquity', 0) or 0
            features['debt_equity'] = min(debt_equity / 200, 1.0)
            features['low_debt'] = max(0, 1 - debt_equity / 150) if debt_equity < 150 else 0

            fcf = ticker_info.get('freeCashflow', 0) or 0
            market_cap = ticker_info.get('marketCap', 1) or 1
            fcf_yield = fcf / market_cap if market_cap > 0 else 0
            features['fcf_yield'] = max(min(fcf_yield, 0.2), -0.1)

            features['value_score'] = (
                features['dividend_attractive'] * 0.10 +
                features['pe_attractive'] * 0.30 +
                features['pb_attractive'] * 0.15 +
                features['roe_attractive'] * 0.25 +
                features['low_debt'] * 0.10 +
                features['payout_healthy'] * 0.10
            )

        # NaN 처리
        features = features.replace([np.inf, -np.inf], np.nan)
        features = features.fillna(0)

        return features

    @staticmethod
    def create_adaptive_target(df, horizon=10):
        """적응형 타겟: 종목 변동성 기반 임계값
        - 고변동 종목: 넓은 임계값 → 확실한 방향만 상승/하락
        - 저변동 종목: 좁은 임계값 → 작은 움직임도 감지
        """
        future_return = df['Close'].shift(-horizon) / df['Close'] - 1

        # 20일 롤링 변동성 기반 임계값 (평균 ATR의 1배)
        daily_vol = df['Close'].pct_change().rolling(20).std()
        threshold = daily_vol * np.sqrt(horizon) * 0.7  # horizon일 변동성의 70%
        threshold = threshold.clip(lower=0.015, upper=0.08)  # 1.5%~8% 범위 제한

        # 0: 하락, 1: 보합, 2: 상승
        target = pd.Series(1, index=df.index, dtype=float)  # 기본 보합
        target[future_return > threshold] = 2   # 상승
        target[future_return < -threshold] = 0  # 하락

        # 미래 데이터 없는 구간 NaN
        target[future_return.isna()] = np.nan

        return target

    @staticmethod
    def create_target(df, horizon=5, threshold=0.02):
        """기존 호환용: 고정 임계값 타겟"""
        future_return = df['Close'].shift(-horizon) / df['Close'] - 1
        target = pd.cut(future_return,
                       bins=[-np.inf, -threshold, threshold, np.inf],
                       labels=[0, 1, 2]).astype(float)
        return target


class LSTMModel(nn.Module):
    """LSTM + Attention 시계열 예측 모델"""

    def __init__(self, input_size, hidden_size=128, num_layers=2, num_classes=3, dropout=0.3):
        super(LSTMModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True
        )

        self.attention = nn.MultiheadAttention(hidden_size * 2, num_heads=4, batch_first=True)
        self.fc1 = nn.Linear(hidden_size * 2, 64)
        self.fc2 = nn.Linear(64, num_classes)
        self.dropout = nn.Dropout(dropout)
        self.relu = nn.ReLU()

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        out = attn_out[:, -1, :]
        out = self.dropout(self.relu(self.fc1(out)))
        out = self.fc2(out)
        return out


class EnsemblePredictor:
    """풀링 학습 앙상블 (XGBoost + LSTM)"""

    def __init__(self, sequence_length=20, value_mode=False):
        self.sequence_length = sequence_length
        self.value_mode = value_mode
        self.xgb_model = None
        self.lstm_model = None
        self.onnx_session = None
        self.feature_engineer = FeatureEngineer()
        self.feature_columns = None
        self.ticker_info = None

    def prepare_data(self, ticker, period='5y'):
        """단일 종목 데이터 준비"""
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)

        if len(df) < 100:
            print(f"   {ticker}: 데이터 부족 ({len(df)}일)")
            return None, None, None, None

        ticker_info = None
        if self.value_mode:
            try:
                ticker_info = stock.info
                self.ticker_info = ticker_info
            except Exception:
                pass

        spy_df = self.feature_engineer.get_spy_data(period)
        features = self.feature_engineer.create_features(df, ticker_info, self.value_mode, spy_df)
        target = self.feature_engineer.create_adaptive_target(df, horizon=10)

        valid_idx = ~(features.isna().any(axis=1) | target.isna())
        features = features[valid_idx]
        target = target[valid_idx]
        df = df[valid_idx]

        self.feature_columns = features.columns.tolist()

        return df, features, target, ticker_info

    def train_xgboost(self, X_train, y_train, X_val, y_val):
        """XGBoost 학습 (클래스 불균형 보정)"""
        if not XGBOOST_AVAILABLE:
            return None

        print("   XGBoost 학습 중...")

        # 클래스 비율 계산 → sample_weight
        class_counts = y_train.value_counts()
        total = len(y_train)
        n_classes = len(class_counts)
        class_weights = {c: total / (n_classes * count) for c, count in class_counts.items()}
        sample_weights = y_train.map(class_weights).values

        self.xgb_model = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.7,
            min_child_weight=5,
            gamma=0.1,
            reg_alpha=0.1,
            reg_lambda=1.0,
            n_jobs=os.cpu_count(),
            random_state=42,
            use_label_encoder=False,
            eval_metric='mlogloss'
        )

        self.xgb_model.fit(
            X_train, y_train,
            sample_weight=sample_weights,
            eval_set=[(X_val, y_val)],
            verbose=False
        )

        val_acc = (self.xgb_model.predict(X_val) == y_val).mean()
        print(f"   XGBoost 검증 정확도: {val_acc:.2%}")
        return self.xgb_model

    def train_lstm(self, X_train, y_train, X_val, y_val, epochs=80, batch_size=64,
                   pre_sequences=None):
        """LSTM 학습 (pre_sequences: 종목별 사전 생성된 시퀀스, 경계 크로스 방지)"""
        if not PYTORCH_AVAILABLE:
            return None

        print(f"   LSTM 학습 중 ({TORCH_DEVICE})...")

        if pre_sequences is not None:
            X_train_seq, y_train_seq, X_val_seq, y_val_seq = pre_sequences
        else:
            X_train_seq = self._create_sequences(X_train)
            X_val_seq = self._create_sequences(X_val)

            y_train_seq = y_train.iloc[self.sequence_length-1:].values
            y_val_seq = y_val.iloc[self.sequence_length-1:].values

            min_len_train = min(len(X_train_seq), len(y_train_seq))
            X_train_seq = X_train_seq[:min_len_train]
            y_train_seq = y_train_seq[:min_len_train]
            min_len_val = min(len(X_val_seq), len(y_val_seq))
            X_val_seq = X_val_seq[:min_len_val]
            y_val_seq = y_val_seq[:min_len_val]

        if len(X_train_seq) < 50:
            print(f"   LSTM 스킵 (시퀀스 부족: {len(X_train_seq)})")
            return None

        # 클래스 불균형 보정 (CrossEntropyLoss weight)
        class_counts = pd.Series(y_train_seq).value_counts()
        total = len(y_train_seq)
        n_classes = 3
        weight_list = []
        for c in range(n_classes):
            count = class_counts.get(c, 1)
            weight_list.append(total / (n_classes * count))
        class_weight_tensor = torch.FloatTensor(weight_list).to(TORCH_DEVICE)

        X_train_t = torch.FloatTensor(X_train_seq).to(TORCH_DEVICE)
        y_train_t = torch.LongTensor(y_train_seq.astype(int)).to(TORCH_DEVICE)
        X_val_t = torch.FloatTensor(X_val_seq).to(TORCH_DEVICE)
        y_val_t = torch.LongTensor(y_val_seq.astype(int)).to(TORCH_DEVICE)

        train_dataset = TensorDataset(X_train_t, y_train_t)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

        input_size = X_train_seq.shape[2]
        self.lstm_model = LSTMModel(input_size=input_size).to(TORCH_DEVICE)

        criterion = nn.CrossEntropyLoss(weight=class_weight_tensor)
        optimizer = torch.optim.AdamW(self.lstm_model.parameters(), lr=0.001, weight_decay=0.01)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

        best_val_acc = 0
        patience = 15
        patience_counter = 0
        best_model_state = None

        for epoch in range(epochs):
            self.lstm_model.train()
            for X_batch, y_batch in train_loader:
                optimizer.zero_grad()
                outputs = self.lstm_model(X_batch)
                loss = criterion(outputs, y_batch)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.lstm_model.parameters(), 1.0)
                optimizer.step()

            scheduler.step()

            self.lstm_model.eval()
            with torch.no_grad():
                val_outputs = self.lstm_model(X_val_t)
                val_pred = val_outputs.argmax(dim=1)
                val_acc = (val_pred == y_val_t).float().mean().item()

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                patience_counter = 0
                best_model_state = self.lstm_model.state_dict().copy()
            else:
                patience_counter += 1

            if patience_counter >= patience:
                print(f"   LSTM early stop @ epoch {epoch+1}")
                break

            if (epoch + 1) % 20 == 0:
                print(f"   Epoch {epoch+1}/{epochs} - Val Acc: {val_acc:.2%}")

        if best_model_state:
            self.lstm_model.load_state_dict(best_model_state)
        print(f"   LSTM 최고 검증 정확도: {best_val_acc:.2%}")

        # ONNX 변환 (ASCII 경로 사용 → utf-8 에러 방지)
        if ONNX_AVAILABLE:
            self._export_to_onnx(input_size)

        return self.lstm_model

    def _export_to_onnx(self, input_size):
        """ONNX 변환 (ASCII 경로로 utf-8 에러 방지)"""
        try:
            self.lstm_model.eval()
            self.lstm_model.cpu()

            dummy_input = torch.randn(1, self.sequence_length, input_size)

            # ASCII 경로 사용 (한글 경로 회피)
            onnx_path = os.path.join(CACHE_DIR, 'model_temp.onnx')

            torch.onnx.export(
                self.lstm_model,
                dummy_input,
                onnx_path,
                input_names=['input'],
                output_names=['output'],
                dynamic_axes={
                    'input': {0: 'batch_size'},
                    'output': {0: 'batch_size'}
                },
                opset_version=18
            )

            self.onnx_session = ort.InferenceSession(
                onnx_path,
                providers=ONNX_PROVIDERS
            )

            provider_used = self.onnx_session.get_providers()[0]
            accel = "DirectML" if 'Dml' in provider_used else ("CUDA" if 'CUDA' in provider_used else "CPU")
            print(f"   ONNX {accel} acceleration OK")

        except Exception as e:
            self.onnx_session = None

    def _create_sequences(self, X):
        """시퀀스 데이터 생성"""
        X_values = X.values if hasattr(X, 'values') else X
        n = len(X_values) - self.sequence_length + 1
        if n <= 0:
            return np.array([])
        sequences = np.array([X_values[i:i+self.sequence_length] for i in range(n)])
        return sequences

    def predict(self, X_new):
        """앙상블 예측"""
        predictions = {}
        probabilities = {}

        if self.xgb_model is not None:
            xgb_pred = self.xgb_model.predict(X_new)
            xgb_prob = self.xgb_model.predict_proba(X_new)
            predictions['xgboost'] = xgb_pred
            probabilities['xgboost'] = xgb_prob

        if (self.onnx_session is not None or self.lstm_model is not None) and len(X_new) >= self.sequence_length:
            X_seq = self._create_sequences(X_new)
            if len(X_seq) > 0:
                lstm_out = None

                if self.onnx_session is not None:
                    try:
                        onnx_input = {self.onnx_session.get_inputs()[0].name: X_seq.astype(np.float32)}
                        lstm_out = self.onnx_session.run(None, onnx_input)[0]
                        exp_out = np.exp(lstm_out - np.max(lstm_out, axis=1, keepdims=True))
                        lstm_prob = exp_out / np.sum(exp_out, axis=1, keepdims=True)
                        lstm_pred = lstm_out.argmax(axis=1)
                    except Exception:
                        self.onnx_session = None
                        lstm_out = None

                if lstm_out is None and self.lstm_model is not None:
                    self.lstm_model.cpu()
                    X_t = torch.FloatTensor(X_seq)
                    self.lstm_model.eval()
                    with torch.no_grad():
                        lstm_out = self.lstm_model(X_t)
                        lstm_prob = torch.softmax(lstm_out, dim=1).cpu().numpy()
                        lstm_pred = lstm_out.argmax(dim=1).cpu().numpy()

                if lstm_out is not None:
                    predictions['lstm'] = lstm_pred
                    probabilities['lstm'] = lstm_prob

        # 앙상블
        if 'xgboost' in probabilities and 'lstm' in probabilities:
            offset = len(probabilities['xgboost']) - len(probabilities['lstm'])
            xgb_prob_aligned = probabilities['xgboost'][offset:]
            ensemble_prob = 0.4 * xgb_prob_aligned + 0.6 * probabilities['lstm']
            ensemble_pred = ensemble_prob.argmax(axis=1)
            predictions['ensemble'] = ensemble_pred
            probabilities['ensemble'] = ensemble_prob

        return predictions, probabilities

    def get_signal(self, prob):
        """확률 → 신호"""
        if prob[2] > 0.5:
            return "🚀 Strong Buy", prob[2]
        elif prob[2] > 0.35:
            return "📈 Buy", prob[2]
        elif prob[0] > 0.5:
            return "🔻 Sell", prob[0]
        elif prob[0] > 0.35:
            return "📉 Weak", prob[0]
        else:
            return "➡️ Hold", max(prob)


def _get_cache_key(tickers, value_mode):
    """캐시 키 생성 (날짜 + 종목 + 모드)"""
    today = datetime.now().strftime('%Y%m%d')
    ticker_hash = hashlib.md5(','.join(sorted(tickers)).encode()).hexdigest()[:8]
    mode = 'value' if value_mode else 'growth'
    return f"{today}_{mode}_{ticker_hash}"


def _save_model_cache(predictor, cache_key):
    """학습된 모델 캐시 저장"""
    try:
        cache_path = os.path.join(CACHE_DIR, f'{cache_key}_xgb.pkl')
        if predictor.xgb_model is not None:
            with open(cache_path, 'wb') as f:
                pickle.dump(predictor.xgb_model, f)

        if predictor.lstm_model is not None:
            lstm_path = os.path.join(CACHE_DIR, f'{cache_key}_lstm.pt')
            torch.save(predictor.lstm_model.state_dict(), lstm_path)

        # 메타데이터
        meta_path = os.path.join(CACHE_DIR, f'{cache_key}_meta.pkl')
        with open(meta_path, 'wb') as f:
            pickle.dump({
                'feature_columns': predictor.feature_columns,
                'sequence_length': predictor.sequence_length,
            }, f)

        print(f"   모델 캐시 저장 완료: {cache_key}")
    except Exception as e:
        print(f"   캐시 저장 실패: {e}")


def _load_model_cache(predictor, cache_key, input_size):
    """캐시된 모델 로드"""
    try:
        xgb_path = os.path.join(CACHE_DIR, f'{cache_key}_xgb.pkl')
        lstm_path = os.path.join(CACHE_DIR, f'{cache_key}_lstm.pt')
        meta_path = os.path.join(CACHE_DIR, f'{cache_key}_meta.pkl')

        if not (os.path.exists(xgb_path) and os.path.exists(meta_path)):
            return False

        with open(meta_path, 'rb') as f:
            meta = pickle.load(f)

        with open(xgb_path, 'rb') as f:
            predictor.xgb_model = pickle.load(f)

        predictor.feature_columns = meta['feature_columns']

        if os.path.exists(lstm_path) and PYTORCH_AVAILABLE:
            predictor.lstm_model = LSTMModel(input_size=input_size).to(TORCH_DEVICE)
            predictor.lstm_model.load_state_dict(torch.load(lstm_path, map_location=TORCH_DEVICE, weights_only=True))
            predictor.lstm_model.eval()

            if ONNX_AVAILABLE:
                predictor._export_to_onnx(input_size)

        print(f"   캐시된 모델 로드 완료: {cache_key}")
        return True
    except Exception:
        return False


def train_and_predict(tickers, save_models=True, value_mode=False):
    """풀링 학습: 모든 종목 데이터를 합쳐서 1개 모델 학습 → 각 종목 예측

    v1 대비 개선:
    - 종목별 학습 → 풀링 학습 (데이터 10배, 속도 5배)
    - 2년 → 5년 데이터
    - 시장 상대강도 피처 (SPY 대비)
    - 적응형 타겟 (변동성 기반 임계값)
    - 클래스 불균형 보정
    - 모델 캐시 (당일 재실행 시 즉시)
    """
    predictor = EnsemblePredictor(sequence_length=20, value_mode=value_mode)
    results = []

    mode_str = "가치주" if value_mode else "성장주"
    print(f"\n{'='*60}")
    print(f"📊 풀링 학습 모드: {mode_str} ({len(tickers)}개 종목)")
    print(f"{'='*60}")

    # === 1단계: 전체 종목 데이터 수집 ===
    print(f"\n📥 데이터 수집 중 ({len(tickers)}개)...")
    all_features = []
    all_targets = []
    ticker_data = {}  # 종목별 데이터 보관 (예측용)
    ticker_infos = {}

    spy_df = FeatureEngineer.get_spy_data('5y')

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period='5y')

            if len(df) < 200:
                print(f"   {ticker}: 데이터 부족 ({len(df)}일), 스킵")
                continue

            ticker_info = None
            try:
                ticker_info = stock.info
                ticker_infos[ticker] = ticker_info
            except Exception:
                pass

            features = FeatureEngineer.create_features(df, ticker_info, value_mode, spy_df)
            target = FeatureEngineer.create_adaptive_target(df, horizon=10)

            valid_idx = ~(features.isna().any(axis=1) | target.isna())
            features = features[valid_idx]
            target = target[valid_idx]
            df = df[valid_idx]

            if len(features) < 100:
                continue

            # 풀링용 (학습 데이터 - 마지막 60일 제외)
            train_cutoff = len(features) - 60
            all_features.append(features.iloc[:train_cutoff])
            all_targets.append(target.iloc[:train_cutoff])

            # 종목별 보관 (예측용)
            ticker_data[ticker] = {
                'df': df,
                'features': features,
                'target': target,
                'info': ticker_info
            }

            print(f"   {ticker}: {len(features)}일 로드 완료")

        except Exception as e:
            print(f"   {ticker}: 실패 - {str(e)[:40]}")
            continue

    if not all_features:
        print("데이터 수집 실패")
        return results

    # === 2단계: 종목별 시간순 Train/Val 분할 ===
    # (종목 A 전체 → train에, 종목 B 전체 → val에 가는 문제 방지)
    all_X_train, all_y_train = [], []
    all_X_val, all_y_val = [], []
    lstm_train_seq, lstm_train_y = [], []
    lstm_val_seq, lstm_val_y = [], []
    seq_len = predictor.sequence_length

    for feat, tgt in zip(all_features, all_targets):
        split = int(len(feat) * 0.8)
        X_tr, y_tr = feat.iloc[:split], tgt.iloc[:split]
        X_va, y_va = feat.iloc[split:], tgt.iloc[split:]

        # XGBoost용 (flat 데이터)
        all_X_train.append(X_tr)
        all_y_train.append(y_tr)
        all_X_val.append(X_va)
        all_y_val.append(y_va)

        # LSTM용: 종목별 시퀀스 생성 (종목 경계 크로스 방지)
        tr_seq = predictor._create_sequences(X_tr)
        if len(tr_seq) > 0:
            tr_y = y_tr.iloc[seq_len-1:].values[:len(tr_seq)]
            lstm_train_seq.append(tr_seq)
            lstm_train_y.append(tr_y)
        va_seq = predictor._create_sequences(X_va)
        if len(va_seq) > 0:
            va_y = y_va.iloc[seq_len-1:].values[:len(va_seq)]
            lstm_val_seq.append(va_seq)
            lstm_val_y.append(va_y)

    X_train = pd.concat(all_X_train, ignore_index=True)
    y_train = pd.concat(all_y_train, ignore_index=True)
    X_val = pd.concat(all_X_val, ignore_index=True)
    y_val = pd.concat(all_y_val, ignore_index=True)

    # LSTM 시퀀스 결합
    pre_sequences = None
    if lstm_train_seq and lstm_val_seq:
        lstm_X_tr = np.concatenate(lstm_train_seq)
        lstm_y_tr = np.concatenate(lstm_train_y)
        lstm_X_va = np.concatenate(lstm_val_seq)
        lstm_y_va = np.concatenate(lstm_val_y)
        pre_sequences = (lstm_X_tr, lstm_y_tr, lstm_X_va, lstm_y_va)

    # 피처 컬럼 통일
    predictor.feature_columns = X_train.columns.tolist()
    total_samples = len(X_train) + len(X_val)

    print(f"\n📊 풀링 데이터: {total_samples:,}일 x {len(predictor.feature_columns)}피처")

    # 클래스 분포 확인
    all_tgt = pd.concat([y_train, y_val])
    class_dist = all_tgt.value_counts().sort_index()
    print(f"   클래스 분포: 하락={class_dist.get(0,0):,} / 보합={class_dist.get(1,0):,} / 상승={class_dist.get(2,0):,}")
    if pre_sequences:
        print(f"   LSTM 시퀀스: Train {len(pre_sequences[0]):,} / Val {len(pre_sequences[2]):,} (종목별 생성)")

    # === 3단계: 캐시 확인 ===
    cache_key = _get_cache_key(tickers, value_mode)
    input_size = len(predictor.feature_columns)

    if _load_model_cache(predictor, cache_key, input_size):
        print("   캐시된 모델로 예측 진행!")
    else:
        # === 4단계: 모델 학습 ===
        print(f"\n🔧 풀링 모델 학습 (Train: {len(X_train):,} / Val: {len(X_val):,})")

        predictor.train_xgboost(X_train, y_train, X_val, y_val)
        predictor.train_lstm(X_train, y_train, X_val, y_val, epochs=80, batch_size=64,
                           pre_sequences=pre_sequences)

        if save_models:
            _save_model_cache(predictor, cache_key)

    # === 5단계: 각 종목 예측 ===
    print(f"\n🎯 종목별 예측 중...")

    for ticker in tickers:
        if ticker not in ticker_data:
            continue

        data = ticker_data[ticker]
        features = data['features']
        df = data['df']
        info = data['info']

        try:
            # 피처 컬럼 맞추기 (풀링 학습 시 컬럼과 동일)
            for col in predictor.feature_columns:
                if col not in features.columns:
                    features[col] = 0
            features = features[predictor.feature_columns]

            recent = features.iloc[-40:]
            predictions, probabilities = predictor.predict(recent)

            if 'ensemble' in probabilities:
                latest_prob = probabilities['ensemble'][-1]
            elif 'xgboost' in probabilities:
                latest_prob = probabilities['xgboost'][-1]
            else:
                continue

            signal, confidence = predictor.get_signal(latest_prob)

            # 실시간 가격
            try:
                if info:
                    current_price = info.get('currentPrice') or info.get('regularMarketPrice') or df['Close'].iloc[-1]
                else:
                    current_price = yf.Ticker(ticker).info.get('currentPrice') or df['Close'].iloc[-1]
            except Exception:
                current_price = df['Close'].iloc[-1]

            result = {
                'ticker': ticker,
                'price': current_price,
                'signal': signal,
                'confidence': confidence,
                'prob_down': latest_prob[0],
                'prob_neutral': latest_prob[1],
                'prob_up': latest_prob[2],
                'market_cap': info.get('marketCap', 0) if info else 0,
                'avg_volume': info.get('averageVolume', 0) if info else 0
            }

            if value_mode and info:
                result['dividend_yield'] = info.get('dividendYield', 0) or 0
                result['pe_ratio'] = info.get('trailingPE', 0) or 0
                result['pb_ratio'] = info.get('priceToBook', 0) or 0
                result['value_score'] = features['value_score'].iloc[-1] if 'value_score' in features.columns else 0

            results.append(result)

            print(f"   {ticker}: ${current_price:.2f} | {signal} ({confidence:.1%}) | "
                  f"[{latest_prob[0]:.0%}/{latest_prob[1]:.0%}/{latest_prob[2]:.0%}]")

        except Exception as e:
            print(f"   {ticker}: 예측 실패 - {str(e)[:40]}")
            continue

    return results


def quick_predict(ticker):
    """단일 종목 빠른 예측"""
    predictor = EnsemblePredictor(sequence_length=20)

    print(f"\n🔮 {ticker} AI 예측 분석")
    print("="*50)

    df, features, target, _ = predictor.prepare_data(ticker, period='5y')
    if df is None:
        return None

    split_idx = int(len(features) * 0.8)
    X_train = features.iloc[:split_idx]
    y_train = target.iloc[:split_idx]
    X_val = features.iloc[split_idx:]
    y_val = target.iloc[split_idx:]

    predictor.train_xgboost(X_train, y_train, X_val, y_val)
    predictor.train_lstm(X_train, y_train, X_val, y_val, epochs=80)

    recent = features.iloc[-40:]
    predictions, probabilities = predictor.predict(recent)

    if 'ensemble' in probabilities:
        latest_prob = probabilities['ensemble'][-1]
    else:
        latest_prob = probabilities.get('xgboost', [[0.33, 0.34, 0.33]])[-1]

    signal, confidence = predictor.get_signal(latest_prob)

    print(f"\n📊 결과:")
    print(f"   현재가: ${df['Close'].iloc[-1]:.2f}")
    print(f"   AI 신호: {signal}")
    print(f"   신뢰도: {confidence:.1%}")
    print(f"   10일 후 예측 확률:")
    print(f"      하락: {latest_prob[0]:.1%}")
    print(f"      보합: {latest_prob[1]:.1%}")
    print(f"      상승: {latest_prob[2]:.1%}")

    return {
        'ticker': ticker,
        'price': df['Close'].iloc[-1],
        'signal': signal,
        'confidence': confidence,
        'probabilities': latest_prob
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    print("ML Predictor v2.0 - Pooled Training + Market Relative Strength")

    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        quick_predict(ticker)
    else:
        test_tickers = ['NVDA', 'AAPL', 'MSFT', 'GOOGL', 'TSLA']
        results = train_and_predict(test_tickers)

        print("\n" + "="*60)
        print("Results Summary")
        print("="*60)
        for r in results:
            print(f"{r['ticker']:6s} | ${r['price']:8.2f} | {r['signal']:15s} | {r['confidence']:.1%}")
