# free-stockdb-510880 V2

升级内容：
- 数据采集模块
- SQLite数据仓库
- MA250 + RSI V7策略框架

运行：

pip install -r requirements.txt

python collector/update_510880.py

python strategy/ma250_rsi_v7.py

结果：

reports/trades.csv
