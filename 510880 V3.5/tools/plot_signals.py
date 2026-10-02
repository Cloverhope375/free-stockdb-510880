# -*- coding: utf-8 -*-
"""510880 年线波段图（2018起）：跌破年线信号 vs 真正买卖点"""
import sqlite3, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'strategy'))
import pandas as pd
from indicators import ma
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

rcParams['font.sans-serif'] = ['Noto Sans SC', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False

conn = sqlite3.connect(Path(__file__).resolve().parent.parent / 'data' / 'market.db')
df = pd.read_sql('select * from etf_daily order by date', conn); conn.close()
df['date'] = pd.to_datetime(df['date'])
df['MA'] = ma(df['close'], 250)
df['bias'] = df['close'] / df['MA'] - 1
df = df.dropna(subset=['MA']).reset_index(drop=True)
sub = df[df['date'] >= pd.to_datetime('2018-01-01')].reset_index(drop=True)

SELL = json.load(open(Path(__file__).resolve().parent.parent / 'config.json', encoding='utf8'))['sell_bias']
cash = 1.0; sh = 0.0; buys = []; sells = []
for i in range(len(sub)):
    P = float(sub['close'].iloc[i]); b = float(sub['bias'].iloc[i])
    if sh < 1e-12 and cash > 0 and b <= 0:
        sh = cash / P; cash = 0; buys.append(i)
    elif sh > 0 and b >= SELL:
        cash = sh * P; sh = 0; sells.append(i)

evs = []; in_ev = False
for i in range(len(sub)):
    b = float(sub['bias'].iloc[i])
    if not in_ev and b <= 0:
        in_ev = True; evs.append(i)
    elif in_ev and b > 0:
        in_ev = False
bset = set(buys)
other = [e for e in evs if e not in bset]
print('跌破年线信号 %d 个 = 真买入 %d + 持仓期 %d' % (len(evs), len(buys), len(other)))

fig, ax = plt.subplots(2, 1, figsize=(16, 10), gridspec_kw={'height_ratios': [3, 1.25]}, sharex=True)

ax[0].plot(sub['date'], sub['close'], color='#1f5fa8', lw=1.3, label='收盘价（不复权）', zorder=2)
ax[0].plot(sub['date'], sub['MA'], color='#e8a33d', lw=1.8, label='年线 MA250', zorder=3)
ax[0].scatter(sub['date'].iloc[other], sub['close'].iloc[other], s=58, color='#C026D3',
              marker='o', edgecolors='white', linewidths=0.9, zorder=4,
              label='跌破年线信号·发生在满仓期间（%d个，买不了）' % len(other))
ax[0].scatter(sub['date'].iloc[buys], sub['close'].iloc[buys], s=190, color='#12a150',
              marker='^', edgecolors='black', linewidths=0.6, zorder=6, label='真正买入（%d次）' % len(buys))
ax[0].scatter(sub['date'].iloc[sells], sub['close'].iloc[sells], s=190, color='#d63a3a',
              marker='v', edgecolors='black', linewidths=0.6, zorder=6, label='卖出·偏离≥+%.1f%%（%d次）' % (SELL * 100, len(sells)))
for k, i in enumerate(buys, 1):
    ax[0].annotate('%d' % k, xy=(sub['date'].iloc[i], sub['close'].iloc[i]),
                   xytext=(0, 14), textcoords='offset points', ha='center',
                   fontsize=10, fontweight='bold', color='#0b7a3c', zorder=7)
ax[0].set_title('510880 红利ETF · 围绕年线的波段（2018-01 ~ 2026-09）\n'
                '跌破年线信号共 %d 个 → 只有 %d 个发生在"空仓"时、能真正买入' % (len(evs), len(buys)),
                fontsize=14, pad=14)
ax[0].set_ylabel('价格（元）', fontsize=12)
ax[0].legend(loc='upper left', fontsize=10, framealpha=0.92)
ax[0].grid(alpha=.25)

ax[1].plot(sub['date'], sub['bias'] * 100, color='#7b3fa0', lw=1.1, label='偏离度 %', zorder=2)
ax[1].axhline(0, color='#12a150', ls='--', lw=1.2)
ax[1].axhline(SELL * 100, color='#d63a3a', ls='--', lw=1.2)
ax[1].axhline(-3, color='#999', ls=':', lw=1)
ax[1].axhline(-5, color='#999', ls=':', lw=1)
ax[1].scatter(sub['date'].iloc[other], sub['bias'].iloc[other] * 100, s=58, color='#C026D3', edgecolors='white', linewidths=0.9, zorder=4)
ax[1].scatter(sub['date'].iloc[buys], sub['bias'].iloc[buys] * 100, s=160, color='#12a150',
              marker='^', edgecolors='black', linewidths=0.6, zorder=6)
ax[1].scatter(sub['date'].iloc[sells], sub['bias'].iloc[sells] * 100, s=160, color='#d63a3a',
              marker='v', edgecolors='black', linewidths=0.6, zorder=6)
ax[1].text(sub['date'].iloc[5], SELL * 100, ' 卖出线 +%.1f%%' % (SELL * 100), color='#d63a3a', fontsize=9, va='center')
ax[1].text(sub['date'].iloc[5], 0, ' 年线 0%', color='#12a150', fontsize=9, va='center')
ax[1].text(sub['date'].iloc[5], -3, ' -3%', color='#777', fontsize=9, va='center')
ax[1].text(sub['date'].iloc[5], -5, ' -5%', color='#777', fontsize=9, va='center')
ax[1].set_ylabel('偏离年线 %', fontsize=12)
ax[1].grid(alpha=.25)

plt.tight_layout()
out = str(Path(__file__).resolve().parent.parent / 'reports' / '510880_signals_2018.png')
plt.savefig(out, dpi=130)
print('已出图:', out)
print('真买入:', [str(sub['date'].iloc[i].date()) for i in buys])
print('卖出:', [str(sub['date'].iloc[i].date()) for i in sells])
