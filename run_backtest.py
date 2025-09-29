import json
from dotenv import load_dotenv
from backtester.data import fetch_historical_data
from backtester.backtest import run_backtest
from backtester.performance import calculate_performance
from backtester.plotter import plot_results
import time 
from binance.client import Client

def main():
    load_dotenv()
    with open('settings.json', 'r') as f:
        settings = json.load(f)
    strategy_settings = settings['strategy_settings']
    
    timeframe = Client.KLINE_INTERVAL_15MINUTE 
    start_date = "1 Jan, 2024"
    initial_balance = 1000
    
    for symbol in strategy_settings['symbols']:
        print(f"\n{'='*40}")
        print(f"'{symbol}' İÇİN BACKTEST BAŞLATILIYOR ({timeframe} aralığında)")
        print(f"{'='*40}\n")
        
        historical_df = fetch_historical_data(symbol, start_date, interval=timeframe)
        
        # DEĞİŞİKLİK: 'strategy_settings'i doğrudan gönderiyoruz
        trades, backtest_df = run_backtest(historical_df, strategy_settings)
        
        if not trades.empty:
            performance_results = calculate_performance(trades, initial_balance)
            print(f"\n--- {symbol} PERFORMANS RAPORU ---")
            for key, value in performance_results.items():
                print(f"{key}: {value}")
            print("----------------------------------\n")
            plot_results(backtest_df, trades, symbol)
        else:
            print(f"'{symbol}' için yeterli işlem bulunamadı.")
        
        time.sleep(1)

if __name__ == "__main__":
    main()