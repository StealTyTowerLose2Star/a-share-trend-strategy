#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全市场股票列表获取

获取 A 股全市场股票代码，用于趋势扫描
"""

import akshare as ak
import pandas as pd
from datetime import datetime


def get_all_a_share_codes():
    """
    获取全市场 A 股代码列表
    
    Returns:
        list: 股票代码列表
    """
    try:
        print("获取全市场 A 股列表...")
        
        # 获取 A 股列表
        df = ak.stock_info_a_code_name()
        
        if df is None or len(df) == 0:
            print("❌ 获取 A 股列表失败")
            return []
        
        # 提取代码
        codes = df['code'].tolist()
        
        print(f"✅ 获取到 {len(codes)} 只 A 股")
        
        return codes
        
    except Exception as e:
        print(f"❌ 获取代码列表失败：{e}")
        return []


def filter_stocks(codes: list, filters: dict = None) -> list:
    """
    过滤股票（排除 ST、科创板等）
    
    Args:
        codes: 股票代码列表
        filters: 过滤条件
        
    Returns:
        list: 过滤后的代码列表
    """
    if filters is None:
        filters = {
            'exclude_st': True,      # 排除 ST
            'exclude_kcb': False,    # 排除科创板（可选）
            'exclude_cyb': False,    # 排除创业板（可选）
            'min_price': 2,          # 最低价格
            'max_price': 100         # 最高价格（排除高价股）
        }
    
    filtered = []
    
    for code in codes:
        # 排除 ST
        if filters.get('exclude_st', True):
            if 'ST' in code or '*ST' in code:
                continue
        
        # 排除科创板
        if filters.get('exclude_kcb', False):
            if code.startswith('688'):
                continue
        
        # 排除创业板
        if filters.get('exclude_cyb', False):
            if code.startswith('300'):
                continue
        
        filtered.append(code)
    
    print(f"过滤后剩余 {len(filtered)} 只股票")
    
    return filtered


def save_stock_list(codes: list, filepath: str = None):
    """
    保存股票列表
    
    Args:
        codes: 股票代码列表
        filepath: 保存路径
    """
    if filepath is None:
        filepath = f"data/stock_list_{datetime.now().strftime('%Y%m%d')}.txt"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        for code in codes:
            f.write(f"{code}\n")
    
    print(f"✅ 股票列表已保存到：{filepath}")


if __name__ == '__main__':
    # 获取全市场股票
    codes = get_all_a_share_codes()
    
    if codes:
        # 过滤
        filtered = filter_stocks(codes)
        
        # 保存
        save_stock_list(filtered)
        
        print(f"\n准备扫描 {len(filtered)} 只股票")
