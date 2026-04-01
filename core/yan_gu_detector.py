#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
妖股特征识别模块

基于 A 股游资经验和历史妖股统计：
- 冷门板块突然爆发
- 连续涨停 + 高换手
- 龙虎榜游资席位
- 小市值 + 低股价
- 题材概念催化

捕捉市场中的妖股机会
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class YanGuDetector:
    """妖股检测器"""
    
    def __init__(self):
        pass
    
    def get_stock_basic(self, code: str) -> Optional[Dict]:
        """获取股票基本信息"""
        try:
            import akshare as ak
            
            # 获取基本信息
            df = ak.stock_individual_info_em(symbol=code)
            
            if df is None:
                return None
            
            info = {}
            for _, row in df.iterrows():
                if '市值' in str(row['item']):
                    info['market_cap'] = row['value']
                elif '股价' in str(row['item']):
                    info['price'] = row['value']
                elif '股本' in str(row['item']):
                    info['shares'] = row['value']
            
            return info
            
        except:
            return None
    
    def get_price_data(self, code: str, days: int = 60) -> Optional[pd.DataFrame]:
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
                '成交量': 'volume',
                '成交额': 'amount',
                '换手率': 'turnover',
                '涨跌幅': 'change_pct'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            return df
            
        except:
            return None
    
    def check_continuous_limit_up(self, df: pd.DataFrame) -> Dict:
        """
        检查连续涨停
        
        妖股特征：连续 3 板以上
        """
        if df is None or len(df) < 10:
            return {'continuous': False, 'count': 0}
        
        # 统计连续涨停
        limit_up_count = 0
        max_continuous = 0
        current_continuous = 0
        
        for i in range(len(df) - 1, -1, -1):
            change_pct = df['change_pct'].iloc[i]
            
            # 涨停判断（>9.5%）
            if change_pct > 9.5:
                current_continuous += 1
                limit_up_count += 1
                max_continuous = max(max_continuous, current_continuous)
            else:
                current_continuous = 0
        
        # 妖股标准：连续 3 板以上
        is_yan_gu = max_continuous >= 3
        
        return {
            'continuous': is_yan_gu,
            'count': max_continuous,
            'total_limit_up': limit_up_count
        }
    
    def check_high_turnover(self, df: pd.DataFrame) -> Dict:
        """
        检查高换手率
        
        妖股特征：换手率持续>10%
        """
        if df is None or len(df) < 20:
            return {'high_turnover': False}
        
        recent_turnover = df['turnover'].iloc[-20:]
        
        # 平均换手率
        avg_turnover = recent_turnover.mean()
        
        # 高换手天数
        high_turnover_days = (recent_turnover > 10).sum()
        
        # 妖股标准：平均换手>15% 或 高换手天数>10 天
        is_high = avg_turnover > 15 or high_turnover_days > 10
        
        return {
            'high_turnover': is_high,
            'avg_turnover': round(avg_turnover, 1),
            'high_turnover_days': int(high_turnover_days)
        }
    
    def check_small_cap(self, market_cap: float) -> Dict:
        """
        检查小市值
        
        妖股特征：市值<50 亿
        """
        if market_cap is None:
            return {'small_cap': False}
        
        # 转换为亿
        if isinstance(market_cap, str):
            if '亿' in market_cap:
                market_cap = float(market_cap.replace('亿', ''))
            elif '万' in market_cap:
                market_cap = float(market_cap.replace('万', '')) / 10000
        
        # 妖股标准：市值<50 亿
        is_small = market_cap < 50
        
        return {
            'small_cap': is_small,
            'market_cap': market_cap
        }
    
    def check_low_price(self, price: float) -> Dict:
        """
        检查低股价
        
        妖股特征：股价<20 元
        """
        if price is None:
            return {'low_price': False}
        
        if isinstance(price, str):
            price = float(price.replace('元', ''))
        
        # 妖股标准：股价<20 元
        is_low = price < 20
        
        return {
            'low_price': is_low,
            'price': price
        }
    
    def check_cold_sector_surge(self, code: str) -> Dict:
        """
        检查冷门板块突然爆发
        
        妖股特征：冷门板块 + 突然爆发
        """
        try:
            import akshare as ak
            
            # 获取所属板块
            df = ak.stock_board_industry_name_em()
            
            # 简化处理：假设是冷门板块
            # 实际应该检查板块历史热度
            
            return {
                'cold_sector': True,  # 简化
                'surge': True
            }
            
        except:
            return {'cold_sector': False, 'surge': False}
    
    def detect_yan_gu(self, code: str) -> Optional[Dict]:
        """
        检测妖股特征
        
        Args:
            code: 股票代码
            
        Returns:
            dict: 妖股特征
        """
        # 获取数据
        df = self.get_price_data(code, days=60)
        basic = self.get_stock_basic(code)
        
        if df is None:
            return None
        
        # 各项检查
        limit_up = self.check_continuous_limit_up(df)
        turnover = self.check_high_turnover(df)
        
        if basic:
            market_cap = self.check_small_cap(basic.get('market_cap', 100))
            price = self.check_low_price(basic.get('price', 50))
        else:
            market_cap = {'small_cap': False, 'market_cap': 100}
            price = {'low_price': False, 'price': 50}
        
        cold_sector = self.check_cold_sector_surge(code)
        
        # 综合评分
        score = 0
        
        if limit_up['continuous']:
            score += 30  # 连续涨停
        if turnover['high_turnover']:
            score += 20  # 高换手
        if market_cap['small_cap']:
            score += 20  # 小市值
        if price['low_price']:
            score += 15  # 低股价
        if cold_sector['cold_sector']:
            score += 15  # 冷门板块
        
        # 妖股标准：评分>=60
        is_yan_gu = score >= 60
        
        return {
            'code': code,
            'is_yan_gu': is_yan_gu,
            'score': score,
            'features': {
                'continuous_limit_up': limit_up,
                'high_turnover': turnover,
                'small_cap': market_cap,
                'low_price': price,
                'cold_sector': cold_sector
            },
            'date': datetime.now().strftime('%Y-%m-%d')
        }


def scan_yan_gu(codes: list) -> list:
    """
    扫描妖股
    
    Args:
        codes: 股票代码列表
        
    Returns:
        list: 妖股列表
    """
    detector = YanGuDetector()
    yan_gu_list = []
    
    print(f"扫描 {len(codes)} 只股票的妖股特征...")
    
    for i, code in enumerate(codes):
        if (i + 1) % 100 == 0:
            print(f"已扫描 {i+1}/{len(codes)}")
        
        try:
            result = detector.detect_yan_gu(code)
            if result and result['is_yan_gu']:
                yan_gu_list.append(result)
        except:
            continue
    
    # 按评分排序
    yan_gu_list.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"\n✅ 扫描完成，发现 {len(yan_gu_list)} 只妖股")
    
    return yan_gu_list


if __name__ == '__main__':
    # 测试
    print("=" * 60)
    print("测试妖股识别")
    print("=" * 60)
    
    test_codes = ['600105', '002149', '300834']
    
    detector = YanGuDetector()
    
    for code in test_codes:
        print(f"\n测试：{code}")
        result = detector.detect_yan_gu(code)
        
        if result:
            print(f"  妖股：{'是' if result['is_yan_gu'] else '否'}")
            print(f"  评分：{result['score']}")
            print(f"  连续涨停：{result['features']['continuous_limit_up']['count']}板")
            print(f"  换手率：{result['features']['high_turnover']['avg_turnover']}%")
        else:
            print("  无数据")
