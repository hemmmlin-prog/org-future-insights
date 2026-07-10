#!/bin/bash
# 每日自动化：跑百炼管道 → git commit → git push。由 launchd 06:30 触发。
# 退出码约定（bailian.pipeline）：0 全成功 / 2 部分成功 → 提交；1 全失败 → 跳过。
set -o pipefail
REPO="/Users/emmah/org-future-insights"
cd "$REPO" || exit 1
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:$PATH"
TODAY=$(date +%F)
LOG="$REPO/daily-raw/_logs/daily-auto.$TODAY.log"

{
  echo "===== daily-auto $TODAY $(date +%T) ====="
  /usr/bin/python3 -m bailian.pipeline "$TODAY"
  code=$?
  echo "pipeline exit code: $code"
  if [ "$code" -eq 1 ]; then
    echo "❌ pipeline 全失败，跳过提交与推送"
    git checkout -- . 2>/dev/null  # 清理部分阶段留下的残留（如指向缺失报告的死链侧边栏）
    exit 1
  fi
  git add -A
  if git diff --cached --quiet; then
    echo "ℹ️ 无变更，无需提交"
    exit 0
  fi
  git commit -m "auto: daily pipeline $TODAY (exit=$code)"
  if git push origin main; then
    echo "✅ push 成功"
  else
    echo "⚠️ push 失败——请检查钥匙串中的 GitHub PAT 是否有效"
    exit 3
  fi
} >> "$LOG" 2>&1
