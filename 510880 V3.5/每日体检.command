#!/bin/bash
cd "$(dirname "$0")"
python3 "tools/daily_check.py"
echo
read -n 1 -s -r -p "按任意键关闭…"
