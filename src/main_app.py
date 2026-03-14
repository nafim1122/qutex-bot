"""
Main GUI Application for USD/BDT OTC Trading Bot
Built with PySimpleGUI for cross-platform compatibility
"""

import PySimpleGUI as sg
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import config_manager, UI_CONFIG, TRADING_CONFIG, TIMEFRAMES
from data_fetcher import DataFetcher
from lstm_model import LSTMPredictor
from signal_generator import SignalGenerator
from risk_manager import RiskManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradingBotApp:
    """Main trading bot application with GUI"""
    
    def __init__(self):
        """Initialize the application"""
        self.window = None
        self.running = False
        self.trading_active = False
        
        # Core components
        self.data_fetcher = DataFetcher()
        self.lstm_predictor = LSTMPredictor()
        self.signal_generator = None
        self.risk_manager = None
        
        # Data
        self.current_price = 0.0
        self.price_history = []
        self.signals = []
        self.trades = []
        
        # UI state
        self.log_lines = []
        self.max_log_lines = UI_CONFIG.get('log_max_lines', 1000)
        
        # Set theme
        sg.theme(UI_CONFIG.get('theme', 'DarkBlue3'))
    
    def log_message(self, message: str, level: str = "INFO"):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.log_lines.append(log_entry)
        
        # Keep only recent logs
        if len(self.log_lines) > self.max_log_lines:
            self.log_lines = self.log_lines[-self.max_log_lines:]
        
        logger.log(getattr(logging, level), message)
    
    def create_login_layout(self):
        """Create login window layout"""
        layout = [
            [sg.Text("USD/BDT Trading Bot Login", font=("Arial", 14, "bold"))],
            [sg.Text("User ID:", size=(15, 1)), sg.InputText(key="-USER_ID-", size=(25, 1))],
            [sg.Text("Password:", size=(15, 1)), sg.InputText(key="-PASSWORD-", size=(25, 1), password_char="*")],
            [sg.Checkbox("Remember credentials", key="-REMEMBER-")],
            [sg.Button("Login"), sg.Button("Cancel")],
            [sg.Text("Demo mode: Use any credentials", font=("Arial", 9, "italic"), text_color="gray")],
        ]
        return layout
    
    def create_main_layout(self):
        """Create main trading window layout"""
        left_column = [
            [sg.Text("Trading Controls", font=("Arial", 12, "bold"))],
            [sg.Text("Timeframe:", size=(15, 1)), 
             sg.Combo(list(TIMEFRAMES.keys()), default_value="5m", key="-TIMEFRAME-", size=(15, 1))],
            [sg.Text("Trade Amount:", size=(15, 1)), 
             sg.Slider((1, 1000), default_value=100, key="-AMOUNT-", orientation="h", size=(20, 15))],
            [sg.Button("START", size=(10, 2), button_color=("white", "green")), 
             sg.Button("STOP", size=(10, 2), button_color=("white", "red"), disabled=True)],
            [sg.Button("Pause Trading"), sg.Button("Resume Trading")],
            [sg.Button("Manual Trade"), sg.Button("Close All Trades")],
            
            [sg.Text("", size=(30, 1))],  # Spacer
            [sg.Text("Account Statistics", font=("Arial", 12, "bold"))],
            [sg.Multiline(size=(40, 10), key="-STATS-", disabled=True)],
            
            [sg.Text("Model Status", font=("Arial", 12, "bold"))],
            [sg.Multiline(size=(40, 8), key="-MODEL_STATUS-", disabled=True)],
        ]
        
        right_column = [
            [sg.Text("Market Data & Signals", font=("Arial", 12, "bold"))],
            [sg.Text("Current Price: --", key="-CURRENT_PRICE-", font=("Arial", 11, "bold"))],
            [sg.Text("Price Change: --", key="-PRICE_CHANGE-")],
            
            [sg.Text("Latest Signal", font=("Arial", 11, "bold"))],
            [sg.Multiline(size=(60, 6), key="-LATEST_SIGNAL-", disabled=True)],
            
            [sg.Text("Recent Signals", font=("Arial", 11, "bold"))],
            [sg.Listbox(
                values=[], 
                size=(60, 10), 
                key="-SIGNAL_HISTORY-",
                disabled=True
            )],
        ]
        
        middle_column = [
            [sg.Text("Live Log", font=("Arial", 12, "bold"))],
            [sg.Multiline(
                size=(60, 30),
                key="-LOG-",
                disabled=True,
                autoscroll=True
            )],
        ]
        
        layout = [
            [sg.Column(left_column), sg.Column([middle_column]), sg.Column(right_column)],
            [sg.Button("Train Model"), sg.Button("Save Settings"), sg.Button("Exit")],
        ]
        
        return layout
    
    def handle_login(self, values):
        """Handle login"""
        user_id = values["-USER_ID-"]
        password = values["-PASSWORD-"]
        
        if not user_id or not password:
            sg.popup_error("Please enter both user ID and password", title="Login Error")
            return False
        
        if values["-REMEMBER-"]:
            try:
                config_manager.store_credentials(user_id, password)
            except Exception as e:
                sg.popup_error(f"Failed to save credentials: {e}", title="Error")
        
        self.log_message(f"User {user_id} logged in")
        return True
    
    def initialize_models(self):
        """Initialize trading models"""
        try:
            self.log_message("Initializing models...")
            
            # Initialize risk manager
            self.risk_manager = RiskManager(
                max_trades_per_session=TRADING_CONFIG['max_trades_per_session'],
                max_consecutive_losses=TRADING_CONFIG['max_consecutive_losses'],
                default_stop_loss_pips=TRADING_CONFIG['default_stop_loss_pips'],
                default_take_profit_pips=TRADING_CONFIG['default_take_profit_pips'],
                account_balance=10000.0
            )
            
            # Initialize signal generator
            self.signal_generator = SignalGenerator(
                self.lstm_predictor,
                use_gbc_confirmation=True
            )
            
            # Try to load pre-trained model
            self.lstm_predictor.load_model()
            
            self.log_message("Models initialized successfully")
            return True
        except Exception as e:
            self.log_message(f"Error initializing models: {e}", "ERROR")
            return False
    
    def train_model_thread(self):
        """Train LSTM model in background thread"""
        try:
            self.log_message("Starting model training...")
            self.log_message("Fetching historical data...")
            
            # Fetch data
            df = self.data_fetcher.fetch_historical_data("2018-01-01", "2023-12-31")
            
            if df.empty:
                self.log_message("Failed to fetch training data", "ERROR")
                return
            
            self.log_message(f"Loaded {len(df)} historical records")
            
            # Train LSTM
            self.log_message("Training LSTM model (this may take several minutes)...")
            metrics = self.lstm_predictor.train(df)
            
            self.log_message(f"LSTM training complete. Accuracy: {metrics.get('test_accuracy', 0):.2%}")
            
            # Train GBC confirmation layer
            if self.signal_generator:
                self.log_message("Training GBC confirmation model...")
                self.signal_generator.train_gbc(df)
                self.log_message("GBC training complete")
            
            self.log_message("Model training finished successfully!")
            self.update_model_status(metrics)
        
        except Exception as e:
            self.log_message(f"Error during model training: {e}", "ERROR")
    
    def update_model_status(self, metrics: dict = None):
        """Update model status display"""
        if not metrics:
            metrics = self.lstm_predictor.get_model_info() if self.lstm_predictor else {}
        
        status_text = (
            f"Model: LSTM Neural Network\n"
            f"Lookback: {metrics.get('lookback_period', '--')} periods\n"
            f"Layers: {metrics.get('lstm_layers', '--')}\n"
            f"Features: {', '.join(metrics.get('feature_columns', [])[:3])}\n"
            f"Status: {'Trained' if self.lstm_predictor.model else 'Not trained'}\n"
        )
        
        if 'test_accuracy' in metrics:
            status_text += f"Accuracy: {metrics['test_accuracy']:.2%}"
        
        return status_text
    
    def update_price_data(self, timeframe: str):
        """Fetch and update price data"""
        try:
            # Get live rate
            self.current_price = self.data_fetcher.fetch_live_rate()
            
            if self.current_price:
                # Fetch intraday data for analysis
                df = self.data_fetcher.fetch_intraday_data(timeframe, periods=100)
                
                if not df.empty:
                    self.price_history = df['close'].tolist()
                    
                    # Generate signal
                    if self.signal_generator:
                        signal = self.signal_generator.generate_signal(df, self.current_price)
                        
                        if signal:
                            self.signals.append(signal)
                            return signal, df
            
            return None, None
        
        except Exception as e:
            self.log_message(f"Error updating price data: {e}", "ERROR")
            return None, None
    
    def trading_loop_thread(self, timeframe: str):
        """Main trading loop (runs in background thread)"""
        update_interval = UI_CONFIG.get('update_interval', 1000) / 1000  # Convert to seconds
        
        while self.trading_active:
            try:
                signal, df = self.update_price_data(timeframe)
                
                if self.current_price > 0:
                    # Update display values (will be retrieved by main thread)
                    pass
                
                if signal and not self.risk_manager.trading_paused:
                    # Validate and execute trade
                    valid, reason = self.signal_generator.validate_signal(signal, self.current_price)
                    
                    if valid:
                        trade = self.risk_manager.create_trade(
                            direction=signal['final_direction'],
                            entry_price=signal['entry_price'],
                            quantity=signal.get('quantity', 100),
                            confidence=signal['final_confidence'],
                            stop_loss=signal['stop_loss'],
                            take_profit=signal['take_profit']
                        )
                        
                        if trade:
                            self.log_message(
                                f"TRADE OPENED: {trade.direction} {trade.quantity} @ {trade.entry_price}",
                                "INFO"
                            )
                            self.trades.append(trade)
                    else:
                        self.log_message(f"Signal validation failed: {reason}", "DEBUG")
                
                # Update active trades with current price
                if self.current_price > 0:
                    closed = self.risk_manager.update_price(self.current_price)
                    for trade in closed:
                        self.log_message(
                            f"TRADE CLOSED: {trade.status.value} | PnL: {trade.pnl:.4f} ({trade.pnl_percent:.2f}%)",
                            "INFO"
                        )
                
                # Small delay to avoid overwhelming the system
                import time
                time.sleep(update_interval)
            
            except Exception as e:
                self.log_message(f"Error in trading loop: {e}", "ERROR")
    
    def run(self):
        """Run the application"""
        # Show login window
        login_layout = self.create_login_layout()
        login_window = sg.Window("Login", login_layout, finalize=True)
        
        while True:
            event, values = login_window.read()
            
            if event == sg.WINDOW_CLOSED or event == "Cancel":
                login_window.close()
                return
            
            if event == "Login":
                if self.handle_login(values):
                    login_window.close()
                    break
                else:
                    sg.popup_error("Login failed", title="Error")
        
        # Initialize models
        if not self.initialize_models():
            sg.popup_error(
                "Failed to initialize models.\n\nPlease ensure all dependencies are installed:\n"
                "pip install -r requirements.txt",
                title="Initialization Error"
            )
            return
        
        # Create main window
        self.running = True
        main_layout = self.create_main_layout()
        self.window = sg.Window(
            "USD/BDT OTC Trading Bot - DEMO MODE",
            main_layout,
            finalize=True,
            size=UI_CONFIG.get('window_size', (1200, 800))
        )
        
        self.log_message("Application started")
        self.log_message("Ready to trade (DEMO MODE - No real money involved)")
        
        # Main event loop
        trading_thread = None
        
        while self.running:
            event, values = self.window.read(timeout=1000)
            
            if event == sg.WINDOW_CLOSED or event == "Exit":
                break
            
            # Update displays
            if self.current_price > 0:
                self.window["-CURRENT_PRICE-"].update(f"Current Price: {self.current_price:.4f} BDT")
            
            # Update log
            log_text = "\n".join(self.log_lines[-50:])  # Show last 50 lines
            self.window["-LOG-"].update(log_text)
            
            # Update statistics
            if self.risk_manager:
                stats = self.risk_manager.get_statistics()
                stats_text = (
                    f"Total Trades: {stats['total_trades']}\n"
                    f"Win Rate: {stats['win_rate']:.2%}\n"
                    f"Total PnL: {stats['total_pnl']:.4f}\n"
                    f"Balance: {stats['current_balance']:.2f}\n"
                    f"Active: {stats['active_trades']}"
                )
                self.window["-STATS-"].update(stats_text)
            
            # Update model status
            if event == "Train Model":
                # Confirm before training
                if sg.popup_yes_no("Train LSTM model on historical data?\nThis may take 5-10 minutes.", title="Confirm") == "Yes":
                    thread = threading.Thread(target=self.train_model_thread, daemon=True)
                    thread.start()
            
            if event == "START":
                timeframe = values["-TIMEFRAME-"]
                self.trading_active = True
                self.log_message(f"Trading started with timeframe: {timeframe}")
                
                self.window["-START-"].update(disabled=True)
                self.window["-STOP-"].update(disabled=False)
                self.window["-TIMEFRAME-"].update(disabled=True)
                
                # Start trading thread
                trading_thread = threading.Thread(
                    target=self.trading_loop_thread,
                    args=(timeframe,),
                    daemon=True
                )
                trading_thread.start()
            
            elif event == "STOP":
                self.trading_active = False
                self.log_message("Trading stopped by user")
                
                self.window["-START-"].update(disabled=False)
                self.window["-STOP-"].update(disabled=True)
                self.window["-TIMEFRAME-"].update(disabled=False)
            
            elif event == "Pause Trading":
                if self.risk_manager:
                    self.risk_manager.pause_trading()
                    self.log_message("Trading paused")
            
            elif event == "Resume Trading":
                if self.risk_manager:
                    self.risk_manager.resume_trading()
                    self.log_message("Trading resumed")
            
            elif event == "Close All Trades":
                if self.current_price > 0 and self.risk_manager:
                    self.risk_manager.close_all_trades(self.current_price)
                    self.log_message("All trades closed")
            
            elif event == "Save Settings":
                config_manager.save_config()
                sg.popup_ok("Settings saved", title="Success")
                self.log_message("Settings saved to config.json")
            
            elif event == "Manual Trade":
                sg.popup_ok("Manual trading interface - Feature to be implemented", title="Info")
        
        # Cleanup
        self.running = False
        if self.window:
            self.window.close()
        
        self.log_message("Application closed")


def main():
    """Entry point"""
    app = TradingBotApp()
    app.run()


if __name__ == "__main__":
    main()
