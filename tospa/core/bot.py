import logging
import time
import json
import os
from threading import Event
from datetime import datetime

# Proje içi modülleri import ediyoruz
from tospa.core.config import load_settings, Settings
from tospa.api.binance_client import TospaBinanceClient
from tospa.strategies.warrior_turtle import WarriorTurtleStrategy
from tospa.core.logging_config import setup_logging

class TospaBot:
    """
    Stratejiyi, API istemcisini ve yapılandırmayı bir araya getirerek
    alım-satım döngüsünü yöneten ana bot sınıfı.
    Artık TP/SL takibi yapar ve pozisyonları bir JSON dosyasında saklar.
    """
    def __init__(self):
        self._stop_event = Event()
        self.is_running = False
        setup_logging()
        logging.info("Tospa Bot nesnesi oluşturuldu...")
        self.settings = load_settings()
        self.client = None
        self.strategy = None
        self.positions_file = "data/positions.json"
        self.open_positions = self._load_positions() # Pozisyonları dosyadan yükle

    def _load_positions(self):
        """Mevcut pozisyonları positions.json dosyasından yükler."""
        if os.path.exists(self.positions_file):
            try:
                with open(self.positions_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}

    def _save_positions(self):
        """Mevcut pozisyonları positions.json dosyasına kaydeder."""
        log_dir = "data"
        if not os.path.exists(log_dir): os.makedirs(log_dir)
        with open(self.positions_file, 'w') as f:
            json.dump(self.open_positions, f, indent=4)

    def _initialize(self, force_live: bool = False):
        # ... (kod aynı kalıyor) ...
        self.settings = load_settings()
        use_testnet = self.settings.IS_TEST_MODE and not force_live
        api_key = self.settings.TEST_BINANCE_API_KEY if use_testnet else self.settings.LIVE_BINANCE_API_KEY
        api_secret = self.settings.TEST_BINANCE_API_SECRET if use_testnet else self.settings.LIVE_BINANCE_API_SECRET
        self.client = TospaBinanceClient(api_key=api_key, api_secret=api_secret, testnet=use_testnet)
        if self.client and self.client.is_ready:
            self.strategy = WarriorTurtleStrategy(self.client, self.settings)
        return self.client

    def start(self):
        self.is_running = True
        self._stop_event.clear()
        logging.info("Bot ana döngüsü başlatıldı.")
        self.run()
        
    def stop(self):
        self.is_running = False
        self._stop_event.set()
        logging.info("Bot için durdurma sinyali gönderildi.")

    def run(self):
        self._initialize()
        
        while not self._stop_event.is_set():
            try:
                self._initialize() # Ayarları ve istemciyi her döngüde yenile
                
                # 1. TP/SL Kontrolü
                self._check_positions_for_tp_sl()

                # 2. Strateji Analizi
                logging.info(f"Yeni strateji analiz döngüsü başlıyor. Pariteler: {self.settings.TARGET_PAIRS}")
                for pair in self.settings.TARGET_PAIRS:
                    if self._stop_event.is_set(): break
                    self._process_symbol(pair)
                
                if not self._stop_event.is_set():
                    logging.info(f"Analiz tamamlandı. 30 saniye bekleniyor...")
                    for _ in range(30):
                        if self._stop_event.is_set(): break
                        time.sleep(1)
            
            except Exception as e:
                logging.error(f"Ana döngüde beklenmedik bir hata oluştu: {e}", exc_info=True)
                time.sleep(30)
        
        logging.info("Bot döngüsü başarıyla durduruldu.")

    def _check_positions_for_tp_sl(self):
        """Açık pozisyonları kontrol eder ve TP/SL tetiklenmişse satar."""
        if not self.open_positions:
            return
        
        logging.info("TP/SL için açık pozisyonlar kontrol ediliyor...")
        positions_to_close = []

        for symbol, pos_data in self.open_positions.items():
            price_info = self.client.get_symbol_ticker(symbol)
            if not price_info: continue
            
            current_price = float(price_info['price'])
            tp_price = pos_data.get('tp_price', 0)
            sl_price = pos_data.get('sl_price', 0)

            if tp_price > 0 and current_price >= tp_price:
                logging.info(f"✅ TP TETİKLENDİ: {symbol} | Mevcut Fiyat: {current_price} >= TP Fiyatı: {tp_price}")
                self._execute_trade(symbol, "SELL", "TP_TRIGGER")
                positions_to_close.append(symbol)

            elif sl_price > 0 and current_price <= sl_price:
                logging.info(f"❌ SL TETİKLENDİ: {symbol} | Mevcut Fiyat: {current_price} <= SL Fiyatı: {sl_price}")
                self._execute_trade(symbol, "SELL", "SL_TRIGGER")
                positions_to_close.append(symbol)

        # Kapatılan pozisyonları listeden kaldır
        if positions_to_close:
            for symbol in positions_to_close:
                if symbol in self.open_positions:
                    del self.open_positions[symbol]
            self._save_positions()

    def _process_symbol(self, symbol: str):
        """Stratejiye göre alım sinyali varsa işlem yapar."""
        if not self.client or not self.client.is_ready: return
        if symbol in self.open_positions: return # Zaten açık pozisyon varsa strateji alımı yapma

        signal = self.strategy.analyze(symbol)
        if signal == "BUY":
            self._execute_trade(symbol, "BUY", "STRATEGY")

    def _execute_trade(self, symbol: str, side: str, reason: str):
        """Bir alım/satım işlemini gerçekleştirir ve kaydeder."""
        logging.info(f"{side} EMRİ ({reason}): {symbol}. İşlem yapılıyor...")
        
        order_quantity = 0
        if side == "BUY":
            balance = self.client.get_account_balance("USDT")
            amount_to_invest = float(balance) * (self.settings.TRADE_AMOUNT_PERCENT / 100)
            price = float(self.client.get_symbol_ticker(symbol)['price'])
            raw_quantity = amount_to_invest / price
            order_quantity = self.client.adjust_quantity_to_lot_size(symbol, raw_quantity)
        
        elif side == "SELL":
            # Satışta, mevcut pozisyonun tamamını sat
            quantity_to_sell = self.open_positions.get(symbol, {}).get('quantity', 0)
            order_quantity = self.client.adjust_quantity_to_lot_size(symbol, quantity_to_sell)

        if not order_quantity or order_quantity <= 0:
            logging.warning(f"Hesaplanan miktar geçersiz ({order_quantity}). İşlem iptal edildi.")
            return

        order_result = self.client.create_order(symbol, side, "MARKET", order_quantity) if not self.settings.IS_TEST_MODE else self.client.create_test_order(symbol, side, "MARKET", order_quantity)

        if order_result and order_result.get('status') == 'FILLED':
            price = float(self.client.get_symbol_ticker(symbol)['price'])
            self._log_trade(symbol, side, order_quantity, price)
            
            # Pozisyon hafızasını güncelle
            if side == "BUY":
                tp_price = price * (1 + self.settings.DEFAULT_TP_PERCENT / 100)
                sl_price = price * (1 - self.settings.DEFAULT_SL_PERCENT / 100)
                self.open_positions[symbol] = {
                    "quantity": order_quantity,
                    "entry_price": price,
                    "tp_price": tp_price,
                    "sl_price": sl_price
                }
            elif side == "SELL" and symbol in self.open_positions:
                del self.open_positions[symbol]
            
            self._save_positions()
        else:
            logging.error(f"{symbol} için {side} emri gerçekleştirilemedi: {order_result}")

    def _log_trade(self, symbol, side, quantity, price):
        # ... (kod aynı kalıyor) ...
        trade_data = {"timestamp": datetime.now().isoformat(), "symbol": symbol, "side": side, "quantity": quantity, "price": price}
        log_dir, log_file = "data", "data/trades.json"
        if not os.path.exists(log_dir): os.makedirs(log_dir)
        trades = []
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                try: trades = json.load(f)
                except json.JSONDecodeError: pass
        trades.append(trade_data)
        with open(log_file, 'w') as f:
            json.dump(trades, f, indent=4)
        logging.info(f"İşlem kaydedildi: {symbol} {side} {quantity}")

