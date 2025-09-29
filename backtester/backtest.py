import pandas as pd

def calculate_rsi(data, period=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def run_backtest(df, params): # 'settings' yerine 'params' alıyor
    """
    Verilen veri ve parametrelerle stratejiyi test eder.
    """
    # Ayarları artık doğrudan params sözlüğünden alıyoruz
    trend_period = params.get('ema_trend_period', 200)
    rsi_period = params.get('rsi_period', 14)
    rsi_buy_level = params.get('rsi_buy_level', 50)
    rsi_sell_level = params.get('rsi_sell_level', 75)

    df['ema_short'] = df['Close'].ewm(span=params['ema_short_period'], adjust=False).mean()
    df['ema_long'] = df['Close'].ewm(span=params['ema_long_period'], adjust=False).mean()
    df['ema_trend'] = df['Close'].ewm(span=trend_period, adjust=False).mean()
    df['rsi'] = calculate_rsi(df, rsi_period)

    df['signal'] = 0
    
    buy_crossover = (df['ema_short'] > df['ema_long']) & (df['ema_short'].shift(1) <= df['ema_long'].shift(1))
    buy_trend = df['Close'] > df['ema_trend']
    df.loc[buy_crossover & buy_trend, 'signal'] = 1

    sell_crossover = (df['ema_short'] < df['ema_long']) & (df['ema_short'].shift(1) >= df['ema_long'].shift(1))
    sell_overbought = df['rsi'] > rsi_sell_level
    df.loc[sell_crossover | sell_overbought, 'signal'] = -1
    
    position = 0
    trades = []
    for i, row in df.iterrows():
        if row['signal'] == 1 and position == 0:
            position = 1
            trades.append({'date': i, 'type': 'BUY', 'price': row['Close']})
        elif row['signal'] == -1 and position == 1:
            position = 0
            trades.append({'date': i, 'type': 'SELL', 'price': row['Close']})
            
    return pd.DataFrame(trades), df