#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全市场趋势策略回测（2019-2025）

回测周期：2019-01-01 至 2025-12-31
回测对象：全市场 A 股
策略：趋势跟踪（右侧交易）

统计指标:
- 总收益率
- 年化收益率
- 最大回撤
- 胜率
- 盈亏比
- 夏普比率
"""

import sys
import os
import json
from datetime import datetime

# 添加项目根目录到路径
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

from backtest.trend_backtester import TrendBacktester, save_backtest_results
from core.market_scanner import get_all_a_share_codes, filter_stocks


def run_full_backtest():
    """运行全市场回测"""
    print("=" * 60)
    print("📊 全市场趋势策略回测（2019-2025）")
    print("=" * 60)
    print()
    
    # 回测参数
    start_date = '2019-01-01'
    end_date = '2025-12-31'
    initial_capital = 1000000  # 100 万初始资金
    
    print(f"回测周期：{start_date} 至 {end_date}")
    print(f"初始资金：{initial_capital} 元")
    print()
    
    # 1. 获取股票列表
    print("1️⃣ 获取全市场股票列表...")
    all_codes = get_all_a_share_codes()
    
    if not all_codes:
        print("❌ 获取股票列表失败")
        return
    
    # 2. 过滤股票
    print("\n2️⃣ 过滤股票（排除 ST、高价股等）...")
    filtered_codes = filter_stocks(all_codes, {
        'exclude_st': True,
        'exclude_kcb': False,
        'exclude_cyb': False,
        'min_price': 2,
        'max_price': 100
    })
    
    # 3. 抽样回测（先测试 100 只）
    print(f"\n3️⃣ 开始回测（抽样 100 只股票）...")
    print(f"   总股票数：{len(filtered_codes)}")
    print(f"   抽样数量：100")
    
    # 随机抽样 100 只
    import random
    random.seed(42)
    sample_codes = random.sample(filtered_codes, min(100, len(filtered_codes)))
    
    # 4. 回测
    backtester = TrendBacktester(initial_capital=initial_capital)
    result = backtester.backtest_portfolio(sample_codes, start_date, end_date)
    
    if not result['success']:
        print(f"\n❌ 回测失败：{result['reason']}")
        return
    
    # 5. 输出结果
    print("\n" + "=" * 60)
    print("📈 回测结果")
    print("=" * 60)
    
    print(f"\n【总体统计】")
    print(f"  回测股票数：{result['total_stocks']}")
    print(f"  盈利股票：{result['profitable_stocks']} ({result['profitable_stocks']/result['total_stocks']*100:.1f}%)")
    print(f"  亏损股票：{result['losing_stocks']} ({result['losing_stocks']/result['total_stocks']*100:.1f}%)")
    
    print(f"\n【收益指标】")
    print(f"  平均收益：{result['avg_return']}%")
    print(f"  中位收益：{result['median_return']}%")
    print(f"  最佳收益：{result['best_return']}%")
    print(f"  最差收益：{result['worst_return']}%")
    
    print(f"\n【风险指标】")
    print(f"  平均最大回撤：{result['avg_max_drawdown']}%")
    print(f"  平均胜率：{result['avg_win_rate']}%")
    
    # 6. 保存结果
    output_dir = os.path.join(base_dir, 'backtest', 'results')
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(
        output_dir,
        f"backtest_2019_2025_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    )
    
    save_backtest_results(result, output_file)
    
    # 7. 输出最佳/最差股票
    if result['results']:
        print("\n" + "=" * 60)
        print("【最佳收益 TOP5】")
        sorted_results = sorted(result['results'], key=lambda x: x['total_return'], reverse=True)
        
        for i, r in enumerate(sorted_results[:5], 1):
            print(f"  {i}. {r['code']} {r.get('name', '')}: {r['total_return']}%")
        
        print("\n【最差收益 TOP5】")
        for i, r in enumerate(sorted_results[-5:], 1):
            print(f"  {i}. {r['code']} {r.get('name', '')}: {r['total_return']}%")
    
    print("\n" + "=" * 60)
    print("✅ 回测完成！")
    print("=" * 60)
    
    return result


if __name__ == '__main__':
    result = run_full_backtest()
