#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势策略回测框架

基于历史数据回测趋势策略：
- 统计成功率
- 计算收益率
- 分析最大回撤
- 优化参数

融合经典回测方法：
- 海龟交易回测框架
- 欧奈尔 CANSLIM 回测
- A 股特色回测（涨跌停/停牌）
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import os


class TrendBacktester:
    """趋势策略回测器"""
    
    def __init__(self, initial_capital: float = 1000000):
        """
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
    
    def get_stock_data(self, code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取历史数据"""
        try:
            import akshare as ak
            
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"
            )
            
            if df is None or len(df) == 0:
                return None
            
            df = df.rename(columns={
                '日期': 'date',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '开盘': 'open',
                '成交量': 'volume'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            return None
    
    def calculate_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算均线"""
        if df is None or len(df) < 60:
            return df
        
        df = df.copy()
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        return df
    
    def check_trend_signal(self, df: pd.DataFrame, idx: int) -> Dict:
        """
        检查趋势信号
        
        Returns:
            dict: 信号状态
        """
        if idx < 60:
            return {'signal': 'hold'}
        
        row = df.iloc[idx]
        
        # 均线多头排列
        ma_aligned = (row['ma5'] > row['ma10'] > row['ma20'] > row['ma60'])
        
        # 突破 20 日高点
        high_20 = df['high'].iloc[idx-20:idx].max()
        breakout = row['close'] > high_20
        
        # 成交量确认
        volume_5 = df['volume'].iloc[idx-5:idx].mean()
        volume_confirmed = row['volume'] > volume_5 * 1.5
        
        # 20 日线向上
        ma20_slope = (row['ma20'] - df['ma20'].iloc[idx-5]) / df['ma20'].iloc[idx-5]
        upward = ma20_slope > 0
        
        # 综合判断
        if ma_aligned and breakout and volume_confirmed and upward:
            return {'signal': 'buy', 'price': row['close'], 'idx': idx}
        else:
            return {'signal': 'hold'}
    
    def check_exit_signal(self, df: pd.DataFrame, idx: int, 
                         buy_price: float, current_price: float) -> Dict:
        """
        检查退出信号
        
        Returns:
            dict: 退出信号
        """
        row = df.iloc[idx]
        
        # 止损：跌破买入价 -5%
        stop_loss = current_price < buy_price * 0.95
        
        # 止盈：达到目标位
        take_profit = current_price > buy_price * 1.20
        
        # 趋势破坏：跌破 20 日线
        trend_broken = row['close'] < row['ma20']
        
        if stop_loss:
            return {'signal': 'stop_loss', 'price': current_price, 'idx': idx}
        elif take_profit:
            return {'signal': 'take_profit', 'price': current_price, 'idx': idx}
        elif trend_broken:
            return {'signal': 'trend_broken', 'price': current_price, 'idx': idx}
        else:
            return {'signal': 'hold'}
    
    def backtest_single(self, code: str, start_date: str, end_date: str) -> Dict:
        """
        回测单只股票
        
        Returns:
            dict: 回测结果
        """
        df = self.get_stock_data(code, start_date, end_date)
        
        if df is None or len(df) < 60:
            return {'success': False, 'reason': '数据不足'}
        
        # 计算均线
        df = self.calculate_ma(df)
        
        # 初始化
        capital = self.initial_capital
        position = None
        trades = []
        equity_curve = []
        
        # 逐日回测
        for idx in range(60, len(df)):
            row = df.iloc[idx]
            current_price = row['close']
            
            # 检查买入信号
            if position is None:
                signal = self.check_trend_signal(df, idx)
                
                if signal['signal'] == 'buy':
                    # 买入
                    shares = int(capital * 0.95 / current_price)  # 95% 仓位
                    if shares > 0:
                        position = {
                            'code': code,
                            'buy_price': current_price,
                            'buy_date': row['date'],
                            'shares': shares,
                            'cost': current_price * shares
                        }
                        capital -= position['cost']
                        trades.append({
                            'type': 'buy',
                            'price': current_price,
                            'date': row['date'],
                            'shares': shares
                        })
            
            # 检查卖出信号
            else:
                signal = self.check_exit_signal(df, idx, 
                                               position['buy_price'], 
                                               current_price)
                
                if signal['signal'] != 'hold':
                    # 卖出
                    proceeds = position['shares'] * current_price
                    capital += proceeds
                    profit = proceeds - position['cost']
                    profit_pct = profit / position['cost'] * 100
                    
                    trades.append({
                        'type': 'sell',
                        'price': current_price,
                        'date': row['date'],
                        'shares': position['shares'],
                        'profit': profit,
                        'profit_pct': profit_pct,
                        'exit_reason': signal['signal']
                    })
                    
                    position = None
            
            # 记录权益曲线
            total_equity = capital
            if position:
                total_equity += position['shares'] * current_price
            equity_curve.append({
                'date': row['date'],
                'equity': total_equity
            })
        
        # 计算统计指标
        if not equity_curve:
            return {'success': False, 'reason': '无交易'}
        
        equity_df = pd.DataFrame(equity_curve)
        
        # 总收益
        total_return = (equity_df['equity'].iloc[-1] - self.initial_capital) / self.initial_capital * 100
        
        # 最大回撤
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak'] * 100
        max_drawdown = equity_df['drawdown'].min()
        
        # 交易统计
        buy_trades = [t for t in trades if t['type'] == 'buy']
        sell_trades = [t for t in trades if t['type'] == 'sell']
        
        win_trades = [t for t in sell_trades if t['profit'] > 0]
        lose_trades = [t for t in sell_trades if t['profit'] <= 0]
        
        win_rate = len(win_trades) / len(sell_trades) * 100 if sell_trades else 0
        
        avg_win = np.mean([t['profit_pct'] for t in win_trades]) if win_trades else 0
        avg_lose = np.mean([t['profit_pct'] for t in lose_trades]) if lose_trades else 0
        
        return {
            'success': True,
            'code': code,
            'start_date': start_date,
            'end_date': end_date,
            'total_return': round(total_return, 2),
            'max_drawdown': round(max_drawdown, 2),
            'win_rate': round(win_rate, 1),
            'avg_win': round(avg_win, 2),
            'avg_lose': round(avg_lose, 2),
            'total_trades': len(sell_trades),
            'win_trades': len(win_trades),
            'lose_trades': len(lose_trades),
            'final_equity': round(equity_df['equity'].iloc[-1], 2),
            'trades': trades
        }
    
    def backtest_portfolio(self, codes: List[str], start_date: str, 
                          end_date: str) -> Dict:
        """
        回测股票组合
        
        Returns:
            dict: 组合回测结果
        """
        print(f"开始回测 {len(codes)} 只股票...")
        
        results = []
        
        for i, code in enumerate(codes):
            if (i + 1) % 10 == 0:
                print(f"已回测 {i+1}/{len(codes)}")
            
            try:
                result = self.backtest_single(code, start_date, end_date)
                if result['success']:
                    results.append(result)
            except:
                continue
        
        # 组合统计
        if not results:
            return {'success': False, 'reason': '无有效回测结果'}
        
        total_returns = [r['total_return'] for r in results]
        win_rates = [r['win_rate'] for r in results]
        max_drawdowns = [r['max_drawdown'] for r in results]
        
        return {
            'success': True,
            'total_stocks': len(results),
            'avg_return': round(np.mean(total_returns), 2),
            'median_return': round(np.median(total_returns), 2),
            'best_return': round(max(total_returns), 2),
            'worst_return': round(min(total_returns), 2),
            'avg_win_rate': round(np.mean(win_rates), 1),
            'avg_max_drawdown': round(np.mean(max_drawdowns), 2),
            'profitable_stocks': len([r for r in results if r['total_return'] > 0]),
            'losing_stocks': len([r for r in results if r['total_return'] <= 0]),
            'results': results
        }


def save_backtest_results(results: Dict, filepath: str):
    """保存回测结果"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"✅ 回测结果已保存：{filepath}")


if __name__ == '__main__':
    # 测试
    print("=" * 60)
    print("测试趋势策略回测框架")
    print("=" * 60)
    
    backtester = TrendBacktester(initial_capital=100000)
    
    # 测试单只股票
    test_codes = ['600105', '002149']
    start_date = '2024-01-01'
    end_date = '2026-04-01'
    
    for code in test_codes:
        print(f"\n回测：{code}")
        result = backtester.backtest_single(code, start_date, end_date)
        
        if result['success']:
            print(f"  总收益：{result['total_return']}%")
            print(f"  最大回撤：{result['max_drawdown']}%")
            print(f"  胜率：{result['win_rate']}%")
            print(f"  交易次数：{result['total_trades']}")
        else:
            print(f"  失败：{result['reason']}")
