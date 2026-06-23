#!/usr/bin/env bash
# serve.sh · org-future-insights Docsify 本地站点启动器
# 用法：bash serve.sh
# 之后浏览器访问 http://localhost:3000

set -eo pipefail

PORT="${PORT:-3000}"
HOST="${HOST:-localhost}"
WORKSPACE="$(cd "$(dirname "$0")" && pwd)"

echo "═══════════════════════════════════════════════════════"
echo "  组织演变 · Docsify 本地站点"
echo "═══════════════════════════════════════════════════════"
echo "  📂 站点根目录：$WORKSPACE"
echo "  🌐 访问地址：http://$HOST:$PORT"
echo "  ⏹️  停止方式：Ctrl+C"
echo "═══════════════════════════════════════════════════════"
echo ""

# 检查端口占用
if lsof -i ":$PORT" &>/dev/null; then
    echo "⚠️ 端口 $PORT 已被占用，正在尝试 $((PORT+1))..."
    PORT=$((PORT+1))
fi

# 优先用 python3，回退到 python
if command -v python3 &>/dev/null; then
    SERVER="python3 -m http.server $PORT --bind $HOST"
elif command -v python &>/dev/null; then
    SERVER="python -m SimpleHTTPServer $PORT"
else
    echo "❌ 系统未安装 python3，请先安装 Python 3"
    exit 1
fi

cd "$WORKSPACE"
echo "→ 启动命令：$SERVER"
echo "→ 浏览器自动打开 http://$HOST:$PORT ..."
echo ""

# 后台 5 秒后打开浏览器
( sleep 2 && open "http://$HOST:$PORT" 2>/dev/null ) &

exec $SERVER
