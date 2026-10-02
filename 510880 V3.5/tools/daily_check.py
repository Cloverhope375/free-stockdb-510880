# -*- coding: utf-8 -*-
"""
510880 红利ETF · 每日体检
跑一次 = 联网更新数据 + 告诉你：今天到没到买卖点、价位是多少。

用法：
  Windows：双击根目录的「每日体检.bat」
  Mac    ：双击根目录的「每日体检.command」
  命令行 ：python tools/daily_check.py
"""
import json, sqlite3, sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "strategy"))
sys.path.insert(0, str(ROOT / "collector"))


def ensure_pandas():
    try:
        import pandas  # noqa: F401
        return
    except ImportError:
        pass
    print("首次运行，正在安装依赖（约需 1 分钟，只需一次）…")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pandas"])
    except Exception as e:
        print("依赖安装失败：%s" % e)
        print("请手动运行：pip install pandas")
        sys.exit(1)


def refresh():
    """尝试联网更新数据；失败则退回本地缓存"""
    try:
        import update_510880 as C
        rows = C.fetch_sina()
        if len(rows) > 500:
            C.save(rows)
            return True
    except Exception:
        pass
    return False


def main():
    ensure_pandas()
    import pandas as pd
    from indicators import ma

    fresh = refresh()

    cfg = json.load(open(ROOT / "config.json", encoding="utf8"))
    conn = sqlite3.connect(ROOT / "data" / "market.db")
    df = pd.read_sql("select * from etf_daily order by date", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    df["MA"] = ma(df["close"], cfg["ma_period"])
    df = df.dropna(subset=["MA"]).reset_index(drop=True)

    r = df.iloc[-1]
    P = float(r["close"]); M = float(r["MA"]); b = P / M - 1
    n = cfg["ma_period"]
    sell = M * (1 + cfg["sell_bias"])                  # 主仓轨卖点（年线+5%）
    buy = M * (1 + cfg["buy_bias"])                    # 主仓轨买点（年线）
    em_buy = M * (1 + cfg["emergency"]["buy_bias"])    # 极限轨买点（年线-5%）
    em_sell = M * (1 + cfg["emergency"]["sell_bias"])  # 极限轨卖点（年线+7.5%）
    deep = M * 0.90

    W = "=" * 48
    print(W)
    print("  510880 红利ETF · 今日体检")
    print("  数据截至 %s  %s" % (r["date"].date(), "（已联网更新）" if fresh else "（本地缓存，未联网）"))
    print(W)
    print()
    print("【价格快照】")
    print("  最新收盘            %.3f" % P)
    print("  年线 MA%-4d         %.3f   (不复权)" % (n, M))
    print("  偏离度              %+.2f%%" % (b * 100))
    print()
    print("【双轨 · 操作价位】（年线每天在动，记得同步到价提醒）")
    print("  主仓轨   买 年线          %.3f   ／   卖 年线+5%%     %.3f" % (buy, sell))
    print("  极限轨   买 年线-5%%       %.3f   ／   卖 年线+7.5%%  %.3f" % (em_buy, em_sell))
    print("  （深坑参考 年线-10%% = %.3f）" % deep)
    print()
    print("【今天怎么动】")
    if b <= cfg["buy_bias"]:
        print("  偏离度 %+.2f%%  → 已跌破年线 →【主仓轨 · 买入区】：尾盘满仓买入" % (b * 100))
    elif b >= cfg["sell_bias"]:
        print("  偏离度 %+.2f%%  → 已超 +5%%  →【主仓轨 · 卖出区】：尾盘清仓" % (b * 100))
    else:
        print("  偏离度 %+.2f%%  →【持有 / 观望区】：什么都不用做" % (b * 100))
    if b <= cfg["emergency"]["buy_bias"]:
        print("  → 已跌破 -5%% →【极限轨 · 买入区】：动用预留资金全投（%.3f）" % em_buy)
    elif b >= cfg["emergency"]["sell_bias"]:
        print("  → 已超 +7.5%% →【极限轨 · 卖出区】：全部卖出（%.3f）" % em_sell)
    else:
        print("  → 极限轨：无动作（买 %.3f / 卖 %.3f）" % (em_buy, em_sell))
    print()
    print("【还差多少】")
    print("  主仓轨   距卖出点还需涨 %+.2f%%   ｜   距买入点还需跌 %+.2f%%"
          % ((sell / P - 1) * 100, (1 - buy / P) * 100))
    print("  极限轨   距买入点还需跌 %+.2f%%" % ((1 - em_buy / P) * 100))
    print()
    print("（提示：年线每日变化，本表仅供参考，不构成投资建议）")


if __name__ == "__main__":
    main()
