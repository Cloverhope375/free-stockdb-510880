"""技术指标：MA250 / RSI(Wilder) / 偏离度 bias"""
import pandas as pd

def ma(close, period=250):
    return close.rolling(period).mean()

def rsi_wilder(close, period=14):
    """标准 Wilder RSI"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1.0/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0/period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def bias(close, ma250):
    """偏离度 = 收盘/年线 - 1"""
    return close / ma250 - 1
