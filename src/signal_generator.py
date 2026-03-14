"""
Signal Generator Module
Generates trading signals using LSTM + Gradient Boosting Classifier confirmation
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from typing import Tuple, Optional, Dict
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalGenerator:
    """Generates trading signals using LSTM + GBC confirmation"""
    
    def __init__(
        self,
        lstm_predictor,
        min_confidence: float = 0.65,
        use_gbc_confirmation: bool = True
    ):
        """
        Initialize Signal Generator
        
        Args:
            lstm_predictor: Trained LSTM model
            min_confidence: Minimum confidence to generate signal
            use_gbc_confirmation: Use GBC as secondary confirmation
        """
        self.lstm_predictor = lstm_predictor
        self.min_confidence = min_confidence
        self.use_gbc_confirmation = use_gbc_confirmation
        self.gbc_model = None
        self.gbc_scaler = StandardScaler()
        self.gbc_features = None
        self.signal_history = []
    
    def train_gbc(
        self,
        df: pd.DataFrame,
        lookback: int = 60,
        feature_cols: list = None
    ):
        """
        Train Gradient Boosting Classifier for signal confirmation
        
        Args:
            df: Training DataFrame with OHLCV and features
            lookback: Number of periods to look back
            feature_cols: Columns to use for GBC
        """
        if feature_cols is None:
            feature_cols = ['rsi', 'macd', 'volume_change', 'volatility', 'hl_range']
        
        self.gbc_features = [col for col in feature_cols if col in df.columns]
        
        if not self.gbc_features:
            logger.warning("No valid GBC features found")
            self.use_gbc_confirmation = False
            return
        
        # Prepare training data
        X = []
        y = []
        
        for i in range(lookback, len(df)):
            X.append(df[self.gbc_features].iloc[i-lookback:i].mean())
            
            # Target: 1 if next close > current close
            next_close = df['close'].iloc[i]
            current_close = df['close'].iloc[i-1]
            y.append(1 if next_close > current_close else 0)
        
        if len(X) < 10:
            logger.warning("Insufficient data for GBC training")
            return
        
        X = np.array(X)
        y = np.array(y)
        
        # Scale and train
        X_scaled = self.gbc_scaler.fit_transform(X)
        
        self.gbc_model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42,
            verbose=0
        )
        
        self.gbc_model.fit(X_scaled, y)
        
        # Evaluate
        accuracy = self.gbc_model.score(X_scaled, y)
        logger.info(f"GBC model trained with accuracy: {accuracy:.4f}")
    
    def _get_gbc_confirmation(
        self,
        df: pd.DataFrame,
        lookback: int = 60
    ) -> Tuple[str, float]:
        """
        Get confirmation signal from GBC model
        
        Args:
            df: DataFrame with latest data
            lookback: Lookback period
        
        Returns:
            Tuple of (direction, confidence)
        """
        if self.gbc_model is None or not self.gbc_features:
            return None, 0.0
        
        if len(df) < lookback:
            return None, 0.0
        
        try:
            # Get recent feature means
            recent_features = df[self.gbc_features].iloc[-lookback:].mean().values
            recent_features = recent_features.reshape(1, -1)
            
            # Scale and predict
            X_scaled = self.gbc_scaler.transform(recent_features)
            
            prediction = self.gbc_model.predict(X_scaled)[0]
            probability = self.gbc_model.predict_proba(X_scaled)[0]
            
            direction = "UP" if prediction == 1 else "DOWN"
            confidence = float(max(probability))
            
            return direction, confidence
        except Exception as e:
            logger.error(f"GBC prediction error: {e}")
            return None, 0.0
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float,
        lookback: int = 60
    ) -> Optional[Dict]:
        """
        Generate trading signal using LSTM + GBC
        
        Args:
            df: DataFrame with OHLCV and features (scaled for LSTM)
            current_price: Current market price
            lookback: Lookback period for LSTM
        
        Returns:
            Signal dictionary or None if no signal
        """
        if len(df) < lookback:
            logger.warning(f"Insufficient data: {len(df)} < {lookback}")
            return None
        
        # LSTM prediction
        lstm_data = df[self.lstm_predictor.feature_columns or ['close']].values
        lstm_data_scaled = self.lstm_predictor.scaler.transform(lstm_data)
        lstm_direction, lstm_confidence = self.lstm_predictor.predict(
            lstm_data_scaled[-lookback:]
        )
        
        logger.debug(f"LSTM: {lstm_direction} ({lstm_confidence:.2%})")
        
        # Check LSTM confidence
        if lstm_confidence < self.min_confidence:
            logger.debug(f"LSTM confidence {lstm_confidence:.2%} below threshold {self.min_confidence:.2%}")
            return None
        
        # GBC confirmation
        signal = {
            'timestamp': datetime.now(),
            'pair': 'USD/BDT',
            'current_price': current_price,
            'lstm_direction': lstm_direction,
            'lstm_confidence': lstm_confidence,
            'gbc_direction': None,
            'gbc_confidence': 0.0,
            'confirmed': False,
            'final_direction': None,
            'final_confidence': 0.0,
        }
        
        if self.use_gbc_confirmation and self.gbc_model:
            gbc_dir, gbc_conf = self._get_gbc_confirmation(df, lookback)
            signal['gbc_direction'] = gbc_dir
            signal['gbc_confidence'] = gbc_conf
            
            # Both models must agree for confirmation
            if gbc_dir and gbc_dir == lstm_direction and gbc_conf >= self.min_confidence:
                signal['confirmed'] = True
                signal['final_direction'] = lstm_direction
                signal['final_confidence'] = (lstm_confidence + gbc_conf) / 2
                
                logger.debug(f"Signal CONFIRMED: {lstm_direction} ({signal['final_confidence']:.2%})")
            else:
                logger.debug(
                    f"GBC disagreement or low confidence. "
                    f"LSTM: {lstm_direction} ({lstm_confidence:.2%}), "
                    f"GBC: {gbc_dir} ({gbc_conf:.2%})"
                )
        else:
            # Use LSTM alone if GBC not available
            signal['confirmed'] = True
            signal['final_direction'] = lstm_direction
            signal['final_confidence'] = lstm_confidence
        
        if not signal['confirmed']:
            return None
        
        # Add entry/exit recommendations based on volatility
        volatility = df['volatility'].iloc[-1] if 'volatility' in df.columns else 0.01
        
        signal['entry_price'] = current_price
        
        # Calculate SL and TP based on volatility and direction
        if signal['final_direction'] == "UP":
            pip_distance = max(100, int(volatility * 10000 * 10))
            signal['stop_loss'] = current_price - (pip_distance * 0.0001)
            signal['take_profit'] = current_price + (pip_distance * 1.5 * 0.0001)
        else:
            pip_distance = max(100, int(volatility * 10000 * 10))
            signal['stop_loss'] = current_price + (pip_distance * 0.0001)
            signal['take_profit'] = current_price - (pip_distance * 1.5 * 0.0001)
        
        # Store in history
        self.signal_history.append(signal)
        
        return signal
    
    def get_signal_string(self, signal: Dict) -> str:
        """
        Format signal as readable string
        
        Args:
            signal: Signal dictionary
        
        Returns:
            Formatted signal string
        """
        if not signal:
            return "NO SIGNAL"
        
        direction = signal['final_direction']
        confidence = signal['final_confidence']
        entry = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        
        confidence_level = "STRONG" if confidence > 0.8 else "MODERATE" if confidence > 0.7 else "WEAK"
        
        return (
            f"USD/BDT - {direction} - "
            f"Entry: {entry:.4f} - "
            f"SL: {stop_loss:.4f} - "
            f"TP: {take_profit:.4f} - "
            f"Confidence: {confidence:.2%} ({confidence_level})"
        )
    
    def validate_signal(
        self,
        signal: Dict,
        current_price: float
    ) -> Tuple[bool, str]:
        """
        Validate signal before execution
        
        Args:
            signal: Signal dictionary
            current_price: Current price
        
        Returns:
            Tuple of (valid, reason)
        """
        if not signal:
            return False, "No signal"
        
        if not signal.get('confirmed'):
            return False, "Signal not confirmed"
        
        direction = signal['final_direction']
        entry = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        
        if direction == "BUY":
            if stop_loss >= entry:
                return False, "Stop loss must be below entry price for BUY"
            if take_profit <= entry:
                return False, "Take profit must be above entry price for BUY"
        else:  # SELL
            if stop_loss <= entry:
                return False, "Stop loss must be above entry price for SELL"
            if take_profit >= entry:
                return False, "Take profit must be below entry price for SELL"
        
        return True, "Valid"
    
    def get_signal_history(self, limit: int = 100) -> list:
        """Get recent signals"""
        return self.signal_history[-limit:]
    
    def get_statistics(self) -> Dict:
        """Get signal statistics"""
        if not self.signal_history:
            return {
                'total_signals': 0,
                'upside_signals': 0,
                'downside_signals': 0,
                'avg_confidence': 0.0,
            }
        
        signals = self.signal_history
        upside = len([s for s in signals if s['final_direction'] == 'UP'])
        downside = len([s for s in signals if s['final_direction'] == 'DOWN'])
        avg_conf = np.mean([s['final_confidence'] for s in signals])
        
        return {
            'total_signals': len(signals),
            'upside_signals': upside,
            'downside_signals': downside,
            'avg_confidence': round(avg_conf, 4),
        }


# Example usage
if __name__ == "__main__":
    from data_fetcher import DataFetcher
    from lstm_model import LSTMPredictor
    
    # Load data and train models
    fetcher = DataFetcher()
    df = fetcher.fetch_historical_data("2021-01-01", "2023-12-31")
    
    if not df.empty:
        # Train LSTM
        lstm = LSTMPredictor()
        lstm.train(df)
        
        # Initialize signal generator
        gen = SignalGenerator(lstm, use_gbc_confirmation=True)
        gen.train_gbc(df)
        
        # Generate signals on recent data
        recent_df = df.tail(100)
        current_price = recent_df['close'].iloc[-1]
        
        signal = gen.generate_signal(recent_df, current_price)
        if signal:
            print(f"Signal: {gen.get_signal_string(signal)}")
        else:
            print("No signal generated")
