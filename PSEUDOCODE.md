# USD/BDT Trading Bot - Pseudocode & Signal Generation Logic

## High-Level Trading Algorithm

```pseudocode
PROGRAM: USD/BDT Trading Bot

INITIALIZATION:
    Load configuration from config.json
    Initialize LSTM model from saved weights
    Initialize GBC confirmation model
    Initialize Risk Manager with max_trades=10, max_losses=2
    account_balance = 10000.0
    consecutive_losses = 0
    active_trades = []
    
MAIN LOOP (while user clicks START):
    EVERY timeframe_interval seconds:
        
        // Step 1: Fetch current market data
        current_price = fetch_live_rate()
        if current_price is NULL:
            log "ERROR: Could not fetch price"
            continue
        
        // Step 2: Fetch historical data for analysis
        historical_data = fetch_intraday_data(timeframe, periods=100)
        if historical_data.empty():
            continue
        
        // Step 3: Generate trading signal
        signal = generate_signal(historical_data, current_price)
        if signal is not NULL:
            log "SIGNAL GENERATED: " + signal.direction + 
                ", Confidence: " + signal.confidence
        
        // Step 4: Update existing trades with current price
        closed_trades = risk_manager.update_prices(current_price)
        for each trade in closed_trades:
            log "TRADE CLOSED: " + trade.status + 
                ", PnL: " + trade.pnl
            if trade.pnl < 0:
                consecutive_losses += 1
            else:
                consecutive_losses = 0
            
            if consecutive_losses >= max_consecutive_losses:
                log "TRADING PAUSED: Max consecutive losses reached"
                trading_paused = true
        
        // Step 5: Execute new trade if signal is valid
        if signal is not NULL AND not trading_paused:
            if can_create_trade(signal):
                trade = risk_manager.create_trade(
                    direction = signal.direction,
                    entry_price = current_price,
                    quantity = calculate_position_size(signal),
                    confidence = signal.confidence,
                    stop_loss = signal.stop_loss,
                    take_profit = signal.take_profit
                )
                
                if trade is not NULL:
                    active_trades.add(trade)
                    log "TRADE OPENED: " + trade.direction + 
                        ", Entry: " + trade.entry_price +
                        ", SL: " + trade.stop_loss +
                        ", TP: " + trade.take_profit
        
        // Step 6: Update UI displays
        update_price_display(current_price)
        update_statistics_display(account_balance, consecutive_losses)
        update_log_display()
        
        // Step 7: Sleep before next iteration
        sleep(update_interval)

END MAIN LOOP

SHUTDOWN:
    close_all_trades(current_price)
    save_configuration()
    save_trade_history()
    log "Trading session ended"
```

## Signal Generation Algorithm (Detailed)

```pseudocode
FUNCTION: generate_signal(historical_data, current_price)
    
    INPUT:
        historical_data: DataFrame with OHLCV + features (normalized)
        current_price: float (current market price)
    
    OUTPUT:
        signal: Dictionary with direction, confidence, SL, TP
        NULL: if no valid signal
    
    // Step 1: LSTM Prediction
    log "Generating signal..."
    
    // Get last 60 periods of data
    lookback_data = historical_data.tail(60)
    
    if lookback_data.length < 60:
        return NULL  // Not enough data
    
    // Normalize features using fitted scaler
    normalized_lookback = scaler.transform(lookback_data)
    
    // Run LSTM inference
    lstm_output = lstm_model.predict(normalized_lookback)
    // lstm_output is in range [0, 1]
    
    lstm_direction = IF lstm_output > 0.5 THEN "UP" ELSE "DOWN"
    lstm_confidence = IF lstm_direction == "UP" 
                       THEN lstm_output 
                       ELSE (1 - lstm_output)
    
    log "LSTM: " + lstm_direction + " (" + lstm_confidence + "%)"
    
    // Step 2: Confidence Check
    if lstm_confidence < confidence_threshold (0.65):
        log "LSTM confidence below threshold, skipping signal"
        return NULL
    
    // Step 3: GBC Confirmation
    log "Running GBC confirmation..."
    
    // Extract features for GBC
    gbc_features = [rsi, macd, volume_change, volatility, hl_range]
    recent_features = historical_data.tail(60)[gbc_features].mean()
    recent_features_scaled = gbc_scaler.transform(recent_features)
    
    // Run GBC model
    gbc_output = gbc_model.predict(recent_features_scaled)
    gbc_probability = gbc_model.predict_proba(recent_features_scaled)
    
    gbc_direction = IF gbc_output[0] == 1 THEN "UP" ELSE "DOWN"
    gbc_confidence = max(gbc_probability[0])
    
    log "GBC: " + gbc_direction + " (" + gbc_confidence + "%)"
    
    // Step 4: Dual Consensus Check
    confirmed = FALSE
    final_direction = NULL
    final_confidence = 0.0
    
    if lstm_direction == gbc_direction AND gbc_confidence >= threshold:
        confirmed = TRUE
        final_direction = lstm_direction
        final_confidence = (lstm_confidence + gbc_confidence) / 2.0
        log "CONSENSUS: Both models agree on " + final_direction
    else:
        log "NO CONSENSUS: LSTM=" + lstm_direction + 
            ", GBC=" + gbc_direction + ". Signal rejected."
        return NULL
    
    if final_confidence < threshold:
        log "Final confidence too low, skipping"
        return NULL
    
    // Step 5: Calculate Stop-Loss & Take-Profit
    current_volatility = historical_data['volatility'].iloc[-1]
    
    // Volatility-adjusted pip distance
    pip_distance = MAX(100, 
                      INT(current_volatility * 10000 * 10))
    pip_value = 0.0001
    
    if final_direction == "UP":
        entry_price = current_price
        stop_loss = entry_price - (pip_distance * pip_value)
        take_profit = entry_price + (pip_distance * 1.5 * pip_value)
    else:  // DOWN
        entry_price = current_price
        stop_loss = entry_price + (pip_distance * pip_value)
        take_profit = entry_price - (pip_distance * 1.5 * pip_value)
    
    // Step 6: Create Signal Object
    signal = {
        "timestamp": current_time,
        "pair": "USD/BDT",
        "current_price": current_price,
        "lstm_direction": lstm_direction,
        "lstm_confidence": lstm_confidence,
        "gbc_direction": gbc_direction,
        "gbc_confidence": gbc_confidence,
        "confirmed": TRUE,
        "final_direction": final_direction,
        "final_confidence": final_confidence,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "signal_strength": "STRONG" IF final_confidence > 0.8 
                          ELSE "MODERATE" IF final_confidence > 0.7
                          ELSE "WEAK"
    }
    
    log "SIGNAL CONFIRMED: " + final_direction + 
        " @ " + entry_price + " (Confidence: " + final_confidence + "%)"
    
    return signal
    
END FUNCTION
```

