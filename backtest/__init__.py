"""
回测分析模块

专注于回测框架和数据分析:
- 趋势策略回测框架
- 统计分析与报告
- 参数优化
"""

from .trend_backtester import TrendBacktester, save_backtest_results
from .stats_analyzer import BacktestAnalyzer, analyze_latest_backtest
from .parameter_optimizer import ParameterOptimizer, optimize_trend_params

__all__ = [
    # 回测器
    'TrendBacktester',
    'save_backtest_results',
    
    # 统计分析
    'BacktestAnalyzer',
    'analyze_latest_backtest',
    
    # 参数优化
    'ParameterOptimizer',
    'optimize_trend_params'
]
