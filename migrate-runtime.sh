#!/usr/bin/env bash
# migrate-runtime.sh · org-future-insights
# 把 launchd 运行时迁出 Desktop（避开 macOS TCC 隐私保护拒绝 python3 访问 Desktop 的问题）
#
# 迁移后的目录布局：
#   ~/org-future-insights/
#       ├── scripts/fetch_daily.py     ← launchd 调用此处
#       ├── daily-raw/                 ← 抓取产物（每日 JSON）
#       │   └── _logs/                 ← launchd stdout/stderr
#
# Desktop 工作区只保留：
#   - SKILL 主目录 .qoder/skills/org-future-insights/（设计文档/模板/源码主版本）
#   - daily-reports/（Agent 生成的分析报告 + Docsify 站点）
#   - _sidebar.md / 知识包正文（与 Docsify 渲染相关）
#
# 用法：bash migrate-runtime.sh

set -eo pipefail

WORKSPACE="/Users/emmah/Desktop/AI学习/Qoder文档/Emmafolder/组织演变"
SCRIPT_SRC="$WORKSPACE/.qoder/skills/org-future-insights/scripts/fetch_daily.py"

RUNTIME_DIR="$HOME/org-future-insights"
RUNTIME_SCRIPTS="$RUNTIME_DIR/scripts"
RUNTIME_RAW="$RUNTIME_DIR/daily-raw"
RUNTIME_LOGS="$RUNTIME_RAW/_logs"

LABEL="com.emma.org-future-insights"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
INSTALLED_PLIST="$LAUNCH_AGENTS/$LABEL.plist"
USER_UID="$(id -u)"
DOMAIN="gui/${USER_UID}"

echo "═══════════════════════════════════════════════════════"
echo "  org-future-insights · 运行时迁出 Desktop（绕开 TCC）"
echo "═══════════════════════════════════════════════════════"
echo ""

# 1. 校验源文件
if [ ! -f "$SCRIPT_SRC" ]; then
    echo "❌ 找不到源脚本：$SCRIPT_SRC"
    exit 1
fi
echo "✅ 源脚本存在：$SCRIPT_SRC"

# 2. 创建运行时目录
echo ""
echo "→ 创建运行时目录 $RUNTIME_DIR ..."
mkdir -p "$RUNTIME_SCRIPTS" "$RUNTIME_RAW" "$RUNTIME_LOGS"
echo "✅ 目录就绪："
ls -ld "$RUNTIME_DIR" "$RUNTIME_SCRIPTS" "$RUNTIME_RAW" "$RUNTIME_LOGS"

# 3. 拷贝抓取脚本
echo ""
echo "→ 拷贝 fetch_daily.py ..."
cp "$SCRIPT_SRC" "$RUNTIME_SCRIPTS/fetch_daily.py"
chmod +x "$RUNTIME_SCRIPTS/fetch_daily.py"
echo "✅ 已拷贝并赋予可执行权限：$RUNTIME_SCRIPTS/fetch_daily.py"

# 4. 卸载旧 launchd 任务
echo ""
echo "→ 卸载旧 launchd 任务（如有）..."
launchctl bootout "$DOMAIN" "$INSTALLED_PLIST" 2>/dev/null || \
    launchctl unload "$INSTALLED_PLIST" 2>/dev/null || true
launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
rm -f "$INSTALLED_PLIST"
echo "✅ 旧任务已清理"

# 5. 生成新 plist（路径全部指向 RUNTIME_DIR + 设置 OFI_PROJECT_ROOT 环境变量）
echo ""
echo "→ 生成新 plist ..."
mkdir -p "$LAUNCH_AGENTS"
cat > "$INSTALLED_PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$RUNTIME_SCRIPTS/fetch_daily.py</string>
        <string>--priority</string>
        <string>2</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>OFI_PROJECT_ROOT</key>
        <string>$RUNTIME_DIR</string>
    </dict>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>WorkingDirectory</key>
    <string>$RUNTIME_DIR</string>

    <key>StandardOutPath</key>
    <string>$RUNTIME_LOGS/launchd.out.log</string>

    <key>StandardErrorPath</key>
    <string>$RUNTIME_LOGS/launchd.err.log</string>

    <key>Nice</key>
    <integer>10</integer>

    <key>ThrottleInterval</key>
    <integer>3600</integer>
</dict>
</plist>
PLIST_EOF
echo "✅ plist 已写入：$INSTALLED_PLIST"

# 6. plist 语法校验
echo ""
echo "→ plist 语法校验 ..."
if ! plutil -lint "$INSTALLED_PLIST"; then
    echo "❌ plist 语法错误"
    exit 1
fi

# 7. 注册到 launchd
echo ""
echo "→ 注册到 launchd（domain: $DOMAIN）..."
if launchctl bootstrap "$DOMAIN" "$INSTALLED_PLIST" 2>/tmp/launchctl.err; then
    echo "✅ bootstrap 成功"
else
    echo "❌ bootstrap 失败："
    cat /tmp/launchctl.err
    exit 1
fi

# 8. 立即触发一次（kickstart）
echo ""
echo "→ 立即触发一次抓取测试 ..."
launchctl kickstart -k "$DOMAIN/$LABEL"
echo "✅ kickstart 已触发，等待 8 秒让脚本跑..."
sleep 8

# 9. 检查结果
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  核实结果"
echo "═══════════════════════════════════════════════════════"

echo ""
echo "[1] launchctl 状态："
launchctl print "$DOMAIN/$LABEL" 2>&1 | grep -E "^\s*(state|last exit code|program|domain)" | head -10

echo ""
echo "[2] 抓取产物（$RUNTIME_RAW）："
ls -lat "$RUNTIME_RAW" | grep -v "^d" | head -5

echo ""
echo "[3] launchd.out.log（末 8 行）："
tail -8 "$RUNTIME_LOGS/launchd.out.log" 2>/dev/null || echo "    （日志为空）"

echo ""
echo "[4] launchd.err.log（应为空表示一切顺利）："
if [ -s "$RUNTIME_LOGS/launchd.err.log" ]; then
    echo "    ⚠️ 有报错："
    tail -10 "$RUNTIME_LOGS/launchd.err.log" | sed 's/^/    /'
else
    echo "    ✅ 无报错"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  迁移完成"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "📍 运行时根目录：$RUNTIME_DIR"
echo "📍 LaunchAgent ：$INSTALLED_PLIST"
echo ""
echo "⚠️ 重要：之后调用 SKILL --daily 时，Agent 应优先从"
echo "   $RUNTIME_RAW/"
echo "   读取最新 raw JSON（已迁出 Desktop）。"
echo ""
echo "如果上面 [4] 显示无报错 + [2] 看到刚抓取的 JSON，则一切正常。"
echo "下次凌晨 6:00 自动跑，无需手动干预。"
