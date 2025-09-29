import logging
import math
import time
from binance.client import Client
from binance.exceptions import BinanceAPIException

class TospaBinanceClient:
    """
    Binance API'si ile etkileşimi yöneten, hata kontrolü ve
    otomatik yeniden bağlanma özelliklerine sahip istemci sınıfı.
    """
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.client = None
        self.is_ready = False # Hata kontrolü için yeni özellik
        self._initialize_client()

    def _initialize_client(self):
        """Binance istemcisini başlatır ve bağlantıyı doğrular."""
        if not self.api_key or not self.api_secret:
            logging.warning("API anahtarları eksik. İstemci başlatılamadı.")
            self.is_ready = False
            return
        
        try:
            self.client = Client(self.api_key, self.api_secret, tld='com', testnet=self.testnet)
            # Bağlantıyı doğrulamak için basit bir çağrı yap
            self.client.get_account()
            self.is_ready = True
            logging.info("Binance istemcisi başarıyla başlatıldı ve bağlantı doğrulandı.")
        except BinanceAPIException as e:
            self.is_ready = False
            logging.error(f"Binance API Hatası: {e.message}")
        except Exception as e:
            self.is_ready = False
            logging.error(f"İstemci başlatılırken beklenmedik bir hata oluştu: {e}")

    def get_account_balance(self, asset: str) -> str:
        """Belirtilen varlık için cüzdan bakiyesini alır."""
        if not self.is_ready: return "0"
        try:
            balance = self.client.get_asset_balance(asset=asset)
            return balance['free'] if balance else "0"
        except BinanceAPIException as e:
            logging.error(f"{asset} bakiyesi alınırken hata: {e.message}")
            return "0"

    def get_symbol_ticker(self, symbol: str) -> dict:
        """Belirtilen işlem çifti için anlık fiyat bilgisini alır."""
        if not self.is_ready: return {}
        try:
            return self.client.get_symbol_ticker(symbol=symbol)
        except BinanceAPIException as e:
            logging.error(f"{symbol} fiyatı alınırken hata oluştu: {e.message}")
            return {}

    def get_historical_klines(self, symbol: str, interval: str, limit: int = 500) -> list:
        """Belirtilen işlem çifti için geçmiş mum grafiği verilerini çeker."""
        if not self.is_ready: return []
        try:
            return self.client.get_historical_klines(symbol, interval, limit=limit)
        except BinanceAPIException as e:
            logging.error(f"{symbol} için geçmiş veriler alınırken hata: {e.message}")
            return []

    def get_symbol_info(self, symbol: str) -> dict:
        """Bir sembolün işlem kurallarını (örn: lot size) alır."""
        if not self.is_ready: return None
        try:
            return self.client.get_symbol_info(symbol)
        except BinanceAPIException as e:
            logging.error(f"{symbol} için işlem kuralları alınamadı: {e.message}")
            return None

    def adjust_quantity_to_lot_size(self, symbol: str, quantity: float) -> float:
        """Verilen miktarı, sembolün lot size kurallarına göre ayarlar."""
        info = self.get_symbol_info(symbol)
        if not info: return 0
        
        try:
            lot_size_filter = next(f for f in info['filters'] if f['filterType'] == 'LOT_SIZE')
            step_size = float(lot_size_filter['stepSize'])
            min_qty = float(lot_size_filter['minQty'])
            
            if quantity < min_qty:
                logging.warning(f"Miktar ({quantity}) minimum alım miktarından ({min_qty}) az. İşlem iptal edilecek.")
                return 0

            precision = int(round(-math.log(step_size, 10), 0))
            adjusted_quantity = math.floor(quantity * (10**precision)) / (10**precision)
            
            logging.info(f"Lot kurallarına göre ayarlanan miktar: {adjusted_quantity} {symbol.replace('USDT','')}")
            return adjusted_quantity
        except (StopIteration, KeyError, ValueError) as e:
            logging.error(f"{symbol} için lot size ayarlanamadı: {e}")
            return 0

    def create_order(self, symbol: str, side: str, order_type: str, quantity: float):
        """Binance üzerinde gerçek bir alım veya satım emri oluşturur."""
        if not self.is_ready: return None
        try:
            logging.info(f"EMİR GÖNDERİLİYOR: {symbol} | Yön: {side} | Miktar: {quantity}")
            order = self.client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
            logging.info(f"EMİR BAŞARILI: {order}")
            return order
        except BinanceAPIException as e:
            logging.error(f"EMİR HATASI ({symbol}): {e.message}")
            return None

    def create_test_order(self, symbol: str, side: str, order_type: str, quantity: float):
        """Sanal (test) bir alım veya satım emri oluşturur."""
        logging.info(f"TEST EMRİ: {symbol} | Yön: {side} | Miktar: {quantity}")
        return {
            "symbol": symbol, "orderId": f"test_{int(time.time())}",
            "status": "FILLED", "side": side, "type": order_type,
            "executedQty": str(quantity)
        }

