# 如何把 V3 推回你的 GitHub 仓库

> 说明：我运行在隔离沙箱里，**没有你的 GitHub 账号凭据，无法直接替你 push**。
> 所以最后一步"上传"要你在自己电脑上操作，跟着下面做即可，全程约 3 分钟。

---

## 方案 A：命令行（推荐，一次配好终身受用）

### 0. 准备
- 电脑装好 Git（Windows 装 Git for Windows，Mac 自带）
- 在 GitHub 上建好 Personal Access Token（见文末"没权限怎么推"）

### 1. 把仓库拉到本地
```bash
git clone https://github.com/Cloverhope375/free-stockdb-510880.git
cd free-stockdb-510880
```

### 2. 用 V3 覆盖旧文件
把我给你的 `free-stockdb-510880-V3.zip` 解压，把里面**所有文件**复制到这个目录，覆盖同名文件。
最终目录应该长这样：
```
free-stockdb-510880/
├── config.json          ← 含 start_date（可切换起算年份）
├── requirements.txt     ← 已锁版本、已去掉用不了的 akshare
├── README.md
├── collector/
│   └── update_510880.py
├── strategy/
│   ├── indicators.py
│   └── ma250_rsi_v7.py
├── tools/
│   └── plot.py          ← 新增：一键出图
├── data/
│   └── market.db
└── reports/             ← 新增：回测后自动生成 CSV + 图
```

### 3. 提交并推送
```bash
git add -A
git commit -m "V3: 修复买入方向/复利/RSI，新增 start_date 起算点与一键出图"
git push
```
提示输入用户名和密码时，**密码处粘贴你的 Personal Access Token**（不是登录密码）。

---

## 方案 B：图形界面（不想碰命令行）

1. 装 **GitHub Desktop**（github.com/apps/desktop），登录你的账号。
2. `File → Clone repository →` 选 `Cloverhope375/free-stockdb-510880`。
3. 把 V3 文件复制进本地目录（同上），软件会自动识别改动。
4. 左下角填一句说明 → **Commit to main** → 右上角 **Push origin**。完事。

---

## 没权限怎么推？（GitHub 已停用密码推送）

生成一个 Token 当作密码用：
1. GitHub 右上角头像 → **Settings** → 左侧最下 **Developer settings**
2. **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**
3. 勾选 **repo** 权限，有效期选 90 天或自定义 → 生成
4. **复制这串 token**（只显示一次！），push 时当密码粘贴

---

## 以后每次更新，只要重复第 3 步
```bash
git add -A && git commit -m "更新说明" && git push
```

---

## 在本地跑起来（验证）
```bash
pip install -r requirements.txt
python collector/update_510880.py     # 更新数据
python strategy/ma250_rsi_v7.py        # 跑回测 → reports/
python tools/plot.py                   # 出图 → reports/510880_chart.png
```
改 `config.json` 里的 `"start_date"` 就能切换起算年份（2007 / 2014 / 2018）。
