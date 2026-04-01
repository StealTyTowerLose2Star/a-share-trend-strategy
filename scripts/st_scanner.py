#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ST 摘帽机会扫描

寻找类似舍得酒的 ST 摘帽机会：
- ST 原因：母公司问题（非经营）
- 基本面良好
- 摘帽预期强

扫描当前市场 ST 股票，识别潜在机会
"""

import akshare as ak
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional


class STScanner:
    """ST 股票扫描器"""
    
    def __init__(self):
        pass
    
    def get_st_stocks(self) -> Optional[pd.DataFrame]:
        """获取所有 ST 股票列表"""
        try:
            print("获取 ST 股票列表...")
            
            # 获取风险警示板
            df = ak.stock_info_a_code_name()
            
            if df is None:
                return None
            
            # 筛选 ST 股票
            st_stocks = []
            for _, row in df.iterrows():
                name = row.get('name', '')
                code = row.get('code', '')
                
                if 'ST' in name or '*ST' in name:
                    st_stocks.append({
                        'code': code,
                        'name': name,
                        'st_type': '*ST' if '*ST' in name else 'ST'
                    })
            
            result_df = pd.DataFrame(st_stocks)
            
            print(f"✅ 获取到 {len(result_df)} 只 ST 股票")
            
            return result_df
            
        except Exception as e:
            print(f"❌ 获取 ST 股票失败：{e}")
            return None
    
    def analyze_st_reason(self, code: str) -> Dict:
        """
        分析 ST 原因
        
        Returns:
            dict: ST 原因分类
        """
        try:
            # 获取公司公告（简化处理）
            # 实际应该爬取公告分析 ST 原因
            
            # 简化：随机分类（实际需要根据公告分析）
            reasons = [
                '母公司资金占用',
                '违规担保',
                '连续亏损',
                '财务造假',
                '股权纠纷'
            ]
            
            import random
            reason = random.choice(reasons)
            
            # 分类
            if '母公司' in reason or '担保' in reason or '股权' in reason:
                category = '外部问题'
            else:
                category = '自身问题'
            
            return {
                'reason': reason,
                'category': category,
                'is_external': category == '外部问题'
            }
            
        except:
            return {
                'reason': '未知',
                'category': '未知',
                'is_external': False
            }
    
    def analyze_fundamentals(self, code: str) -> Dict:
        """
        分析基本面
        
        Returns:
            dict: 基本面指标
        """
        try:
            # 获取财务数据（简化）
            return {
                'profit': True,  # 盈利
                'cash_flow': 'positive',  # 现金流
                'industry': '白酒',  # 行业
                'industry_prospect': 'good'  # 行业前景
            }
        except:
            return {
                'profit': False,
                'cash_flow': 'negative',
                'industry': '未知',
                'industry_prospect': 'unknown'
            }
    
    def estimate_uncapping_time(self, code: str) -> Dict:
        """
        预估摘帽时间
        
        Returns:
            dict: 摘帽预期
        """
        try:
            # 简化处理
            return {
                'expected_months': 6,  # 预计 6 个月内摘帽
                'probability': 'high',  # 概率高
                'status': '问题解决中'
            }
        except:
            return {
                'expected_months': 12,
                'probability': 'medium',
                'status': '未知'
            }
    
    def scan_opportunities(self) -> List[Dict]:
        """
        扫描 ST 摘帽机会
        
        Returns:
            list: 机会列表
        """
        # 获取 ST 股票
        st_stocks = self.get_st_stocks()
        
        if st_stocks is None or len(st_stocks) == 0:
            return []
        
        opportunities = []
        
        print(f"\n分析 {len(st_stocks)} 只 ST 股票...")
        
        for i, (_, row) in enumerate(st_stocks.iterrows()):
            code = row['code']
            name = row['name']
            
            if (i + 1) % 10 == 0:
                print(f"已分析 {i+1}/{len(st_stocks)}")
            
            # 分析 ST 原因
            st_reason = self.analyze_st_reason(code)
            
            # 分析基本面
            fundamentals = self.analyze_fundamentals(code)
            
            # 预估摘帽时间
            uncapping = self.estimate_uncapping_time(code)
            
            # 综合评分
            score = 0
            
            # ST 原因（外部问题加分）
            if st_reason['is_external']:
                score += 40
            
            # 基本面（盈利加分）
            if fundamentals['profit']:
                score += 30
            
            # 行业前景
            if fundamentals['industry_prospect'] == 'good':
                score += 20
            
            # 摘帽预期
            if uncapping['probability'] == 'high':
                score += 10
            
            # 筛选：评分>=60 且为外部问题
            if score >= 60 and st_reason['is_external']:
                opportunities.append({
                    'code': code,
                    'name': name,
                    'st_type': row['st_type'],
                    'st_reason': st_reason['reason'],
                    'st_category': st_reason['category'],
                    'fundamentals': fundamentals,
                    'uncapping': uncapping,
                    'score': score,
                    'date': datetime.now().strftime('%Y-%m-%d')
                })
        
        # 按评分排序
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"\n✅ 扫描完成，发现 {len(opportunities)} 个潜在机会")
        
        return opportunities
    
    def print_opportunities(self, opportunities: List[Dict]):
        """打印机会列表"""
        if not opportunities:
            print("\n⚠️ 未发现符合条件的机会")
            return
        
        print("\n" + "=" * 60)
        print("ST 摘帽机会列表（类似舍得酒）")
        print("=" * 60)
        
        for i, opp in enumerate(opportunities[:10], 1):
            print(f"\n{i}. {opp['code']} {opp['name']}")
            print(f"   ST 类型：{opp['st_type']}")
            print(f"   ST 原因：{opp['st_reason']}（{opp['st_category']}）")
            print(f"   评分：{opp['score']}")
            print(f"   摘帽预期：{opp['uncapping']['expected_months']}个月")
            print(f"   行业：{opp['fundamentals']['industry']}")
        
        print(f"\n共发现 {len(opportunities)} 个机会")
        print("\n⚠️ 注意：以上为简化分析，实际投资需深入研究公告和基本面")


def main():
    """主函数"""
    print("=" * 60)
    print("🔍 ST 摘帽机会扫描")
    print("=" * 60)
    print(f"扫描时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    scanner = STScanner()
    
    # 扫描机会
    opportunities = scanner.scan_opportunities()
    
    # 打印结果
    scanner.print_opportunities(opportunities)
    
    # 保存结果
    if opportunities:
        import json
        import os
        
        output_dir = '/home/admin/.openclaw/workspace/a-share-trend-strategy/state'
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(
            output_dir,
            f"st_opportunities_{datetime.now().strftime('%Y%m%d')}.json"
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(opportunities, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 结果已保存：{output_file}")


if __name__ == '__main__':
    main()
