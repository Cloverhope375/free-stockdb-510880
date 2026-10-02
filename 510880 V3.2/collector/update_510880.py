"""
510880 数据采集模块（不依赖 akshare；用新浪+腾讯公开接口）
输出：data/raw/510880.csv + data/market.db (表 etf_daily)
字段：date, open, high, low, close, volume

【口径】close 为【不复权】收盘价 —— 即交易所真实成交价，与你交易软件显示的年线口径一致。

⚠️⚠️ 重要数据陷阱（务必记住）⚠️⚠️
  腾讯的【前复权 qfq】接口对 510880 返回的数据是【错的】：
  其日波动约为真实盘面的 1.8~2 倍（例：2015-08-24 真实 -10.00%，qfq -17.93%）。
  用 qfq 回测会得到虚高约 2 倍的收益（2018 起 19.6% vs 真实的 8.25%）。
  → 交叉验证一律用【后复权 hfq】或【新浪不复权】；永久禁用腾讯 qfq。
"""
from pathlib import Path
import sqlite3, json, urllib.request, time, datetime
import math

DATA = Path(__file__).resolve().parent.parent / "data"
RAW = DATA / "raw"
RAW.mkdir(parents=True, exist_ok=True)


def _get(url, ref='https://gu.qq.com/', dec='utf-8', t=25, r=5):
    last = None
    for _ in range(r):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': ref})
            return urllib.request.urlopen(req, timeout=t).read().decode(dec, 'ignore')
        except Exception as e:
            last = e; time.sleep(1.5)
    raise last


def fetch_sina(symbol='sh510880', datalen=5000):
    """新浪历史K线（不复权，含开高低收）—— 入库口径"""
    u = ('https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/'
         'CN_MarketData.getKLineData?symbol=%s&scale=240&ma=no&datalen=%d' % (symbol, datalen))
    arr = json.loads(_get(u, ref='https://finance.sina.com.cn/'))
    rows = []
    for x in arr:
        rows.append({
            'date': x['day'],
            'open': float(x['open']),
            'high': float(x['high']),
            'low': float(x['low']),
            'close': float(x['close']),
            'volume': float(x['volume']),
        })
    return rows


def fetch_tencent(symbol='sh510880', fq='hfq', start='2013-01-01', end=None):
    """腾讯日线。fq: 'hfq'=后复权(默认，用于验证)；'qfq'=前复权【对510880不可信，禁用】"""
    if fq == 'qfq':
        raise ValueError("腾讯 qfq 对 510880 数据有误，请改用 'hfq'")
    end = end or datetime.date.today().isoformat()
    rows = {}; e = end; g = 0
    while g < 60:
        g += 1; kl = []
        for host in ['web.ifzq.gtimg.cn', 'ifzq.gtimg.cn']:
            try:
                u = ('https://%s/appstock/app/fqkline/get?param=%s,day,%s,%s,640,%s'
                     % (host, symbol, start, e, fq))
                j = json.loads(_get(u))
                x = j.get('data', {}).get(symbol) or {}
                kl = x.get(fq + 'day') or x.get('day') or []
                if kl: break
            except Exception:
                time.sleep(0.8)
        if not kl: break
        for r in kl:
            rows[r[0]] = float(r[2])   # close
        f = kl[0][0]
        if f <= start: break
        e = (datetime.date.fromisoformat(f) - datetime.timedelta(days=1)).isoformat()
    return {k: rows[k] for k in sorted(rows)}


def save(rows):
    import csv
    csv_path = RAW / "510880.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['date', 'open', 'high', 'low', 'close', 'volume'])
        w.writeheader()
        for r in rows: w.writerow(r)
    conn = sqlite3.connect(DATA / "market.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS etf_daily(
        date TEXT PRIMARY KEY, open REAL, high REAL, low REAL, close REAL, volume REAL)""")
    conn.execute("DELETE FROM etf_daily")
    conn.executemany("INSERT INTO etf_daily(date,open,high,low,close,volume) VALUES(?,?,?,?,?,?)",
                     [(r['date'], r['open'], r['high'], r['low'], r['close'], r['volume']) for r in rows])
    conn.commit(); conn.close()
    print("updated: %s  (%d 行, %s ~ %s)" % (csv_path, len(rows), rows[0]['date'], rows[-1]['date']))


def verify_values(rows_raw, alt, label='腾讯hfq', sample=None):
    """值的交叉验证：比对【日收益】（默认全历史）。
    注意：不复权在除息日会跳降、而 hfq 不会，故除息日偏差天然偏大——
    因此以【中位数偏差】判好坏，并把大偏差日列为"疑似除息日"。
    （坏数据如腾讯qfq 会因波动翻倍而让中位数偏差放大到 0.3% 以上）"""
    raw = {r['date']: r['close'] for r in rows_raw}
    common = sorted(set(raw) & set(alt))
    if sample:
        common = common[-sample:]
    if len(common) < 10:
        print("交叉验证: 共同交易日不足"); return
    devs = []
    for i in range(1, len(common)):
        d0, d1 = common[i - 1], common[i]
        devs.append((abs((raw[d1] / raw[d0] - 1) - (alt[d1] / alt[d0] - 1)), d1))
    devs.sort()
    vals = [x[0] for x in devs]
    med = vals[len(vals) // 2]
    big = [d for v, d in devs if v > 0.01]
    big_ratio = len(big) / max(1, len(devs))
    # 正常复权数据：中位偏差很小(除息日才大)；坏数据(qfq)：中位偏差大 且 异常日占比高
    if med < 0.0025 and big_ratio < 0.08:
        flag = "✅ 一致"
    elif med < 0.008 and big_ratio < 0.20:
        flag = "⚠️ 偏差偏大，需人工复核"
    else:
        flag = "❌ 数据不一致（疑为坏数据，勿用于回测）"
    print("交叉验证(日收益, 共%d日, 对比%s): %s 中位偏差%.3f%%，>1%%异常日%d天(%.1f%%)"
          % (len(common), label, flag, med * 100, len(big), big_ratio * 100))
    if "❌" in flag:
        print("   ⚠️ 该数据源很可能有问题（正常的复权源异常日应<8%），请勿用于回测！")


if __name__ == "__main__":
    raw = fetch_sina()
    save(raw)
    try:
        alt = fetch_tencent('sh510880', fq='hfq', start=raw[0]['date'])
        verify_values(raw, alt, '腾讯hfq')
    except Exception as e:
        print("（腾讯交叉验证跳过：%s）" % e)
