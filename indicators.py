import pandas as pd

def rsi(series,period=14):
    delta=series.diff()
    gain=delta.clip(lower=0).rolling(period).mean()
    loss=(-delta.clip(upper=0)).rolling(period).mean()
    rs=gain/loss
    return 100-(100/(1+rs))
