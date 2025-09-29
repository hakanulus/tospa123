import pandas as pd
import logging
from binance.client import Client

# Proje içi modülleri import ediyoruz
from tospa.api.binance_client import TospaBinanceClient
from tospa.strategies.indicators import calculate_ema
from tospa.core.config import Settings # Ayarları import et

class WarriorTurtleStrategy:
    """
    "Savaşçı Kaplumbağa" alım-satım stratejisi.
    Artık ayarları dinamik olarak config nesnesinden okur.
    """
    def __init__(self, client: TospaBinanceClient, settings: Settings):
        """
        Stratejiyi başlatır.

        Args:
            client (TospaBinanceClient): Veri çekmek için kullanılacak Binance istemcisi.
            settings (Settings): Uygulama ayarları nesnesi.
        """
        self.client = client
        self.settings = settings # Ayarların tamamını bir nesne olarak sakla
        
        # Ayarlar nesnesinin içindeki değerlere erişerek kontrol yap
        if self.settings.SLOW_EMA_PERIOD <= self.settings.FAST_EMA_PERIOD:
            raise ValueError("Yavaş EMA periyodu, Hızlı EMA periyodundan büyük olmalıdır.")

    def analyze(self, symbol: str, interval: str = Client.KLINE_INTERVAL_1HOUR) -> str:
        """
        Belirtilen sembolü analiz eder ve bir alım-satım sinyali üretir.
        """
        # Ayarları self.settings üzerinden kullan
        limit = self.settings.SLOW_EMA_PERIOD + 100
        klines = self.client.get_historical_klines(symbol, interval, limit=limit)
        
        # Veri kontrolünü daha sağlam hale getirelim
        if not klines or len(klines) < self.settings.SLOW_EMA_PERIOD:
            logging.warning(f"{symbol} için yeterli veri alınamadı ({len(klines)} mum). Analiz atlanıyor.")
            return "HOLD"

        # Gelen veriyi pandas DataFrame'e çevirelim
        df = pd.DataFrame(klines, columns=['Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close time', 'Quote asset volume', 'Number of trades', 'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'])
        df['Close'] = pd.to_numeric(df['Close'])

        # İndikatörleri ayarlar nesnesinden gelen değerlerle hesapla
        fast_ema = calculate_ema(df['Close'], self.settings.FAST_EMA_PERIOD)
        slow_ema = calculate_ema(df['Close'], self.settings.SLOW_EMA_PERIOD)

        # Sinyal üretmek için son iki mumu kontrol et
        last_fast_ema = fast_ema.iloc[-1]
        previous_fast_ema = fast_ema.iloc[-2]
        last_slow_ema = slow_ema.iloc[-1]
        previous_slow_ema = slow_ema.iloc[-2]

        # ALIM Sinyali: Hızlı EMA, Yavaş EMA'yı yukarı keserse
        if previous_fast_ema <= previous_slow_ema and last_fast_ema > last_slow_ema:
            return "BUY"
        
        # SATIM Sinyali: Hızlı EMA, Yavaş EMA'yı aşağı keserse
        elif previous_fast_ema >= previous_slow_ema and last_fast_ema < last_slow_ema:
            return "SELL"
        
        # Diğer tüm durumlar
        else:
            return "HOLD"

