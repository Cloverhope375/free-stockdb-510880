"""一键出图：价格+年线+买卖点 / 偏离度 / 净值曲线  → reports/510880_chart.png"""
import json, sqlite3, sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "strategy"))
from indicators import ma, rsi_wilder, bias

rcParams['font.sans-serif'] = ['Noto Sans SC', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False

REP = ROOT / "reports"; REP.mkdir(parents=True, exist_ok=True)
cfg = json.load(open(ROOT / "config.json", encoding="utf8"))

conn = sqlite3.connect(ROOT / "data" / "market.db")
full = pd.read_sql("select * from etf_daily order by date", conn); conn.close()
full["date"] = pd.to_datetime(full["date"])
full["MA"] = ma(full["close"], cfg["ma_period"])
full["bias"] = bias(full["close"], full["MA"])
df = full[full["date"] >= pd.to_datetime(cfg["start_date"])].reset_index(drop=True)

# 重放交易（与回测同逻辑）
def replay(df):
    cash = cfg["capital"]; sh = 0.0; buy_px = []; sell_px = []
    navs = []; cost = cfg.get("cost", 1e-4)
    for _, r in df.iterrows():
        P = r["close"]; b = r["bias"]
        if not pd.isna(b):
            if sh < 1e-9 and cash > 1e-9 and b <= cfg["buy_bias"]:
                sh = cash / P * (1 - cost); cash = 0.0; buy_px.append((r["date"], P))
            elif sh > 1e-9 and b >= cfg["sell_bias"]:
                cash += sh * P * (1 - cost); sh = 0.0; sell_px.append((r["date"], P))
        navs.append(cash + sh * P)
    return buy_px, sell_px, navs

bp, sp, navs = replay(df)

fig, ax = plt.subplots(3, 1, figsize=(15, 12), gridspec_kw={'height_ratios': [3, 1.3, 1.3]})
ax[0].plot(df["date"], df["close"], lw=1.0, color='#1f5fa8', label='收盘价(不复权)')
ax[0].plot(df["date"], df["MA"], lw=1.4, color='#e8a33d', label='年线 MA250')
if bp:
    xs, ys = zip(*bp); ax[0].scatter(xs, ys, marker='^', s=90, color='#12a150', zorder=5, label='买入')
if sp:
    xs, ys = zip(*sp); ax[0].scatter(xs, ys, marker='v', s=90, color='#d63a3a', zorder=5, label='卖出')
ax[0].set_title('510880 红利ETF · 年线策略买卖点（起算 %s）' % cfg["start_date"])
ax[0].legend(loc='upper left'); ax[0].grid(alpha=.25)

ax[1].plot(df["date"], df["bias"] * 100, lw=1.0, color='#7b3fa0')
ax[1].axhline(0, color='#12a150', ls='--', lw=1)
ax[1].axhline(cfg["sell_bias"] * 100, color='#d63a3a', ls='--', lw=1)
ax[1].axhline(cfg["emergency"]["buy_bias"] * 100, color='#12a150', ls=':', lw=1.2)
ax[1].set_ylabel('偏离度 %'); ax[1].grid(alpha=.25)

ax[2].plot(df["date"], [v / 1e4 for v in navs], lw=1.3, color='#c0392b')
ax[2].set_ylabel('主仓净值(万)'); ax[2].grid(alpha=.25)

plt.tight_layout()
out = REP / "510880_chart.png"
plt.savefig(out, dpi=130)
print("已出图:", out)
print("买入%d次, 卖出%d次" % (len(bp), len(sp)))