## Trade Creation & Risk Management

```pseudocode
FUNCTION: create_trade(signal)
    
    INPUT:
        signal: Dictionary with direction, confidence, SL, TP
    
    OUTPUT:
        trade: Trade object
        NULL: if creation failed
    
    // Step 1: Validate Trading Status
    if trading_paused:
        log "ERROR: Trading paused"
        return NULL
    
    if number_of_trades >= max_trades_per_session (10):
        log "ERROR: Max trades reached"
        return NULL
    
    if consecutive_losses >= max_consecutive_losses (2):
        log "ERROR: Max consecutive losses reached"
        return NULL
    
    // Step 2: Validate Signal
    if signal.confirmed != TRUE:
        return NULL
    
    if signal.final_confidence < confidence_threshold:
        return NULL
    
    // Step 3: Validate Price Levels
    entry = signal.entry_price
    sl = signal.stop_loss
    tp = signal.take_profit
    
    if signal.final_direction == "BUY":
        if NOT (sl < entry AND tp > entry):
            log "ERROR: Invalid price levels for BUY"
            return NULL
    else:  // SELL
        if NOT (sl > entry AND tp < entry):
            log "ERROR: Invalid price levels for SELL"
            return NULL
    
    // Step 4: Calculate Position Size
    // Using fixed position sizing: 2% risk per trade
    max_risk_amount = account_balance * 0.02
    
    if signal.final_direction == "BUY":
        risk_per_unit = entry - sl
    else:
        risk_per_unit = sl - entry
    
    position_size = max_risk_amount / risk_per_unit
    
    // Cap at max trade amount
    if position_size > max_trade_amount (1000):
        position_size = max_trade_amount
    
    // Step 5: Validate Risk
    potential_loss = position_size * risk_per_unit
    risk_percent = (potential_loss / account_balance) * 100
    
    if risk_percent > max_risk_percent (2%):
        log "WARNING: Risk too high, reducing position size"
        position_size = (account_balance * max_risk_percent / 100) / risk_per_unit
    
    // Step 6: Create Trade Object
    trade = {
        "trade_id": next_trade_id,
        "timestamp": current_time,
        "direction": signal.final_direction,
        "entry_price": entry,
        "quantity": position_size,
        "stop_loss": sl,
        "take_profit": tp,
        "signal_confidence": signal.final_confidence,
        "status": "OPEN",
        "exit_price": NULL,
        "exit_time": NULL,
        "pnl": 0.0,
        "pnl_percent": 0.0
    }
    
    log "TRADE #" + trade.trade_id + " CREATED: " +
        trade.direction + " " + position_size + 
        " @ " + entry + 
        ", SL=" + sl + ", TP=" + tp
    
    return trade
    
END FUNCTION
```

## Trade Monitoring & Closure

