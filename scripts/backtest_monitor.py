#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测健康监控脚本

每 5 分钟检查一次回测状态：
- 进程是否存活
- 进度是否正常更新
- 失败率是否异常
- 日志是否有错误

发现异常立即通知
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Optional

# 项目根目录
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 配置文件
LOG_DIR = os.path.join(base_dir, 'logs')
STATE_DIR = os.path.join(base_dir, 'state')
PROGRESS_FILE = os.path.join(STATE_DIR, 'backtest_progress.json')

# 阈值配置
MAX_FAILURE_RATE = 0.5  # 最大失败率 50%
MAX_STALL_MINUTES = 10  # 最大停滞时间（分钟）
CHECK_INTERVAL_SECONDS = 300  # 检查间隔（5 分钟）


def get_backtest_process() -> Optional[Dict]:
    """获取回测进程信息"""
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )
        
        for line in result.stdout.split('\n'):
            if 'run_backtest_parallel.py' in line and 'grep' not in line:
                parts = line.split()
                return {
                    'pid': parts[1],
                    'cpu': float(parts[2]),
                    'memory': float(parts[3]),
                    'status': 'running'
                }
        
        return None
        
    except Exception as e:
        return None


def check_progress() -> Dict:
    """检查回测进度"""
    if not os.path.exists(PROGRESS_FILE):
        return {
            'status': 'no_progress',
            'message': '进度文件不存在'
        }
    
    try:
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            progress = json.load(f)
        
        completed = len(progress.get('completed', []))
        failed = len(progress.get('failed', []))
        total = completed + failed
        
        if total == 0:
            return {
                'status': 'no_data',
                'message': '暂无回测数据'
            }
        
        failure_rate = failed / total if total > 0 else 0
        
        return {
            'status': 'running',
            'completed': completed,
            'failed': failed,
            'total': total,
            'failure_rate': failure_rate,
            'last_update': os.path.getmtime(PROGRESS_FILE)
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'读取进度失败：{e}'
        }


def check_logs() -> Dict:
    """检查日志文件"""
    today = datetime.now().strftime('%Y%m%d')
    log_files = [
        os.path.join(LOG_DIR, f'backtest_{today}_first.log'),
        os.path.join(LOG_DIR, f'backtest_{today}_restart.log'),
        os.path.join(LOG_DIR, f'backtest_{today}.log')
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            try:
                # 读取最后 100 行
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[-100:]
                
                # 检查错误
                errors = []
                for i, line in enumerate(lines):
                    if 'Error' in line or 'Exception' in line or '❌' in line:
                        errors.append({
                            'line': i,
                            'content': line.strip()
                        })
                
                return {
                    'status': 'ok',
                    'file': log_file,
                    'lines': len(lines),
                    'errors': errors[:10]  # 最多 10 个错误
                }
                
            except Exception as e:
                return {
                    'status': 'error',
                    'message': f'读取日志失败：{e}'
                }
    
    return {
        'status': 'no_log',
        'message': '未找到今日日志文件'
    }


def send_alert(message: str, level: str = 'warning'):
    """发送警报"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    alert = f"""
{'='*60}
🚨 回测异常警报 [{level.upper()}]
时间：{timestamp}
{'='*60}

{message}

{'='*60}
"""
    
    # 输出到控制台
    print(alert)
    
    # 保存到警报文件
    alert_file = os.path.join(LOG_DIR, f'alerts_{datetime.now().strftime("%Y%m%d")}.log')
    os.makedirs(LOG_DIR, exist_ok=True)
    
    with open(alert_file, 'a', encoding='utf-8') as f:
        f.write(alert + '\n')
    
    # TODO: 可以添加飞书/邮件通知
    # send_feishu_alert(alert)


def health_check() -> bool:
    """执行健康检查"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 执行健康检查...")
    
    alerts = []
    
    # 1. 检查进程
    process = get_backtest_process()
    if not process:
        alert = "❌ 回测进程未运行！\n\n请检查:\n1. 是否手动停止了回测\n2. 回测是否已崩溃\n3. 查看日志文件了解原因"
        alerts.append(alert)
        send_alert(alert, 'critical')
    else:
        print(f"✅ 回测进程运行中 (PID: {process['pid']}, CPU: {process['cpu']}%, 内存：{process['memory']}%)")
    
    # 2. 检查进度
    progress = check_progress()
    print(f"📊 回测进度：{progress.get('completed', 0)}/{progress.get('total', 0)} (失败：{progress.get('failed', 0)})")
    
    if progress['status'] == 'running':
        failure_rate = progress.get('failure_rate', 0)
        if failure_rate > MAX_FAILURE_RATE:
            alert = f"❌ 失败率过高：{failure_rate*100:.1f}%\n\n已完成：{progress['completed']}\n已失败：{progress['failed']}\n\n可能原因:\n1. 数据源接口变化\n2. 股票代码无效\n3. 网络问题"
            alerts.append(alert)
            send_alert(alert, 'critical')
        
        # 检查停滞
        last_update = progress.get('last_update', 0)
        stall_minutes = (time.time() - last_update) / 60
        
        if stall_minutes > MAX_STALL_MINUTES:
            alert = f"⚠️ 进度停滞超过{stall_minutes:.1f}分钟\n\n最后更新：{datetime.fromtimestamp(last_update).strftime('%Y-%m-%d %H:%M:%S')}\n\n可能原因:\n1. 程序卡死\n2. 网络超时\n3. 数据量过大"
            alerts.append(alert)
            send_alert(alert, 'warning')
    
    # 3. 检查日志
    logs = check_logs()
    if logs['status'] == 'ok' and logs['errors']:
        error_summary = '\n'.join([e['content'] for e in logs['errors'][:5]])
        alert = f"⚠️ 日志中发现错误:\n\n{error_summary}"
        alerts.append(alert)
        send_alert(alert, 'warning')
    
    # 4. 总结
    if not alerts:
        print("✅ 健康检查通过 - 一切正常")
        return True
    else:
        print(f"\n⚠️ 发现 {len(alerts)} 个异常，请检查！")
        return False


def run_monitor():
    """运行监控（持续）"""
    print("=" * 60)
    print("🔍 回测健康监控启动")
    print("=" * 60)
    print(f"检查间隔：{CHECK_INTERVAL_SECONDS/60:.0f} 分钟")
    print(f"失败率阈值：{MAX_FAILURE_RATE*100:.0f}%")
    print(f"停滞阈值：{MAX_STALL_MINUTES} 分钟")
    print()
    
    check_count = 0
    
    try:
        while True:
            health_check()
            check_count += 1
            
            # 每 12 次检查（1 小时）显示一次摘要
            if check_count % 12 == 0:
                print(f"\n[摘要] 已检查 {check_count} 次，当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            time.sleep(CHECK_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        print("\n\n监控已手动停止")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='回测健康监控')
    parser.add_argument('--once', action='store_true', help='只检查一次')
    parser.add_argument('--interval', type=int, default=300, help='检查间隔（秒）')
    
    args = parser.parse_args()
    
    if args.once:
        # 只检查一次
        success = health_check()
        sys.exit(0 if success else 1)
    else:
        # 持续监控
        if args.interval:
            CHECK_INTERVAL_SECONDS = args.interval
        run_monitor()
