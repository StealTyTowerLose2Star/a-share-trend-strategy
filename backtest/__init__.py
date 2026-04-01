"""
回测模块
"""

from .trend_backtester import TrendBacktester, save_backtest_results
from .stats_analyzer import BacktestAnalyzer, analyze_latest_backtest
from .parameter_optimizer import ParameterOptimizer, optimize_trend_params
from .st_backtester import STBacktester, run_st_backtest

__all__ = [
    # 回测器
    'TrendBacktester',
    'save_backtest_results',
    
    # 统计分析
    'BacktestAnalyzer',
    'analyze_latest_backtest',
    
    # 参数优化
    'ParameterOptimizer',
    'optimize_trend_params',
    
    # ST 回测
    'STBacktester',
    'run_st_backtest'
]
