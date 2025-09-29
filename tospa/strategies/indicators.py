import pandas as pd
import numpy as np
from typing import List

def calculate_sma(data: pd.Series, window: int) -> pd.Series:
    """
    Basit Hareketli Ortalama (Simple Moving Average - SMA) hesaplar.

    Args:
        data (pd.Series): Genellikle kapanış fiyatlarını içeren pandas Serisi.
        window (int): Ortalama için kullanılacak periyot sayısı.

    Returns:
        pd.Series: Hesaplanan SMA değerlerini içeren Seri.
    """
    if not isinstance(data, pd.Series):
        raise TypeError("Veri, bir pandas Serisi olmalıdır.")
    if window <= 0:
        raise ValueError("Periyot (window) pozitif bir tamsayı olmalıdır.")
        
    return data.rolling(window=window).mean()

def calculate_ema(data: pd.Series, window: int) -> pd.Series:
    """
    Üstel Hareketli Ortalama (Exponential Moving Average - EMA) hesaplar.

    Args:
        data (pd.Series): Genellikle kapanış fiyatlarını içeren pandas Serisi.
        window (int): Ortalama için kullanılacak periyot sayısı.

    Returns:
        pd.Series: Hesaplanan EMA değerlerini içeren Seri.
    """
    if not isinstance(data, pd.Series):
        raise TypeError("Veri, bir pandas Serisi olmalıdır.")
    if window <= 0:
        raise ValueError("Periyot (window) pozitif bir tamsayı olmalıdır.")

    return data.ewm(span=window, adjust=False).mean()

# Bu dosya doğrudan çalıştırıldığında fonksiyonların doğru çalışıp çalışmadığını
# test etmek için bir kontrol bloğu.
if __name__ == "__main__":
    print("--- İndikatörler Modülü Testi ---")
    # Örnek bir fiyat serisi oluşturalım
    test_prices = pd.Series([10, 12, 15, 14, 16, 18, 20, 19, 22, 25])
    
    print("Örnek Fiyatlar:\n", test_prices.values)
    
    # 3 periyotluk SMA hesapla
    sma_3 = calculate_sma(test_prices, 3)
    print("\n3 Periyotluk SMA:\n", np.round(sma_3.values, 2))

    # 3 periyotluk EMA hesapla
    ema_3 = calculate_ema(test_prices, 3)
    print("\n3 Periyotluk EMA:\n", np.round(ema_3.values, 2))
    
    print("\nTest Başarılı!")
