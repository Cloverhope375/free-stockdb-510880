"""超配仓（跌破年线-5%一次性全投 / 涨到+7.5%全卖）专项出图
口径：不复权（与交易软件一致）｜ MA250 ｜ 起算见 config
输出：reports/chart_emergency.png
"""
import json, urllib.request, time
from pathlib import Path
import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

ROOT = Path(__file__).resolve().parent.parent
rcParams['font.sans-serif'] = ['Noto Sans SC', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False
REP = ROOT / "reports"; REP.mkdir(parents=True, exist_ok=True)
cfg = json.load(open(ROOT / "config.json", encoding="utf8"))


def get(u, ref='https://finance.sina.com.cn/'):
    for _ in range(6):
        try:
            req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0', 'Referer': ref})
            return urllib.request.urlopen(req, timeout=25).read().decode('utf-8', 'ignore')
        except Exception:
            time.sleep(1.2)
    return ''


txt = get('https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh510880&scale=240&ma=no&datalen=5000')
arr = json.loads(txt)
raw = [(x['day'], float(x['close'])) for x in arr]
start = cfg.get("start_date", "2013-01-01")
alld = [d for d, _ in raw]

N = cfg.get("ma_period", 250)
full_c = [c for _, c in raw]; n = len(full_c)
MA = [None] * n
for i in range(N - 1, n):
    MA[i] = sum(full_c[i - N + 1:i + 1]) / N
idx = [i for i in range(n) if raw[i][0] >= start]
buy_b = cfg["emergency"]["buy_bias"]; sell_b = cfg["emergency"]["sell_bias"]

cap = cfg["emergency"]["capital"]; cash = cap; sh = 0.0; stage = 0; was = True
navs = []; rounds = []; entry = None; days = []
for i in idx:
    d = raw[i][0]; P = raw[i][1]; b = None if MA[i] is None else P / MA[i] - 1
    if b is not None:
        if stage == 0 and was and b <= buy_b and cash > 1:
            sh = cash / P; cash = 0.0; stage = 1; entry = (d, P)
        if stage == 1 and b >= sell_b and sh > 0:
            cash = sh * P; sh = 0.0; stage = 0
            rounds.append((entry[0], entry[1], d, P, P / entry[1] - 1))
    navs.append(cash + sh * P); days.append(d); was = (b > buy_b) if b is not None else was

closes = [raw[i][1] for i in idx]; mas = [MA[i] for i in idx]; biases = [(c / m - 1) * 100 if m else None for c, m in zip(closes, mas)]
buys = [(r[0], r[1]) for r in rounds] + ([(entry[0], entry[1])] if stage == 1 and entry else [])
sells = [(r[2], r[3]) for r in rounds]

fig, ax = plt.subplots(3, 1, figsize=(15, 12), gridspec_kw={'height_ratios': [3, 1.2, 1.4]})
ax[0].plot(days, closes, lw=1.0, color='#1f5fa8', label='收盘价(不复权)')
ax[0].plot(days, mas, lw=1.4, color='#e8a33d', label='年线 MA250')
if buys:
    xs, ys = zip(*buys); ax[0].scatter(xs, ys, marker='^', s=110, color='#12a150', zorder=5, label='超配买入(-5%)')
if sells:
    xs, ys = zip(*sells); ax[0].scatter(xs, ys, marker='v', s=110, color='#d63a3a', zorder=5, label='卖出(+7.5%)')
for k, r in enumerate(rounds, 1):
    ax[0].annotate('%d轮 +%.1f%%' % (k, r[4] * 100), xy=(r[2], r[3]), xytext=(4, 10),
                   textcoords='offset points', fontsize=8.5, color='#d63a3a')
ax[0].set_title('510880 超配仓（跌破年线-5%%%s全投 / +7.5%%卖）· 起算 %s' % (' ', start))
ax[0].legend(loc='upper left'); ax[0].grid(alpha=.25)

ax[1].plot(days, biases, lw=1.0, color='#7b3fa0')
ax[1].axhline(0, color='#555', ls=':', lw=1)
ax[1].axhline(buy_b * 100, color='#12a150', ls='--', lw=1.2, label='买 -5%')
ax[1].axhline(sell_b * 100, color='#d63a3a', ls='--', lw=1.2, label='卖 +7.5%')
ax[1].set_ylabel('偏离度 %'); ax[1].legend(loc='upper left', fontsize=8); ax[1].grid(alpha=.25)

ax[2].plot(days, [v / 1e4 for v in navs], lw=1.4, color='#c0392b')
ax[2].axhline(cap / 1e4, color='#888', ls=':', lw=1)
ax[2].set_ylabel('超配仓净值(万)'); ax[2].grid(alpha=.25)

yrs = len(days) / 243.0
fin = navs[-1]; ann = (fin / cap) ** (1 / yrs) - 1
ax[2].set_title('起始 %.0f万 → 期末 %.1f万  (年化 %.2f%%, %d轮, %s)'
                % (cap / 1e4, fin / 1e4, ann * 100, len(rounds),
                   '当前持仓中' if stage == 1 else '当前空仓'))

plt.tight_layout()
out = REP / "chart_emergency.png"
plt.savefig(out, dpi=130)
print("已出图:", out)
print("轮次:"); 
for k, r in enumerate(rounds, 1):
    print("  %d轮 %s买%.3f → %s卖%.3f  %+.1f%%" % (k, r[0], r[1], r[2], r[3], r[4] * 100))
print("期末 %.1f万  年化 %.2f%%  %s" % (fin / 1e4, ann * 100, '持仓中' if stage == 1 else '空仓'))
