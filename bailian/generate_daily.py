"""
bailian/generate_daily.py — A 任务：基于 raw JSON 全自动生成日报

用法：
    python3 -m bailian.generate_daily                                # 用最新 raw
    python3 -m bailian.generate_daily 2026-06-14                     # 指定日期
    python3 -m bailian.generate_daily --model qwen-plus              # 指定模型

输出：
    daily-reports/YYYY-MM-DD-auto.md
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from bailian.client import chat, DEFAULT_MODEL

WORKSPACE = Path(__file__).resolve().parent.parent  # 仓库根目录（bailian/ 上一级），随仓库位置自动适配
RUNTIME = Path.home() / "org-future-insights"
RAW_DIR = RUNTIME / "daily-raw"
LOG_DIR = RAW_DIR / "_logs"
REPORT_DIR = WORKSPACE / "daily-reports"
PROMPTS_DIR = Path(__file__).parent / "prompts"

LOG_DIR.mkdir(parents=True, exist_ok=True)


def find_latest_raw() -> Path:
    """找最新的 raw JSON 文件"""
    files = sorted(RAW_DIR.glob("20*-*-*.json"), reverse=True)
    if not files:
        raise FileNotFoundError(f"❌ {RAW_DIR} 下没有 raw JSON")
    return files[0]


def find_raw_by_date(date_str: str) -> Path:
    """按日期找 raw"""
    f = RAW_DIR / f"{date_str}.json"
    if not f.exists():
        raise FileNotFoundError(f"❌ {f} 不存在")
    return f


def serialize_items(raw: dict) -> tuple[str, int, int]:
    """把 raw 的 sources / items 平铺为 prompt 友好的文本，返回（文本，成功源数，items 总数）"""
    success_sources = [s for s in raw["sources"] if s.get("items_count", 0) > 0]
    total_items = sum(s["items_count"] for s in success_sources)

    chunks = []
    for src in success_sources:
        chunks.append(f"\n### [{src['category']}] {src['name']} ({src['items_count']} items)")
        chunks.append(f"URL: {src['url']}")
        for i, item in enumerate(src["items"][:10], 1):  # 最多 10 条/源
            title = item.get("title", "").strip()
            link = item.get("link", "")
            pub = item.get("pubDate", "")
            summary = (item.get("summary") or "").strip()
            # 摘要限制 300 字符以控制 token
            if len(summary) > 300:
                summary = summary[:300] + "..."
            chunks.append(f"\n{i}. **{title}**")
            chunks.append(f"   - 链接: {link}")
            chunks.append(f"   - 发布: {pub}")
            chunks.append(f"   - 摘要: {summary}")

    return "\n".join(chunks), len(success_sources), total_items


def build_user_prompt(raw: dict, raw_text: str, success_count: int, total_items: int) -> str:
    """填充 daily_report.txt 模板"""
    template = (PROMPTS_DIR / "daily_report.txt").read_text()
    snapshot = raw.get("snapshot_time", "")
    date_str = snapshot.split("T")[0] if "T" in snapshot else datetime.now().strftime("%Y-%m-%d")
    return (
        template
        .replace("{DATE}", date_str)
        .replace("{SNAPSHOT_TIME}", snapshot)
        .replace("{SUCCESS_COUNT}", str(success_count))
        .replace("{TOTAL_ITEMS}", str(total_items))
        .replace("{RAW_ITEMS}", raw_text)
    )


def log_cost(date: str, resp_dict: dict, mode: str = "daily"):
    """记录 token 消耗"""
    log_file = LOG_DIR / "bailian.cost.log"
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "date": date,
        "mode": mode,
        **resp_dict,
    }
    with log_file.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main(date: str | None = None, model: str = DEFAULT_MODEL) -> Path:
    raw_path = find_raw_by_date(date) if date else find_latest_raw()
    print(f"📂 读取 raw: {raw_path.name}")
    raw = json.loads(raw_path.read_text())

    raw_text, success_count, total_items = serialize_items(raw)
    if total_items == 0:
        raise RuntimeError(f"❌ {raw_path.name} 没有任何成功 items，无法生成报告")

    print(f"📊 {success_count} 源成功 / {total_items} 条 items")

    system_prompt = (PROMPTS_DIR / "role_system.txt").read_text()
    user_prompt = build_user_prompt(raw, raw_text, success_count, total_items)
    print(f"📝 system={len(system_prompt)} chars | user={len(user_prompt)} chars")

    print(f"🚀 调用百炼 {model}（预计 30-60s）...")
    resp = chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=model,
        temperature=0.5,
        max_tokens=8000,
    )
    print(f"✅ 生成完成 | tokens: {resp.input_tokens}→{resp.output_tokens} (total {resp.total_tokens}) | {resp.elapsed_sec:.1f}s")

    # 保存报告
    date_str = raw_path.stem  # e.g., 2026-06-14
    report_path = REPORT_DIR / f"{date_str}-auto.md"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(resp.text)
    print(f"💾 已写入: {report_path.relative_to(WORKSPACE)}")

    # 记日志
    log_cost(date_str, resp.to_dict(), mode="daily")
    return report_path


if __name__ == "__main__":
    args = sys.argv[1:]
    date = None
    model = DEFAULT_MODEL
    i = 0
    while i < len(args):
        if args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]
            i += 2
        else:
            date = args[i]
            i += 1
    try:
        main(date=date, model=model)
        sys.exit(0)
    except Exception as e:
        print(f"❌ 失败: {e}", file=sys.stderr)
        sys.exit(1)
