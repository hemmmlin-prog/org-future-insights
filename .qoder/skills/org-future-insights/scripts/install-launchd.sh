#!/usr/bin/env bash
# install-launchd.sh · org-future-insights v0.1.1
# 一键安装 launchd 调度，让 fetch_daily.py 在凌晨 6 点自动跑
#
# v0.1.1 修复：
#   • 移除 plist 中的 KeepAlive（避免循环重启 + macOS 14+ 拒绝 NetworkState key）
#   • launchctl load → bootstrap（macOS 11+ 新接口，旧接口已废弃）
#   • 加 plutil -lint 校验，提前发现 plist 写错
#   • 加 set -u 防变量拼错；macOS sed 兼容（虽然本脚本未用 -i，仍标记）
#
# 用法：
#   bash install-launchd.sh             # 安装并立即跑一次测试
#   bash install-launchd.sh --uninstall # 卸载
#   bash install-launchd.sh --status    # 查看状态
#   bash install-launchd.sh --reinstall # 卸载后重装

# v0.1.2 修复：去掉 set -u（macOS 自带 bash 3.2 在某些函数调用后会误判 unbound）
set -eo pipefail

# ---------- 路径 ----------
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLIST_TEMPLATE="$SCRIPT_DIR/com.emma.org-future-insights.plist"
PYTHON_SCRIPT="$SCRIPT_DIR/fetch_daily.py"
LABEL="com.emma.org-future-insights"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
INSTALLED_PLIST="$LAUNCH_AGENTS/$LABEL.plist"

# 项目根目录（组织演变/）
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../../.." && pwd )"
LOG_DIR="$PROJECT_ROOT/daily-raw/_logs"

# launchd 用户域（macOS 11+ 推荐用 gui/<uid>）
USER_UID="$(id -u)"
DOMAIN="gui/$USER_UID"

# ---------- 卸载（兼容新旧 launchctl）----------
do_unload() {
    if [ -f "$INSTALLED_PLIST" ]; then
        # 优先 bootout（新），失败则 fallback 到 unload（旧）
        launchctl bootout "$DOMAIN" "$INSTALLED_PLIST" 2>/dev/null || \
            launchctl unload "$INSTALLED_PLIST" 2>/dev/null || true
    fi
    # 再做一次按 label 卸载（防御性）
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
}

# ---------- 命令分发 ----------
case "${1:-install}" in
    --uninstall)
        echo "→ 卸载 launchd 任务 ..."
        do_unload
        if [ -f "$INSTALLED_PLIST" ]; then
            rm "$INSTALLED_PLIST"
            echo "✅ 已卸载（plist 已删除）"
        else
            echo "⚠️ 未发现已安装的 plist，无需卸载"
        fi
        exit 0
        ;;
    --status)
        echo "→ 检查状态 ..."
        echo ""
        echo "[1] plist 文件："
        if [ -f "$INSTALLED_PLIST" ]; then
            echo "    ✅ 存在：$INSTALLED_PLIST"
            echo "    plutil -lint 校验："
            plutil -lint "$INSTALLED_PLIST" || true
        else
            echo "    ❌ 不存在：$INSTALLED_PLIST"
        fi
        echo ""
        echo "[2] launchctl 注册状态："
        if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
            echo "    ✅ 已注册（domain: $DOMAIN）"
            launchctl print "$DOMAIN/$LABEL" | grep -E "^\s*(state|last exit code|path|program)" || true
        else
            echo "    ❌ 未注册"
        fi
        echo ""
        echo "[3] 最近日志："
        if [ -f "$LOG_DIR/launchd.out.log" ]; then
            echo "    --- launchd.out.log（末 10 行）---"
            tail -10 "$LOG_DIR/launchd.out.log" | sed 's/^/    /'
        else
            echo "    （无 stdout 日志）"
        fi
        if [ -f "$LOG_DIR/launchd.err.log" ] && [ -s "$LOG_DIR/launchd.err.log" ]; then
            echo "    --- launchd.err.log（末 10 行）---"
            tail -10 "$LOG_DIR/launchd.err.log" | sed 's/^/    /'
        fi
        exit 0
        ;;
    --reinstall)
        echo "→ 重装：先卸载 ..."
        do_unload
        rm -f "$INSTALLED_PLIST"
        echo "✅ 旧任务已卸载，继续安装 ..."
        ;;
