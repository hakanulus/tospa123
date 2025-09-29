import pandas as pd
from binance.client import Client
import os

def fetch_historical_data(symbol, start_str, interval=Client.KLINE_INTERVAL_1HOUR):
    """
    Binance'ten geçmişe dönük OHLCV verilerini çeker ve CSV olarak kaydeder.
    """
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_SECRET_KEY")
    client = Client(api_key, api_secret)
    
    # Dosya adının zaman aralığını da içermesini sağla ki veriler karışmasın
    csv_filename = f"{symbol}_{interval}_{start_str.replace(' ', '_').replace(',', '')}.csv"
    
    if os.path.exists(csv_filename):
        print(f"Veri dosyası '{csv_filename}' zaten mevcut. Mevcut dosya kullanılıyor.")
        df = pd.read_csv(csv_filename, index_col=0, parse_dates=True)
        return df

    print(f"'{csv_filename}' için Binance'ten veri çekiliyor...")
    klines = client.get_historical_klines(symbol, interval, start_str)
    
    df = pd.DataFrame(klines, columns=[
        'Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close Time',
        'Quote Asset Volume', 'Number of Trades', 'Taker Buy Base Asset Volume',
        'Taker Buy Quote Asset Volume', 'Ignore'
    ])
    
    # Gerekli sütunları seç ve veri tiplerini ayarla
    df = df[['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume']]
    df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
    df.set_index('Open Time', inplace=True)
    
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[col] = pd.to_numeric(df[col])

    df.to_csv(csv_filename)
    print(f"Veriler '{csv_filename}' dosyasına kaydedildi.")
    
    return df