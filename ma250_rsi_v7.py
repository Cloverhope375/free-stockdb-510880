"""
V7 MA250 + RSI动态卖出回测框架
"""
import json,sqlite3
import pandas as pd
from strategy.indicators import rsi

cfg=json.load(open("config.json",encoding="utf8"))

conn=sqlite3.connect("data/market.db")
df=pd.read_sql("select * from etf_daily",conn)
conn.close()

date=[c for c in df.columns if "日期" in c or "date" in c.lower()][0]
close=[c for c in df.columns if "收盘" in c or "close" in c.lower()][0]

df[date]=pd.to_datetime(df[date])
df=df.sort_values(date)
df["MA250"]=df[close].rolling(cfg["ma_period"]).mean()
df["RSI"]=rsi(df[close],cfg["rsi_period"])

cash=1.0
hold=False
trades=[]

for _,row in df.iterrows():
    if not hold and row[close]>row["MA250"]:
        buy=row
        hold=True
    elif hold and row["RSI"]>=cfg["sell_rsi"]:
        sell=row
        trades.append({
            "buy_date":buy[date],
            "buy_price":buy[close],
            "sell_date":sell[date],
            "sell_price":sell[close]
        })
        hold=False

pd.DataFrame(trades).to_csv("reports/trades.csv",index=False)
print("saved reports/trades.csv")
