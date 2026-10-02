"""
510880 数据更新脚本
功能：
1. 获取 ETF 日线数据
2. 保存 CSV
3. 写入 SQLite

首次运行会创建 data/market.db
"""

from pathlib import Path
import pandas as pd

DB_DIR = Path("data")
DB_DIR.mkdir(exist_ok=True)

CSV_DIR = DB_DIR / "raw"
CSV_DIR.mkdir(exist_ok=True)

DB_FILE = DB_DIR / "market.db"


def fetch_510880():
    try:
        import akshare as ak
    except ImportError:
        raise SystemExit("请先 pip install akshare")

    # 红利ETF历史数据接口
    df = ak.fund_etf_hist_em(
        symbol="510880",
        adjust="qfq"
    )

    df["code"] = "510880"
    return df


def save_data(df):
    csv_file = CSV_DIR / "510880.csv"
    df.to_csv(csv_file, index=False, encoding="utf-8-sig")

    import sqlite3
    conn = sqlite3.connect(DB_FILE)

    df.to_sql(
        "etf_daily",
        conn,
        if_exists="replace",
        index=False
    )

    conn.close()

    print("完成:")
    print(csv_file)
    print(DB_FILE)


if __name__ == "__main__":
    data = fetch_510880()
    save_data(data)
