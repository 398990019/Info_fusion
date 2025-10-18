from __future__ import annotations

import os
import sys

# 将项目根目录加入模块搜索路径
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from main import run_data_aggregation

if __name__ == "__main__":
    try:
        data = run_data_aggregation()
        count = len(data)
        sample = data[0].get("title") if data else "N/A"
        print("AGG_COUNT", count)
        print("AGG_SAMPLE_TITLE", sample)
    except Exception as e:
        print("AGG_ERR", e)