```pseudocode
FUNCTION: update_trade_prices(current_price)
    
    INPUT:
        current_price: float (current market price)
    
    OUTPUT:
        closed_trades: List of trades that were closed
    
    closed_trades = []
    
    for each active_trade in active_trades:
        
        if active_trade.status == "CLOSED":
            continue  // Already closed
        
        hit_tp = FALSE
        hit_sl = FALSE
        exit_status = NULL
        
        // Check Take-Profit & Stop-Loss
        if active_trade.direction == "BUY":
            
            if current_price >= active_trade.take_profit:
                hit_tp = TRUE
                exit_status = "CLOSED_TP"
                exit_price = active_trade.take_profit
            
            else if current_price <= active_trade.stop_loss:
                hit_sl = TRUE
                exit_status = "CLOSED_SL"
                exit_price = active_trade.stop_loss
        
        else:  // SELL direction
            
            if current_price <= active_trade.take_profit:
                hit_tp = TRUE
                exit_status = "CLOSED_TP"
                exit_price = active_trade.take_profit
            
            else if current_price >= active_trade.stop_loss:
                hit_sl = TRUE
                exit_status = "CLOSED_SL"
                exit_price = active_trade.stop_loss
        
        // Close trade if triggered
        if hit_tp OR hit_sl:
            
            // Calculate P&L
            if active_trade.direction == "BUY":
                pnl = (exit_price - active_trade.entry_price) * active_trade.quantity
            else:
                pnl = (active_trade.entry_price - exit_price) * active_trade.quantity
            
            pnl_percent = (pnl / (active_trade.entry_price * active_trade.quantity)) * 100
            
            // Update trade object
            active_trade.status = exit_status
            active_trade.exit_price = exit_price
            active_trade.exit_time = current_time
            active_trade.pnl = pnl
            active_trade.pnl_percent = pnl_percent
            
            // Update account balance
            account_balance += pnl
            
            // Track consecutive losses
            if pnl < 0:
                consecutive_losses += 1
                log "TRADE CLOSED (LOSS): " + 
                    "PnL=" + pnl + " (" + pnl_percent + "%)"
            else:
                consecutive_losses = 0
                log "TRADE CLOSED (WIN): " + 
                    "PnL=" + pnl + " (" + pnl_percent + "%)"
            
            // Check max consecutive losses
            if consecutive_losses >= max_consecutive_losses:
                log "WARNING: Max consecutive losses reached. Pausing trading."
                trading_paused = TRUE
            
            closed_trades.add(active_trade)
    
    // Remove closed trades from active list
    active_trades = active_trades - closed_trades
    
    return closed_trades
    
END FUNCTION
```

## Position Sizing Examples

```pseudocode
EXAMPLE 1: Fixed Position Sizing
├─ Account Balance: $10,000
├─ Risk per Trade: 2% = $200
├─ Entry Price: 110.50
├─ Stop-Loss: 110.40
├─ Risk per Unit: 0.10 BDT
└─ Position Size = $200 / 0.10 = 2,000 units

EXAMPLE 2: Volatility-Adjusted SL/TP
├─ Current Volatility: 0.015 (1.5%)
├─ Base Pip Distance: 100 + (0.015 * 10000 * 10) = 1,600 pips
├─ For BUY @ 110.50:
│  ├─ Stop-Loss = 110.50 - (1,600 * 0.0001) = 109.34
│  └─ Take-Profit = 110.50 + (1,600 * 0.0001 * 1.5) = 111.74
└─ Reward/Risk Ratio = (110.50 - 111.74) / (110.50 - 109.34) = 1.5:1

EXAMPLE 3: Risk Management in Action
├─ Start: Account = $10,000, Trades = 0, Losses = 0
├─ Trade 1: SELL -2,000 units @ 110.50, Exit @ 110.30 → Win $400 → Losses = 0
├─ Trade 2: BUY +2,000 units @ 110.25, Exit @ 110.20 → Loss $100 → Losses = 1
├─ Trade 3: SELL -1,500 units @ 110.35, Exit @ 110.25 → Loss $150 → Losses = 2
├─ Trade 4: Would generate signal but TRADING_PAUSED = TRUE
└─ Account Balance = $10,000 + 400 - 100 - 150 = $10,150
```

## Key Decision Points

```
┌─ Signal Generated?
│  ├─ NO → Wait for next candle
│  └─ YES → Continue
│
├─ Confidence >= 65%?
│  ├─ NO → Reject signal
│  └─ YES → Continue
│
├─ LSTM & GBC Agree?
│  ├─ NO → Reject signal
│  └─ YES → Continue
│
├─ Trading Paused?
│  ├─ YES → Skip trade, wait for resume
│  └─ NO → Continue
│
├─ Max Trades (10) Reached?
│  ├─ YES → Skip trade
│  └─ NO → Continue
│
├─ Max Consecutive Losses (2)?
│  ├─ YES → Auto-pause trading
│  └─ NO → Continue
│
└─ Create Trade
   ├─ Calculate Position Size (2% risk)
   ├─ Validate Price Levels
   ├─ Open Trade
   └─ Monitor for SL/TP
```

---

This pseudocode provides the complete logic flow for the USD/BDT trading bot. All modules in the actual implementation follow these algorithms.
