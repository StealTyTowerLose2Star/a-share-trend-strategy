#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势阶段判断模块

基于欧奈尔 CANSLIM 和 A 股游资经验：
- 鱼头：突破初期（0-30%）→ 观望，风险高
- 鱼身：趋势确认（30-70%）→ 重仓，最确定
- 鱼尾：趋势末期（70-100%）→ 轻仓或退出

只做鱼身段，放弃鱼头和鱼尾
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta


class TrendStageAnalyzer:
    """趋势阶段分析器"""
    
    def __init__(self):
        pass
    
    def get_price_data(self, code: str, days: int = 250) -> Optional[pd.DataFrame]:
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
            
            # 标准化
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
            print(f"获取数据失败：{e}")
            return None
    
    def identify_platform(self, df: pd.DataFrame) -> Dict:
        """
        识别价格平台（突破前的整理区间）
        
        Returns:
            dict: 平台信息
        """
        if df is None or len(df) < 60:
            return {'found': False}
        
        # 最近 20 日的价格区间
        recent_20 = df.iloc[-20:]
        platform_high = recent_20['high'].max()
        platform_low = recent_20['low'].min()
        platform_range = (platform_high - platform_low) / platform_low * 100
        
        # 平台整理时间
        consolidation_days = len(recent_20)
        
        # 判断是否是有效平台（振幅<20%）
        is_valid = platform_range < 20
        
        current_price = df.iloc[-1]['close']
        
        # 突破状态
        breakout = current_price > platform_high
        breakout_pct = (current_price - platform_high) / platform_high * 100 if breakout else 0
        
        return {
            'found': is_valid,
            'platform_high': platform_high,
            'platform_low': platform_low,
            'platform_range': platform_range,
            'consolidation_days': consolidation_days,
            'breakout': breakout,
            'breakout_pct': breakout_pct,
            'current_price': current_price
        }
    
    def calculate_trend_stage(self, df: pd.DataFrame) -> Dict:
        """
        计算趋势阶段（鱼头/鱼身/鱼尾）
        
        Returns:
            dict: 趋势阶段
        """
        if df is None or len(df) < 120:
            return {'stage': 'unknown', 'stage_pct': 0}
        
        current_price = df.iloc[-1]['close']
        
        # 找到趋势起点（120 日低点）
        low_120 = df['low'].iloc[-120:].min()
        high_120 = df['high'].iloc[-120:].max()
        
        # 计算趋势位置
        trend_range = high_120 - low_120
        if trend_range > 0:
            stage_pct = (current_price - low_120) / trend_range * 100
        else:
            stage_pct = 50
        
        # 判断阶段
        if stage_pct < 30:
            stage = '鱼头期'
            description = '突破初期，风险较高'
            action = '观望'
            position = 0
        elif 30 <= stage_pct < 70:
            stage = '鱼身期'
            description = '趋势确认，最确定阶段'
            action = '重仓参与'
            position = 80
        elif 70 <= stage_pct < 90:
            stage = '鱼身末期'
            description = '趋势延续，但空间有限'
            action = '轻仓参与'
            position = 40
        else:
            stage = '鱼尾期'
            description = '趋势末期，风险加大'
            action = '退出或观望'
            position = 0
        
        return {
            'stage': stage,
            'stage_pct': round(stage_pct, 1),
            'description': description,
            'action': action,
            'position': position,
            'low_120': low_120,
            'high_120': high_120,
            'current_price': current_price
        }
    
    def check_pullback(self, df: pd.DataFrame) -> Dict:
        """
        检查回踩确认（鱼身期最佳买入点）
        
        Returns:
            dict: 回踩状态
        """
        if df is None or len(df) < 60:
            return {'pullback': False}
        
        # 计算 20 日线
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        ma10 = df['close'].rolling(10).mean().iloc[-1]
        
        current_price = df.iloc[-1]['close']
        
        # 回踩 20 日线
        pullback_to_ma20 = abs(current_price - ma20) / ma20 < 0.03  # 3% 以内
        
        # 回踩不破
        today_low = df.iloc[-1]['low']
        yesterday_low = df.iloc[-2]['low']
        
        pullback_hold = today_low > ma20 * 0.97  # 未跌破 20 日线 3%
        
        # 成交量萎缩后放大
        volume_5d = df['volume'].iloc[-5:].mean()
        volume_yesterday = df['volume'].iloc[-2]
        volume_today = df['volume'].iloc[-1]
        
        volume_shrink_expand = volume_yesterday < volume_5d * 0.8 and volume_today > volume_yesterday * 1.5
        
        # 回踩确认
        pullback_confirmed = pullback_to_ma20 and pullback_hold
        
        return {
            'pullback': pullback_confirmed,
            'pullback_to_ma20': pullback_to_ma20,
            'pullback_hold': pullback_hold,
            'volume_shrink_expand': volume_shrink_expand,
            'ma20': ma20,
            'ma10': ma10,
            'current_price': current_price
        }
    
    def analyze_stage_full(self, code: str) -> Optional[Dict]:
        """
        完整趋势阶段分析
        
        Args:
            code: 股票代码
            
        Returns:
            dict: 完整分析结果
        """
        df = self.get_price_data(code, days=250)
        
        if df is None or len(df) < 120:
            return None
        
        # 平台识别
        platform = self.identify_platform(df)
        
        # 趋势阶段
        stage = self.calculate_trend_stage(df)
        
        # 回踩确认
        pullback = self.check_pullback(df)
        
        # 综合判断
        if stage['stage'] == '鱼身期' and pullback['pullback']:
            signal = '强烈买入'
            confidence = 90
        elif stage['stage'] == '鱼身期':
            signal = '买入'
            confidence = 75
        elif stage['stage'] == '鱼身末期':
            signal = '谨慎买入'
            confidence = 60
        elif stage['stage'] == '鱼头期':
            signal = '观望'
            confidence = 40
        else:
            signal = '退出'
            confidence = 20
        
        return {
            'code': code,
            'platform': platform,
            'stage': stage,
            'pullback': pullback,
            'signal': signal,
            'confidence': confidence,
            'date': datetime.now().strftime('%Y-%m-%d')
        }


