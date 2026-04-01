#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势识别模块（右侧确认）

基于经典趋势跟踪理论：
- 海龟交易法则：突破 N 日高点
- 欧奈尔 CANSLIM：平台突破 + 成交量
- 均线多头排列

只做右侧交易：趋势已形成才介入
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class TrendDetector:
    """趋势检测器（右侧确认）"""
    
    def __init__(self):
        self.cache = {}
    
    def get_stock_data(self, code: str, days: int = 120) -> Optional[pd.DataFrame]:
        """
        获取个股历史数据
        
        Args:
            code: 股票代码
            days: 天数
            
        Returns:
            DataFrame: OHLCV 数据
        """
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )
            
            if df is None or len(df) == 0:
                return None
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })
            
            # 确保日期为 datetime 类型
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            # print(f"获取{code}数据失败：{e}")
            return None
    
    def calculate_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算均线
        
        Args:
            df: 价格数据
            
        Returns:
            DataFrame: 添加均线数据
        """
        if df is None or len(df) < 60:
            return df
        
        df = df.copy()
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        return df
    
    def check_ma_alignment(self, df: pd.DataFrame) -> Dict:
        """
        检查均线多头排列
        
        Args:
            df: 价格数据（包含均线）
            
        Returns:
            dict: 排列状态
        """
        if df is None or len(df) < 60:
            return {'aligned': False, 'score': 0}
        
        latest = df.iloc[-1]
        
        # 检查多头排列
        ma5 = latest['ma5']
        ma10 = latest['ma10']
        ma20 = latest['ma20']
        ma60 = latest['ma60']
        
        # 完美多头：MA5>MA10>MA20>MA60
        perfect = ma5 > ma10 > ma20 > ma60
        
        # 部分多头：MA5>MA10 且 MA20>MA60
        partial = ma5 > ma10 and ma20 > ma60
        
        # 计算评分
        score = 0
        if ma5 > ma10:
            score += 25
        if ma10 > ma20:
            score += 25
        if ma20 > ma60:
            score += 25
        if ma5 > ma60:
            score += 25
        
        return {
            'aligned': perfect,
            'partial': partial,
            'score': score,
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'ma60': ma60
        }
    
    def check_breakout(self, df: pd.DataFrame, n_days: int = 20) -> Dict:
        """
        检查突破 N 日高点（海龟交易法则）
        
        Args:
            df: 价格数据
            n_days: N 日
            
        Returns:
            dict: 突破状态
        """
        if df is None or len(df) < n_days:
            return {'breakout': False, 'score': 0}
        
        latest = df.iloc[-1]
        prev_high = df['high'].iloc[-n_days:-1].max()  # 不包括今日
        
        current_price = latest['close']
        
        # 突破
        breakout = current_price > prev_high
        
        # 突破强度
        if breakout:
            breakout_pct = (current_price - prev_high) / prev_high * 100
        else:
            breakout_pct = 0
        
        # 评分
        if breakout_pct > 5:
            score = 100
        elif breakout_pct > 3:
            score = 80
        elif breakout_pct > 0:
            score = 60
        else:
            score = 0
        
        return {
            'breakout': breakout,
            'breakout_pct': breakout_pct,
            'prev_high': prev_high,
            'score': score
        }
    
    def check_volume(self, df: pd.DataFrame) -> Dict:
        """
        检查成交量确认
        
        Args:
            df: 价格数据
            
        Returns:
            dict: 成交量状态
        """
        if df is None or len(df) < 10:
            return {'confirmed': False, 'score': 0}
        
        latest = df.iloc[-1]
        ma5_volume = df['volume'].iloc[-5:].mean()
        
        current_volume = latest['volume']
        
        # 成交量比率
        if ma5_volume > 0:
            volume_ratio = current_volume / ma5_volume
        else:
            volume_ratio = 1
        
        # 确认标准：成交量 > 5 日均量 150%
        confirmed = volume_ratio >= 1.5
        
        # 评分
        if volume_ratio >= 2.0:
            score = 100
        elif volume_ratio >= 1.5:
            score = 80
        elif volume_ratio >= 1.2:
            score = 60
        else:
            score = 40
        
        return {
            'confirmed': confirmed,
            'volume_ratio': volume_ratio,
            'ma5_volume': ma5_volume,
            'score': score
        }
    
    def check_trend_slope(self, df: pd.DataFrame) -> Dict:
        """
        检查 20 日线斜率（趋势方向）
        
        Args:
            df: 价格数据
            
        Returns:
            dict: 斜率状态
        """
        if df is None or len(df) < 40:
            return {'upward': False, 'slope': 0}
        
        # 计算 20 日线斜率
        ma20_current = df['ma20'].iloc[-1]
        ma20_5days_ago = df['ma20'].iloc[-5]
        
        slope = (ma20_current - ma20_5days_ago) / ma20_5days_ago * 100
        
        upward = slope > 0
        
        # 评分
        if slope > 5:
            score = 100
        elif slope > 2:
            score = 80
        elif slope > 0:
            score = 60
        else:
            score = 20
        
        return {
            'upward': upward,
            'slope': slope,
            'score': score
        }
    
    def detect_trend(self, code: str) -> Optional[Dict]:
        """
        检测个股趋势（右侧确认）
        
        Args:
            code: 股票代码
            
        Returns:
            dict: 趋势状态
        """
        # 获取数据
        df = self.get_stock_data(code, days=120)
        
        if df is None or len(df) < 60:
            return None
        
        # 计算均线
        df = self.calculate_ma(df)
        
        # 各项检查
        ma_check = self.check_ma_alignment(df)
        breakout_check = self.check_breakout(df, n_days=20)
        volume_check = self.check_volume(df)
        slope_check = self.check_trend_slope(df)
        
        # 综合评分
        total_score = (
            ma_check['score'] * 0.30 +
            breakout_check['score'] * 0.25 +
            volume_check['score'] * 0.20 +
            slope_check['score'] * 0.25
        )
        
        # 趋势形成标准
        trend_formed = (
            ma_check['aligned'] and  # 均线多头排列
            breakout_check['breakout'] and  # 突破 20 日高点
            volume_check['confirmed'] and  # 成交量确认
            slope_check['upward']  # 20 日线向上
        )
        
        # 趋势强度
        if total_score >= 80:
            strength = '强趋势'
        elif total_score >= 60:
            strength = '中等趋势'
        elif total_score >= 40:
            strength = '弱趋势'
        else:
            strength = '无趋势'
        
        return {
            'code': code,
            'name': df.iloc[-1].get('股票名称', ''),
            'date': df.iloc[-1]['date'].strftime('%Y-%m-%d'),
            'price': float(df.iloc[-1]['close']),
            'trend_formed': trend_formed,
            'trend_formed': trend_formed,
            'strength': strength,
            'total_score': round(total_score, 1),
            'ma_alignment': ma_check,
            'breakout': breakout_check,
            'volume': volume_check,
            'slope': slope_check,
            'details': {
                'ma5': float(ma_check['ma5']),
                'ma10': float(ma_check['ma10']),
                'ma20': float(ma_check['ma20']),
                'ma60': float(ma_check['ma60']),
                'prev_high': float(breakout_check['prev_high']),
                'volume_ratio': round(volume_check['volume_ratio'], 2),
                'slope_pct': round(slope_check['slope'], 2)
            }
        }


def scan_market_trends(stock_codes: List[str], min_score: float = 60) -> List[Dict]:
    """
    扫描全市场趋势
    
    Args:
        stock_codes: 股票代码列表
        min_score: 最低评分
        
    Returns:
        list: 趋势股票列表
    """
    detector = TrendDetector()
    trends = []
    
    print(f"开始扫描 {len(stock_codes)} 只股票...")
    
    for i, code in enumerate(stock_codes):
        if (i + 1) % 100 == 0:
            print(f"已扫描 {i+1}/{len(stock_codes)} 只")
        
        try:
            result = detector.detect_trend(code)
            
            if result and result['total_score'] >= min_score:
                trends.append(result)
                
        except Exception as e:
            continue
    
    # 按评分排序
    trends.sort(key=lambda x: x['total_score'], reverse=True)
    
    print(f"\n✅ 扫描完成，发现 {len(trends)} 只趋势股")
    
    return trends


if __name__ == '__main__':
    # 测试
    print("=" * 60)
    print("测试趋势识别模块")
    print("=" * 60)
    
    # 测试股票
    test_codes = ['600105', '002149', '300834']
    
    detector = TrendDetector()
    
    for code in test_codes:
        print(f"\n测试：{code}")
        result = detector.detect_trend(code)
        
        if result:
            print(f"  价格：{result['price']}")
            print(f"  趋势：{result['strength']} ({result['total_score']}分)")
            print(f"  均线：{result['ma_alignment']['score']}分")
            print(f"  突破：{result['breakout']['score']}分")
            print(f"  成交量：{result['volume']['score']}分")
            print(f"  斜率：{result['slope']['score']}分")
        else:
            print("  无数据")
