#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场状态报告生成脚本

每日运行，输出大盘市场状态 + 仓位建议。
支持飞书推送和文件保存。

用法:
    python3 scripts/market_state_report.py                    # 终端输出
    python3 scripts/market_state_report.py --save             # 保存到 state/
    python3 scripts/market_state_report.py --push             # 推送飞书
"""

import sys
import os
import json
from datetime import datetime

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.market_state import assess_market, format_report


def save_report(result: dict):
    """保存报告到 state/"""
    os.makedirs("state", exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    filepath = f"state/market_state_{date_str}.json"

    # 保存详细数据
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    print(f"✅ 报告已保存: {filepath}")
    return filepath


def push_to_feishu(result: dict):
    """推送市场状态到飞书"""
    report_text = format_report(result)
    try:
        from core.feishu_sender import send_feishu_message
        send_feishu_message(
            title=f"📊 市场状态报告 | {result['data_date']}",
            content=report_text,
            msg_type="日报"
        )
        print("✅ 已推送飞书")
    except ImportError:
        print("⚠️ 未找到 feishu_sender 模块，跳过推送")
    except Exception as e:
        print(f"⚠️ 飞书推送失败: {e}")


def main():
    # 参数
    do_save = "--save" in sys.argv
    do_push = "--push" in sys.argv

    print("📊 A 股市场状态分析...")
    print("=" * 50)

    result = assess_market()
    print(format_report(result))

    if do_save:
        save_report(result)

    if do_push:
        push_to_feishu(result)


if __name__ == "__main__":
    main()