esac

# ---------- 安装流程 ----------

echo "═══════════════════════════════════════════════════════"
echo "  org-future-insights · launchd 安装器 v0.1.2"
echo "═══════════════════════════════════════════════════════"
echo ""

# 防御性重赋值（防 bash 3.2 函数调用后变量作用域误判）
USER_UID="$(id -u)"
DOMAIN="gui/${USER_UID}"

# 1. 检查 Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ 错误：未找到 python3。请先安装 Python 3（macOS 通常自带）。"
    exit 1
fi
PYTHON_BIN="$(command -v python3)"
echo "✅ 找到 Python：$PYTHON_BIN"

# 2. 检查 plist 模板与抓取脚本
if [ ! -f "$PLIST_TEMPLATE" ]; then
    echo "❌ 错误：未找到 plist 模板：$PLIST_TEMPLATE"
    exit 1
fi
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ 错误：未找到抓取脚本：$PYTHON_SCRIPT"
    exit 1
fi
chmod +x "$PYTHON_SCRIPT"
echo "✅ 抓取脚本就绪：$PYTHON_SCRIPT"

# 3. 准备日志目录
mkdir -p "$LOG_DIR"
echo "✅ 日志目录：$LOG_DIR"

# 4. 先卸载可能的旧版本（防止 bootstrap 报 "service already loaded"）
echo "→ 清理旧版本（如有）..."
do_unload
rm -f "$INSTALLED_PLIST"

# 5. 生成实际 plist（先写到工作区，避开 LaunchAgents 写权限问题）
GENERATED_PLIST="$LOG_DIR/com.emma.org-future-insights.generated.plist"
sed -e "s|__SCRIPT_PATH__|$PYTHON_SCRIPT|g" \
    -e "s|__WORKING_DIR__|$PROJECT_ROOT|g" \
    -e "s|__LOG_DIR__|$LOG_DIR|g" \
    "$PLIST_TEMPLATE" > "$GENERATED_PLIST"
echo "✅ plist 已生成：$GENERATED_PLIST"

# 5b. 校验占位符全部被替换
if grep -q '__SCRIPT_PATH__\|__WORKING_DIR__\|__LOG_DIR__' "$GENERATED_PLIST"; then
    echo "❌ plist 中仍有未替换的占位符，请检查：$GENERATED_PLIST"
    grep -n '__' "$GENERATED_PLIST" || true
    exit 1
fi

# 5c. 拷贝到 LaunchAgents（反验错误，给出明确指引）
mkdir -p "$LAUNCH_AGENTS"
if cp "$GENERATED_PLIST" "$INSTALLED_PLIST" 2>/tmp/cp.err; then
    echo "✅ plist 已拷到：$INSTALLED_PLIST"
