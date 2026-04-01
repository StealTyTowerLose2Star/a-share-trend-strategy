#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测结果统计分析

对回测结果进行深度统计分析：
- 收益分布
- 胜率分析
- 风险指标
- 高胜率模式提炼
- 参数敏感性分析
"""

import json
import os
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import sys

# 添加项目根目录到路径
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)


class BacktestAnalyzer:
    """回测结果分析师"""
    
    def __init__(self, results_file: str):
        """
        Args:
            results_file: 回测结果 JSON 文件路径
        """
        self.results_file = results_file
        self.data = self._load_results()
        self.df = None
        
        if self.data and 'results' in self.data:
            self.df = pd.DataFrame(self.data['results'])
    
    def _load_results(self) -> Optional[Dict]:
        """加载回测结果"""
        try:
            with open(self.results_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载结果失败：{e}")
            return None
    
    def basic_statistics(self) -> Dict:
        """基础统计"""
        if self.df is None or self.df.empty:
            return {}
        
        return {
            'total_stocks': len(self.df),
            'avg_return': self.df['total_return'].mean(),
            'median_return': self.df['total_return'].median(),
            'std_return': self.df['total_return'].std(),
            'best_return': self.df['total_return'].max(),
            'worst_return': self.df['total_return'].min(),
            'profitable_count': len(self.df[self.df['total_return'] > 0]),
            'losing_count': len(self.df[self.df['total_return'] <= 0]),
            'profitable_ratio': len(self.df[self.df['total_return'] > 0]) / len(self.df) * 100
        }
    
    def win_rate_analysis(self) -> Dict:
        """胜率分析"""
        if self.df is None or self.df.empty:
            return {}
        
        # 按胜率分组
        high_win = self.df[self.df['win_rate'] >= 60]
        medium_win = self.df[(self.df['win_rate'] >= 50) & (self.df['win_rate'] < 60)]
        low_win = self.df[self.df['win_rate'] < 50]
        
        return {
            'overall_avg_win_rate': self.df['win_rate'].mean(),
            'high_win_rate_stocks': len(high_win),
            'high_win_rate_avg_return': high_win['total_return'].mean() if len(high_win) > 0 else 0,
            'medium_win_rate_stocks': len(medium_win),
            'medium_win_rate_avg_return': medium_win['total_return'].mean() if len(medium_win) > 0 else 0,
            'low_win_rate_stocks': len(low_win),
            'low_win_rate_avg_return': low_win['total_return'].mean() if len(low_win) > 0 else 0
        }
    
    def drawdown_analysis(self) -> Dict:
        """回撤分析"""
        if self.df is None or self.df.empty:
            return {}
        
        # 回撤分级
        low_dd = self.df[self.df['max_drawdown'] > -10]
        medium_dd = self.df[(self.df['max_drawdown'] <= -10) & (self.df['max_drawdown'] > -20)]
        high_dd = self.df[self.df['max_drawdown'] <= -20]
        
        return {
            'avg_max_drawdown': self.df['max_drawdown'].mean(),
            'low_drawdown_stocks': len(low_dd),
            'low_drawdown_avg_return': low_dd['total_return'].mean() if len(low_dd) > 0 else 0,
            'medium_drawdown_stocks': len(medium_dd),
            'medium_drawdown_avg_return': medium_dd['total_return'].mean() if len(medium_dd) > 0 else 0,
            'high_drawdown_stocks': len(high_dd),
            'high_drawdown_avg_return': high_dd['total_return'].mean() if len(high_dd) > 0 else 0
        }
    
    def extract_high_win_patterns(self) -> List[Dict]:
        """
        提炼高胜率模式
        
        Returns:
            list: 高胜率模式列表
        """
        if self.df is None or self.df.empty:
            return []
        
        patterns = []
        
        # 筛选高胜率股票（胜率>=60%）
        high_win_stocks = self.df[self.df['win_rate'] >= 60].copy()
        
        if len(high_win_stocks) == 0:
            return patterns
        
        # 分析共同特征
        pattern = {
            'name': '高胜率模式',
            'sample_size': len(high_win_stocks),
            'win_rate': high_win_stocks['win_rate'].mean(),
            'avg_return': high_win_stocks['total_return'].mean(),
            'avg_drawdown': high_win_stocks['max_drawdown'].mean(),
            'characteristics': {}
        }
        
        # 统计特征分布
        # 这里简化处理，实际应该分析交易记录中的特征
        pattern['characteristics']['avg_trades'] = high_win_stocks['total_trades'].mean() if 'total_trades' in high_win_stocks.columns else 0
        pattern['characteristics']['avg_win'] = high_win_stocks['avg_win'].mean() if 'avg_win' in high_win_stocks.columns else 0
        pattern['characteristics']['avg_lose'] = high_win_stocks['avg_lose'].mean() if 'avg_lose' in high_win_stocks.columns else 0
        
        patterns.append(pattern)
        
        return patterns
    
    def generate_report(self, output_file: str = None):
        """
        生成分析报告
        
        Args:
            output_file: 输出文件路径
        """
        report = []
        report.append("=" * 60)
        report.append("📊 回测结果统计分析报告")
        report.append("=" * 60)
        report.append("")
        
        # 基础统计
        report.append("【基础统计】")
        basic = self.basic_statistics()
        if basic:
            report.append(f"  回测股票数：{basic['total_stocks']}")
            report.append(f"  平均收益：{basic['avg_return']:.2f}%")
            report.append(f"  中位收益：{basic['median_return']:.2f}%")
            report.append(f"  收益标准差：{basic['std_return']:.2f}%")
            report.append(f"  最佳收益：{basic['best_return']:.2f}%")
            report.append(f"  最差收益：{basic['worst_return']:.2f}%")
            report.append(f"  盈利股票：{basic['profitable_count']} ({basic['profitable_ratio']:.1f}%)")
            report.append(f"  亏损股票：{basic['losing_count']}")
        report.append("")
        
        # 胜率分析
        report.append("【胜率分析】")
        win_analysis = self.win_rate_analysis()
        if win_analysis:
            report.append(f"  平均胜率：{win_analysis['overall_avg_win_rate']:.1f}%")
            report.append(f"  高胜率股票（>=60%）: {win_analysis['high_win_rate_stocks']} 只，平均收益 {win_analysis['high_win_rate_avg_return']:.2f}%")
            report.append(f"  中胜率股票（50-60%）: {win_analysis['medium_win_rate_stocks']} 只，平均收益 {win_analysis['medium_win_rate_avg_return']:.2f}%")
            report.append(f"  低胜率股票（<50%）: {win_analysis['low_win_rate_stocks']} 只，平均收益 {win_analysis['low_win_rate_avg_return']:.2f}%")
        report.append("")
        
        # 回撤分析
        report.append("【回撤分析】")
        dd_analysis = self.drawdown_analysis()
        if dd_analysis:
            report.append(f"  平均最大回撤：{dd_analysis['avg_max_drawdown']:.2f}%")
            report.append(f"  低回撤股票（>-10%）: {dd_analysis['low_drawdown_stocks']} 只，平均收益 {dd_analysis['low_drawdown_avg_return']:.2f}%")
            report.append(f"  中回撤股票（-10% 至 -20%）: {dd_analysis['medium_drawdown_stocks']} 只，平均收益 {dd_analysis['medium_drawdown_avg_return']:.2f}%")
            report.append(f"  高回撤股票（<=-20%）: {dd_analysis['high_drawdown_stocks']} 只，平均收益 {dd_analysis['high_drawdown_avg_return']:.2f}%")
        report.append("")
        
        # 高胜率模式
        report.append("【高胜率模式提炼】")
        patterns = self.extract_high_win_patterns()
        if patterns:
            for i, pattern in enumerate(patterns, 1):
                report.append(f"  模式{i}: {pattern['name']}")
                report.append(f"    样本数：{pattern['sample_size']}")
                report.append(f"    胜率：{pattern['win_rate']:.1f}%")
                report.append(f"    平均收益：{pattern['avg_return']:.2f}%")
                report.append(f"    平均回撤：{pattern['avg_drawdown']:.2f}%")
        report.append("")
        
        # 最佳/最差股票
        report.append("【最佳收益 TOP10】")
        if self.df is not None and not self.df.empty:
            top10 = self.df.nlargest(10, 'total_return')
            for i, (_, row) in enumerate(top10.iterrows(), 1):
                report.append(f"  {i}. {row.get('code', 'N/A')}: {row['total_return']:.2f}%")
        
        report.append("")
        report.append("【最差收益 TOP10】")
        if self.df is not None and not self.df.empty:
            bottom10 = self.df.nsmallest(10, 'total_return')
            for i, (_, row) in enumerate(bottom10.iterrows(), 1):
                report.append(f"  {i}. {row.get('code', 'N/A')}: {row['total_return']:.2f}%")
        
        report_text = "\n".join(report)
        
        # 保存报告
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"✅ 报告已保存：{output_file}")
        
        return report_text


def analyze_latest_backtest():
    """分析最新回测结果"""
    # 查找最新结果文件
    results_dir = os.path.join(base_dir, 'backtest', 'results', 'daily')
    
    if not os.path.exists(results_dir):
        print("❌ 回测结果目录不存在")
        return
    
    # 获取最新文件
    files = sorted([f for f in os.listdir(results_dir) if f.endswith('.json')])
    
    if not files:
        print("❌ 未找到回测结果文件")
        return
    
    latest_file = os.path.join(results_dir, files[-1])
    print(f"分析最新回测结果：{latest_file}")
    
    # 创建分析师
    analyzer = BacktestAnalyzer(latest_file)
    
    # 生成报告
    output_file = os.path.join(
        base_dir, 'backtest', 'reports',
        f"analysis_{datetime.now().strftime('%Y%m%d')}.md"
    )
    
    report = analyzer.generate_report(output_file)
    print("\n" + report)
    
    return analyzer


if __name__ == '__main__':
    analyze_latest_backtest()
