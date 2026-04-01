#!/bin/bash
# 增强的每日自动回测脚本
# 包含异常检测和通知功能

# 环境变量
export PATH=/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin
export PYTHONIOENCODING=utf-8

# 项目目录
PROJECT_DIR="/home/admin/.openclaw/workspace/a-share-trend-strategy"
LOG_DIR="$PROJECT_DIR/logs"
STATE_DIR="$PROJECT_DIR/state"
DATE=$(date +%Y%m%d)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE="$LOG_DIR/backtest_$DATE.log"
ALERT_FILE="$LOG_DIR/alerts_$DATE.log"

# 创建目录
mkdir -p $LOG_DIR
mkdir -p $STATE_DIR

# 通知函数
send_notification() {
    local message="$1"
    local level="$2"
    
    echo "[$TIMESTAMP] [$level] $message" | tee -a $LOG_FILE
    
    # 保存到警报文件
    if [ "$level" != "INFO" ]; then
        echo "[$TIMESTAMP] [$level] $message" >> $ALERT_FILE
    fi
    
    # TODO: 飞书通知
    # curl -X POST "YOUR_WEBHOOK" \
    #   -H "Content-Type: application/json" \
    #   -d "{\"msg_type\":\"text\",\"content\":{\"text\":\"$message\"}}"
}

# 打印启动信息
echo "========================================" | tee -a $LOG_FILE
echo "启动时间：$TIMESTAMP" | tee -a $LOG_FILE
echo "回测任务启动（增强版）" | tee -a $LOG_FILE
echo "========================================" | tee -a $LOG_FILE

send_notification "回测任务开始" "INFO"

# 进入项目目录
cd $PROJECT_DIR

# 清理旧进度文件（如果需要重新开始）
if [ "$1" == "--reset" ]; then
    rm -f $STATE_DIR/backtest_progress.json
    send_notification "已重置进度文件" "INFO"
fi

# 检查是否已有回测在运行
EXISTING_PID=$(pgrep -f "run_backtest_parallel.py" || echo "")
if [ -n "$EXISTING_PID" ]; then
    send_notification "警告：已有回测进程在运行 (PID: $EXISTING_PID)" "WARNING"
    # 可以选择终止或退出
    # kill $EXISTING_PID
    # send_notification "已终止旧进程" "INFO"
fi

# 运行回测（4 线程并行）
echo "" | tee -a $LOG_FILE
echo "开始回测..." | tee -a $LOG_FILE

# 启动回测进程
python3.10 scripts/run_backtest_parallel.py \
    --workers 4 \
    >> $LOG_FILE 2>&1 &

BACKTEST_PID=$!
send_notification "回测进程已启动 (PID: $BACKTEST_PID)" "INFO"

# 监控回测进度
echo "" | tee -a $LOG_FILE
echo "开始监控回测进度..." | tee -a $LOG_FILE

LAST_PROGRESS=0
STALL_COUNT=0
MAX_STALL=12  # 10 分钟（2 分钟检查一次，检查 6 次）

while kill -0 $BACKTEST_PID 2>/dev/null; do
    sleep 120  # 每 2 分钟检查一次
    
    # 检查进度文件
    if [ -f "$STATE_DIR/backtest_progress.json" ]; then
        COMPLETED=$(python3.10 -c "import json; d=json.load(open('$STATE_DIR/backtest_progress.json')); print(len(d.get('completed', [])))" 2>/dev/null || echo "0")
        FAILED=$(python3.10 -c "import json; d=json.load(open('$STATE_DIR/backtest_progress.json')); print(len(d.get('failed', [])))" 2>/dev/null || echo "0")
        TOTAL=$((COMPLETED + FAILED))
        
        if [ "$TOTAL" -gt 0 ]; then
            FAILURE_RATE=$(python3.10 -c "print(f'{$FAILED/$TOTAL*100:.1f}')" 2>/dev/null || echo "0")
            
            echo "[$(date '+%H:%M:%S')] 进度：$TOTAL 只 (成功:$COMPLETED 失败:$FAILED 失败率:$FAILURE_RATE%)" | tee -a $LOG_FILE
            
            # 检查失败率
            if (( $(echo "$FAILURE_RATE > 50" | bc -l 2>/dev/null || echo 0) )); then
                send_notification "失败率过高：$FAILURE_RATE% (成功:$COMPLETED 失败:$FAILED)" "CRITICAL"
            fi
            
            # 检查停滞
            if [ "$TOTAL" -eq "$LAST_PROGRESS" ]; then
                STALL_COUNT=$((STALL_COUNT + 1))
                if [ $STALL_COUNT -ge $MAX_STALL ]; then
                    send_notification "进度停滞超过 10 分钟！(成功:$COMPLETED 失败:$FAILED)" "WARNING"
                fi
            else
                STALL_COUNT=0
                LAST_PROGRESS=$TOTAL
            fi
        fi
    fi
    
    # 检查进程状态
    if ! kill -0 $BACKTEST_PID 2>/dev/null; then
        break
    fi
done

# 等待进程结束
wait $BACKTEST_PID
EXIT_CODE=$?

# 打印完成信息
echo "" | tee -a $LOG_FILE
echo "========================================" | tee -a $LOG_FILE
echo "完成时间：$(date '+%Y-%m-%d %H:%M:%S')" | tee -a $LOG_FILE

if [ $EXIT_CODE -eq 0 ]; then
    send_notification "回测成功完成" "SUCCESS"
    echo "✅ 回测成功完成" | tee -a $LOG_FILE
else
    send_notification "回测失败，退出码：$EXIT_CODE" "ERROR"
    echo "❌ 回测失败，退出码：$EXIT_CODE" | tee -a $LOG_FILE
fi

echo "========================================" | tee -a $LOG_FILE
echo "日志文件：$LOG_FILE" | tee -a $LOG_FILE
echo "警报文件：$ALERT_FILE" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# 显示摘要
if [ -f "$STATE_DIR/backtest_progress.json" ]; then
    echo "【回测摘要】" | tee -a $LOG_FILE
    python3.10 -c "
import json
with open('$STATE_DIR/backtest_progress.json') as f:
    d = json.load(f)
print(f'  成功：{len(d.get(\"completed\", []))} 只')
print(f'  失败：{len(d.get(\"failed\", []))} 只')
" | tee -a $LOG_FILE
fi

exit $EXIT_CODE
