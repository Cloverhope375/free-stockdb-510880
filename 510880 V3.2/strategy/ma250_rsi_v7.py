"""
510880 年线策略回测框架（对齐"红利年线策略"最终定稿）
主仓：偏离度<=0 满仓买入；偏离度>=7.5% 清仓（复利滚动，全资金）
应急金：首次跌破-5% 一次性全投；涨到+7.5% 全卖
支持 config.json 的 start_date（起算点，如 2007/2014/2018）
输出：reports/trades.csv、reports/summary.csv、reports/nav.csv
"""
import json, sqlite3, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "strategy"))
from indicators import ma, rsi_wilder, bias

REP = ROOT / "reports"
REP.mkdir(parents=True, exist_ok=True)

def load():
    cfg = json.load(open(ROOT / "config.json", encoding="utf8"))
    conn = sqlite3.connect(ROOT / "data" / "market.db")
    df = pd.read_sql("select * from etf_daily order by date", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    # 指标用【全历史】计算，避免截断后前250行为空
    df["MA"] = ma(df["close"], cfg["ma_period"])
    df["RSI"] = rsi_wilder(df["close"], cfg["rsi_period"])
    df["bias"] = bias(df["close"], df["MA"])
    start = cfg.get("start_date")
    if start:
        df = df[df["date"] >= pd.to_datetime(start)].reset_index(drop=True)
    return cfg, df

def max_drawdown(navs):
    peak = navs[0]; m = 0.0
    for v in navs:
        peak = max(peak, v); m = min(m, v / peak - 1)
    return abs(m)

def sim(df, cfg, trig=0.075, cash0=None):
    """主仓：满仓复利滚动。trig=卖出偏离阈值（默认+7.5%）"""
    cap = cash0 if cash0 else cfg["capital"]
    cash = cap; sh = 0.0; trades = []; navs = []; cost = cfg.get("cost", 0.0001)
    for _, row in df.iterrows():
        P = row["close"]; b = row["bias"]
        if pd.isna(b):
            navs.append(cash + sh * P); continue
        if sh < 1e-9 and cash > 1e-9 and b <= cfg["buy_bias"]:
            sh = cash / P * (1 - cost); cash = 0.0
            trades.append({"date": row["date"].date(), "action": "buy", "price": round(P, 4),
                           "bias": round(b, 4), "note": "主仓满仓"})
        elif sh > 1e-9 and b >= trig:
            cash += sh * P * (1 - cost); sh = 0.0
            trades.append({"date": row["date"].date(), "action": "sell", "price": round(P, 4),
                           "bias": round(b, 4), "note": "偏离>=%.1f%%" % (trig * 100)})
        navs.append(cash + sh * P)
    final = navs[-1]
    years = (len(df) - 1) / 243.0
    ann = (final / cap) ** (1 / years) - 1 if final > 0 and years > 0 else -1
    return {"final": final, "annual": ann, "mdd": max_drawdown(navs), "trades": trades,
            "open_pos": sh > 1e-9, "navs": navs}

def sim_emergency(df, cfg):
    trig = cfg["emergency"]["buy_bias"]; sell = cfg["emergency"]["sell_bias"]
    c0 = cfg["emergency"]["capital"]
    cash = c0; sh = 0.0; stage = 0; was_above = True
    trades = []; navs = []; cost = cfg.get("cost", 0.0001)
    for _, row in df.iterrows():
        P = row["close"]; b = row["bias"]
        if pd.isna(b):
            navs.append(cash + sh * P); continue
        if stage == 0 and was_above and b <= trig and cash > 1e-9:
            use = cash; sh = use / P * (1 - cost); cash = 0.0; stage = 1
            trades.append({"date": row["date"].date(), "action": "buy", "price": round(P, 4),
                           "bias": round(b, 4), "note": "应急金全投"})
        if stage == 1 and b >= sell and sh > 1e-9:
            cash += sh * P * (1 - cost); sh = 0.0; stage = 0
            trades.append({"date": row["date"].date(), "action": "sell", "price": round(P, 4),
                           "bias": round(b, 4), "note": "应急金卖出"})
        was_above = b > trig
        navs.append(cash + sh * P)
    final = navs[-1]; years = (len(df) - 1) / 243.0
    ann = (final / c0) ** (1 / years) - 1 if final > 0 and years > 0 else -1
    return {"final": final, "annual": ann, "mdd": max_drawdown(navs), "trades": trades,
            "open_pos": sh > 1e-9, "navs": navs}

if __name__ == "__main__":
    cfg, df = load()
    print("起算点(config.start_date): %s" % cfg.get("start_date"))
    print("数据区间: %s ~ %s  共%d行" % (df["date"].iloc[0].date(), df["date"].iloc[-1].date(), len(df)))

    m = sim(df, cfg); e = sim_emergency(df, cfg)
    pd.DataFrame(m["trades"] + e["trades"]).to_csv(REP / "trades.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"date": df["date"].dt.date, "nav_main": m["navs"], "nav_emergency": e["navs"],
                  "close": df["close"], "MA250": df["MA"], "bias": df["bias"]}
                 ).to_csv(REP / "nav.csv", index=False, encoding="utf-8-sig")
    rows = [
        {"account": "主仓", "start": cfg.get("start_date"), "final": round(m["final"], 0),
         "annual": "%.2f%%" % (m["annual"] * 100), "max_dd": "%.1f%%" % (m["mdd"] * 100),
         "trades": len(m["trades"]), "open": m["open_pos"]},
        {"account": "应急金", "start": cfg.get("start_date"), "final": round(e["final"], 0),
         "annual": "%.2f%%" % (e["annual"] * 100), "max_dd": "%.1f%%" % (e["mdd"] * 100),
         "trades": len(e["trades"]), "open": e["open_pos"]},
    ]
    pd.DataFrame(rows).to_csv(REP / "summary.csv", index=False, encoding="utf-8-sig")
    print("\n=== 回测结果 ===")
    for r in rows:
        print("  %-4s 期末 %10s  年化 %8s  最大回撤 %8s  交易%2d笔  持仓中=%s"
              % (r["account"], r["final"], r["annual"], r["max_dd"], r["trades"], r["open"]))
    print("\n明细: reports/trades.csv / summary.csv / nav.csv")
