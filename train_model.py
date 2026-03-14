"""
Training script for USD/BDT LSTM model
Standalone script to train and evaluate the model
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_fetcher import DataFetcher
from lstm_model import LSTMPredictor
from signal_generator import SignalGenerator
import pandas as pd
import numpy as np


def train_model():
    """Train the LSTM model"""
    
    print("=" * 70)
    print("USD/BDT LSTM Model Training")
    print("=" * 70)
    
    # Step 1: Fetch historical data
    print("\n[Step 1/4] Fetching historical data...")
    print("  - Source: Yahoo Finance")
    print("  - Period: 2018-2023")
    print("  - Pair: USD/BDT")
    
    fetcher = DataFetcher()
    df = fetcher.fetch_historical_data(
        start_date="2018-01-01",
        end_date="2023-12-31",
        interval="1d"
    )
    
    if df.empty:
        print("  ✗ Failed to fetch data")
        return False
    
    print(f"  ✓ Loaded {len(df)} records")
    print(f"  Date range: {df['date'].min() if 'date' in df.columns else df.index.min()} to {df['date'].max() if 'date' in df.columns else df.index.max()}")
    
    # Step 2: Initialize and train LSTM
    print("\n[Step 2/4] Training LSTM Neural Network...")
    print("  Architecture:")
    print("  - Layers: 2 LSTM (128 units each)")
    print("  - Dropout: 0.2")
    print("  - Lookback: 60 periods")
    print("  - Epochs: 50")
    
    predictor = LSTMPredictor(
        lookback_period=60,
        lstm_units=128,
        lstm_layers=2,
        dropout_rate=0.2,
        batch_size=32,
        epochs=50,
        model_path="models/usdbdt_lstm_model.h5"
    )
    
    metrics = predictor.train(df)
    
    print(f"  ✓ Training complete!")
    print(f"  Test Accuracy: {metrics.get('test_accuracy', 0):.4f}")
    print(f"  Test F1 Score: {metrics.get('test_f1', 0):.4f}")
    print(f"  Test Samples: {metrics.get('test_samples', 0)}")
    
    # Step 3: Train GBC confirmation layer
    print("\n[Step 3/4] Training Gradient Boosting Confirmation Layer...")
    
    signal_gen = SignalGenerator(
        lstm_predictor,
        use_gbc_confirmation=True
    )
    
    signal_gen.train_gbc(df, lookback=60)
    
    print("  ✓ GBC training complete!")
    
    # Step 4: Evaluate on test set
    print("\n[Step 4/4] Evaluating model performance...")
    
    # Evaluate LSTM
    eval_metrics = predictor.evaluate(df)
    print(f"  LSTM Accuracy: {eval_metrics.get('accuracy', 0):.4f}")
    print(f"  F1 Score: {eval_metrics.get('f1_score', 0):.4f}")
    
    # Test signal generation
    print("\n  Testing signal generation...")
    recent_df = df.tail(200)
    current_price = recent_df['close'].iloc[-1]
    
    signal = signal_gen.generate_signal(recent_df, current_price, lookback=60)
    
    if signal:
        signal_str = signal_gen.get_signal_string(signal)
        print(f"  ✓ Sample signal: {signal_str}")
    else:
        print("  - No signal generated (confidence threshold not met)")
    
    # Summary
    print("\n" + "=" * 70)
    print("TRAINING SUMMARY")
    print("=" * 70)
    print(f"✓ Model trained successfully!")
    print(f"✓ Models saved to: models/")
    print(f"✓ LSTM Accuracy: {metrics.get('test_accuracy', 0):.2%}")
    print(f"✓ F1 Score: {metrics.get('test_f1', 0):.2%}")
    print("\nModel is ready for live trading!")
    print("\nNext step: Run the trading bot with 'python src/main_app.py'")
    
    return True


def quick_test():
    """Quick test of the model"""
    
    print("\n" + "=" * 70)
    print("Quick Model Test")
    print("=" * 70)
    
    fetcher = DataFetcher()
    predictor = LSTMPredictor()
    
    # Try to load existing model
    predictor.load_model()
    
    if predictor.model is None:
        print("✗ No trained model found. Please run training first.")
        return False
    
    # Fetch recent data
    print("\nFetching recent data...")
    df = fetcher.fetch_intraday_data("1h", 100)
    
    if df.empty:
        print("✗ Could not fetch data")
        return False
    
    # Generate sample prediction
    lstm_data = df[predictor.feature_columns or ['close']].values
    lstm_data_scaled = predictor.scaler.transform(lstm_data)
    
    direction, confidence = predictor.predict(lstm_data_scaled[-60:])
    
    print(f"\nSample Prediction:")
    print(f"  Direction: {direction}")
    print(f"  Confidence: {confidence:.2%}")
    print(f"  Current Price: {df['close'].iloc[-1]:.4f}")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="USD/BDT Trading Bot Model Trainer")
    parser.add_argument("--train", action="store_true", help="Train new model")
    parser.add_argument("--test", action="store_true", help="Quick test of existing model")
    parser.add_argument("--all", action="store_true", help="Train and test")
    
    args = parser.parse_args()
    
    # Default to training if no args
    if not args.train and not args.test and not args.all:
        args.train = True
    
    if args.train or args.all:
        success = train_model()
        if not success:
            sys.exit(1)
    
    if args.test or args.all:
        success = quick_test()
        if not success:
            sys.exit(1)
    
    print("\n✓ Done!")