def analyze_trend_stages(codes: list) -> list:
    """
    批量分析趋势阶段
    
    Args:
        codes: 股票代码列表
        
    Returns:
        list: 分析结果
    """
    analyzer = TrendStageAnalyzer()
    results = []
    
    print(f"分析 {len(codes)} 只股票的趋势阶段...")
    
    for i, code in enumerate(codes):
        if (i + 1) % 100 == 0:
            print(f"已分析 {i+1}/{len(codes)}")
        
        try:
            result = analyzer.analyze_stage_full(code)
            if result:
                results.append(result)
        except:
            continue
    
    # 筛选鱼身期
    fish_body = [r for r in results if r['stage']['stage'] in ['鱼身期', '鱼身末期']]
    
    print(f"\n✅ 分析完成")
    print(f"   鱼身期：{len(fish_body)} 只")
    
    return results


if __name__ == '__main__':
    # 测试
    print("=" * 60)
    print("测试趋势阶段判断")
    print("=" * 60)
    
    test_codes = ['600105', '002149', '300834']
    
    analyzer = TrendStageAnalyzer()
    
    for code in test_codes:
        print(f"\n测试：{code}")
        result = analyzer.analyze_stage_full(code)
        
        if result:
            print(f"  平台：{result['platform']['stage']}")
            print(f"  趋势：{result['stage']['stage']} ({result['stage']['stage_pct']}%)")
            print(f"  回踩：{result['pullback']['pullback']}")
            print(f"  信号：{result['signal']} (置信度：{result['confidence']})")
        else:
            print("  无数据")
