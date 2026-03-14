"""
Configuration module for USD/BDT Trading Bot
Handles all configuration settings, encryption, and secrets management
"""

import os
import json
from pathlib import Path
from cryptography.fernet import Fernet

# Project paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"
CONFIG_FILE = BASE_DIR / "config.json"

# Trading Configuration
TRADING_CONFIG = {
    "pair": "USD/BDT",
    "max_trades_per_session": 10,
    "max_consecutive_losses": 2,
    "default_timeframe": "5m",
    "min_trade_amount": 1,
    "max_trade_amount": 1000,
    "default_stop_loss_pips": 100,
    "default_take_profit_pips": 150,
}

# Model Configuration
MODEL_CONFIG = {
    "lstm_units": 128,
    "lstm_layers": 2,
    "dropout_rate": 0.2,
    "batch_size": 32,
    "epochs": 50,
    "lookback_period": 60,  # Number of past periods to look back
    "test_split": 0.2,
    "validation_split": 0.1,
}

# API Configuration
API_CONFIG = {
    "historical_data_source": "yfinance",  # Can be expanded to other sources
    "live_data_endpoints": [
        "https://api.example.com/v1/rates/USDBDT",  # Placeholder
        "https://api.rapidapi.com/forex/USDBDT",    # Placeholder
    ],
    "api_timeout": 10,
    "retry_attempts": 3,
    "retry_delay": 2,
}

# Risk Management Configuration
RISK_CONFIG = {
    "position_sizing": "fixed",  # Can be "fixed", "kelly", or "atr_based"
    "max_risk_per_trade": 2,     # Percentage of account
    "confidence_threshold": 0.65, # Minimum confidence to generate signal
}

# UI Configuration
UI_CONFIG = {
    "theme": "DarkBlue3",
    "window_size": (1200, 800),
    "update_interval": 1000,  # milliseconds
    "log_max_lines": 1000,
}

# Timeframe mapping (in seconds)
TIMEFRAMES = {
    "5s": 5,
    "15s": 15,
    "30s": 30,
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
}


class EncryptionManager:
    """Handles encryption/decryption of sensitive data"""
    
    def __init__(self, key_file: str = "secret.key"):
        self.key_file = BASE_DIR / key_file
        self.cipher = self._load_or_create_key()
    
    def _load_or_create_key(self):
        """Load existing key or create new one"""
        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
        
        return Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt a string"""
        encrypted = self.cipher.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt a string"""
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")


class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self):
        self.config = self._load_config()
        self.encryption = EncryptionManager()
    
    def _load_config(self) -> dict:
        """Load configuration from file or use defaults"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
        
        return {
            "trading": TRADING_CONFIG,
            "model": MODEL_CONFIG,
            "api": API_CONFIG,
            "risk": RISK_CONFIG,
            "ui": UI_CONFIG,
        }
    
    def save_config(self):
        """Save current configuration to file"""
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)
    
    def get(self, section: str, key: str, default=None):
        """Get a configuration value"""
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value):
        """Set a configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save_config()
    
    def store_credentials(self, user_id: str, password: str):
        """Store encrypted credentials"""
        encrypted_password = self.encryption.encrypt(password)
        self.set("credentials", user_id, encrypted_password)
    
    def get_credentials(self, user_id: str) -> str:
        """Retrieve and decrypt password"""
        encrypted = self.config.get("credentials", {}).get(user_id)
        if encrypted:
            return self.encryption.decrypt(encrypted)
        return None


# Global config instance
config_manager = ConfigManager()
