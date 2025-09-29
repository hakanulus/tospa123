import numpy as np

def calculate_performance(trades_df, initial_balance):
    if trades_df.empty or len(trades_df) < 2:
        return {}

    balance = float(initial_balance)
    peak_balance = float(initial_balance)
    max_drawdown = 0.0
    wins, losses = 0, 0
    
    if len(trades_df) % 2 != 0:
        trades_df = trades_df.iloc[:-1]

    buy_prices = trades_df[trades_df['type'] == 'BUY']['price'].values
    sell_prices = trades_df[trades_df['type'] == 'SELL']['price'].values
    
    for i in range(len(buy_prices)):
        buy_price = float(buy_prices[i])
        sell_price = float(sell_prices[i])
        quantity = balance / buy_price
        new_balance = quantity * sell_price
        
        if new_balance > balance: wins += 1
        else: losses += 1
            
        balance = new_balance
        
        if balance > peak_balance: peak_balance = balance
        
        drawdown = (peak_balance - balance) / peak_balance
        if drawdown > max_drawdown: max_drawdown = drawdown

    total_trades = wins + losses
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
    final_balance = balance
    total_profit = final_balance - initial_balance
    profit_percentage = (total_profit / initial_balance) * 100
    
    return {
        "Başlangıç Bakiyesi": f"{initial_balance:.2f} USDT",
        "Bitiş Bakiyesi": f"{final_balance:.2f} USDT",
        "Toplam Kâr/Zarar": f"{total_profit:.2f} USDT",
        "Kâr Yüzdesi": f"{profit_percentage:.2f}%",
        "Toplam İşlem Sayısı": total_trades,
        "Kazanan İşlem Sayısı": wins,
        "Kaybeden İşlem Sayısı": losses,
        "Kazanma Oranı": f"{win_rate:.2f}%",
        "Maksimum Düşüş (Max Drawdown)": f"{max_drawdown * 100:.2f}%"
    }