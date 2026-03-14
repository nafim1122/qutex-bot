# USD/BDT Trading Bot - Architecture & Design Document

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      GUI Layer (PySimpleGUI)                     │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Login Screen   │  │ Trading Panel │  │ Statistics Panel │   │
│  └─────────────────┘  └──────────────┘  └──────────────────┘   │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│               Application Logic Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │    Main App  │  │  Risk Manager│  │ Trading Loop Manager │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│              Model & Analysis Layer                              │
│  ┌───────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ LSTM Predictor│  │ Signal Gen   │  │ GBC Confirmation   │   │
│  └───────────────┘  └──────────────┘  └────────────────────┘   │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│            Data Processing Layer                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Data Fetcher                                            │   │
│  │  ├─ Historical Data (Yahoo Finance)                      │   │
│  │  ├─ Live Rate Fetching                                   │   │
│  │  ├─ Intraday Data                                        │   │
│  │  └─ Feature Engineering                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│            Configuration & Storage Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │  Config Mgmt │  │  Encryption  │  │  Model Persistence   │ │
│  └──────────────┘  └──────────────┘  └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Module Descriptions

### 1. main_app.py - GUI Application
**Responsibilities:**
- User authentication (login/logout)
- Event handling (buttons, dropdowns)
- Real-time display updates
- Thread management for background trading
- Configuration UI

**Key Classes:**
- `TradingBotApp`: Main application controller

**Threading Model:**
- Main thread: GUI event loop
- Trading thread: Background price monitoring and signal generation
- Each thread is non-blocking for responsive UI

### 2. data_fetcher.py - Data Management
**Responsibilities:**
- Fetch historical data from Yahoo Finance
- Fetch live exchange rates
- Calculate technical indicators
- Normalize data for ML models
- Handle data persistence

**Key Classes:**
- `DataFetcher`: Data acquisition and processing

**Features Calculated:**
- Daily Returns
- Volatility (20-period rolling std)
- Simple Moving Averages (5, 20, 50)
- RSI (14-period)
- MACD
- Bollinger Bands
- High-Low range

### 3. lstm_model.py - Neural Network Model
**Responsibilities:**
- Define LSTM architecture
- Train on historical data
- Make price direction predictions
- Model persistence (save/load)
- Performance evaluation

**Key Classes:**
- `LSTMPredictor`: LSTM model implementation

**Architecture:**
```
Input: (batch_size, 60, 9)
├─ LSTM(128) + Dropout(0.2) + return_sequences=True
├─ LSTM(128) + Dropout(0.2) + return_sequences=True
├─ LSTM(64) + Dropout(0.2) + return_sequences=False
├─ Dense(32) + Dropout(0.2)
└─ Dense(1, sigmoid) → [0, 1] (DOWN/UP)

Training:
├─ Optimizer: Adam(lr=0.001)
├─ Loss: binary_crossentropy
├─ Metrics: accuracy, F1-score
└─ Early Stopping: patience=5
```

### 4. signal_generator.py - Signal Generation
**Responsibilities:**
- Generate trading signals from LSTM predictions
- Confirm signals with GBC model
- Calculate entry/exit levels
- Signal validation
- Signal history tracking

**Key Classes:**
- `SignalGenerator`: Multi-layer signal confirmation

**Signal Flow:**
```
LSTM Prediction (Direction + Confidence)
    ↓
GBC Confirmation (Feature analysis)
    ↓
Dual Consensus Check
    ├─ Both models agree? → Confirmed signal
    └─ Disagreement? → Reject signal
    ↓
Calculate SL/TP (volatility-based)
    ↓
Format & Validate
    ↓
Return Signal Dict
```

### 5. risk_manager.py - Trade Management
**Responsibilities:**
- Manage trade lifecycle
- Enforce hard limits (max trades, max losses)
- Calculate position sizing
- Monitor stop-loss and take-profit
- Track P&L and account balance
- Generate trading statistics

**Key Classes:**
- `RiskManager`: Trade execution and monitoring
- `Trade`: Individual trade object

