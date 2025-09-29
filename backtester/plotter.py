import matplotlib.pyplot as plt

def plot_results(df, trades_df, symbol):
    """
    Fiyat, EMA'lar ve alım/satım noktalarını içeren bir grafik çizer.
    """
    plt.figure(figsize=(15, 7))
    plt.plot(df.index, df['Close'], label='Fiyat', color='blue', alpha=0.6)
    plt.plot(df.index, df['ema_short'], label='Kısa EMA', color='orange', linestyle='--')
    plt.plot(df.index, df['ema_long'], label='Uzun EMA', color='purple', linestyle='--')
    
    if 'ema_trend' in df.columns:
        plt.plot(df.index, df['ema_trend'], label='Ana Trend EMA', color='gray', linestyle=':')

    buy_signals = trades_df[trades_df['type'] == 'BUY']
    sell_signals = trades_df[trades_df['type'] == 'SELL']

    plt.scatter(buy_signals['date'], buy_signals['price'], marker='^', color='green', s=100, label='Al Sinyali', zorder=5)
    plt.scatter(sell_signals['date'], sell_signals['price'], marker='v', color='red', s=100, label='Sat Sinyali', zorder=5)

    plt.title(f'{symbol} Backtest Sonuçları')
    plt.xlabel('Tarih')
    plt.ylabel('Fiyat (USDT)')
    plt.legend()
    plt.grid(True)
    plt.show()