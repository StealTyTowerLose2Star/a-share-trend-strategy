#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全市场趋势扫描脚本

每日扫描全市场 5000+ 股票，识别趋势形成机会
"""

import sys
import os
import json
from datetime import datetime

# 添加项目根目录到路径
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

from core import (
    get_all_a_share_codes,
    filter_stocks,
    scan_market_trends,
    TrendDetector
)


def main():
    """主函数"""
    print("=" * 60)
    print("🔍 全市场趋势扫描")
    print("=" * 60)
    print(f"扫描时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    # 1. 获取股票列表
    print("1️⃣ 获取全市场股票列表...")
    all_codes = get_all_a_share_codes()
    
    if not all_codes:
        print("❌ 获取股票列表失败，退出")
        return
    
    # 2. 过滤股票
    print("\n2️⃣ 过滤股票（排除 ST 等）...")
    filtered_codes = filter_stocks(all_codes, {
        'exclude_st': True,
        'exclude_kcb': False,  # 不排除科创板，捕捉妖股
        'exclude_cyb': False,  # 不排除创业板
        'min_price': 2,
        'max_price': 100
    })
    
    # 3. 扫描趋势
    print(f"\n3️⃣ 扫描趋势（{len(filtered_codes)} 只股票）...")
    trends = scan_market_trends(filtered_codes, min_score=60)
    
    # 4. 保存结果
    state_dir = os.path.join(base_dir, 'state')
    os.makedirs(state_dir, exist_ok=True)
    
    result_file = os.path.join(
        state_dir,
        f"trend_pool_{datetime.now().strftime('%Y%m%d')}.json"
    )
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_scanned': len(filtered_codes),
            'trends_found': len(trends),
            'trends': trends[:50]  # 保存前 50 个
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 结果已保存到：{result_file}")
    
    # 5. 输出摘要
    print("\n" + "=" * 60)
    print("📊 扫描结果摘要")
    print("=" * 60)
    
    if trends:
        print(f"\n发现 {len(trends)} 只趋势股\n")
        
        print("【强趋势 TOP10】")
        for i, trend in enumerate(trends[:10], 1):
            print(f"{i}. {trend['code']} {trend.get('name', '')}")
            print(f"   价格：{trend['price']}  评分：{trend['total_score']}")
            print(f"   强度：{trend['strength']}")
            print()
    else:
        print("\n⚠️ 未发现符合条件的趋势股")
        print("   可能是市场震荡或数据获取失败")


if __name__ == '__main__':
    main()
