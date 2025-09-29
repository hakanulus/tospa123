import os
import json
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

def update_env_file(key: str, value: str):
    """
    .env dosyasındaki belirli bir anahtarın değerini günceller veya ekler.
    Dosyanın geri kalanını korur.
    """
    env_file_path = ".env"
    lines = []
    key_found = False
    
    if os.path.exists(env_file_path):
        with open(env_file_path, 'r') as f:
            lines = f.readlines()

    with open(env_file_path, 'w') as f:
        for line in lines:
            if line.strip().startswith(key + '='):
                # Değer boolean ise tırnaksız yaz
                if value in ['True', 'False']:
                    f.write(f'{key}={value}\n')
                else:
                    f.write(f'{key}="{value}"\n')
                key_found = True
            elif line.strip():
                f.write(line)
        
        if not key_found:
            if value in ['True', 'False']:
                f.write(f'{key}={value}\n')
            else:
                f.write(f'{key}="{value}"\n')

class Settings(BaseSettings):
    """
    Pydantic kullanarak uygulama ayarlarını yönetir.
    Değerleri .env ve settings.json dosyalarından okur.
    """
    # .env dosyasından okunacaklar
    LIVE_BINANCE_API_KEY: str = ""
    LIVE_BINANCE_API_SECRET: str = ""
    TEST_BINANCE_API_KEY: str = ""
    TEST_BINANCE_API_SECRET: str = ""
    IS_TEST_MODE: bool = True

    # settings.json dosyasından okunacaklar
    TARGET_PAIRS: List[str] = ["BTCUSDT", "ETHUSDT"]
    TRADE_AMOUNT_PERCENT: float = 25.0
    FAST_EMA_PERIOD: int = 12
    SLOW_EMA_PERIOD: int = 26
    DEFAULT_TP_PERCENT: float = 2.0
    DEFAULT_SL_PERCENT: float = 1.0
    BINANCE_FEE_PERCENT: float = 0.1 # Standart %0.1 komisyon oranı

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

    def save_dynamic_settings(self):
        """Dinamik ayarları settings.json dosyasına kaydeder."""
        dynamic_data = self.model_dump(include={
            'TARGET_PAIRS', 'TRADE_AMOUNT_PERCENT', 
            'FAST_EMA_PERIOD', 'SLOW_EMA_PERIOD',
            'DEFAULT_TP_PERCENT', 'DEFAULT_SL_PERCENT',
            'BINANCE_FEE_PERCENT' # Yeni ayarı ekle
        })
        with open("settings.json", "w") as f:
            json.dump(dynamic_data, f, indent=4)

def load_settings() -> Settings:
    """
    Ayarları .env ve settings.json dosyalarından yükler.
    """
    settings_obj = Settings()
    
    settings_file = "settings.json"
    if os.path.exists(settings_file):
        with open(settings_file, "r") as f:
            try:
                dynamic_data = json.load(f)
                updated_data = settings_obj.model_dump()
                updated_data.update(dynamic_data)
                settings_obj = Settings(**updated_data)
            except (json.JSONDecodeError, TypeError):
                print("UYARI: settings.json dosyası bozuk veya uyumsuz, varsayılanlar oluşturuluyor.")
                settings_obj.save_dynamic_settings()
    else:
        settings_obj.save_dynamic_settings()
        
    return settings_obj

# Proje genelinde kullanılacak tek bir ayar nesnesi
settings = load_settings()

