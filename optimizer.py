import json
import itertools
from operator import itemgetter
from backtester.data import fetch_historical_data
from backtester.backtest import run_backtest
from backtester.performance import calculate_performance
from binance.client import Client

def run_optimization():
    """
    Strateji parametrelerinin farklı kombinasyonlarını test ederek en iyisini bulur.
    """
    print("Optimizasyon Motoru Başlatılıyor...")

    # --- OPTİMİZASYON AYARLARI ---
    symbol_to_optimize = "SOLUSDT"
    timeframe = Client.KLINE_INTERVAL_15MINUTE
    start_date = "1 Jan, 2024"
    initial_balance = 1000

    param_grid = {
        'ema_short_period': range(5, 16, 2),
        'ema_long_period': range(20, 41, 5),
    }
    
    static_params = {
        'ema_trend_period': 100,
        'rsi_period': 14,
        'rsi_buy_level': 50,
        'rsi_sell_level': 75
    }

    print(f"'{symbol_to_optimize}' için veri çekiliyor...")
    df = fetch_historical_data(symbol_to_optimize, start_date, interval=timeframe)
    if df.empty:
        print("Veri çekilemedi, optimizasyon durduruldu.")
        return

    keys, values = zip(*param_grid.items())
    combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
    
    total_combinations = len(combinations)
    print(f"Toplam {total_combinations} farklı parametre kombinasyonu test edilecek...")
    
    results = []

    for i, combo in enumerate(combinations):
        if combo['ema_short_period'] >= combo['ema_long_period']:
            continue

        current_params = {**combo, **static_params}
        
        print(f"[{i+1}/{total_combinations}] Test ediliyor: {combo}")

        trades, _ = run_backtest(df.copy(), current_params)
        
        if not trades.empty:
            performance = calculate_performance(trades, initial_balance)
            results.append({'params': combo, 'performance': performance})

    if not results:
        print("Hiçbir test başarılı bir sonuç üretmedi.")
        return

    # --- HATA DÜZELTME BÖLÜMÜ BAŞLANGIÇ ---
    # Sonuçları sıralamak için bir "skor" belirle
    for res in results:
        # Kâr Yüzdesi'ni al ve metinden sayıya çevir
        profit_str = res['performance'].get('Kâr Yüzdesi', '0%')
        profit = float(profit_str.replace('%', '')) # <-- DÜZELTME BURADA

        # Maksimum Düşüş'ü al ve metinden sayıya çevir
        drawdown_str = res['performance'].get('Maksimum Düşüş (Max Drawdown)', '100%')
        drawdown = float(drawdown_str.replace('%', ''))
        
        if drawdown < 1:
            drawdown = 1.0
            
        res['score'] = profit / drawdown
    # --- HATA DÜZELTME BÖLÜMÜ BİTİŞ ---

    sorted_results = sorted(results, key=itemgetter('score'), reverse=True)

    print("\n\n--- OPTİMİZASYON TAMAMLANDI ---")
    print("En İyi 5 Sonuç (Skora Göre):\n")
    
    for i, res in enumerate(sorted_results[:5]):
        p = res['performance']
        print(f"#{i+1} SKOR: {res['score']:.2f}")
        print(f"  Parametreler: {res['params']}")
        print(f"  Kâr Yüzdesi: {p.get('Kâr Yüzdesi', 'N/A')}")
        print(f"  Max Düşüş: {p.get('Maksimum Düşüş (Max Drawdown)', 'N/A')}")
        print(f"  Kazanma Oranı: {p.get('Kazanma Oranı', 'N/A')}")
        print(f"  İşlem Sayısı: {p.get('Toplam İşlem Sayısı', 'N/A')}")
        print("-" * 30)

if __name__ == "__main__":
    run_optimization()