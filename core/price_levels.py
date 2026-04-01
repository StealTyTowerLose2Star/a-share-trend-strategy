#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精确价位计算模块

基于技术分析和历史统计，计算：
- 精确买入区间（到分）
- 精确止损位（到分）
- 精确目标位（到分）

融合经典理论：
- 海龟交易：ATR 动态止损
- 欧奈尔：平台突破买点
- A 股游资：整数关口/前高/均线
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


class PriceLevelCalculator:
    """精确价位计算器"""
    
    def __init__(self):
        pass
    
    def get_price_data(self, code: str, days: int = 120) -> Optional[pd.DataFrame]:
        """获取价格数据"""
        try:
            import akshare as ak
            
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
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
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        计算 ATR（平均真实波幅）
        
        用于动态止损位计算
        """
        if df is None or len(df) < period + 1:
            return 0
        
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        return atr
    
    def calculate_support_levels(self, df: pd.DataFrame, current_price: float) -> List[float]:
        """
        计算支撑位（从强到弱）
        
        方法：
        1. 前期低点
        2. 均线位置
        3. 整数关口
        4. 跳空缺口
        """
        supports = []
        
        # 1. 前期低点（最近 60 日）
        if len(df) >= 60:
            low_60 = df['low'].iloc[-60:-5].min()  # 排除最近 5 日
            if low_60 < current_price:
                supports.append(round(low_60, 2))
        
        # 2. 均线位置
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        ma60 = df['close'].rolling(60).mean().iloc[-1]
        
        if ma20 < current_price:
            supports.append(round(ma20, 2))
        if ma60 < current_price:
            supports.append(round(ma60, 2))
        
        # 3. 整数关口
        round_price = round(current_price / 10) * 10
        if round_price < current_price:
            supports.append(round_price)
        
        # 4. 跳空缺口
        for i in range(len(df) - 1, 5, -1):
            prev_high = df['high'].iloc[i-1]
            curr_low = df['low'].iloc[i]
            
            if curr_low > prev_high:  # 向上跳空
                gap_support = (prev_high + curr_low) / 2
                if gap_support < current_price and gap_support > current_price * 0.9:
                    supports.append(round(gap_support, 2))
                    break
        
        # 去重排序
        supports = sorted(list(set(supports)))
        
        return supports[:5]  # 返回最强的 5 个支撑
    
    def calculate_resistance_levels(self, df: pd.DataFrame, current_price: float) -> List[float]:
        """
        计算阻力位（从近到远）
        
        方法：
        1. 前期高点
        2. 整数关口
        3. 跳空缺口
        4. 百分比目标
        """
        resistances = []
        
        # 1. 前期高点（最近 60 日）
        if len(df) >= 60:
            high_60 = df['high'].iloc[-60:-5].max()
            if high_60 > current_price:
                resistances.append(round(high_60, 2))
        
        # 2. 整数关口
        round_price_1 = round(current_price / 5) * 5
        round_price_2 = round(current_price / 2) * 2
        
        if round_price_1 > current_price:
            resistances.append(round_price_1)
        if round_price_2 > current_price and round_price_2 != round_price_1:
            resistances.append(round_price_2)
        
        # 3. 百分比目标（8%/15%/25%）
        target_8 = round(current_price * 1.08, 2)
        target_15 = round(current_price * 1.15, 2)
        target_25 = round(current_price * 1.25, 2)
        
        resistances.extend([target_8, target_15, target_25])
        
        # 去重排序
        resistances = sorted(list(set([r for r in resistances if r > current_price])))
        
        return resistances[:5]  # 返回最近的 5 个阻力
    
    def calculate_buy_zone(self, df: pd.DataFrame, platform_high: float) -> Dict:
        """
        计算买入区间
        
        基于平台突破理论：
        - 理想买入：回踩平台顶部
        - 激进买入：突破确认点
        - 保守买入：回踩 20 日线
        """
        current_price = df.iloc[-1]['close']
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        
        # 平台顶部（突破点）
        breakout_point = round(platform_high, 2)
        
        # 理想买入：回踩平台顶部 +1-3%
        ideal_buy_low = round(breakout_point * 1.01, 2)
        ideal_buy_high = round(breakout_point * 1.03, 2)
        
        # 激进买入：突破确认（当前价 +2%）
        aggressive_buy = round(current_price * 1.02, 2)
        
        # 保守买入：回踩 20 日线
        conservative_buy = round(ma20 * 1.01, 2)
        
        return {
            'ideal': {
                'low': ideal_buy_low,
                'high': ideal_buy_high,
                'description': '回踩平台顶部（最佳买点）'
            },
            'aggressive': {
                'price': aggressive_buy,
                'description': '突破确认（激进买点）'
            },
            'conservative': {
                'price': conservative_buy,
                'description': '回踩 20 日线（保守买点）'
            }
        }
    
    def calculate_stop_loss(self, df: pd.DataFrame, buy_price: float, 
                           stage: str = '鱼身期') -> Dict:
        """
        计算止损位
        
        基于：
        1. 固定百分比（-5%/-7%）
        2. ATR 动态止损（2*ATR）
        3. 技术位（平台底部/20 日线）
        """
        current_price = df.iloc[-1]['close']
        atr = self.calculate_atr(df, period=14)
        
        # 支撑位
        supports = self.calculate_support_levels(df, current_price)
        strong_support = supports[0] if supports else current_price * 0.95
        
        # 方法 1：固定百分比
        if stage == '鱼身期':
            fixed_pct = 0.05  # 5%
        elif stage == '鱼身末期':
            fixed_pct = 0.07  # 7%
        else:
            fixed_pct = 0.05
        
        fixed_stop = round(buy_price * (1 - fixed_pct), 2)
        
        # 方法 2：ATR 动态止损
        atr_stop = round(buy_price - 2 * atr, 2)
        
        # 方法 3：技术位止损
        tech_stop = round(strong_support * 0.97, 2)  # 支撑位下方 3%
        
        # 选择最严格的止损
        stop_loss = min(fixed_stop, atr_stop, tech_stop)
        
        # 确保不超过 -10%
        max_stop = round(buy_price * 0.90, 2)
        stop_loss = max(stop_loss, max_stop)
        
        return {
            'stop_price': stop_loss,
            'stop_pct': round((1 - stop_loss / buy_price) * 100, 1),
            'methods': {
                'fixed': fixed_stop,
                'atr': atr_stop,
                'technical': tech_stop
            },
            'atr': round(atr, 2)
        }
    
    def calculate_price_targets(self, df: pd.DataFrame, buy_price: float,
                               stop_loss: float) -> List[Dict]:
        """
        计算目标位（3 档）
        
        基于：
        1. 阻力位
        2. 百分比目标
        3. 风险收益比（至少 1:2）
        """
        resistances = self.calculate_resistance_levels(df, buy_price)
        
        risk = buy_price - stop_loss
        
        targets = []
        
        # 目标 1：最近阻力或 +8%
        if resistances:
            target1 = resistances[0]
        else:
            target1 = round(buy_price * 1.08, 2)
        
        reward1 = target1 - buy_price
        rr1 = reward1 / risk if risk > 0 else 0
        
        targets.append({
            'level': 1,
            'price': target1,
            'gain_pct': round((target1/buy_price - 1) * 100, 1),
            'rr_ratio': round(rr1, 1),
            'action': '减仓 30%'
        })
        
        # 目标 2：第二阻力或 +15%
        if len(resistances) > 1:
            target2 = resistances[1]
        else:
            target2 = round(buy_price * 1.15, 2)
        
        reward2 = target2 - buy_price
        rr2 = reward2 / risk if risk > 0 else 0
        
        targets.append({
            'level': 2,
            'price': target2,
            'gain_pct': round((target2/buy_price - 1) * 100, 1),
            'rr_ratio': round(rr2, 1),
            'action': '减仓 30%'
        })
        
        # 目标 3：第三阻力或 +25%
        if len(resistances) > 2:
            target3 = resistances[2]
        else:
            target3 = round(buy_price * 1.25, 2)
        
        reward3 = target3 - buy_price
        rr3 = reward3 / risk if risk > 0 else 0
        
        targets.append({
            'level': 3,
            'price': target3,
            'gain_pct': round((target3/buy_price - 1) * 100, 1),
            'rr_ratio': round(rr3, 1),
            'action': '清仓'
        })
        
        return targets
    
    def calculate_trade_plan(self, code: str, stage: str = '鱼身期') -> Optional[Dict]:
        """
        计算完整交易计划
        
        Args:
            code: 股票代码
            stage: 趋势阶段
            
        Returns:
            dict: 交易计划
        """
        df = self.get_price_data(code, days=120)
        
        if df is None or len(df) < 60:
            return None
        
        current_price = df.iloc[-1]['close']
        
        # 获取平台高点（简化处理）
        platform_high = df['high'].iloc[-20:-5].max()
        
        # 买入区间
        buy_zone = self.calculate_buy_zone(df, platform_high)
        
        # 使用理想买入价
        buy_price = buy_zone['ideal']['high']
        
        # 止损位
        stop_loss = self.calculate_stop_loss(df, buy_price, stage)
        
        # 目标位
        targets = self.calculate_price_targets(df, buy_price, stop_loss['stop_price'])
        
        # 风险收益比
        risk = buy_price - stop_loss['stop_price']
        avg_reward = sum(t['price'] - buy_price for t in targets) / 3
        avg_rr = avg_reward / risk if risk > 0 else 0
        
        return {
            'code': code,
            'current_price': round(current_price, 2),
            'buy_zone': buy_zone,
            'stop_loss': stop_loss,
            'targets': targets,
            'risk_reward': round(avg_rr, 1),
            'date': datetime.now().strftime('%Y-%m-%d')
        }


def format_trade_plan(plan: Dict) -> str:
    """格式化交易计划输出"""
    report = []
    
    report.append(f"{plan['code']} 交易计划")
    report.append(f"当前价格：{plan['current_price']}元")
    report.append("")
    
    # 买入区间
    report.append("【买入区间】")
    buy = plan['buy_zone']
    report.append(f"  理想买入：{buy['ideal']['low']}-{buy['ideal']['high']}元")
    report.append(f"    ({buy['ideal']['description']})")
    report.append(f"  激进买入：{buy['aggressive']['price']}元")
    report.append(f"    ({buy['aggressive']['description']})")
    report.append(f"  保守买入：{buy['conservative']['price']}元")
    report.append(f"    ({buy['conservative']['description']})")
    report.append("")
    
    # 止损位
    sl = plan['stop_loss']
    report.append("【止损位】")
    report.append(f"  止损价格：{sl['stop_price']}元")
    report.append(f"  止损幅度：-{sl['stop_pct']}%")
    report.append(f"  ATR: {sl['atr']}元")
    report.append("")
    
    # 目标位
    report.append("【目标位】")
    for t in plan['targets']:
        report.append(f"  目标{t['level']}: {t['price']}元 (+{t['gain_pct']}%)")
        report.append(f"    RR={t['rr_ratio']}  {t['action']}")
    report.append("")
    
    # 风险收益比
    report.append(f"【风险收益比】1:{plan['risk_reward']}")
    
    return "\n".join(report)


if __name__ == '__main__':
    # 测试
    print("=" * 60)
    print("测试精确价位计算")
    print("=" * 60)
    
    test_codes = ['600105', '002149']
    
    calc = PriceLevelCalculator()
    
    for code in test_codes:
        print(f"\n测试：{code}")
        plan = calc.calculate_trade_plan(code)
        
        if plan:
            print(format_trade_plan(plan))
        else:
            print("  无数据")
