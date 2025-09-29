from flask import Flask, render_template, jsonify, Response, request
from threading import Thread
import logging
import time
import json
import os
from datetime import datetime

# Proje içi modülleri import ediyoruz
from tospa.core.bot import TospaBot
from tospa.core.config import settings, load_settings, update_env_file

app = Flask(__name__)
bot = TospaBot()
bot_thread = None

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def index():
    """Ana kontrol paneli sayfasını render eder."""
    return render_template('index.html')

# --- BOT KONTROL ---
@app.route('/api/start', methods=['POST'])
def start_bot():
    """Botu bir arka plan thread'inde başlatır."""
    global bot_thread
    if not bot.is_running:
        try:
            bot._initialize()
        except Exception as e:
            logging.error(f"Bot başlatılamadı. Hata: {e}")
            return jsonify(status="error", message=f"Bot başlatılamadı: {e}")

        bot_thread = Thread(target=bot.start, daemon=True)
        bot_thread.start()
        return jsonify(status="success", message="Bot başlatıldı.")
    return jsonify(status="error", message="Bot zaten çalışıyor.")

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Çalışan bota durdurma sinyali gönderir."""
    if bot.is_running:
        bot.stop()
        return jsonify(status="success", message="Bot durduruluyor.")
    return jsonify(status="error", message="Bot zaten durdurulmuş.")

# --- VERİ GÖNDERME ---
@app.route('/api/status')
def get_status():
    """Arayüz için anlık durum verilerini sağlar."""
    current_settings = load_settings()
    balances = { 'USDT': '0.00', 'BTC': '0.00', 'ETH': '0.00' }
    prices = {}
    if bot.client and bot.client.is_ready:
        try:
            balances = { 'USDT': bot.client.get_account_balance('USDT'), 'BTC': bot.client.get_account_balance('BTC'), 'ETH': bot.client.get_account_balance('ETH'), }
            for p in current_settings.TARGET_PAIRS:
                price_info = bot.client.get_symbol_ticker(p)
                prices[p] = price_info.get('price', 'N/A') if price_info else 'N/A'
        except Exception as e:
            logging.warning(f"Durum alınırken hata oluştu: {e}")
    return jsonify( bot_status= "Çalışıyor" if bot.is_running else "Durduruldu", balances=balances, prices=prices, target_pairs=current_settings.TARGET_PAIRS)

@app.route('/api/logs')
def get_logs():
    def generate():
        try:
            with open('logs/activity.log', 'r') as f:
                f.seek(0,2)
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.5)
                        continue
                    yield f"data: {line}\n\n"
        except FileNotFoundError:
             yield f"data: Log dosyası henüz oluşturulmadı...\n\n"
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/trades')
def get_trades():
    trades_file = "data/trades.json"
    if not os.path.exists(trades_file): return jsonify([])
    try:
        with open(trades_file, 'r') as f:
            trades = json.load(f)
            return jsonify(sorted(trades, key=lambda x: x['timestamp'], reverse=True))
    except Exception: return jsonify([])

@app.route('/api/performance')
def get_performance():
    current_settings = load_settings()
    trades_file = "data/trades.json"
    if not os.path.exists(trades_file): return jsonify({"summary": {}, "chart_data": {}})
    try:
        with open(trades_file, 'r') as f:
            trades = sorted(json.load(f), key=lambda x: x['timestamp'])
    except Exception: return jsonify({"summary": {}, "chart_data": {}})
    pnl, wins, losses = 0.0, 0, 0
    open_positions_calc = {}
    chart_points = []
    initial_balance = 10000 
    fee = current_settings.BINANCE_FEE_PERCENT / 100.0
    for trade in trades:
        symbol, quantity, price = trade['symbol'], float(trade['quantity']), float(trade['price'])
        trade_value = quantity * price
        if trade['side'] == 'BUY':
            if symbol not in open_positions_calc: open_positions_calc[symbol] = {'quantity': 0, 'cost': 0}
            open_positions_calc[symbol]['quantity'] += quantity
            open_positions_calc[symbol]['cost'] += trade_value
            pnl -= trade_value * fee
        elif trade['side'] == 'SELL' and symbol in open_positions_calc and open_positions_calc[symbol]['quantity'] > 0:
            avg_buy_price = open_positions_calc[symbol]['cost'] / open_positions_calc[symbol]['quantity']
            trade_pnl = (price - avg_buy_price) * quantity
            pnl += trade_pnl
            pnl -= trade_value * fee
            if trade_pnl > 0: wins += 1
            else: losses += 1
            open_positions_calc[symbol]['quantity'] -= quantity
            open_positions_calc[symbol]['cost'] -= quantity * avg_buy_price
        chart_points.append({'x': trade['timestamp'], 'y': initial_balance + pnl})
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    summary = {'total_pnl': round(pnl, 2), 'win_rate': round(win_rate, 2), 'wins': wins, 'losses': losses, 'total_trades': total_trades}
    chart_data = {'labels': [datetime.fromisoformat(p['x']).strftime('%H:%M:%S') for p in chart_points], 'data': [p['y'] for p in chart_points]}
    return jsonify(summary=summary, chart_data=chart_data)

@app.route('/api/positions')
def get_positions():
    positions = bot._load_positions()
    return jsonify(positions)

# --- AYAR VE YÖNETİM ---
@app.route('/api/settings', methods=['GET'])
def get_settings():
    current_settings = load_settings()
    return jsonify(current_settings.model_dump())

@app.route('/api/settings/strategy', methods=['POST'])
def save_strategy_settings():
    current_settings = load_settings()
    data = request.get_json()
    current_settings.FAST_EMA_PERIOD = int(data.get('fast_ema', current_settings.FAST_EMA_PERIOD))
    current_settings.SLOW_EMA_PERIOD = int(data.get('slow_ema', current_settings.SLOW_EMA_PERIOD))
    current_settings.TREND_EMA_PERIOD = int(data.get('trend_ema', current_settings.TREND_EMA_PERIOD))
    current_settings.RSI_PERIOD = int(data.get('rsi_period', current_settings.RSI_PERIOD))
    current_settings.RSI_BUY_LEVEL = float(data.get('rsi_buy', current_settings.RSI_BUY_LEVEL))
    current_settings.RSI_SELL_LEVEL = float(data.get('rsi_sell', current_settings.RSI_SELL_LEVEL))
    current_settings.TRADE_AMOUNT_PERCENT = float(data.get('trade_percent', current_settings.TRADE_AMOUNT_PERCENT))
    current_settings.DEFAULT_TP_PERCENT = float(data.get('default_tp', current_settings.DEFAULT_TP_PERCENT))
    current_settings.DEFAULT_SL_PERCENT = float(data.get('default_sl', current_settings.DEFAULT_SL_PERCENT))
    current_settings.BINANCE_FEE_PERCENT = float(data.get('fee_percent', current_settings.BINANCE_FEE_PERCENT))
    current_settings.save_dynamic_settings()
    return jsonify(status="success", message="Strateji ayarları kaydedildi.")

@app.route('/api/settings/api_keys', methods=['POST'])
def save_api_keys():
    data = request.get_json()
    update_env_file("LIVE_BINANCE_API_KEY", data.get('live_api_key', ''))
    update_env_file("LIVE_BINANCE_API_SECRET", data.get('live_api_secret', ''))
    update_env_file("TEST_BINANCE_API_KEY", data.get('test_api_key', ''))
    update_env_file("TEST_BINANCE_API_SECRET", data.get('test_api_secret', ''))
    return jsonify(status="success", message="Tüm API anahtarları kaydedildi.")

@app.route('/api/settings/trade_mode', methods=['POST'])
def save_trade_mode():
    data = request.get_json()
    if 'test_mode' not in data or not isinstance(data['test_mode'], bool):
        return jsonify(status="error", message="Geçersiz mod verisi.")
    is_test = data['test_mode']
    update_env_file("IS_TEST_MODE", is_test)
    return jsonify(status="success", message=f"{'Sanal' if is_test else 'Canlı'} moda geçildi.")

@app.route('/api/add_pair', methods=['POST'])
def add_pair():
    if not bot.client or not bot.client.is_ready:
        return jsonify(status="error", message="Lütfen önce botu en az bir kez başlatın.")
    current_settings = load_settings()
    data = request.get_json()
    new_pair = data.get('pair', '').upper()
    if not new_pair or new_pair in current_settings.TARGET_PAIRS:
        return jsonify(status="error", message="Geçersiz veya mevcut parite.")
    if not bot.client.get_symbol_ticker(new_pair):
         return jsonify(status="error", message=f"{new_pair} Binance'de bulunamadı.")
    current_settings.TARGET_PAIRS.append(new_pair)
    current_settings.save_dynamic_settings()
    return jsonify(status="success", message=f"{new_pair} eklendi.")

@app.route('/api/remove_pair', methods=['POST'])
def remove_pair():
    current_settings = load_settings()
    data = request.get_json()
    pair_to_remove = data.get('pair', '').upper()
    if pair_to_remove in current_settings.TARGET_PAIRS:
        current_settings.TARGET_PAIRS.remove(pair_to_remove)
        current_settings.save_dynamic_settings()
        return jsonify(status="success", message=f"{pair_to_remove} kaldırıldı.")
    return jsonify(status="error", message="Parite bulunamadı.")

@app.route('/api/positions/update', methods=['POST'])
def update_position_tp_sl():
    data = request.get_json()
    symbol = data.get('symbol')
    tp_price = data.get('tp_price')
    sl_price = data.get('sl_price')
    if symbol in bot.open_positions:
        if tp_price is not None: bot.open_positions[symbol]['tp_price'] = float(tp_price)
        if sl_price is not None: bot.open_positions[symbol]['sl_price'] = float(sl_price)
        bot._save_positions()
        return jsonify(status="success", message=f"{symbol} TP/SL güncellendi.")
    return jsonify(status="error", message="Pozisyon bulunamadı.")

@app.route('/api/manual_trade', methods=['POST'])
def manual_trade():
    if not bot.client or not bot.client.is_ready:
        return jsonify(status="error", message="Lütfen önce botu en az bir kez başlatın.")
    data = request.get_json()
    symbol = data.get('symbol', '').upper()
    quantity = float(data.get('quantity', 0))
    side = data.get('side', '').upper()
    tp_price_raw = data.get('tp_price')
    sl_price_raw = data.get('sl_price')
    tp_price = float(tp_price_raw) if tp_price_raw else 0
    sl_price = float(sl_price_raw) if sl_price_raw else 0

    if not symbol or quantity <= 0 or side not in ['BUY', 'SELL']:
        return jsonify(status="error", message="Geçersiz emir verileri.")
    adjusted_quantity = bot.client.adjust_quantity_to_lot_size(symbol, quantity)
    if adjusted_quantity <= 0:
        return jsonify(status="error", message="Miktar, minimum işlem limitinin altında veya geçersiz.")
    order_result = bot.client.create_order(symbol, side, "MARKET", adjusted_quantity) if not bot.settings.IS_TEST_MODE else bot.client.create_test_order(symbol, side, "MARKET", adjusted_quantity)
    if order_result and order_result.get('status') == 'FILLED':
        price_info = bot.client.get_symbol_ticker(symbol)
        price = float(price_info['price']) if price_info else 0
        bot._log_trade(symbol, side, adjusted_quantity, price)
        if side == 'BUY':
            current_pos = bot.open_positions.get(symbol, {"quantity": 0, "entry_price": 0})
            total_quantity = current_pos['quantity'] + adjusted_quantity
            total_cost = (current_pos['quantity'] * current_pos['entry_price']) + (adjusted_quantity * price)
            new_avg_price = total_cost / total_quantity if total_quantity > 0 else 0
            bot.open_positions[symbol] = {
                "quantity": total_quantity, "entry_price": new_avg_price,
                "tp_price": tp_price if tp_price > 0 else current_pos.get('tp_price', 0),
                "sl_price": sl_price if sl_price > 0 else current_pos.get('sl_price', 0)
            }
        elif side == 'SELL' and symbol in bot.open_positions:
            del bot.open_positions[symbol]
        bot._save_positions()
        return jsonify(status="success", message=f"{symbol} için {side} emri başarıyla gerçekleştirildi.")
    else:
        return jsonify(status="error", message=f"Emir gerçekleştirilemedi: {order_result}")

@app.route('/api/close_all_positions', methods=['POST'])
def close_all_positions():
    if not bot.client or not bot.client.is_ready:
        return jsonify(status="error", message="Lütfen önce botu en az bir kez başlatın.")
    open_positions = bot._load_positions()
    if not open_positions:
        return jsonify(status="success", message="Satılacak açık pozisyon bulunmuyor.")
    sell_count, fail_count = 0, 0
    for symbol, pos_data in open_positions.items():
        quantity = pos_data['quantity']
        adjusted_quantity = bot.client.adjust_quantity_to_lot_size(symbol, quantity)
        if adjusted_quantity <= 0:
            fail_count += 1; continue
        order_result = bot.client.create_order(symbol, "SELL", "MARKET", adjusted_quantity) if not bot.settings.IS_TEST_MODE else bot.client.create_test_order(symbol, "SELL", "MARKET", adjusted_quantity)
        if order_result and order_result.get('status') == 'FILLED':
            price_info = bot.client.get_symbol_ticker(symbol)
            price = float(price_info['price']) if price_info else 0
            bot._log_trade(symbol, "SELL", adjusted_quantity, price)
            sell_count += 1
        else:
            fail_count += 1
    if sell_count > 0:
        bot.open_positions.clear()
        bot._save_positions()
    message = f"{sell_count} pozisyon başarıyla kapatıldı."
    if fail_count > 0: message += f" {fail_count} pozisyon kapatılamadı."
    return jsonify(status="success", message=message)

if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)

