# -*- coding: utf-8 -*-
"""510880 三种买点对比图：年线买 vs -3%买 vs -5%买（2018-2026）"""
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


def sim(bb):
    cash = 1.0; sh = 0.0; buys = []; sells = []
    for i in range(len(sub)):
        P = float(sub['close'].iloc[i]); b = float(sub['bias'].iloc[i])
        if sh < 1e-12 and cash > 0 and b <= bb:
            sh = cash / P; cash = 0; buys.append(i)
        elif sh > 0 and b >= SELL:
            cash = sh * P; sh = 0; sells.append(i)
    return buys, sells, cash + sh * float(sub['close'].iloc[-1])


def events(th):
    evs = []; in_ev = False
    for i in range(len(sub)):
        b = float(sub['bias'].iloc[i])
        if not in_ev and b <= th:
            in_ev = True; evs.append(i)
        elif in_ev and b > th:
            in_ev = False
    return evs


A = sim(0.0); B = sim(-0.03); C = sim(-0.05)
nA, nB, nC = len(events(0.0)), len(events(-0.03)), len(events(-0.05))

fig, ax = plt.subplots(2, 1, figsize=(16, 10.5), gridspec_kw={'height_ratios': [3, 1.3]}, sharex=True)

ax[0].plot(sub['date'], sub['close'], color='#1f5fa8', lw=1.3, label='收盘价（不复权）', zorder=2)
ax[0].plot(sub['date'], sub['MA'], color='#e8a33d', lw=1.8, label='年线 MA250', zorder=3)

# 同一轮的三个买点用细虚线连起来，显示"买点沿年线事件下移"
for k in range(min(len(A[0]), len(B[0]), len(C[0]))):
    xs = [sub['date'].iloc[A[0][k]], sub['date'].iloc[B[0][k]], sub['date'].iloc[C[0][k]]]
    ys = [sub['close'].iloc[A[0][k]], sub['close'].iloc[B[0][k]], sub['close'].iloc[C[0][k]]]
    ax[0].plot(xs, ys, color='#bbbbbb', ls=':', lw=1.0, zorder=4)

ax[0].scatter(sub['date'].iloc[A[0]], sub['close'].iloc[A[0]], s=210, marker='^',
              color='#12a150', edgecolors='black', linewidths=0.7, zorder=7,
              label='年线买（绿▲）— 触发%d次 / 买到%d次' % (nA, len(A[0])))
ax[0].scatter(sub['date'].iloc[B[0]], sub['close'].iloc[B[0]], s=170, marker='D',
              color='#1e88e5', edgecolors='black', linewidths=0.7, zorder=6,
              label='年线-3%%买（蓝◆）— 触发%d次 / 买到%d次' % (nB, len(B[0])))
ax[0].scatter(sub['date'].iloc[C[0]], sub['close'].iloc[C[0]], s=150, marker='o',
              color='#C026D3', edgecolors='black', linewidths=0.7, zorder=5,
              label='年线-5%%买（紫●）— 触发%d次 / 买到%d次' % (nC, len(C[0])))
ax[0].scatter(sub['date'].iloc[A[1]], sub['close'].iloc[A[1]], s=200, marker='v',
              color='#d63a3a', edgecolors='black', linewidths=0.7, zorder=7,
              label='卖出 +%.1f%%（三种方案相同，%d次）' % (SELL * 100, len(A[1])))
for k, i in enumerate(A[0], 1):
    ax[0].annotate('%d' % k, xy=(sub['date'].iloc[i], sub['close'].iloc[i]),
                   xytext=(-2, 15), textcoords='offset points', ha='center',
                   fontsize=10, fontweight='bold', color='#0b7a3c', zorder=8)

ax[0].set_title('510880 · 三种买点对比（2018-01 ~ 2026-09）\n'
                '同一条年线事件里：绿▲最早最贵 → 蓝◆更晚更便宜 → 紫●最晚最便宜',
                fontsize=14, pad=12)
ax[0].set_ylabel('价格（元）', fontsize=12)
ax[0].legend(loc='lower left', fontsize=10, framealpha=0.93)
ax[0].grid(alpha=.25)

def _ann(v, yrs): return (v ** (1 / yrs) - 1) * 100
_yrs = len(sub) / 243.0
info = ('年线买    触发%d次 → 买到%d次 → 1元变 %.3f（年化 %.2f%%）\n'
        '年线-3%%买 触发%d次 → 买到%d次 → 1元变 %.3f（年化 %.2f%%）\n'
        '年线-5%%买 触发%d次 → 买到%d次 → 1元变 %.3f（年化 %.2f%%）'
        % (nA, len(A[0]), A[2], _ann(A[2], _yrs),
           nB, len(B[0]), B[2], _ann(B[2], _yrs),
           nC, len(C[0]), C[2], _ann(C[2], _yrs)))
ax[0].text(0.985, 0.975, info, transform=ax[0].transAxes, ha='right', va='top',
           fontsize=11, linespacing=1.5,
           bbox=dict(boxstyle='round,pad=0.6', facecolor='#fffbe6', edgecolor='#d4b106', alpha=0.95))

ax[1].plot(sub['date'], sub['bias'] * 100, color='#7b3fa0', lw=1.1, zorder=2)
for y, c, t in [(0, '#12a150', '年线 0%'), (-3, '#1e88e5', '-3%'), (-5, '#C026D3', '-5%'), (SELL * 100, '#d63a3a', '卖出 +%.1f%%' % (SELL * 100))]:
    ax[1].axhline(y, color=c, ls='--', lw=1.2)
    ax[1].text(sub['date'].iloc[5], y, ' ' + t, color=c, fontsize=9, va='center')
ax[1].scatter(sub['date'].iloc[A[0]], sub['bias'].iloc[A[0]] * 100, s=150, marker='^', color='#12a150', edgecolors='black', linewidths=0.6, zorder=6)
ax[1].scatter(sub['date'].iloc[B[0]], sub['bias'].iloc[B[0]] * 100, s=130, marker='D', color='#1e88e5', edgecolors='black', linewidths=0.6, zorder=6)
ax[1].scatter(sub['date'].iloc[C[0]], sub['bias'].iloc[C[0]] * 100, s=120, marker='o', color='#C026D3', edgecolors='black', linewidths=0.6, zorder=6)
ax[1].scatter(sub['date'].iloc[A[1]], sub['bias'].iloc[A[1]] * 100, s=160, marker='v', color='#d63a3a', edgecolors='black', linewidths=0.6, zorder=6)
ax[1].set_ylabel('偏离年线 %', fontsize=12)
ax[1].grid(alpha=.25)

plt.tight_layout()
out = str(Path(__file__).resolve().parent.parent / 'reports' / '510880_compare_buypoints.png')
plt.savefig(out, dpi=130)
print('已出图:', out)
print('触发次数 A/B/C = %d/%d/%d' % (nA, nB, nC))
print('买入次数 A/B/C = %d/%d/%d' % (len(A[0]), len(B[0]), len(C[0])))
print('期末 A/B/C = %.4f/%.4f/%.4f' % (A[2], B[2], C[2]))
