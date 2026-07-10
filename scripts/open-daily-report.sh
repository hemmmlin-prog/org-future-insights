#!/bin/bash
# open-daily-report.sh
# 每日自动打开最新可视化日报 + macOS 通知
# 由 launchd 每 5 分钟检查一次，仅在 06:30-10:00 首次触发

HOUR=$(date +%H)
MINUTE=$(date +%M)
FLAG_DIR="/Users/emmah/org-future-insights/daily-raw/_logs"
TODAY=$(date +%Y-%m-%d)
FLAG_FILE="$FLAG_DIR/.notify-${TODAY}"

# ── 时间门控：仅 06:30 ~ 10:00 执行 ──
CURRENT_MIN=$((HOUR * 60 + MINUTE))
if [ "$CURRENT_MIN" -lt 390 ] || [ "$CURRENT_MIN" -ge 600 ]; then
    # 390 = 6*60+30, 600 = 10*60
    exit 0
fi

# ── 今天已通知过则跳过 ──
if [ -f "$FLAG_FILE" ]; then
    exit 0
fi

# ── 确定最新可视化日报 ──
PROJECT_DIR="/Users/emmah/org-future-insights"
VISUAL_FILE="$PROJECT_DIR/daily-reports/${TODAY}-visual.md"

if [ -f "$VISUAL_FILE" ]; then
    DATE="$TODAY"
else
    LATEST=$(ls -t "$PROJECT_DIR/daily-reports/"*-visual.md 2>/dev/null | head -1)
    if [ -n "$LATEST" ]; then
        DATE=$(basename "$LATEST" | sed 's/-visual.md//')
    else
        # 无任何可视化日报，静默退出
        exit 0
    fi
fi

# ── 启动本地服务（如果未运行）──
if ! lsof -i:3000 >/dev/null 2>&1; then
    cd "$PROJECT_DIR" && nohup ./serve.sh >/dev/null 2>&1 &
    sleep 3
fi

# ── 打开 Chrome ──
open -a "Google Chrome" "http://localhost:3000/#/daily-reports/${DATE}-visual"

# ── 发送 macOS 通知 ──
osascript -e "display notification \"${DATE} HR 洞察日报已就绪，已在 Chrome 打开\" with title \"📊 组织演变 · 今日日报\" subtitle \"点击查看可视化版\""

# ── 标记今日已通知 ──
mkdir -p "$FLAG_DIR"
touch "$FLAG_FILE"

echo "[$(date)] ✅ 已打开日报 ${DATE}-visual 并发送通知" >> "$FLAG_DIR/notify.log"
