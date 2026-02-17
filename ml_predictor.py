"""
ML Predictor - AI/ML 기반 주가 예측 모델
CPU(XGBoost) + GPU(LSTM) 앙상블 방식
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# CPU: XGBoost
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("⚠️ XGBoost 미설치: pip install xgboost")

# GPU: PyTorch + ONNX Runtime (CUDA / DirectML / CPU)
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    PYTORCH_AVAILABLE = True
    TORCH_DEVICE = torch.device('cpu')  # 학습은 CPU

    if torch.cuda.is_available():
        TORCH_DEVICE = torch.device('cuda')
        print(f"🎮 NVIDIA GPU (학습+추론): {torch.cuda.get_device_name(0)}")

except ImportError:
    PYTORCH_AVAILABLE = False
    TORCH_DEVICE = 'cpu'
    print("⚠️ PyTorch 미설치: pip install torch")

# ONNX Runtime with DirectML (AMD GPU 추론 가속)
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True

    # DirectML provider 확인 (AMD/Intel GPU)
    providers = ort.get_available_providers()
    if 'DmlExecutionProvider' in providers:
        ONNX_PROVIDERS = ['DmlExecutionProvider', 'CPUExecutionProvider']
        print("🎮 AMD/Intel GPU 감지: DirectML 추론 가속 활성화")
    elif 'CUDAExecutionProvider' in providers:
        ONNX_PROVIDERS = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        print("🎮 NVIDIA GPU 감지: CUDA 추론 가속 활성화")
    else:
        ONNX_PROVIDERS = ['CPUExecutionProvider']
        print("🖥️ ONNX Runtime CPU 모드")
except ImportError:
    ONNX_AVAILABLE = False
    ONNX_PROVIDERS = []
    print("⚠️ ONNX Runtime 미설치: pip install onnxruntime-directml")

# 기술 지표 라이브러리
from ta.trend import MACD, ADXIndicator, SMAIndicator, EMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator


class FeatureEngineer:
    """기술 지표 + 가치투자 피처 생성"""

    @staticmethod
    def create_features(df, ticker_info=None, value_mode=False):
        """주가 데이터에서 ML 피처 생성

        Args:
            df: 주가 데이터 (OHLCV)
            ticker_info: yfinance ticker.info 딕셔너리 (가치주 모드용)
            value_mode: True면 가치투자 피처 추가
        """
        features = pd.DataFrame(index=df.index)

        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']

        # 1. 가격 기반 피처
        features['return_1d'] = close.pct_change(1)
        features['return_5d'] = close.pct_change(5)
        features['return_10d'] = close.pct_change(10)
        features['return_20d'] = close.pct_change(20)

        # 2. 이동평균
        features['sma_5'] = SMAIndicator(close, window=5).sma_indicator() / close - 1
        features['sma_10'] = SMAIndicator(close, window=10).sma_indicator() / close - 1
        features['sma_20'] = SMAIndicator(close, window=20).sma_indicator() / close - 1
        features['sma_50'] = SMAIndicator(close, window=50).sma_indicator() / close - 1
        features['ema_12'] = EMAIndicator(close, window=12).ema_indicator() / close - 1
        features['ema_26'] = EMAIndicator(close, window=26).ema_indicator() / close - 1

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
        features['bb_high'] = bb.bollinger_hband() / close - 1
        features['bb_low'] = bb.bollinger_lband() / close - 1
        features['bb_width'] = (bb.bollinger_hband() - bb.bollinger_lband()) / close

        # 6. ATR (변동성)
        atr = AverageTrueRange(high, low, close)
        features['atr'] = atr.average_true_range() / close

        # 7. ADX (추세 강도)
        adx = ADXIndicator(high, low, close)
        features['adx'] = adx.adx() / 100
        features['adx_pos'] = adx.adx_pos() / 100
        features['adx_neg'] = adx.adx_neg() / 100

        # 8. 거래량 지표
        features['volume_change'] = volume.pct_change(1)
        features['volume_ma_ratio'] = volume / volume.rolling(20).mean()
        obv = OnBalanceVolumeIndicator(close, volume)
        features['obv_change'] = obv.on_balance_volume().pct_change(5)

        # 9. 가격 위치
        features['high_low_ratio'] = (close - low) / (high - low + 1e-10)
        features['close_to_high'] = close / high.rolling(20).max() - 1
        features['close_to_low'] = close / low.rolling(20).min() - 1

        # 10. 52주 가격 위치 (가치투자용)
        features['price_52w_high'] = close / close.rolling(252).max() - 1  # 52주 고점 대비
        features['price_52w_low'] = close / close.rolling(252).min() - 1   # 52주 저점 대비
        features['price_52w_position'] = (close - close.rolling(252).min()) / \
                                         (close.rolling(252).max() - close.rolling(252).min() + 1e-10)

        # ===== 가치투자 피처 (value_mode) =====
        if value_mode and ticker_info:
            # 배당률 (Dividend Yield)
            div_yield = ticker_info.get('dividendYield', 0) or 0
            features['dividend_yield'] = div_yield

            # 배당률 매력도 (3% 이상 = 1, 2-3% = 0.5, 2% 미만 = 0)
            if div_yield >= 0.03:
                features['dividend_attractive'] = 1.0
            elif div_yield >= 0.02:
                features['dividend_attractive'] = 0.5
            else:
                features['dividend_attractive'] = 0.0

            # PER (낮을수록 저평가)
            pe_ratio = ticker_info.get('trailingPE', 0) or ticker_info.get('forwardPE', 0) or 30
            features['pe_ratio'] = min(pe_ratio / 100, 1.0)  # 정규화
            # PER 매력도 (15 이하 = 매력적)
            features['pe_attractive'] = max(0, 1 - pe_ratio / 30) if pe_ratio > 0 else 0

            # PBR (낮을수록 저평가)
            pb_ratio = ticker_info.get('priceToBook', 0) or 3
            features['pb_ratio'] = min(pb_ratio / 10, 1.0)  # 정규화
            # PBR 매력도 (1.5 이하 = 매력적)
            features['pb_attractive'] = max(0, 1 - pb_ratio / 3) if pb_ratio > 0 else 0

            # Payout Ratio (배당성향 - 30-60%가 이상적)
            payout = ticker_info.get('payoutRatio', 0) or 0
            features['payout_ratio'] = min(payout, 1.0)
            # 배당성향 적정성 (30-60% = 1, 그 외 = 감소)
            if 0.3 <= payout <= 0.6:
                features['payout_healthy'] = 1.0
            elif 0.2 <= payout < 0.3 or 0.6 < payout <= 0.8:
                features['payout_healthy'] = 0.5
            else:
                features['payout_healthy'] = 0.0

            # ROE (높을수록 좋음)
            roe = ticker_info.get('returnOnEquity', 0) or 0
            features['roe'] = min(max(roe, 0), 0.5)  # 0-50% 범위로 클리핑
            features['roe_attractive'] = 1.0 if roe >= 0.15 else (roe / 0.15 if roe > 0 else 0)

            # 부채비율 (낮을수록 안전)
            debt_equity = ticker_info.get('debtToEquity', 0) or 0
            features['debt_equity'] = min(debt_equity / 200, 1.0)  # 정규화
            features['low_debt'] = 1.0 if debt_equity < 50 else max(0, 1 - debt_equity / 150)

            # FCF Yield (Free Cash Flow / Market Cap)
            fcf = ticker_info.get('freeCashflow', 0) or 0
            market_cap = ticker_info.get('marketCap', 1) or 1
            fcf_yield = fcf / market_cap if market_cap > 0 else 0
            features['fcf_yield'] = max(min(fcf_yield, 0.2), -0.1)  # -10% ~ 20% 범위

            # 가치투자 종합 점수 (배당 비중 축소, PER/ROE 강화)
            features['value_score'] = (
                features['dividend_attractive'] * 0.10 +  # 배당률: 25% → 10%
                features['pe_attractive'] * 0.30 +        # PER: 20% → 30% (저평가 중시)
                features['pb_attractive'] * 0.15 +        # PBR: 15% 유지
                features['roe_attractive'] * 0.25 +       # ROE: 20% → 25% (수익성 중시)
                features['low_debt'] * 0.10 +             # 저부채: 10% 유지
                features['payout_healthy'] * 0.10         # 배당성향: 10% 유지
            )

        # NaN 처리
        features = features.replace([np.inf, -np.inf], np.nan)
        features = features.fillna(0)

        return features

    @staticmethod
    def create_target(df, horizon=5, threshold=0.02):
        """예측 타겟 생성 (N일 후 상승/하락)"""
        future_return = df['Close'].shift(-horizon) / df['Close'] - 1
        # 0: 하락, 1: 보합, 2: 상승
        target = pd.cut(future_return,
                       bins=[-np.inf, -threshold, threshold, np.inf],
                       labels=[0, 1, 2]).astype(float)
        return target


class LSTMModel(nn.Module):
    """LSTM 기반 시계열 예측 모델 (GPU 활용)"""

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
        # LSTM
        lstm_out, _ = self.lstm(x)

        # Self-Attention
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)

        # 마지막 시점 출력
        out = attn_out[:, -1, :]

        # FC layers
        out = self.dropout(self.relu(self.fc1(out)))
        out = self.fc2(out)

        return out


class EnsemblePredictor:
    """앙상블 예측기 (XGBoost + LSTM with ONNX DirectML)"""

    def __init__(self, sequence_length=20, value_mode=False):
        self.sequence_length = sequence_length
        self.value_mode = value_mode  # 가치주 모드
        self.xgb_model = None
        self.lstm_model = None
        self.onnx_session = None  # ONNX Runtime 세션 (DirectML 가속)
        self.feature_engineer = FeatureEngineer()
        self.feature_columns = None
        self.ticker_info = None  # 가치주 펀더멘털 정보

    def prepare_data(self, ticker, period='2y'):
        """데이터 준비"""
        print(f"📥 {ticker} 데이터 다운로드 중...")
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)

        if len(df) < 100:
            print(f"⚠️ {ticker}: 데이터 부족 ({len(df)}일)")
            return None, None, None

        # 가치주 모드: 펀더멘털 정보 가져오기
        ticker_info = None
        if self.value_mode:
            try:
                ticker_info = stock.info
                self.ticker_info = ticker_info
                div_yield = ticker_info.get('dividendYield', 0) or 0
                pe_ratio = ticker_info.get('trailingPE', 0) or 0
                pb_ratio = ticker_info.get('priceToBook', 0) or 0
                print(f"   📊 가치지표: 배당률 {div_yield*100:.1f}%, PER {pe_ratio:.1f}, PBR {pb_ratio:.1f}")
            except Exception as e:
                print(f"   ⚠️ 펀더멘털 정보 로드 실패: {str(e)[:30]}")

        # 피처 생성 (가치주 모드면 추가 피처 포함)
        features = self.feature_engineer.create_features(df, ticker_info, self.value_mode)
        target = self.feature_engineer.create_target(df, horizon=5, threshold=0.02)

        # NaN 제거
        valid_idx = ~(features.isna().any(axis=1) | target.isna())
        features = features[valid_idx]
        target = target[valid_idx]
        df = df[valid_idx]

        self.feature_columns = features.columns.tolist()

        return df, features, target

    def train_xgboost(self, X_train, y_train, X_val, y_val):
        """XGBoost 모델 학습 (CPU)"""
        if not XGBOOST_AVAILABLE:
            return None

        print("🔧 XGBoost 학습 중 (CPU)...")

        # CPU 코어 전체 활용
        import os
        n_jobs = os.cpu_count()

        self.xgb_model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            n_jobs=n_jobs,
            random_state=42,
            use_label_encoder=False,
            eval_metric='mlogloss'
        )

        self.xgb_model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )

        # 검증 정확도
        val_acc = (self.xgb_model.predict(X_val) == y_val).mean()
        print(f"   XGBoost 검증 정확도: {val_acc:.2%}")

        return self.xgb_model

    def train_lstm(self, X_train, y_train, X_val, y_val, epochs=50, batch_size=32):
        """LSTM 모델 학습 + ONNX 변환 (DirectML 추론 가속)"""
        if not PYTORCH_AVAILABLE:
            return None

        print(f"🔧 LSTM 학습 중 ({TORCH_DEVICE})...")

        # 시퀀스 데이터 생성
        X_train_seq = self._create_sequences(X_train)
        X_val_seq = self._create_sequences(X_val)
        y_train_seq = y_train[self.sequence_length-1:]
        y_val_seq = y_val[self.sequence_length-1:]

        # Tensor 변환
        X_train_t = torch.FloatTensor(X_train_seq).to(TORCH_DEVICE)
        y_train_t = torch.LongTensor(y_train_seq.values).to(TORCH_DEVICE)
        X_val_t = torch.FloatTensor(X_val_seq).to(TORCH_DEVICE)
        y_val_t = torch.LongTensor(y_val_seq.values).to(TORCH_DEVICE)

        # DataLoader
        train_dataset = TensorDataset(X_train_t, y_train_t)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

        # 모델 초기화
        input_size = X_train_seq.shape[2]
        self.lstm_model = LSTMModel(input_size=input_size).to(TORCH_DEVICE)

        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.AdamW(self.lstm_model.parameters(), lr=0.001, weight_decay=0.01)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

        best_val_acc = 0
        patience = 10
        patience_counter = 0

        for epoch in range(epochs):
            # 학습
            self.lstm_model.train()
            train_loss = 0
            for X_batch, y_batch in train_loader:
                optimizer.zero_grad()
                outputs = self.lstm_model(X_batch)
                loss = criterion(outputs, y_batch)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.lstm_model.parameters(), 1.0)
                optimizer.step()
                train_loss += loss.item()

            scheduler.step()

            # 검증
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
                print(f"   Early stopping at epoch {epoch+1}")
                break

            if (epoch + 1) % 10 == 0:
                print(f"   Epoch {epoch+1}/{epochs} - Val Acc: {val_acc:.2%}")

        # 최적 모델 로드
        self.lstm_model.load_state_dict(best_model_state)
        print(f"   LSTM 최고 검증 정확도: {best_val_acc:.2%}")

        # ONNX 변환 (DirectML 추론 가속용)
        if ONNX_AVAILABLE:
            self._export_to_onnx(X_train_seq.shape[2])

        return self.lstm_model

    def _export_to_onnx(self, input_size):
        """LSTM 모델을 ONNX로 변환"""
        try:
            print("🔄 ONNX 변환 중 (DirectML 가속 준비)...")
            self.lstm_model.eval()
            self.lstm_model.cpu()

            # 더미 입력
            dummy_input = torch.randn(1, self.sequence_length, input_size)

            # ONNX 내보내기 (opset 18 for better DirectML compatibility)
            import io
            import tempfile
            import os

            # 임시 파일로 저장 후 로드 (더 안정적)
            with tempfile.NamedTemporaryFile(suffix='.onnx', delete=False) as f:
                temp_path = f.name

            torch.onnx.export(
                self.lstm_model,
                dummy_input,
                temp_path,
                input_names=['input'],
                output_names=['output'],
                dynamic_axes={
                    'input': {0: 'batch_size'},
                    'output': {0: 'batch_size'}
                },
                opset_version=18
            )

            # ONNX Runtime 세션 생성 (DirectML 사용)
            self.onnx_session = ort.InferenceSession(
                temp_path,
                providers=ONNX_PROVIDERS
            )

            # 임시 파일 삭제
            try:
                os.unlink(temp_path)
            except:
                pass

            provider_used = self.onnx_session.get_providers()[0]
            if 'Dml' in provider_used:
                print("   ✅ ONNX 변환 완료 - AMD GPU(DirectML) 추론 가속 활성화!")
            elif 'CUDA' in provider_used:
                print("   ✅ ONNX 변환 완료 - NVIDIA GPU(CUDA) 추론 가속 활성화!")
            else:
                print("   ✅ ONNX 변환 완료 - CPU 추론")

        except Exception as e:
            print(f"   ⚠️ ONNX 변환 실패 (PyTorch 추론 사용): {e}")
            self.onnx_session = None

    def _create_sequences(self, X):
        """시퀀스 데이터 생성"""
        sequences = []
        X_values = X.values if hasattr(X, 'values') else X
        for i in range(len(X_values) - self.sequence_length + 1):
            sequences.append(X_values[i:i+self.sequence_length])
        return np.array(sequences)

    def predict(self, X_new):
        """앙상블 예측"""
        predictions = {}
        probabilities = {}

        # XGBoost 예측
        if self.xgb_model is not None:
            xgb_pred = self.xgb_model.predict(X_new)
            xgb_prob = self.xgb_model.predict_proba(X_new)
            predictions['xgboost'] = xgb_pred
            probabilities['xgboost'] = xgb_prob

        # LSTM 예측 (ONNX Runtime with DirectML 우선)
        if (self.onnx_session is not None or self.lstm_model is not None) and len(X_new) >= self.sequence_length:
            X_seq = self._create_sequences(X_new)
            if len(X_seq) > 0:
                lstm_out = None

                # ONNX Runtime 사용 시도 (DirectML GPU 가속)
                if self.onnx_session is not None:
                    try:
                        onnx_input = {self.onnx_session.get_inputs()[0].name: X_seq.astype(np.float32)}
                        lstm_out = self.onnx_session.run(None, onnx_input)[0]
                        # Softmax 적용
                        exp_out = np.exp(lstm_out - np.max(lstm_out, axis=1, keepdims=True))
                        lstm_prob = exp_out / np.sum(exp_out, axis=1, keepdims=True)
                        lstm_pred = lstm_out.argmax(axis=1)
                    except Exception as e:
                        print(f"   ⚠️ ONNX 추론 실패, PyTorch 사용: {str(e)[:50]}...")
                        self.onnx_session = None  # 다음부터 PyTorch 사용
                        lstm_out = None

                # PyTorch fallback
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

        # 앙상블 (가중 평균)
        if 'xgboost' in probabilities and 'lstm' in probabilities:
            # LSTM은 시퀀스 길이만큼 짧음
            offset = len(probabilities['xgboost']) - len(probabilities['lstm'])
            xgb_prob_aligned = probabilities['xgboost'][offset:]

            # 가중 평균 (XGBoost 0.4, LSTM 0.6)
            ensemble_prob = 0.4 * xgb_prob_aligned + 0.6 * probabilities['lstm']
            ensemble_pred = ensemble_prob.argmax(axis=1)

            predictions['ensemble'] = ensemble_pred
            probabilities['ensemble'] = ensemble_prob

        return predictions, probabilities

    def get_signal(self, prob):
        """확률을 신호로 변환"""
        # prob: [하락, 보합, 상승] 확률
        if prob[2] > 0.5:  # 상승 확률 50% 이상
            return "🚀 Strong Buy", prob[2]
        elif prob[2] > 0.35:  # 상승 확률 35% 이상
            return "📈 Buy", prob[2]
        elif prob[0] > 0.5:  # 하락 확률 50% 이상
            return "🔻 Sell", prob[0]
        elif prob[0] > 0.35:  # 하락 확률 35% 이상
            return "📉 Weak", prob[0]
        else:
            return "➡️ Hold", max(prob)


def train_and_predict(tickers, save_models=True, value_mode=False):
    """여러 종목에 대해 학습 및 예측

    Args:
        tickers: 분석할 종목 리스트
        save_models: 모델 저장 여부
        value_mode: True면 가치투자 피처 사용 (배당률, PER, PBR 등)
    """
    predictor = EnsemblePredictor(sequence_length=20, value_mode=value_mode)
    results = []

    mode_str = "가치주" if value_mode else "성장주"
    print(f"\n🔍 분석 모드: {mode_str}")

    for ticker in tickers:
        print(f"\n{'='*50}")
        print(f"📊 {ticker} 분석 중... [{mode_str} 모드]")
        print('='*50)

        try:
            # 데이터 준비 (value_mode면 펀더멘털 피처 포함)
            df, features, target = predictor.prepare_data(ticker, period='2y')
            if df is None:
                continue

            # Train/Val 분할 (시간순)
            split_idx = int(len(features) * 0.8)
            X_train = features.iloc[:split_idx]
            y_train = target.iloc[:split_idx]
            X_val = features.iloc[split_idx:]
            y_val = target.iloc[split_idx:]

            # 모델 학습
            predictor.train_xgboost(X_train, y_train, X_val, y_val)
            predictor.train_lstm(X_train, y_train, X_val, y_val, epochs=30)

            # 최신 데이터로 예측
            recent_features = features.iloc[-30:]
            predictions, probabilities = predictor.predict(recent_features)

            # 최신 예측 결과
            if 'ensemble' in probabilities:
                latest_prob = probabilities['ensemble'][-1]
                signal, confidence = predictor.get_signal(latest_prob)
            elif 'xgboost' in probabilities:
                latest_prob = probabilities['xgboost'][-1]
                signal, confidence = predictor.get_signal(latest_prob)
            else:
                signal, confidence = "❓ Unknown", 0

            current_price = df['Close'].iloc[-1]

            result = {
                'ticker': ticker,
                'price': current_price,
                'signal': signal,
                'confidence': confidence,
                'prob_down': latest_prob[0],
                'prob_neutral': latest_prob[1],
                'prob_up': latest_prob[2]
            }

            # 가치주 모드: 추가 정보
            if value_mode and predictor.ticker_info:
                result['dividend_yield'] = predictor.ticker_info.get('dividendYield', 0) or 0
                result['pe_ratio'] = predictor.ticker_info.get('trailingPE', 0) or 0
                result['pb_ratio'] = predictor.ticker_info.get('priceToBook', 0) or 0
                result['value_score'] = features['value_score'].iloc[-1] if 'value_score' in features.columns else 0

            results.append(result)

            print(f"\n🎯 {ticker} 예측 결과:")
            print(f"   현재가: ${current_price:.2f}")
            print(f"   신호: {signal} (신뢰도: {confidence:.1%})")
            print(f"   확률 - 하락: {latest_prob[0]:.1%}, 보합: {latest_prob[1]:.1%}, 상승: {latest_prob[2]:.1%}")

            if value_mode and predictor.ticker_info:
                div_y = predictor.ticker_info.get('dividendYield', 0) or 0
                print(f"   💰 가치점수: {result.get('value_score', 0):.2f} | 배당률: {div_y*100:.1f}%")

        except Exception as e:
            print(f"❌ {ticker} 분석 실패: {e}")
            continue

    return results


def quick_predict(ticker):
    """단일 종목 빠른 예측"""
    predictor = EnsemblePredictor(sequence_length=20)

    print(f"\n🔮 {ticker} AI 예측 분석")
    print("="*50)

    # 데이터 준비
    df, features, target = predictor.prepare_data(ticker, period='2y')
    if df is None:
        return None

    # Train/Val 분할
    split_idx = int(len(features) * 0.8)
    X_train = features.iloc[:split_idx]
    y_train = target.iloc[:split_idx]
    X_val = features.iloc[split_idx:]
    y_val = target.iloc[split_idx:]

    # 모델 학습
    predictor.train_xgboost(X_train, y_train, X_val, y_val)
    predictor.train_lstm(X_train, y_train, X_val, y_val, epochs=30)

    # 예측
    recent_features = features.iloc[-30:]
    predictions, probabilities = predictor.predict(recent_features)

    if 'ensemble' in probabilities:
        latest_prob = probabilities['ensemble'][-1]
    else:
        latest_prob = probabilities.get('xgboost', [[0.33, 0.34, 0.33]])[-1]

    signal, confidence = predictor.get_signal(latest_prob)

    print(f"\n📊 결과:")
    print(f"   현재가: ${df['Close'].iloc[-1]:.2f}")
    print(f"   AI 신호: {signal}")
    print(f"   신뢰도: {confidence:.1%}")
    print(f"   5일 후 예측 확률:")
    print(f"      📉 하락 (-2% 이상): {latest_prob[0]:.1%}")
    print(f"      ➡️ 보합 (-2% ~ +2%): {latest_prob[1]:.1%}")
    print(f"      📈 상승 (+2% 이상): {latest_prob[2]:.1%}")

    return {
        'ticker': ticker,
        'price': df['Close'].iloc[-1],
        'signal': signal,
        'confidence': confidence,
        'probabilities': latest_prob
    }


if __name__ == "__main__":
    import sys

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║            ML PREDICTOR - AI 주가 예측 시스템             ║
    ║                  XGBoost (CPU) + LSTM (GPU)              ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        quick_predict(ticker)
    else:
        # 테스트: 주요 기술주 예측
        test_tickers = ['NVDA', 'AAPL', 'MSFT', 'GOOGL', 'TSLA']
        results = train_and_predict(test_tickers)

        print("\n" + "="*60)
        print("📊 전체 예측 결과 요약")
        print("="*60)
        for r in results:
            print(f"{r['ticker']:6s} | ${r['price']:8.2f} | {r['signal']:15s} | 신뢰도: {r['confidence']:.1%}")