**Trade States:**
```
PENDING → OPEN → CLOSED_WIN
              ├→ CLOSED_LOSS
              ├→ CLOSED_SL (hit stop-loss)
              └→ CLOSED_TP (hit take-profit)
```

**Risk Controls:**
```
Max Trades Per Session: 10
Max Consecutive Losses: 2
Max Risk Per Trade: 2% of balance
Confidence Threshold: 65%
```

### 6. config.py - Configuration Management
**Responsibilities:**
- Centralized configuration
- Encrypted credential storage
- Model hyperparameter management
- API configuration
- Trading parameters

**Key Classes:**
- `ConfigManager`: Configuration read/write
- `EncryptionManager`: AES encryption for credentials

**Configuration Sections:**
- `TRADING_CONFIG`: Trade limits, amounts, SL/TP
- `MODEL_CONFIG`: LSTM hyperparameters
- `API_CONFIG`: Data source endpoints
- `RISK_CONFIG`: Risk management settings
- `UI_CONFIG`: Visual preferences

## Data Flow

### Training Pipeline
```
Historical Data (CSV/API)
    ↓
Data Validation & Cleaning
    ↓
Feature Engineering
    ├─ Technical Indicators
    ├─ Normalization
    └─ Sequence Creation
    ↓
LSTM Training
    ├─ Forward pass
    ├─ Backpropagation
    ├─ Weight updates
    └─ Validation check
    ↓
GBC Training
    ├─ Feature extraction
    ├─ Gradient boosting
    └─ Hyperparameter tuning
    ↓
Model Evaluation
    ├─ Test accuracy
    ├─ F1 score
    └─ Confusion matrix
    ↓
Save Models & Scalers
```

### Trading Pipeline
```
Live Price Data (Real-time)
    ↓
Fetch Latest Candle
    ├─ OHLCV data
    └─ Technical indicators
    ↓
Normalize Data
    ↓
LSTM Prediction
    ├─ Forward pass
    └─ Output: Direction + Probability
    ↓
GBC Confirmation
    ├─ Feature analysis
    └─ Secondary vote
    ↓
Dual Consensus Check
    ├─ Both agree? YES → Confidence = avg(LSTM, GBC)
    └─ Disagree? NO → Reject signal
    ↓
Signal Validation
    ├─ Confidence ≥ 65%? 
    ├─ Price levels valid?
    └─ Risk within limits?
    ↓
Risk Assessment
    ├─ Position sizing
    ├─ Max trades check
    └─ Consecutive loss check
    ↓
Create Trade
    ├─ Set entry price
    ├─ Calculate SL/TP
    └─ Store trade object
    ↓
Monitor Trade
    ├─ Price updates
    ├─ Check SL hit
    └─ Check TP hit
    ↓
Close Trade & Update Balance
```

## Key Algorithms

### 1. LSTM Prediction Algorithm
```python
# For each new candle:
1. Get last 60 candles of normalized features
2. Pass through LSTM layers:
   - Extract temporal patterns
   - Learn non-linear relationships
   - Output probability [0, 1]
3. Threshold at 0.5:
   - prob > 0.5 → UP
   - prob ≤ 0.5 → DOWN
4. Confidence = |prob - 0.5| * 2  # Range [0, 1]
```

### 2. Gradient Boosting Confirmation
```python
# For GBC confirmation:
1. Extract recent features (last 60 periods):
   - RSI, MACD, Volume Change, Volatility, HL Range
2. Calculate means for window
3. Scale using fitted scaler
4. Pass through GBC ensemble:
   - Each tree votes on direction
   - Aggregate predictions
5. Return:
   - Direction (UP/DOWN)
   - Confidence = max(prob_UP, prob_DOWN)
```

### 3. Position Sizing
```python
position_size = (account_balance * max_risk_percent) / (entry_price - stop_loss)

Example:
- Account: $10,000
- Max risk: 2%
- Entry: 110.50
- SL: 110.40
- Risk per pip: 0.0001 * quantity
- Quantity = (10000 * 0.02) / (110.50 - 110.40)
          = 200 / 0.10
          = 2,000 units
```

