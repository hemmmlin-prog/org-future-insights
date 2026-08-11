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


# 百炼单次输入上限 30720，留出 system prompt 与模板余量后的安全预算
MAX_PROMPT_CHARS = 24000
# prompt 超预算时的降级梯度：(每源条数, 摘要字符数)
DEGRADE_LADDER = [(10, 300), (8, 220), (6, 160), (5, 110), (4, 80), (3, 60)]


def serialize_items(raw: dict, per_source: int = 10, summary_len: int = 300) -> tuple[str, int, int]:
    """把 raw 的 sources / items 平铺为 prompt 友好的文本，返回（文本，成功源数，items 总数）

    per_source / summary_len 可调，用于 prompt 超长时逐级降级（见 MAX_PROMPT_CHARS）。
    """
    success_sources = [s for s in raw["sources"] if s.get("items_count", 0) > 0]
    total_items = sum(s["items_count"] for s in success_sources)

    chunks = []
    for src in success_sources:
        chunks.append(f"\n### [{src['category']}] {src['name']} ({src['items_count']} items)")
        chunks.append(f"URL: {src['url']}")
        for i, item in enumerate(src["items"][:per_source], 1):
            title = item.get("title", "").strip()
            link = item.get("link", "")
            pub = item.get("pubDate", "")
            summary = (item.get("summary") or "").strip()
            if len(summary) > summary_len:
                summary = summary[:summary_len] + "..."
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

    system_prompt = (PROMPTS_DIR / "role_system.txt").read_text()
    budget = MAX_PROMPT_CHARS - len(system_prompt)

    # 逐级降级，确保 prompt 不超百炼输入上限
    for per_source, summary_len in DEGRADE_LADDER:
        raw_text, success_count, total_items = serialize_items(raw, per_source, summary_len)
        if total_items == 0:
            raise RuntimeError(f"❌ {raw_path.name} 没有任何成功 items，无法生成报告")
        user_prompt = build_user_prompt(raw, raw_text, success_count, total_items)
        if len(user_prompt) <= budget:
            break
        print(f"⚠️  prompt {len(user_prompt)} chars 超预算 {budget}，降级至 每源 {per_source} 条 / 摘要 {summary_len} 字")
    else:
        # 最激进档位仍超限 → 硬截断兜底
        user_prompt = user_prompt[:budget]
        print(f"⚠️  已用最激进档位仍超限，硬截断至 {budget} chars")

    print(f"📊 {success_count} 源成功 / {total_items} 条 items")
    print(f"📝 system={len(system_prompt)} chars | user={len(user_prompt)} chars（预算 {budget}）")

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
