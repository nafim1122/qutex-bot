"""
USD/BDT Trading Bot
AI-powered trading signal generator with LSTM neural network
"""

__version__ = "1.0.0"
__author__ = "QuantAI Trading Systems"
__description__ = "Professional USD/BDT OTC trading bot with LSTM prediction engine"

__all__ = [
    'DataFetcher',
    'LSTMPredictor',
    'SignalGenerator',
    'RiskManager',
    'config_manager',
]

from src.data_fetcher import DataFetcher
from src.lstm_model import LSTMPredictor
from src.signal_generator import SignalGenerator
from src.risk_manager import RiskManager
from src.config import config_manager
