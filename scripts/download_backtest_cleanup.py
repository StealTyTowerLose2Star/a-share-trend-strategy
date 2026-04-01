#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据下载 + 回测 + 清理 一体化脚本

流程:
1. 下载所有股票历史数据到本地
2. 使用本地数据回测
3. 回测完成后删除数据

优点:
- 避免网络问题影响回测
- 数据下载可断点续传
- 回测速度快（本地读取）
- 完成后删除节省空间
"""

import os
import sys
import json
import time
import shutil
from datetime import datetime
from typing import List, Optional

# 项目根目录
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

# 目录配置
data_dir = os.path.join(base_dir, 'data', 'temp_historical')
state_dir = os.path.join(base_dir, 'state')
logs_dir = os.path.join(base_dir, 'logs')

# 确保目录存在
for dir_path in [data_dir, state_dir, logs_dir]:
    os.makedirs(dir_path, exist_ok=True)


class DataDownloader:
    """数据下载器"""
    
    def __init__(self):
        self.download_count = 0
        self.failed_codes = []
    
    def get_all_codes(self) -> List[str]:
        """获取所有股票代码"""
        try:
            import akshare as ak
            
            df = ak.stock_info_a_code_name()
            if df is None:
                return []
            
            codes = df['code'].tolist()
            print(f"✅ 获取到 {len(codes)} 只股票代码")
            
            return codes
            
        except Exception as e:
            print(f"❌ 获取代码列表失败：{e}")
            return []
    
    def download_single(self, code: str, start_date: str = '20190101', 
                       end_date: str = '20251231', max_retries: int = 5) -> bool:
        """
        下载单只股票数据
        
        Returns:
            bool: 是否成功
        """
        filepath = os.path.join(data_dir, f"{code}.csv")
        
        # 检查是否已存在
        if os.path.exists(filepath):
            return True
        
        import akshare as ak
        import time
        import random
        
        for attempt in range(max_retries):
            try:
                # 延迟（避免请求过快）
                if attempt > 0:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    print(f"  重试 {attempt}/{max_retries}，等待 {delay:.1f}秒...")
                    time.sleep(delay)
                
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                )
                
                if df is None or len(df) == 0:
                    if attempt < max_retries - 1:
                        continue
                    print(f"⚠️  {code} 无数据")
                    return False
                
                # 保存
                df.to_csv(filepath, index=False)
                self.download_count += 1
                return True
                
            except Exception as e:
                if attempt < max_retries - 1:
                    continue
                print(f"❌ {code} 下载失败：{e}")
                self.failed_codes.append(code)
                return False
        
        return False
    
    def download_all(self, codes: List[str], batch_size: int = 100):
        """
        批量下载
        
        Args:
            codes: 股票代码列表
            batch_size: 每批下载数量
        """
        total = len(codes)
        print(f"\n开始下载 {total} 只股票历史数据...")
        print(f"数据目录：{data_dir}")
        print(f"批次大小：{batch_size} 只/批")
        print()
        
        start_time = time.time()
        
        for i in range(0, total, batch_size):
            batch_codes = codes[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            batch_start = time.time()
            batch_success = 0
            
            print(f"\n【批次 {batch_num}/{total_batches}】下载 {len(batch_codes)} 只股票...")
            
            for j, code in enumerate(batch_codes, 1):
                if self.download_single(code):
                    batch_success += 1
                
                # 每 10 只显示进度
                if j % 10 == 0:
                    print(f"  进度：{j}/{len(batch_codes)} (成功:{batch_success})")
                
                # 强制延迟（避免被封 IP）
                time.sleep(0.3)
            
            batch_elapsed = (time.time() - batch_start) / 60
            print(f"批次完成：成功 {batch_success}/{len(batch_codes)}，耗时 {batch_elapsed:.1f}分钟")
            
            # 每批保存进度
            self._save_progress(codes, i + batch_size)
            
            # 批次间延迟
            if i + batch_size < total:
                print("批次间休息 10 秒...")
                time.sleep(10)
        
        # 最终统计
        elapsed = (time.time() - start_time) / 60
        print(f"\n{'='*60}")
        print(f"下载完成！")
        print(f"  总计：{total} 只")
        print(f"  成功：{self.download_count} 只")
        print(f"  失败：{len(self.failed_codes)} 只")
        if self.failed_codes:
            print(f"  失败列表：{self.failed_codes[:20]}{'...' if len(self.failed_codes) > 20 else ''}")
        print(f"  耗时：{elapsed:.1f}分钟")
        print(f"{'='*60}")
    
    def _save_progress(self, codes: List[str], downloaded_count: int):
        """保存下载进度"""
        progress_file = os.path.join(state_dir, 'download_progress.json')
        
        progress = {
            'total': len(codes),
            'downloaded': downloaded_count,
            'failed': self.failed_codes,
            'last_update': datetime.now().isoformat()
        }
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)


class LocalBacktester:
    """本地回测器（使用本地数据）"""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.results = []
    
    def load_local_data(self, code: str) -> Optional[pd.DataFrame]:
        """从本地加载数据"""
        import pandas as pd
        
        filepath = os.path.join(self.data_dir, f"{code}.csv")
        
        if not os.path.exists(filepath):
            return None
        
        try:
            df = pd.read_csv(filepath)
            
            # 标准化列名
            columns_map = {}
            for col in df.columns:
                col_lower = col.lower()
                if '日期' in col or 'date' in col_lower:
                    columns_map[col] = 'date'
                elif '收盘' in col or 'close' in col_lower:
                    columns_map[col] = 'close'
                elif '最高' in col or 'high' in col_lower:
                    columns_map[col] = 'high'
                elif '最低' in col or 'low' in col_lower:
                    columns_map[col] = 'low'
                elif '开盘' in col or 'open' in col_lower:
                    columns_map[col] = 'open'
                elif '成交量' in col or 'vol' in col_lower:
                    columns_map[col] = 'volume'
            
            df = df.rename(columns=columns_map)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            print(f"❌ 加载{code}数据失败：{e}")
            return None
    
    def backtest_all(self, codes: List[str]) -> dict:
        """回测所有股票"""
        import pandas as pd
        import numpy as np
        
        print(f"\n开始本地回测 {len(codes)} 只股票...")
        
        results = []
        
        for i, code in enumerate(codes, 1):
            if i % 100 == 0:
                print(f"进度：{i}/{len(codes)} ({i/len(codes)*100:.1f}%)")
            
            df = self.load_local_data(code)
            
            if df is None or len(df) < 60:
                continue
            
            # 简化回测逻辑（示例）
            # 实际应该调用完整的回测框架
            
            # 计算均线
            df['ma20'] = df['close'].rolling(20).mean()
            df['ma60'] = df['close'].rolling(60).mean()
            
            # 简单策略：金叉买入，死叉卖出
            buy_signal = (df['ma20'] > df['ma60']) & (df['ma20'].shift(1) <= df['ma60'].shift(1))
            sell_signal = (df['ma20'] < df['ma60']) & (df['ma20'].shift(1) >= df['ma60'].shift(1))
            
            # 统计
            buy_count = buy_signal.sum()
            sell_count = sell_signal.sum()
            
            if buy_count > 0:
                results.append({
                    'code': code,
                    'data_rows': len(df),
                    'buy_signals': int(buy_count),
                    'sell_signals': int(sell_count),
                    'date_range': f"{df['date'].min().strftime('%Y-%m-%d')} 至 {df['date'].max().strftime('%Y-%m-%d')}"
                })
        
        # 统计
        print(f"\n{'='*60}")
        print(f"回测完成！")
        print(f"  回测股票：{len(results)} 只")
        print(f"{'='*60}")
        
        return {
            'success': True,
            'total_stocks': len(results),
            'results': results
        }


def cleanup_data():
    """删除临时数据"""
    print(f"\n开始清理临时数据...")
    
    if os.path.exists(data_dir):
        file_count = len(os.listdir(data_dir))
        total_size = sum(
            os.path.getsize(os.path.join(data_dir, f)) 
            for f in os.listdir(data_dir)
            if os.path.isfile(os.path.join(data_dir, f))
        ) / (1024 * 1024)  # MB
        
        shutil.rmtree(data_dir)
        
        print(f"✅ 已删除 {file_count} 个文件，释放 {total_size:.1f} MB 空间")
    else:
        print("⚠️  数据目录不存在")


def main():
    """主流程"""
    print("="*60)
    print("📥 数据下载 + 回测 + 清理 一体化流程")
    print("="*60)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 步骤 1：下载数据
    print("【步骤 1/3】下载历史数据...")
    downloader = DataDownloader()
    codes = downloader.get_all_codes()
    
    if not codes:
        print("❌ 获取代码列表失败，终止流程")
        return
    
    downloader.download_all(codes, batch_size=100)
    
    # 步骤 2：本地回测
    print("\n【步骤 2/3】本地回测...")
    backtester = LocalBacktester(data_dir)
    result = backtester.backtest_all(codes)
    
    # 保存回测结果
    if result['success']:
        result_file = os.path.join(base_dir, 'backtest', 'results', 
                                  f'local_backtest_{datetime.now().strftime("%Y%m%d_%H%M")}.json')
        os.makedirs(os.path.dirname(result_file), exist_ok=True)
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 回测结果已保存：{result_file}")
    
    # 步骤 3：清理数据
    print("\n【步骤 3/3】清理临时数据...")
    cleanup = input("是否删除临时数据？(y/n): ").strip().lower()
    
    if cleanup == 'y':
        cleanup_data()
    else:
        print(f"⚠️  临时数据保留在：{data_dir}")
    
    # 完成
    print(f"\n{'='*60}")
    print(f"流程完成！")
    print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")


if __name__ == '__main__':
    import pandas as pd
    main()
