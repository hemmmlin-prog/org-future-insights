"""
bailian/classify_to_modules.py — B 任务：raw items 自动分流到 8 板块

每个板块每天生成一份聚合文件 `<module>/auto-YYYY-MM-DD.md`，
包含分类到该板块的所有素材清单 + 归类理由。

用法：
    python3 -m bailian.classify_to_modules                  # 用最新 raw
    python3 -m bailian.classify_to_modules 2026-06-14
    python3 -m bailian.classify_to_modules --model qwen-plus
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from bailian.client import chat, DEFAULT_MODEL
from bailian.generate_daily import (
    find_latest_raw, find_raw_by_date, log_cost, RAW_DIR, LOG_DIR, WORKSPACE, PROMPTS_DIR
)

BATCH_SIZE = 20  # 每批 20 条 items

# 8 个板块的目录映射
MODULE_DIRS = {
    "companies": WORKSPACE / "companies",
    "research": WORKSPACE / "research",
    "cases": WORKSPACE / "cases",
    "readings": WORKSPACE / "readings",
    "dictionary": WORKSPACE / "dictionary",
    "dashboard": WORKSPACE / "dashboard",
    "events": WORKSPACE / "events",
    "daily_only": None,  # 兜底，不写文件
}


def flatten_items(raw: dict) -> list[dict]:
    """把所有 sources 的 items 平铺为一个列表，带 source 元数据"""
    flat = []
    for src in raw["sources"]:
        if src.get("items_count", 0) == 0:
            continue
        for item in src["items"]:
            flat.append({
                "category": src["category"],
                "source": src["name"],
                "title": (item.get("title") or "").strip(),
                "link": item.get("link", ""),
                "pubDate": item.get("pubDate", ""),
                "summary": (item.get("summary") or "").strip()[:400],
            })
    return flat


def serialize_batch(items: list[dict], start_idx: int) -> str:
    """序列化一批 items 给 qwen"""
    lines = []
    for i, item in enumerate(items, start=start_idx):
        lines.append(f"\n[{i}] [{item['category']}] {item['source']}")
        lines.append(f"  标题: {item['title']}")
        s = item['summary']
        if len(s) > 250:
            s = s[:250] + "..."
        lines.append(f"  摘要: {s}")
    return "\n".join(lines)


def classify_batch(batch: list[dict], start_idx: int, model: str) -> list[dict]:
    """对一批 items 调 qwen 做分类，返回 [{index, module_tags, reason}]"""
    template = (PROMPTS_DIR / "classify.txt").read_text()
    items_text = serialize_batch(batch, start_idx)
    user_prompt = template.replace("{BATCH_SIZE}", str(len(batch))).replace("{ITEMS_BATCH}", items_text)

    system_msg = "你是 HR 内容编辑，负责把信源素材按 8 个板块做多标签分类。严格输出合法 JSON，无任何前后说明文字。"

    resp = chat(
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt},
        ],
        model=model,
        temperature=0.2,  # 分类要稳定
        max_tokens=4000,
        response_format={"type": "json_object"},
    )
    log_cost(datetime.now().strftime("%Y-%m-%d"), resp.to_dict(), mode=f"classify_batch_{start_idx}")

    try:
        data = json.loads(resp.text)
        return data.get("classifications", [])
    except json.JSONDecodeError as e:
        print(f"⚠️ 第 {start_idx} 批 JSON 解析失败: {e}")
        print(f"   原文前 300 字符: {resp.text[:300]}")
        return []


def write_module_aggregate(
    module: str, items: list[dict], date_str: str
):
    """为某板块写聚合文件 <module>/auto-YYYY-MM-DD.md"""
    if module == "daily_only" or not items:
        return
    target_dir = MODULE_DIRS.get(module)
    if not target_dir:
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    out = target_dir / f"auto-{date_str}.md"

    title_map = {
        "companies": "🏢 公司 & 关键人",
        "research": "🎓 报告 & 研究",
        "cases": "📊 转型案例",
        "readings": "📚 延伸阅读",
        "dictionary": "🧭 HR 词典素材池",
        "dashboard": "📈 数据看板素材池",
        "events": "📅 行业议程",
    }

    lines = [
        f"# {title_map.get(module, module)} · {date_str}（自动分流）",
        "",
        f"> 本文由百炼 qwen 自动从当日 raw JSON 分流而来，共 **{len(items)}** 条相关素材。",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
    ]
    for i, item in enumerate(items, 1):
        lines.append(f"### {i}. {item['title']}")
        lines.append("")
        lines.append(f"- **来源**：[{item['category']}] {item['source']}")
        lines.append(f"- **链接**：{item['link']}")
        lines.append(f"- **发布**：{item['pubDate']}")
        lines.append(f"- **归类理由**：{item.get('reason', '—')}")
        if item.get("module_tags"):
            tags = ", ".join(f"`{t}`" for t in item["module_tags"])
            lines.append(f"- **多标签**：{tags}")
        lines.append("")
        s = item['summary']
        if s:
            lines.append("**摘要**：")
            lines.append("")
            lines.append(f"> {s}")
            lines.append("")
        lines.append("---")
        lines.append("")
    out.write_text("\n".join(lines))
    print(f"  💾 {module:12s} → {out.relative_to(WORKSPACE)} ({len(items)} 条)")


def main(date: str | None = None, model: str = DEFAULT_MODEL) -> dict[str, int]:
    raw_path = find_raw_by_date(date) if date else find_latest_raw()
    print(f"📂 读取 raw: {raw_path.name}")
    raw = json.loads(raw_path.read_text())
    date_str = raw_path.stem

    flat_items = flatten_items(raw)
    if not flat_items:
        raise RuntimeError(f"❌ 没有可分流的 items")
    print(f"📊 待分流: {len(flat_items)} 条 items")

    # 分批分类
    all_classifications = {}  # index -> {module_tags, reason}
    for batch_start in range(0, len(flat_items), BATCH_SIZE):
        batch = flat_items[batch_start:batch_start + BATCH_SIZE]
        start_idx = batch_start + 1
        print(f"🔄 分类批 [{start_idx}-{start_idx + len(batch) - 1}] / {len(flat_items)}")
        results = classify_batch(batch, start_idx, model)
        for r in results:
            idx = r.get("index")
            if idx is not None and 1 <= idx <= len(flat_items):
                all_classifications[idx] = {
                    "module_tags": r.get("module_tags", []),
                    "reason": r.get("reason", ""),
                }

    print(f"✅ 已分类 {len(all_classifications)}/{len(flat_items)} 条")

    # 按 module 聚合
    valid_modules = set(MODULE_DIRS.keys())
    by_module: dict[str, list[dict]] = defaultdict(list)
    for i, item in enumerate(flat_items, 1):
        cls = all_classifications.get(i)
        if not cls:
            by_module["daily_only"].append({**item, "module_tags": ["daily_only"], "reason": "未分类（兜底）"})
            continue
        # qwen 偶尔会返回字符串而非数组，统一兜成 list
        raw_tags = cls.get("module_tags", [])
        if isinstance(raw_tags, str):
            tags = [raw_tags]
        elif isinstance(raw_tags, list):
            tags = [t for t in raw_tags if isinstance(t, str)]
        else:
            tags = []
        # 过滤未知 module 名
        tags = [t for t in tags if t in valid_modules]
        if not tags:
            tags = ["daily_only"]
        for tag in tags:
            by_module[tag].append({**item, "module_tags": tags, "reason": cls.get("reason", "")})

    # 写文件
    print(f"\n📝 按 8 板块写入聚合文件...")
    summary = {}
    for module, items in by_module.items():
        write_module_aggregate(module, items, date_str)
        summary[module] = len(items)
    return summary


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
        summary = main(date=date, model=model)
        print(f"\n🎯 分流汇总: {summary}")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