else
    echo ""
    echo "❌❌❌ 拷贝失败：macOS 拒绝写入 ~/Library/LaunchAgents/ ❌❌❌"
    echo ""
    cat /tmp/cp.err
    echo ""
    echo "这是 macOS Sonoma/Sequoia 的 App 管理隐私保护。三种解决实验顺序（推荐顺序从上到下）："
    echo ""
    echo "【方案 1：Finder 拖拽（30 秒）】⏬ 最可靠"
    echo "  1）打开 Finder，按 Cmd+Shift+G，输入：~/Library/LaunchAgents/"
    echo "  2）把下面这个文件拖进去（Finder 有权限）："
    echo "     $GENERATED_PLIST"
    echo "  3）重命名为：com.emma.org-future-insights.plist"
    echo "  4）拖完后回终端跑：bash $0 --status【或重跑 --reinstall，脚本会跳过拷贝处理】"
    echo ""
    echo "【方案 2：给终端 App 授权】⏬ 一劳永逸"
    echo "  1）打开 系统设置 → 隐私与安全性 → App 管理 （App Management）"
    echo "  2）点 + 添加你当前用的终端 App（Terminal.app / iTerm2 / Qoder“集成终端”依附的 shell）"
    echo "  3）可能还需加入“完整磁盘访问”（Full Disk Access）"
    echo "  4）重启终端后重跑：bash $0 --reinstall"
    echo ""
    echo "【方案 3：软链绕过（10 秒，临时试探）】⏬ 不推荐但可验证问题范围"
    echo "  ln -sf \"$GENERATED_PLIST\" \"$INSTALLED_PLIST\""
    echo "  （某些 macOS 版本仍会拒绝创建软链，且软链可能被 launchd 抑制）"
    echo ""
    exit 1
fi

# 6. 校验 plist 语法（提前抓错）
if ! plutil -lint "$INSTALLED_PLIST"; then
    echo "❌ plist 语法错误，请检查 $INSTALLED_PLIST"
    exit 1
fi
echo "✅ plist 语法校验通过"

# 7. 注册到 launchd（macOS 11+ 用 bootstrap，旧版用 load 兜底）
echo "→ 注册到 launchd（domain: $DOMAIN）..."
if launchctl bootstrap "$DOMAIN" "$INSTALLED_PLIST" 2>/tmp/launchctl.err; then
    echo "✅ bootstrap 成功"
else
    BOOT_RC=$?
    if [ -s /tmp/launchctl.err ]; then
        echo "⚠️ bootstrap 输出："
        cat /tmp/launchctl.err
    fi
    echo "→ 尝试旧版 launchctl load 兜底..."
    if launchctl load "$INSTALLED_PLIST" 2>&1; then
        echo "✅ load 成功（旧接口）"
    else
        echo "❌ launchd 注册失败（rc=$BOOT_RC）"
        echo "   请把上面错误信息发给我（或检查 macOS 隐私 / 完整磁盘访问权限）"
        exit 1
    fi
fi

# 8. 确认服务可见
echo "→ 校验服务已注册 ..."
if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
    echo "✅ 服务可见：$DOMAIN/$LABEL"
else
    echo "❌ 服务注册后不可见，请用 --status 排查"
    exit 1
fi

# 9. 立即跑一次测试（手动触发，不依赖 RunAtLoad）
echo ""
echo "→ 立即跑一次测试抓取（priority=3，仅⭐⭐⭐源）..."
echo "═══════════════════════════════════════════════════════"
set +e
"$PYTHON_BIN" "$PYTHON_SCRIPT" --priority 3
TEST_RC=$?
set -e
echo "═══════════════════════════════════════════════════════"

if [ $TEST_RC -eq 0 ]; then
    echo ""
    echo "🎉 安装成功！"
else
    echo ""
    echo "⚠️ 测试抓取返回非零码 $TEST_RC（可能部分源失败，正常情况）"
    echo "   plist 仍已注册，明早 06:00 会自动重试"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "调度计划："
echo "  • 每天凌晨 06:00 自动跑（priority>=2）"
echo "  • RunAtLoad=true：开机加载时也会跑一次（防止错过）"
echo ""
echo "输出位置："
echo "  • 抓取数据：$PROJECT_ROOT/daily-raw/YYYY-MM-DD.json"
echo "  • 运行日志：$LOG_DIR/launchd.{out,err}.log"
echo ""
echo "下一步："
echo "  1. 打开 Qoder，在该工作区敲：/org-future-insights --daily"
echo "  2. SKILL 会读取今日抓取结果，生成 ~3000 字深度报告"
echo ""
echo "管理命令："
echo "  bash $0 --status     # 查看状态"
echo "  bash $0 --uninstall  # 卸载"
echo "  bash $0 --reinstall  # 重装"
echo "═══════════════════════════════════════════════════════"
