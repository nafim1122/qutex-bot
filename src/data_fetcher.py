"""
Data Fetcher Module for USD/BDT
Handles historical and live data retrieval
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from typing import Tuple, Optional
import logging
from config import API_CONFIG, DATA_DIR, TIMEFRAMES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetches historical and live USD/BDT data"""
    
    def __init__(self, pair: str = "USD/BDT"):
        self.pair = pair
        # yfinance ticker for USD/BDT
        self.yf_ticker = "USDBDT=X"  # Yahoo Finance format
        self.timeout = API_CONFIG["api_timeout"]
        self.retry_attempts = API_CONFIG["retry_attempts"]
    
    def fetch_historical_data(
        self, 
        start_date: str = None, 
        end_date: str = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch historical USD/BDT data from Yahoo Finance
        
        Args:
            start_date: Start date (format: 'YYYY-MM-DD'), defaults to 5 years ago
            end_date: End date (format: 'YYYY-MM-DD'), defaults to today
            interval: Data interval ('1d', '1h', '1m', etc.)
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"Fetching historical data: {start_date} to {end_date}")
            
            data = yf.download(
                self.yf_ticker,
                start=start_date,
                end=end_date,
                interval=interval,
                progress=False
            )
            
            if data.empty:
                logger.warning("No data fetched from Yahoo Finance")
                return pd.DataFrame()
            
            # Ensure correct column names
            data.columns = data.columns.str.lower()
            data.index.name = 'date'
            data = data.reset_index()
            
            # Calculate additional features
            data = self._calculate_features(data)
            
            logger.info(f"Successfully fetched {len(data)} records")
            return data
        
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()
    
    def fetch_live_rate(self) -> Optional[float]:
        """
        Fetch current USD/BDT rate from API
        
        Returns:
            Current exchange rate or None if failed
        """
        for attempt in range(self.retry_attempts):
            try:
                # Using multiple endpoints for redundancy
                rate = self._get_from_yfinance()
                if rate:
                    return rate
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    continue
        
        logger.error("Failed to fetch live rate after all attempts")
        return None
    
    def _get_from_yfinance(self) -> Optional[float]:
        """Get live rate from Yahoo Finance"""
        try:
            ticker = yf.Ticker(self.yf_ticker)
            data = ticker.history(period='1d')
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except Exception as e:
            logger.debug(f"YFinance error: {e}")
        return None
    
    def fetch_intraday_data(
        self, 
        timeframe: str = "5m",
        periods: int = 100
    ) -> pd.DataFrame:
        """
        Fetch intraday data for short-term analysis
        
        Args:
            timeframe: Timeframe key ('5m', '15m', '1h', etc.)
            periods: Number of periods to fetch
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Convert timeframe to yfinance interval
            interval_map = {
                "5s": "1m",   # Approximate with 1-minute candles
                "15s": "1m",
                "30s": "1m",
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
            }
            interval = interval_map.get(timeframe, "1m")
            
            logger.info(f"Fetching intraday data ({interval}), {periods} periods")
            
            data = yf.download(
                self.yf_ticker,
                period=f"{periods}d",
                interval=interval,
                progress=False
            )
            
            if data.empty:
                logger.warning("No intraday data fetched")
                return pd.DataFrame()
            
            data.columns = data.columns.str.lower()
            data.index.name = 'date'
            data = data.reset_index()
            data = self._calculate_features(data)
            
            return data[-periods:]  # Return only requested periods
        
        except Exception as e:
            logger.error(f"Error fetching intraday data: {e}")
            return pd.DataFrame()
    
    def _calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators and features"""
        try:
            # Ensure required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    logger.warning(f"Missing column: {col}")
                    return df
            
            # Daily returns
            df['returns'] = df['close'].pct_change()
            
            # Volatility (rolling std of returns)
            df['volatility'] = df['returns'].rolling(window=20).std()
            
            # Simple Moving Averages
            df['sma_5'] = df['close'].rolling(window=5).mean()
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # RSI (Relative Strength Index)
            df['rsi'] = self._calculate_rsi(df['close'])
            
            # MACD
            ema_12 = df['close'].ewm(span=12).mean()
            ema_26 = df['close'].ewm(span=26).mean()
            df['macd'] = ema_12 - ema_26
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            
            # Bollinger Bands
            df['bb_mid'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_mid'] + (bb_std * 2)
            df['bb_lower'] = df['bb_mid'] - (bb_std * 2)
            
            # High-Low range
            df['hl_range'] = (df['high'] - df['low']) / df['close']
            
            # Volume change
            df['volume_change'] = df['volume'].pct_change()
            
            return df
        
        except Exception as e:
            logger.error(f"Error calculating features: {e}")
            return df
    
    @staticmethod
    def _calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def normalize_data(
        self, 
        df: pd.DataFrame,
        feature_cols: list = None
    ) -> Tuple[pd.DataFrame, dict]:
        """
        Normalize data for LSTM input using Min-Max scaling
        
        Args:
            df: Input DataFrame
            feature_cols: Columns to normalize
        
        Returns:
            Normalized DataFrame and scaling parameters
        """
        if feature_cols is None:
            feature_cols = ['close', 'volume', 'returns', 'volatility', 'rsi']
        
        scaling_params = {}
        df_normalized = df.copy()
        
        for col in feature_cols:
            if col in df.columns:
                min_val = df[col].min()
                max_val = df[col].max()
                scaling_params[col] = {'min': min_val, 'max': max_val}
                
                # Min-Max normalization
                df_normalized[col] = (df[col] - min_val) / (max_val - min_val + 1e-8)
        
        return df_normalized, scaling_params
    
    def denormalize_price(
        self, 
        normalized_price: float,
        scaling_params: dict
    ) -> float:
        """Denormalize a price prediction"""
        min_val = scaling_params['close']['min']
        max_val = scaling_params['close']['max']
        return normalized_price * (max_val - min_val) + min_val
    
    def save_data(self, df: pd.DataFrame, filename: str = "usdbdt_data.csv"):
        """Save data to CSV"""
        try:
            filepath = DATA_DIR / filename
            df.to_csv(filepath, index=False)
            logger.info(f"Data saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    def load_data(self, filename: str = "usdbdt_data.csv") -> pd.DataFrame:
        """Load data from CSV"""
        try:
            filepath = DATA_DIR / filename
            if filepath.exists():
                return pd.read_csv(filepath)
            else:
                logger.warning(f"File not found: {filepath}")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return pd.DataFrame()


# Example usage
if __name__ == "__main__":
    fetcher = DataFetcher()
    
    # Fetch historical data
    hist_data = fetcher.fetch_historical_data("2020-01-01", "2023-12-31")
    print(f"Historical data shape: {hist_data.shape}")
    print(hist_data.head())
    
    # Fetch intraday data
    intraday = fetcher.fetch_intraday_data("5m", 100)
    print(f"\nIntraday data shape: {intraday.shape}")
    
    # Fetch live rate
    live_rate = fetcher.fetch_live_rate()
    print(f"\nCurrent USD/BDT rate: {live_rate}")
