"""
V2 数据更新模块
"""
from pathlib import Path
import sqlite3
import pandas as pd

DATA=Path("data")
RAW=DATA/"raw"
RAW.mkdir(parents=True,exist_ok=True)

def fetch():
    import akshare as ak
    return ak.fund_etf_hist_em(symbol="510880", adjust="qfq")

def save(df):
    csv=RAW/"510880.csv"
    df.to_csv(csv,index=False,encoding="utf-8-sig")
    conn=sqlite3.connect(DATA/"market.db")
    df.to_sql("etf_daily",conn,if_exists="replace",index=False)
    conn.close()
    print("updated",csv)

if __name__=="__main__":
    save(fetch())
