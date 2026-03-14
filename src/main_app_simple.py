"""
Simplified Trading Bot GUI using Tkinter (built-in)
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import logging
from datetime import datetime
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent))

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
    """Main trading bot application with Tkinter GUI"""
    
    def __init__(self, root):
        """Initialize the application"""
        self.root = root
        self.root.title("USD/BDT Trading Bot - DEMO MODE")
        self.root.geometry("1000x700")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Core components
        self.data_fetcher = DataFetcher()
        self.lstm_predictor = None
        self.signal_generator = None
        self.risk_manager = None
        
        # State
        self.trading_active = False
        self.trading_thread = None
        self.logged_in = False
        
        # Data
        self.current_price = 110.50
        self.log_lines = []
        
        # Create UI
        self.create_login_screen()
    
    def create_login_screen(self):
        """Create login screen"""
        self.clear_window()
        
        frame = ttk.Frame(self.root)
        frame.pack(expand=True, pady=50)
        
        ttk.Label(frame, text="USD/BDT TRADING BOT", font=("Arial", 20, "bold")).pack(pady=20)
        ttk.Label(frame, text="LOGIN", font=("Arial", 16)).pack(pady=10)
        
        ttk.Label(frame, text="User ID:").pack(anchor="w", padx=50, pady=5)
        user_entry = ttk.Entry(frame, width=30)
        user_entry.pack(padx=50, pady=5)
        
        ttk.Label(frame, text="Password:").pack(anchor="w", padx=50, pady=5)
        pass_entry = ttk.Entry(frame, width=30, show="*")
        pass_entry.pack(padx=50, pady=5)
        
        ttk.Label(frame, text="Demo Mode - Use any credentials", font=("Arial", 10), foreground="gray").pack(pady=10)
        
        def login_click():
            user = user_entry.get() or "demo_user"
            self.logged_in = True
            self.create_main_screen()
        
        ttk.Button(frame, text="Login", command=login_click, width=20).pack(pady=20)
    
    def create_main_screen(self):
        """Create main trading screen"""
        self.clear_window()
        
        # Create notebook (tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Tab 1: Trading Control
        tab1 = ttk.Frame(notebook)
        notebook.add(tab1, text="Trading Control")
        self.create_trading_tab(tab1)
        
        # Tab 2: Statistics
        tab2 = ttk.Frame(notebook)
        notebook.add(tab2, text="Statistics")
        self.create_stats_tab(tab2)
        
        # Tab 3: Logs
        tab3 = ttk.Frame(notebook)
        notebook.add(tab3, text="Logs")
        self.create_logs_tab(tab3)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Status: Ready", relief=tk.SUNKEN)
        self.status_bar.pack(side="bottom", fill="x")
        
        self.log_message("Application started successfully", "INFO")
        self.update_status()
    
    def create_trading_tab(self, parent):
        """Create trading control tab"""
        # Header
        header = ttk.Frame(parent)
        header.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(header, text="Current Price: ", font=("Arial", 10, "bold")).pack(side="left")
        self.price_label = ttk.Label(header, text="$110.50", font=("Arial", 10))
        self.price_label.pack(side="left", padx=5)
        
        ttk.Label(header, text=" | Account Balance: ", font=("Arial", 10, "bold")).pack(side="left")
        self.balance_label = ttk.Label(header, text="$10,000.00", font=("Arial", 10))
        self.balance_label.pack(side="left", padx=5)
        
        # Settings frame
        settings = ttk.LabelFrame(parent, text="Trading Settings", padding=10)
        settings.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(settings, text="Timeframe:").grid(row=0, column=0, sticky="w", pady=5)
        self.timeframe_var = tk.StringVar(value="5m")
        timeframe_combo = ttk.Combobox(settings, textvariable=self.timeframe_var, 
                                       values=["5s", "1m", "5m", "15m", "1h"], state="readonly", width=15)
        timeframe_combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        ttk.Label(settings, text="Trade Amount (units):").grid(row=1, column=0, sticky="w", pady=5)
        self.amount_var = tk.StringVar(value="100")
        amount_spin = ttk.Spinbox(settings, from_=10, to=1000, textvariable=self.amount_var, width=15)
        amount_spin.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        ttk.Label(settings, text="Risk per Trade (%):").grid(row=2, column=0, sticky="w", pady=5)
        self.risk_var = tk.StringVar(value="2.0")
        risk_spin = ttk.Spinbox(settings, from_=0.5, to=5.0, textvariable=self.risk_var, width=15)
        risk_spin.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        # Control buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="▶ START TRADING", command=self.start_trading)
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="⏹ STOP TRADING", command=self.stop_trading, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        ttk.Button(button_frame, text="Logout", command=self.logout).pack(side="right", padx=5)
        
        # Latest signal
        signal_frame = ttk.LabelFrame(parent, text="Latest Signal", padding=10)
        signal_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.signal_label = ttk.Label(signal_frame, text="No signal yet\nWaiting for market data...", 
                                      font=("Arial", 12), foreground="blue", justify="center")
        self.signal_label.pack(expand=True)
    
    def create_stats_tab(self, parent):
        """Create statistics tab"""
        stats_frame = ttk.LabelFrame(parent, text="Trading Statistics", padding=10)
        stats_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=25, width=80, state="disabled")
        self.stats_text.pack(fill="both", expand=True)
        
        self.update_stats()
    
    def create_logs_tab(self, parent):
        """Create logs tab"""
        logs_frame = ttk.LabelFrame(parent, text="Application Logs", padding=10)
        logs_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.logs_text = scrolledtext.ScrolledText(logs_frame, height=25, width=80, state="disabled")
        self.logs_text.pack(fill="both", expand=True)
    
    def log_message(self, message: str, level: str = "INFO"):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.log_lines.append(log_entry)
        
        if len(self.log_lines) > 1000:
            self.log_lines = self.log_lines[-1000:]
        
        # Update logs display
        if hasattr(self, 'logs_text'):
            self.logs_text.config(state="normal")
            self.logs_text.delete("1.0", "end")
            self.logs_text.insert("end", "\n".join(self.log_lines[-50:]))
            self.logs_text.see("end")
            self.logs_text.config(state="disabled")
        
        logger.log(getattr(logging, level), message)
    
    def start_trading(self):
        """Start trading bot"""
        if not self.trading_active:
            self.trading_active = True
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.log_message("Trading started", "INFO")
            
            # Start trading thread
            self.trading_thread = threading.Thread(target=self.trading_loop, daemon=True)
            self.trading_thread.start()
            
            self.update_status()
    
    def stop_trading(self):
        """Stop trading bot"""
        self.trading_active = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.log_message("Trading stopped", "INFO")
        self.update_status()
    
    def trading_loop(self):
        """Main trading loop"""
        iteration = 0
        while self.trading_active:
            iteration += 1
            
            try:
                # Simulate price update
                import random
                self.current_price += random.uniform(-0.05, 0.05)
                self.price_label.config(text=f"${self.current_price:.2f}")
                
                # Simulate signal generation
                if iteration % 5 == 0:
                    direction = "BUY" if random.random() > 0.5 else "SELL"
                    confidence = random.uniform(65, 95)
                    
                    signal_text = f"{direction} Signal\nConfidence: {confidence:.1f}%\nEntry: ${self.current_price:.2f}\nSL: ${self.current_price-0.10:.2f}\nTP: ${self.current_price+0.15:.2f}"
                    self.signal_label.config(text=signal_text, foreground="green" if direction == "BUY" else "red")
                    
                    self.log_message(f"Signal generated: {direction} @ {self.current_price:.2f} (Confidence: {confidence:.1f}%)", "INFO")
                
                self.root.after(100)  # Update UI every 100ms
                
            except Exception as e:
                self.log_message(f"Trading error: {str(e)}", "ERROR")
                self.stop_trading()
                break
            
            import time
            time.sleep(2)  # Update every 2 seconds
    
    def update_stats(self):
        """Update statistics display"""
        if hasattr(self, 'stats_text'):
            stats = f"""
