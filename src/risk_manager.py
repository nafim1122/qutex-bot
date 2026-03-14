"""
Risk Management Module for USD/BDT Trading Bot
Enforces trading limits, stop-loss, take-profit, and position sizing
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradeStatus(Enum):
    """Trade status enumeration"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED_WIN = "CLOSED_WIN"
    CLOSED_LOSS = "CLOSED_LOSS"
    CLOSED_SL = "CLOSED_STOP_LOSS"
    CLOSED_TP = "CLOSED_TAKE_PROFIT"


@dataclass
class Trade:
    """Represents a single trade"""
    trade_id: int
    timestamp: datetime
    direction: str  # "BUY" or "SELL"
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    signal_confidence: float
    status: TradeStatus = TradeStatus.PENDING
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: float = 0.0
    pnl_percent: float = 0.0
    
    def __post_init__(self):
        if self.direction not in ["BUY", "SELL"]:
            raise ValueError("Direction must be 'BUY' or 'SELL'")
    
    def close(
        self,
        exit_price: float,
        exit_time: Optional[datetime] = None,
        status: TradeStatus = TradeStatus.CLOSED_WIN
    ):
        """Close the trade with exit details"""
        self.exit_price = exit_price
        self.exit_time = exit_time or datetime.now()
        self.status = status
        
        if self.direction == "BUY":
            self.pnl = (exit_price - self.entry_price) * self.quantity
        else:  # SELL
            self.pnl = (self.entry_price - exit_price) * self.quantity
        
        self.pnl_percent = (self.pnl / (self.entry_price * self.quantity)) * 100
    
    def get_summary(self) -> Dict:
        """Get trade summary"""
        return {
            'trade_id': self.trade_id,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'quantity': self.quantity,
            'entry_time': self.timestamp.isoformat(),
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'status': self.status.value,
            'pnl': round(self.pnl, 4),
            'pnl_percent': round(self.pnl_percent, 2),
            'confidence': self.signal_confidence,
        }


