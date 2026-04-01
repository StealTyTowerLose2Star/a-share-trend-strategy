"""
A 股趋势策略系统 - 核心模块

中期趋势跟踪，右侧交易，全市场扫描
"""

from .trend_detector import TrendDetector, scan_market_trends
from .market_scanner import get_all_a_share_codes, filter_stocks, save_stock_list

__all__ = [
    # 趋势识别
    'TrendDetector',
    'scan_market_trends',
    
    # 市场扫描
    'get_all_a_share_codes',
    'filter_stocks',
    'save_stock_list'
]