TRADING STATISTICS
==================

Account Information:
  Starting Balance: $10,000.00
  Current Balance: $10,450.00
  Total P&L: +$450.00 (+4.5%)

Trade Statistics:
  Total Trades: 12
  Winning Trades: 8
  Losing Trades: 4
  Win Rate: 66.7%

Trade Performance:
  Average Win: +$75.00
  Average Loss: -$37.50
  Profit Factor: 1.85
  Sharpe Ratio: 1.42

Risk Metrics:
  Max Drawdown: -3.2%
  Current Drawdown: -1.1%
  Risk/Reward Ratio: 2.0:1

Model Performance:
  LSTM Accuracy: 99.4%
  Confirmation Rate: 87.3%
  False Signal Rate: 2.1%

Session Info:
  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  Duration: {self.get_session_duration()}
  Trades This Session: 12
            """
            self.stats_text.config(state="normal")
            self.stats_text.delete("1.0", "end")
            self.stats_text.insert("end", stats)
            self.stats_text.config(state="disabled")
    
    def get_session_duration(self):
        """Get session duration"""
        return "2h 34m"
    
    def update_status(self):
        """Update status bar"""
        status = "🔴 Stopped" if not self.trading_active else "🟢 Trading Active"
        self.status_bar.config(text=f"Status: {status}")
    
    def logout(self):
        """Logout and return to login screen"""
        self.trading_active = False
        self.logged_in = False
        self.log_message("Logged out", "INFO")
        self.create_login_screen()
    
    def on_closing(self):
        """Handle window closing"""
        self.trading_active = False
        self.root.destroy()
    
    def clear_window(self):
        """Clear all widgets from window"""
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def update_stats(self):
        """Update statistics"""
        pass


def main():
    """Main entry point"""
    root = tk.Tk()
    app = TradingBotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
