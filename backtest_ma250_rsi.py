"""
510880 MA250 + RSI 基础回测框架
"""

import sqlite3
import pandas as pd
import numpy as np

DB = "data/market.db"


def load_data():
    conn = sqlite3.connect(DB)
    df = pd.read_sql(
        "select * from etf_daily",
        conn
    )
    conn.close()

    return df


def run():
    df = load_data()

    # 自动寻找日期和收盘字段
    date_col = [c for c in df.columns if "日期" in c or "date" in c.lower()][0]
    close_col = [c for c in df.columns if "收盘" in c or "close" in c.lower()][0]

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)

    df["MA250"] = df[close_col].rolling(250).mean()

    delta = df[close_col].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()

    rs = gain / loss
    df["RSI"] = 100 - 100 / (1 + rs)

    df.to_csv(
        "data/510880_signal.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("回测信号文件已生成")


if __name__ == "__main__":
    run()
