"""
独立策略模块

包含独立的投资策略:
- ST 摘帽策略（类似舍得酒案例）
- 趋势跟踪策略（待开发）
- 行业轮动策略（待开发）
"""

from .st_backtester import STBacktester, run_st_backtest

__all__ = [
    # ST 摘帽策略
    'STBacktester',
    'run_st_backtest'
]