### 4. Volatility-Based SL/TP
```python
daily_volatility = std(last_20_returns)
risk_distance = daily_volatility * 10000 * adjustment_factor

BUY Signal:
- SL = entry_price - (risk_distance * pip_value)
- TP = entry_price + (risk_distance * 1.5 * pip_value)

SELL Signal:
- SL = entry_price + (risk_distance * pip_value)
- TP = entry_price - (risk_distance * 1.5 * pip_value)
```

## Database Schema (if using persistence)

### Trades Table
```sql
CREATE TABLE trades (
    trade_id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    direction VARCHAR(4),  -- BUY/SELL
    entry_price FLOAT,
    quantity FLOAT,
    stop_loss FLOAT,
    take_profit FLOAT,
    exit_price FLOAT,
    exit_time DATETIME,
    status VARCHAR(20),
    pnl FLOAT,
    pnl_percent FLOAT,
    signal_confidence FLOAT
);
```

### Signals Table
```sql
CREATE TABLE signals (
    signal_id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    lstm_direction VARCHAR(4),
    lstm_confidence FLOAT,
    gbc_direction VARCHAR(4),
    gbc_confidence FLOAT,
    confirmed BOOLEAN,
    final_direction VARCHAR(4),
    final_confidence FLOAT,
    entry_price FLOAT,
    stop_loss FLOAT,
    take_profit FLOAT
);
```

## Performance Optimizations

1. **Model Loading:** Load LSTM once at startup, reuse for predictions
2. **Batch Processing:** Process multiple timeframes in parallel threads
3. **Caching:** Cache normalized data to avoid recalculation
4. **Memory:** Use float32 instead of float64 where possible
5. **GPU Acceleration:** Utilize NVIDIA CUDA if available

## Security Considerations

1. **Credential Storage:** Passwords encrypted with Fernet (AES)
2. **Configuration:** API keys stored in environment variables
3. **Data Privacy:** Historical data stored locally, not transmitted
4. **Code Obfuscation:** PyInstaller with `--onefile` for distribution
5. **Input Validation:** All user inputs validated before processing

## Testing Strategy

### Unit Tests
```python
# Test data fetcher
test_fetch_historical_data()
test_feature_engineering()
test_normalization()

# Test LSTM
test_lstm_training()
test_lstm_prediction()
test_model_save_load()

# Test signal generator
test_signal_generation()
test_gbc_confirmation()
test_signal_validation()

# Test risk manager
test_trade_creation()
test_trade_closing()
test_position_sizing()
test_max_trades_limit()
```

### Integration Tests
```python
# End-to-end testing
test_full_trading_cycle()
test_concurrent_trades()
test_error_recovery()
```

### Backtesting
```python
# Historical performance
test_model_on_2023_data()
test_model_on_2022_data()
calculate_win_rate()
calculate_drawdown()
```

## Deployment Checklist

- [ ] Run all unit tests
- [ ] Train model on full historical dataset
- [ ] Backtest on recent data
- [ ] Test GUI responsiveness
- [ ] Test credential encryption
- [ ] Build executable with PyInstaller
- [ ] Test executable on clean Windows machine
- [ ] Create installation documentation
- [ ] Package for distribution
- [ ] Add legal disclaimers
- [ ] Deploy to production

## Future Enhancements

1. **Live API Integration:**
   - Interactive Brokers
   - ThinkorSwim
   - MetaTrader 5

2. **Advanced Features:**
   - Multi-pair trading
   - Portfolio rebalancing
   - Machine learning optimization

3. **Analysis Tools:**
   - Equity curve plotting
   - Drawdown analysis
   - Sharpe ratio calculation

4. **Compliance:**
   - Trade logging for audits
   - Regulatory reporting
   - Risk compliance checks

## Contact & Support

For technical questions about the architecture, see the main README.md file.
