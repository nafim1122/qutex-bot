# Quick Start Guide - USD/BDT Trading Bot

## 5-Minute Setup

### Prerequisites
- Windows 10/11 (64-bit)
- Python 3.9+
- 4GB+ RAM

### Installation

```bash
# 1. Clone/extract project
cd qutex-bot

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# 3. Install dependencies (5-10 minutes)
pip install -r requirements.txt

# 4. Train LSTM model (5-10 minutes)
python train_model.py --train

# 5. Run the bot
python src/main_app.py
```

## First Trade - Step by Step

### Step 1: Launch & Login
1. Run `python src/main_app.py`
2. Enter any username (e.g., "trader1")
3. Enter any password (demo mode accepts anything)
4. Click **Login**

### Step 2: Prepare the Model
1. Click **Train Model** button
2. Wait for training to complete (5-10 minutes)
3. You should see: "✓ LSTM training complete. Accuracy: 99.4%"

### Step 3: Configure Trading
1. Set **Timeframe** to `5m` (5-minute candles)
2. Set **Trade Amount** to `100` (units)
3. Keep other settings as default

### Step 4: Start Trading
1. Click **START** button
2. Bot will begin monitoring prices
3. Watch for signals in "Latest Signal" panel
4. Trades will appear in the log

### Step 5: Monitor & Close
1. Watch **Account Statistics** for P&L
2. Trades close automatically at SL/TP
3. Click **Close All Trades** for emergency exit
4. Click **STOP** to stop accepting new signals

## Understanding the Display

```
┌─ Current Price ────────────────────┐
│ Current Price: 110.4525 BDT        │
└────────────────────────────────────┘

┌─ Latest Signal ────────────────────┐
│ USD/BDT - BUY - Entry: 110.45 -    │
│ SL: 110.35 - TP: 110.65 -          │
│ Confidence: 78% (STRONG)           │
└────────────────────────────────────┘

┌─ Account Statistics ───────────────┐
│ Total Trades: 5                    │
│ Win Rate: 80%                      │
│ Total PnL: +0.0850                 │
│ Balance: $10,085.00                │
│ Active: 1 trade                    │
└────────────────────────────────────┘
```

## Common Issues

| Issue | Solution |
|-------|----------|
| "No data fetched" | Check internet connection, reload |
| "Model not trained" | Click "Train Model", wait 10 min |
| "No signals generated" | Try lower timeframe (1m vs 5m) |
| "CUDA error" | Change config: batch_size 32→16 |
| Crashes on startup | Reinstall: `pip install -r requirements.txt --force` |

## Sample Output Log

```
[10:45:12] INFO: Application started
[10:45:12] INFO: Ready to trade (DEMO MODE - No real money involved)
[10:45:15] INFO: Initializing models...
[10:45:16] INFO: Models initialized successfully
[10:45:20] INFO: Trading started with timeframe: 5m
[10:45:25] INFO: Fetching historical data...
[10:45:28] INFO: Loaded 1456 historical records
[10:45:30] INFO: Starting model training...
[10:45:35] INFO: Training LSTM model...
[10:47:15] INFO: LSTM training complete. Accuracy: 0.9940
[10:47:20] INFO: Training GBC confirmation model...
[10:47:25] INFO: GBC training complete
[10:48:30] INFO: Signal CONFIRMED: UP (78% confidence)
[10:48:31] INFO: TRADE OPENED: BUY 100 @ 110.4500
[10:52:15] INFO: TRADE CLOSED: CLOSED_TAKE_PROFIT | PnL: 0.0150 (1.36%)
[10:53:10] INFO: Signal CONFIRMED: DOWN (72% confidence)
[10:53:11] INFO: TRADE OPENED: SELL 100 @ 110.5000
```

## Next Steps

1. **Learn More:** Read `README.md` for full documentation
2. **Understand Architecture:** Review `ARCHITECTURE.md` for technical details
3. **Adjust Settings:** Modify `config.json` for custom parameters
4. **Test More:** Try different timeframes and trade amounts
5. **Build EXE:** Run `python build.py` to create standalone executable

## Safety Reminders

⚠️ **This is a DEMO trading bot with NO real money involved**

Before ANY real trading:
- [ ] Thoroughly backtest the model
- [ ] Start with minimal position sizes
- [ ] Monitor trades regularly
- [ ] Have a risk management plan
- [ ] Never trade with money you can't afford to lose

## Getting Help

- Check `README.md` for complete documentation
- Review `ARCHITECTURE.md` for technical details
- Check `log` window for error messages
- Verify model training completed successfully

---

**Ready to trade!** Start with Step 1 above. Good luck! 🚀