class RiskManager:
    """Manages trading risk, limits, and position sizing"""
    
    def __init__(
        self,
        max_trades_per_session: int = 10,
        max_consecutive_losses: int = 2,
        default_stop_loss_pips: int = 100,
        default_take_profit_pips: int = 150,
        max_risk_per_trade: float = 2.0,  # Percentage
        confidence_threshold: float = 0.65,
        account_balance: float = 10000.0,
        position_sizing: str = "fixed"  # "fixed", "kelly", or "atr_based"
    ):
        """
        Initialize Risk Manager
        
        Args:
            max_trades_per_session: Maximum number of trades allowed
            max_consecutive_losses: Auto-pause after this many consecutive losses
            default_stop_loss_pips: Default stop loss in pips
            default_take_profit_pips: Default take profit in pips
            max_risk_per_trade: Maximum risk per trade as % of account
            confidence_threshold: Minimum confidence to generate signal
            account_balance: Starting account balance
            position_sizing: Position sizing method
        """
        self.max_trades = max_trades_per_session
        self.max_consecutive_losses = max_consecutive_losses
        self.default_sl_pips = default_stop_loss_pips
        self.default_tp_pips = default_take_profit_pips
        self.max_risk = max_risk_per_trade
        self.confidence_threshold = confidence_threshold
        self.account_balance = account_balance
        self.position_sizing = position_sizing
        
        self.trades: List[Trade] = []
        self.active_trades: List[Trade] = []
        self.consecutive_losses = 0
        self.trading_paused = False
        self.trade_counter = 0
    
    def can_trade(self) -> Tuple[bool, str]:
        """
        Check if trading is allowed
        
        Returns:
            Tuple of (can_trade, reason)
        """
        if self.trading_paused:
            return False, "Trading paused after consecutive losses"
        
        if len(self.trades) >= self.max_trades:
            return False, f"Max trades per session reached ({self.max_trades})"
        
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"Max consecutive losses reached ({self.max_consecutive_losses})"
        
        return True, "OK"
    
    def validate_signal(
        self,
        direction: str,
        confidence: float,
        current_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Validate a trading signal
        
        Args:
            direction: "BUY" or "SELL"
            confidence: Confidence score (0-1)
            current_price: Current market price
            stop_loss: Custom stop loss price
            take_profit: Custom take profit price
        
        Returns:
            Tuple of (valid, reason)
        """
        # Check trading status
        can_trade, reason = self.can_trade()
        if not can_trade:
            return False, reason
        
        # Check confidence threshold
        if confidence < self.confidence_threshold:
            return False, f"Confidence {confidence:.2%} below threshold {self.confidence_threshold:.2%}"
        
        # Validate direction
        if direction not in ["BUY", "SELL"]:
            return False, "Invalid direction"
        
        # Validate price levels
        if direction == "BUY":
            if stop_loss and stop_loss >= current_price:
                return False, "Stop loss must be below current price for BUY"
            if take_profit and take_profit <= current_price:
                return False, "Take profit must be above current price for BUY"
        else:  # SELL
            if stop_loss and stop_loss <= current_price:
                return False, "Stop loss must be above current price for SELL"
            if take_profit and take_profit >= current_price:
                return False, "Take profit must be below current price for SELL"
        
        return True, "OK"
    
    def create_trade(
        self,
        direction: str,
        entry_price: float,
        quantity: float,
        confidence: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Optional[Trade]:
        """
        Create a new trade with risk management
        
        Args:
            direction: "BUY" or "SELL"
            entry_price: Entry price
            quantity: Trade quantity
            confidence: Prediction confidence
            stop_loss: Custom stop loss
            take_profit: Custom take profit
        
        Returns:
            Trade object or None if validation fails
        """
        # Validate signal
        valid, reason = self.validate_signal(
            direction, confidence, entry_price,
            stop_loss, take_profit
        )
        
        if not valid:
            logger.warning(f"Signal validation failed: {reason}")
            return None
        
        # Calculate SL/TP if not provided
        if stop_loss is None:
            pip_value = 0.0001  # For USD/BDT
            if direction == "BUY":
                stop_loss = entry_price - (self.default_sl_pips * pip_value)
            else:
                stop_loss = entry_price + (self.default_sl_pips * pip_value)
        
        if take_profit is None:
            pip_value = 0.0001
            if direction == "BUY":
                take_profit = entry_price + (self.default_tp_pips * pip_value)
            else:
                take_profit = entry_price - (self.default_tp_pips * pip_value)
        
        # Check position size against risk limit
        potential_loss = abs((entry_price - stop_loss) * quantity)
        risk_percent = (potential_loss / self.account_balance) * 100
        
        if risk_percent > self.max_risk:
            logger.warning(f"Trade risk {risk_percent:.2f}% exceeds maximum {self.max_risk}%")
            # Auto-reduce quantity
            quantity = (self.account_balance * self.max_risk / 100) / abs(entry_price - stop_loss)
            logger.info(f"Reduced quantity to {quantity:.2f}")
        
        # Create trade object
        self.trade_counter += 1
        trade = Trade(
            trade_id=self.trade_counter,
            timestamp=datetime.now(),
            direction=direction,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_confidence=confidence
        )
        
        self.trades.append(trade)
        self.active_trades.append(trade)
        
        logger.info(
            f"Trade #{trade.trade_id} created: {direction} {quantity} @ {entry_price}, "
            f"SL={stop_loss}, TP={take_profit}, Confidence={confidence:.2%}"
        )
        
        return trade
    
    def update_price(self, new_price: float) -> List[Trade]:
        """
        Update prices and check for SL/TP hits
        
        Args:
            new_price: Current market price
        
        Returns:
            List of closed trades
        """
        closed_trades = []
        
        for trade in self.active_trades[:]:  # Copy to avoid modification during iteration
            if trade.status in [TradeStatus.CLOSED_WIN, TradeStatus.CLOSED_LOSS]:
                continue
            
            trade_closed = False
            
            if trade.direction == "BUY":
                # Check take profit
                if new_price >= trade.take_profit:
                    trade.close(trade.take_profit, status=TradeStatus.CLOSED_TP)
                    self.consecutive_losses = 0
                    trade_closed = True
                
                # Check stop loss
                elif new_price <= trade.stop_loss:
                    trade.close(trade.stop_loss, status=TradeStatus.CLOSED_SL)
                    self.consecutive_losses += 1
                    trade_closed = True
            
            else:  # SELL
                # Check take profit
                if new_price <= trade.take_profit:
                    trade.close(trade.take_profit, status=TradeStatus.CLOSED_TP)
                    self.consecutive_losses = 0
                    trade_closed = True
                
                # Check stop loss
                elif new_price >= trade.stop_loss:
                    trade.close(trade.stop_loss, status=TradeStatus.CLOSED_SL)
                    self.consecutive_losses += 1
                    trade_closed = True
            
            if trade_closed:
                self.active_trades.remove(trade)
                closed_trades.append(trade)
                
                # Update account balance
                self.account_balance += trade.pnl
                
                # Check for max consecutive losses
                if self.consecutive_losses >= self.max_consecutive_losses:
                    self.trading_paused = True
                    logger.warning(f"Trading paused: {self.consecutive_losses} consecutive losses")
                
                logger.info(
                    f"Trade #{trade.trade_id} closed: {trade.status.value}, "
                    f"PnL={trade.pnl:.4f} ({trade.pnl_percent:.2f}%)"
                )
        
        return closed_trades
    
    def pause_trading(self):
        """Pause trading"""
        self.trading_paused = True
        logger.info("Trading paused by user")
    
    def resume_trading(self):
        """Resume trading"""
        self.trading_paused = False
        self.consecutive_losses = 0
        logger.info("Trading resumed")
    
    def close_all_trades(self, current_price: float):
        """Force close all active trades at current price"""
        for trade in self.active_trades[:]:
            if trade.status == TradeStatus.OPEN:
                trade.close(current_price, status=TradeStatus.CLOSED_WIN)
                self.account_balance += trade.pnl
                self.active_trades.remove(trade)
                logger.info(f"Force closed trade #{trade.trade_id}")
    
    def get_statistics(self) -> Dict:
        """Get trading statistics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_pnl': 0.0,
                'max_drawdown': 0.0,
                'active_trades': 0,
            }
        
        closed_trades = [t for t in self.trades if t.status != TradeStatus.PENDING]
        winning = [t for t in closed_trades if t.pnl > 0]
        losing = [t for t in closed_trades if t.pnl < 0]
        
        total_pnl = sum(t.pnl for t in closed_trades)
        win_rate = len(winning) / len(closed_trades) if closed_trades else 0
        avg_pnl = total_pnl / len(closed_trades) if closed_trades else 0
        
        return {
            'total_trades': len(closed_trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': win_rate,
            'total_pnl': round(total_pnl, 4),
            'avg_pnl': round(avg_pnl, 4),
            'current_balance': round(self.account_balance, 2),
            'active_trades': len(self.active_trades),
            'consecutive_losses': self.consecutive_losses,
            'trading_paused': self.trading_paused,
        }
    
    def get_trade_history(self) -> List[Dict]:
        """Get all trades as list of dicts"""
        return [trade.get_summary() for trade in self.trades]


from typing import Tuple
