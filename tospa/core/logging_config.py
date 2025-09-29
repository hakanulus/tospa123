import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """
    Proje genelinde kullanılacak olan loglama sistemini kurar.
    - Konsola INFO seviyesinde log basar.
    - 'logs/activity.log' dosyasına DEBUG seviyesinde log yazar.
    - Dosya 5MB boyutuna ulaşınca rotasyon yapar (eski logları arşivler).
    """
    # logs klasörünün var olduğundan emin ol
    log_directory = "logs"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # Ana logger'ı al ve seviyesini en düşük olan DEBUG yap
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Mevcut handler'ları temizle (birden fazla handler eklenmesini önlemek için)
    if logger.hasHandlers():
        logger.handlers.clear()

    # Log formatını belirle
    log_format = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

    # Konsol (Stream) Handler'ı oluştur
    # Sadece INFO ve üzeri seviyedeki logları konsola basar.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    # Dosya (File) Handler'ı oluştur
    # Tüm logları (DEBUG ve üzeri) dosyaya yazar.
    # RotatingFileHandler ile dosya boyutu kontrol edilir.
    file_handler = RotatingFileHandler('logs/activity.log', maxBytes=5*1024*1024, backupCount=2)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    logging.info("Loglama sistemi başarıyla kuruldu.")

# Bu dosya doğrudan çalıştırıldığında log sistemini test et
if __name__ == "__main__":
    setup_logging()
    logging.debug("Bu bir debug mesajıdır, sadece dosyada görünmelidir.")
    logging.info("Bu bir info mesajıdır, hem konsolda hem dosyada görünür.")
    logging.warning("Bu bir uyarı mesajıdır.")
    logging.error("Bu bir hata mesajıdır.")
    print("\nLog testi tamamlandı. Lütfen 'logs/activity.log' dosyasını kontrol edin.")
