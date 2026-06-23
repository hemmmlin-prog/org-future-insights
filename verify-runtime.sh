#!/usr/bin/env bash
# verify-runtime.sh · org-future-insights
# 强制 kickstart launchd 任务 + 等 60 秒 + 5 项核实
# 用法：bash verify-runtime.sh

set -eo pipefail

LABEL="com.emma.org-future-insights"
USER_UID="$(id -u)"
DOMAIN="gui/${USER_UID}"
RUNTIME_DIR="$HOME/org-future-insights"

echo "═══════════════════════════════════════════════════════"
echo "  org-future-insights · 抓取验证（kickstart + 60s 等待）"
echo "═══════════════════════════════════════════════════════"
echo ""

echo "→ 强制重启任务（kickstart -k）..."
launchctl kickstart -k "$DOMAIN/$LABEL"
echo "✅ 已触发"
echo ""

echo "⏳ 等 60 秒抓取（24 个 RSS 源约需 30-60 秒）..."
for i in 1 2 3 4 5 6; do
    sleep 10
    JSON_COUNT=$(ls "$RUNTIME_DIR/daily-raw/"*.json 2>/dev/null | wc -l | tr -d ' ')
    OUT_SIZE=$(wc -c < "$RUNTIME_DIR/daily-raw/_logs/launchd.out.log" 2>/dev/null | tr -d ' ' || echo 0)
    echo "  ...已等 $((i*10))s  | JSON 数: $JSON_COUNT  | out.log: ${OUT_SIZE}B"
done

echo ""
echo "═══ 核实结果 ═══"
echo ""

echo "[1] launchctl list（PID Status Label）："
launchctl list | grep org-future || echo "  ⚠️ 未注册"
echo ""

echo "[2] last exit code（应为 0）："
launchctl print "$DOMAIN/$LABEL" 2>&1 | grep -E "^\s*(state|last exit code)" || echo "  ⚠️ 服务不可见"
echo ""

echo "[3] 抓取产物："
ls -la "$RUNTIME_DIR/daily-raw/" | grep -v "^d" | grep -v "^total"
echo ""

echo "[4] out.log（末 8 行）："
if [ -s "$RUNTIME_DIR/daily-raw/_logs/launchd.out.log" ]; then
    tail -8 "$RUNTIME_DIR/daily-raw/_logs/launchd.out.log"
else
    echo "  ⚠️ out.log 为空"
fi
echo ""

echo "[5] err.log（应为空）："
if [ -s "$RUNTIME_DIR/daily-raw/_logs/launchd.err.log" ]; then
    echo "  ⚠️ 有内容："
    tail -10 "$RUNTIME_DIR/daily-raw/_logs/launchd.err.log" | sed 's/^/    /'
else
    echo "  ✅ 空（完美）"
fi
echo ""

echo "═══════════════════════════════════════════════════════"
LATEST=$(ls -t "$RUNTIME_DIR/daily-raw/"*.json 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
    echo "🎉 抓取成功！最新 JSON："
    ls -la "$LATEST"
    echo ""
    python3 -c "
import json
d=json.load(open('$LATEST'))
print(f\"  sources_count: {d.get('sources_count','?')}\")
print(f\"  success: {d.get('success','?')}\")
print(f\"  failure: {d.get('failure','?')}\")
print(f\"  items: {len(d.get('items',[]))}\")
" 2>/dev/null || echo "  （无法解析 JSON 摘要）"
else
    echo "⚠️ 仍无 JSON 产物。请把上面 [1]-[5] 输出贴给 AI 进一步诊断。"
fi
echo "═══════════════════════════════════════════════════════"
