"""
bailian/track_cases.py — G 任务：公司转型案例重点跟踪页

解决的问题：cases/auto-*.md 案例池被 RSS 循环推送的旧内容霸榜（YC IPO 系列、
HBS 2024 年旧文等连续 7-8 天在榜），真正的新案例被噪音掩盖。

做法：
1. 扫描近 WINDOW_DAYS 天的案例池，按链接聚合同一案例的多日出现
2. 按原文发布日期做新鲜度过滤：≤ FRESH_DAYS 天为「重点跟踪」，更早为「复读存档」
3. 输出 cases/tracking-ai-native.md：重点跟踪清单 + 本期新增 + 复读存档（透明列出噪音源）

用法：
    python3 -m bailian.track_cases                 # 用今天
    python3 -m bailian.track_cases 2026-08-18
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from bailian.generate_daily import WORKSPACE

CASES_DIR = WORKSPACE / "cases"
OUT_PATH = CASES_DIR / "tracking-ai-native.md"
WINDOW_DAYS = 30      # 扫描多少天的案例池
FRESH_DAYS = 14       # 原文发布距基准日多少天内算「新鲜」

# 已核实的公司/行业标注（来自案例原文摘要，未核实的留空不臆测）
CURATED_META = {
    "ringcentral": ("RingCentral", "通信 SaaS", "工程→运营全职能"),
    "astrazeneca": ("AstraZeneca", "制药 R&D", "科研智能体系统"),
    "github": ("GitHub", "开发者平台", "法务职能流程"),
    "model ml": ("Model ML", "金融科技", "财务职能"),
    "cathay united bank": ("国泰世华银行", "银行业", "客户中心创新"),
    "joseph tsai": ("国泰世华银行", "银行业", "客户中心创新"),
    "univé": ("Univé", "保险业", "全员 AI 就绪"),
    "unive": ("Univé", "保险业", "全员 AI 就绪"),
    "avatarin": ("avatarin", "零售", "24/7 服务智能体"),
    "lion finance": ("Lion Finance", "银行业", "fintech 化竞争"),
}

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _parse_pub(raw: str) -> datetime | None:
    """解析案例条目里的发布日期，兼容 RFC822 / ISO / '2026-07-31 16:12:09 +0800' 三类格式"""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt:
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except (TypeError, ValueError, IndexError):
        pass
    m = DATE_RE.search(raw)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            return None
    return None


def _cell(text: str, limit: int = 0) -> str:
    """表格单元格安全化：转义竖线并按需截断（标题含 | 会破坏 markdown 表格）"""
    t = (text or "").replace("|", "\\|").strip()
    return t[:limit] + "…" if limit and len(t) > limit else t


def _meta_for(title: str, reason: str) -> tuple[str, str, str]:
    """按已核实清单匹配公司/行业/改造范围，未命中则留空"""
    blob = f"{title} {reason}".lower()
    for key, meta in CURATED_META.items():
        if key in blob:
            return meta
    return ("—", "—", "—")


def collect(ref_date: str) -> tuple[list[dict], list[dict]]:
    """返回（重点跟踪案例, 复读存档案例），均按在榜天数与发布时间排序"""
    ref = datetime.strptime(ref_date, "%Y-%m-%d")
    start = ref - timedelta(days=WINDOW_DAYS)

    agg: dict[str, dict] = {}
    for f in sorted(CASES_DIR.glob("auto-*.md")):
        m = DATE_RE.search(f.name)
        if not m:
            continue
        file_date = datetime.strptime(m.group(1), "%Y-%m-%d")
        if not (start <= file_date <= ref):
            continue
        for blk in re.split(r"^### \d+\. ", f.read_text(), flags=re.M)[1:]:
            title = blk.splitlines()[0].strip()
            src = re.search(r"\*\*来源\*\*：(.+)", blk)
            link = re.search(r"\*\*链接\*\*：(\S+)", blk)
            pub = re.search(r"\*\*发布\*\*：(.+)", blk)
            reason = re.search(r"\*\*归类理由\*\*：(.+)", blk)
            key = link.group(1) if link else title
            rec = agg.setdefault(key, {
                "title": title,
                "source": src.group(1).strip() if src else "—",
                "link": link.group(1) if link else "",
                "pub": _parse_pub(pub.group(1) if pub else ""),
                "reason": reason.group(1).strip() if reason else "",
                "dates": [],
            })
            rec["dates"].append(m.group(1))

    fresh, stale = [], []
    for rec in agg.values():
        rec["dates"] = sorted(set(rec["dates"]))
        rec["first_seen"] = rec["dates"][0]
        rec["last_seen"] = rec["dates"][-1]
        rec["days"] = len(rec["dates"])
        rec["company"], rec["industry"], rec["scope"] = _meta_for(rec["title"], rec["reason"])
        pub = rec["pub"]
        rec["pub_str"] = pub.strftime("%Y-%m-%d") if pub else "未知"
        rec["age"] = (ref - pub).days if pub else None
        (fresh if (rec["age"] is not None and rec["age"] <= FRESH_DAYS) else stale).append(rec)

    fresh.sort(key=lambda r: (-r["days"], r["age"]))
    stale.sort(key=lambda r: -r["days"])
    return fresh, stale


def build_page(ref_date: str) -> Path:
    fresh, stale = collect(ref_date)
    new_today = [r for r in fresh if r["first_seen"] == ref_date]

    lines = [
        "# 📊 公司转型案例 · 重点跟踪",
        "",
        f"> **更新时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')} · 每日随 pipeline 自动刷新",
        f"> **跟踪规则**：扫描近 {WINDOW_DAYS} 天案例池，原文发布 ≤ {FRESH_DAYS} 天为重点跟踪；"
        f"更早的 RSS 循环推送内容降入文末复读存档",
        f"> **本期**：重点跟踪 **{len(fresh)}** 个 · 今日新增 **{len(new_today)}** 个 · 复读存档 {len(stale)} 个",
        "",
        "---",
        "",
        "## 🔥 重点跟踪清单",
        "",
    ]
    if fresh:
        lines += [
            "| 案例 | 公司 | 行业 | 改造范围 | 原文发布 | 在榜 | 首次→最新 | 来源 |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in fresh:
            label = _cell(r["title"], 48)
            t = f"[{label}]({r['link']})" if r["link"] else label
            span = r["first_seen"][5:] if r["days"] == 1 else f"{r['first_seen'][5:]}→{r['last_seen'][5:]}"
            lines.append(
                f"| {t} | **{r['company']}** | {r['industry']} | {r['scope']} | "
                f"{r['pub_str']} | {r['days']} 天 | {span} | {r['source']} |"
            )
    else:
        lines.append("_本期无新鲜案例（近期案例池均为循环推送内容）。_")

    lines += ["", "---", "", "## 🆕 今日新增", ""]
    if new_today:
        for r in new_today:
            lines.append(f"### {r['title']}")
            lines.append("")
            lines.append(f"- **公司 / 行业**：{r['company']} · {r['industry']}")
            lines.append(f"- **来源**：{r['source']} · 原文发布 {r['pub_str']}")
            if r["link"]:
                lines.append(f"- **链接**：{r['link']}")
            if r["reason"]:
                lines.append(f"- **入选理由**：{r['reason']}")
            lines.append("")
    else:
        lines.append("_今日无新增案例。_")

    lines += [
        "", "---", "",
        "## 🗂️ 复读存档（RSS 循环推送，不计入重点跟踪）", "",
        f"> 以下条目原文发布已超过 {FRESH_DAYS} 天但仍被信源反复推送，"
        "列出以便识别噪音来源，不作为新案例跟踪。", "",
    ]
    if stale:
        lines += ["| 案例 | 原文发布 | 在榜天数 | 来源 |", "|---|---|---|---|"]
        for r in stale:
            lines.append(f"| {_cell(r['title'], 52)} | {r['pub_str']} | {r['days']} 天 | {r['source']} |")
    else:
        lines.append("_无。_")

    lines += [
        "", "---", "",
        "> 📐 本页由 `bailian/track_cases.py` 基于 cases/auto-*.md 本地聚合生成，零 API 成本。",
        "",
    ]
    OUT_PATH.write_text("\n".join(lines))
    print(f"  📊 案例跟踪页已刷新 → {OUT_PATH.relative_to(WORKSPACE)}"
          f"（重点 {len(fresh)} · 新增 {len(new_today)} · 存档 {len(stale)}）")
    return OUT_PATH


def main(date: str | None = None) -> dict:
    ref = date or datetime.now().strftime("%Y-%m-%d")
    fresh, stale = collect(ref)
    build_page(ref)
    return {"tracked": len(fresh), "archived": len(stale),
            "new_today": len([r for r in fresh if r["first_seen"] == ref])}


if __name__ == "__main__":
    try:
        print(f"\n🎯 案例跟踪汇总: {main(sys.argv[1] if len(sys.argv) > 1 else None)}")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
