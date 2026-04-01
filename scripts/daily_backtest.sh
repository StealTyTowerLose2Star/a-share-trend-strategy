#!/bin/bash
# 每日自动回测任务启动脚本
# 配置到 crontab，每日 00:00 运行

# 环境变量
export PATH=/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin
export PYTHONIOENCODING=utf-8

# 项目目录
PROJECT_DIR="/home/admin/.openclaw/workspace/a-share-trend-strategy"
LOG_DIR="$PROJECT_DIR/logs"
DATE=$(date +%Y%m%d)
LOG_FILE="$LOG_DIR/backtest_$DATE.log"

# 创建日志目录
mkdir -p $LOG_DIR

# 打印启动信息
echo "========================================" | tee -a $LOG_FILE
echo "启动时间：$(date '+%Y-%m-%d %H:%M:%S')" | tee -a $LOG_FILE
echo "回测任务启动" | tee -a $LOG_FILE
echo "========================================" | tee -a $LOG_FILE

# 进入项目目录
cd $PROJECT_DIR

# 运行回测（4 线程并行）
echo "" | tee -a $LOG_FILE
echo "开始回测..." | tee -a $LOG_FILE

python3.10 scripts/run_backtest_parallel.py \
    --workers 4 \
    >> $LOG_FILE 2>&1

EXIT_CODE=$?

# 打印完成信息
echo "" | tee -a $LOG_FILE
echo "========================================" | tee -a $LOG_FILE
echo "完成时间：$(date '+%Y-%m-%d %H:%M:%S')" | tee -a $LOG_FILE

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 回测成功完成" | tee -a $LOG_FILE
else
    echo "❌ 回测失败，退出码：$EXIT_CODE" | tee -a $LOG_FILE
fi

echo "========================================" | tee -a $LOG_FILE
echo "日志文件：$LOG_FILE" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# 发送通知（可选，需要配置飞书 webhook）
# curl -X POST "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK" \
#   -H "Content-Type: application/json" \
#   -d "{\"msg_type\":\"text\",\"content\":{\"text\":\"回测任务完成\"}}"

exit $EXIT_CODE
