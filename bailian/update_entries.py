"""
bailian/update_entries.py — F 任务：板块入口保鲜（导航/侧边栏/README/看板快照）

保证站点各板块入口至少周维度保持最新：
1. 看板快照：最新 snapshot 超过 7 天 → 基于近 7 天素材池 + 日报共识矩阵本地聚合重新生成（零 API 成本）
2. _navbar.md：日报 / 数据 / 议程 三个日期型入口自动指向最新文件
3. _sidebar.md：数据看板分组置顶最新快照（⭐），旧快照自动降级
4. 板块 README（companies/research/cases/readings）：维护「最新自动分流」区块，列最近 7 期

用法：
    python3 -m bailian.update_entries                # 用今天日期
    python3 -m bailian.update_entries 2026-07-25
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from bailian.generate_daily import WORKSPACE, REPORT_DIR
from bailian.track_cases import main as run_track_cases

DASHBOARD_DIR = WORKSPACE / "dashboard"
NAVBAR_PATH = WORKSPACE / "_navbar.md"
SIDEBAR_PATH = WORKSPACE / "_sidebar.md"
SNAPSHOT_MAX_AGE_DAYS = 7
README_MODULES = ["companies", "research", "cases", "readings"]
AUTO_BEGIN = "<!-- AUTO-LATEST:BEGIN -->"
AUTO_END = "<!-- AUTO-LATEST:END -->"

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _date_of(path: Path) -> str | None:
    m = DATE_RE.search(path.name)
    return m.group(1) if m else None


def _latest_by_date(paths: list[Path]) -> Path | None:
    dated = [(d, p) for p in paths if (d := _date_of(p))]
    return max(dated)[1] if dated else None


# ─────────────────── 1. 看板快照周更 ───────────────────

def parse_source_stats(date_str: str) -> str | None:
    """从当日 auto 日报头部提取「N 源成功 / M 条 items」"""
    report = REPORT_DIR / f"{date_str}-auto.md"
    if not report.exists():
        autos = sorted(REPORT_DIR.glob("*-auto.md"))
        if not autos:
            return None
        report = autos[-1]
    m = re.search(r"(\d+)\s*源成功\s*/\s*(\d+)\s*条", report.read_text())
    return f"{m.group(1)} 源 / {m.group(2)} 条 items（{report.stem.replace('-auto','')}）" if m else None


def collect_consensus_rows(window_dates: list[str]) -> list[tuple[str, str, str, int, str]]:
    """收集窗口内日报共识矩阵行 (议题, 资本立场, 学术立场, 共识%, 日期)，同议题保留最新"""
    rows: dict[str, tuple[str, str, str, int, str]] = {}
    for d in window_dates:  # 从旧到新，新的覆盖旧的
        report = REPORT_DIR / f"{d}-auto.md"
        if not report.exists():
            continue
        for line in report.read_text().splitlines():
            m = re.match(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)%\s*\|$", line)
            if m and "议题" not in m.group(1) and "---" not in m.group(1):
                topic = m.group(1).replace("*", "").strip()  # 去除源表格残留的加粗符号
                rows[topic] = (topic, m.group(2), m.group(3), int(m.group(4)), d[5:].replace("-", "/"))
    return sorted(rows.values(), key=lambda r: -r[3])


def collect_pool_items(window_dates: list[str]) -> list[tuple[str, str, str, str]]:
    """收集窗口内看板素材池条目 (标题, 来源, 链接, 日期)，按链接去重"""
    items: dict[str, tuple[str, str, str, str]] = {}
    for d in window_dates:
        pool = DASHBOARD_DIR / f"auto-{d}.md"
        if not pool.exists():
            continue
        text = pool.read_text()
        for block in re.split(r"^### \d+\. ", text, flags=re.M)[1:]:
            title = block.splitlines()[0].strip()
            src = re.search(r"\*\*来源\*\*：(.+)", block)
            link = re.search(r"\*\*链接\*\*：(\S+)", block)
            key = link.group(1) if link else title
            items[key] = (title, src.group(1).strip() if src else "—",
                          link.group(1) if link else "", d[5:].replace("-", "/"))
    return list(items.values())


def generate_snapshot(date_str: str) -> Path:
    """基于近 7 天数据本地聚合生成看板快照（零 API 成本）"""
    target = datetime.strptime(date_str, "%Y-%m-%d")
    window = [(target - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    win_label = f"{window[0][5:].replace('-','/')}–{window[-1][5:].replace('-','/')}"

    stats = parse_source_stats(date_str)
    consensus = collect_consensus_rows(window)
    pool = collect_pool_items(window)

    lines = [
        f"# 📈 数据看板 · {date_str} 关键数字速查（自动周更）",
        "",
        f"> **更新时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> **数据来源**：{win_label} 看板素材池自动分流 + 日报跨源共识矩阵（本地聚合，零 API 成本）",
        "> **使用场景**：会议汇报\"AI 时代的市场体温\"时直接引用",
        "",
        "---",
        "",
        "## 📊 信源体温",
        "",
    ]
    if stats:
        lines.append(f"- 最新抓取：**{stats}**")
    lines.append(f"- 本窗口看板素材命中：**{len(pool)} 条**（去重后）")
    lines += ["", "---", "", "## 📊 跨源共识度（近一周议题）", ""]
    if consensus:
        lines += ["| 议题 | 资本/科技立场 | 学术/智库立场 | 共识度 | 日期 |", "|---|---|---|---|---|"]
        for t, cap, aca, pct, d in consensus:
            lines.append(f"| {t} | {cap} | {aca} | **{pct}%** | {d} |")
        hi = [r for r in consensus if r[3] >= 85]
        lo = [r for r in consensus if r[3] < 70]
        lines.append("")
        if hi:
            lines.append(f"**高共识（≥85%）**：{'、'.join(r[0] for r in hi)} → HR 行动可直接落地。")
        if lo:
            lines.append(f"**低共识（<70%）**：{'、'.join(r[0] for r in lo)} → 建议两端押注避险。")
    else:
        lines.append("_本窗口日报中未解析到共识矩阵数据。_")
    lines += ["", "---", "", "## 💰 本周数据类素材（自动分流命中）", ""]
    if pool:
        lines += ["| 日期 | 素材 | 来源 |", "|---|---|---|"]
        for title, src, link, d in pool:
            t = f"[{title}]({link})" if link else title
            lines.append(f"| {d} | {t} | {src} |")
    else:
        lines.append("_本窗口无看板类素材命中。_")
    lines += [
        "", "---", "",
        "## ⚠️ 数据使用提示", "",
        "- 本页由 `bailian/update_entries.py` 每周自动聚合生成，趋势比绝对值更可信",
        "- 素材可能为历史内容被当日 RSS 重推，引用前核对原文日期",
        "- 共识度由 qwen-max 逐日自动评估，为参考值而非统计量",
        "", "---", "",
        "## 🔗 联动资源", "",
        f"- 📅 [{date_str} 日报（自动版）](../daily-reports/{date_str}-auto.md)",
        "- 🗂️ 历史快照：" + " / ".join(
            f"[{_date_of(p)}]({p.name})" for p in sorted(DASHBOARD_DIR.glob("*-snapshot.md"), reverse=True)
            if _date_of(p) != date_str
        ),
        "",
    ]
    out = DASHBOARD_DIR / f"{date_str}-snapshot.md"
    out.write_text("\n".join(lines))
    print(f"  💾 看板快照重新生成 → {out.relative_to(WORKSPACE)}")
    return out


def ensure_snapshot(date_str: str) -> Path:
    """快照超龄（>7 天）则重新生成，返回最新快照路径"""
    latest = _latest_by_date(list(DASHBOARD_DIR.glob("*-snapshot.md")))
    if latest:
        age = (datetime.strptime(date_str, "%Y-%m-%d")
               - datetime.strptime(_date_of(latest), "%Y-%m-%d")).days
        if age < SNAPSHOT_MAX_AGE_DAYS:
            print(f"  ✅ 看板快照 {latest.name} 距今 {age} 天，未超龄")
            return latest
    return generate_snapshot(date_str)


# ─────────────────── 2. 导航栏保鲜 ───────────────────

def refresh_navbar(snapshot: Path) -> bool:
    if not NAVBAR_PATH.exists():
        return False
    s = orig = NAVBAR_PATH.read_text()
    latest_report = (_latest_by_date(list(REPORT_DIR.glob("*-visual.md")))
                     or _latest_by_date(list(REPORT_DIR.glob("*-auto.md"))))
    latest_event = _latest_by_date(list((WORKSPACE / "events").glob("auto-*.md")))
    if latest_report:
        s = re.sub(r"- \[📅 日报\]\([^)]+\)", f"- [📅 日报](daily-reports/{latest_report.name})", s)
    s = re.sub(r"- \[📈 数据\]\([^)]+\)", f"- [📈 数据](dashboard/{snapshot.name})", s)
    if latest_event:
        s = re.sub(r"- \[📅 议程\]\([^)]+\)", f"- [📅 议程](events/{latest_event.name})", s)
    if s != orig:
        NAVBAR_PATH.write_text(s)
        print("  📌 导航栏入口已刷新（日报/数据/议程 → 最新）")
        return True
    print("  ✅ 导航栏已是最新")
    return False


# ─────────────────── 3. 侧边栏看板分组保鲜 ───────────────────

def refresh_sidebar_dashboard(snapshot: Path) -> bool:
    if not SIDEBAR_PATH.exists():
        return False
    s = orig = SIDEBAR_PATH.read_text()
    if snapshot.name not in s:
        # 旧快照条目全部降级（去 ⭐，改叫历史快照）
        s = re.sub(r"  - \[(\d{4}-\d{2}-\d{2}) · [^\]]+\]\((dashboard/\d{4}-\d{2}-\d{2}-snapshot\.md)\)",
                   r"  - [\1 · 历史快照](\2)", s)
        marker = "- 📈 数据看板"
        pos = s.find(marker)
        if pos != -1:
            line_end = s.find("\n", pos)
            entry = f"\n  - [{_date_of(snapshot)} · 关键数据速查 ⭐](dashboard/{snapshot.name})"
            s = s[:line_end] + entry + s[line_end:]
    if s != orig:
        SIDEBAR_PATH.write_text(s)
        print("  📌 侧边栏看板分组已置顶最新快照")
        return True
    print("  ✅ 侧边栏看板分组已是最新")
    return False


# ─────────────────── 4. 板块 README 最新分流区块 ───────────────────

def refresh_module_readmes() -> int:
    changed = 0
    for module in README_MODULES:
        readme = WORKSPACE / module / "README.md"
        if not readme.exists():
            continue
        autos = sorted((WORKSPACE / module).glob("auto-*.md"), reverse=True)[:7]
        if not autos:
            continue
        rows = []
        for p in autos:
            n = len(re.findall(r"^### \d+\. ", p.read_text(), flags=re.M))
            rows.append(f"- [{_date_of(p)} · {n} 条素材]({p.name})")
        block = "\n".join([
            AUTO_BEGIN,
            "",
            "## �� 最新自动分流（每日更新）",
            "",
            f"> 由 pipeline 自动维护 · 刷新于 {datetime.now().strftime('%Y-%m-%d')}，最近 {len(autos)} 期：",
            "",
            *rows,
            "",
            AUTO_END,
        ])
        s = readme.read_text()
        if AUTO_BEGIN in s and AUTO_END in s:
            new = re.sub(re.escape(AUTO_BEGIN) + r".*?" + re.escape(AUTO_END), block, s, flags=re.S)
        else:
            new = s.rstrip() + "\n\n---\n\n" + block + "\n"
        if new != s:
            readme.write_text(new)
            changed += 1
            print(f"  📌 {module}/README.md 最新分流区块已刷新")
    return changed


# ─────────────────── 5. 首页 README 今日精华刷新 ───────────────────

def _parse_auto_report(date_str: str) -> dict | None:
    """从当日 auto.md 解析首页所需字段"""
    report = REPORT_DIR / f"{date_str}-auto.md"
    if not report.exists():
        return None
    text = report.read_text()

    win = re.search(r"\*\*抓取窗口\*\*：(\S+)", text)
    cov = re.search(r"\*\*信源覆盖\*\*：(.+)", text)

    signals = []
    for blk in re.split(r"^### 信号 ?\d+ ?[：:]", text, flags=re.M)[1:]:
        title = blk.splitlines()[0].strip()
        fact = re.search(r"\*\*事实\*\*：(.+)", blk)
        insight = re.search(r"\*\*HR 启示\*\*：(.+)", blk)
        counter = re.search(r"\*\*反方对冲\*\*：(.+)", blk)
        signals.append({
            "title": title,
            "fact": fact.group(1).strip() if fact else "",
            "insight": insight.group(1).strip() if insight else "",
            "counter": counter.group(1).strip() if counter else "",
        })

    # 行动速查表（跳过表头与分隔行）
    actions = []
    sect = re.search(r"## 💼 本周 HR 行动速查[^\n]*\n(.*?)(?=\n---)", text, flags=re.S)
    if sect:
        for line in sect.group(1).splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else []
            if len(cells) == 4 and "优先级" not in cells[0] and "---" not in cells[0]:
                actions.append(cells)

    # 金句出处作为素材亮点
    sources = []
    for m in re.finditer(r"——\s*(.+?)\s*$", text, flags=re.M):
        s = m.group(1).strip().rstrip("*")
        if s and s not in sources:
            sources.append(s)

    return {
        "window": win.group(1)[:16].replace("T", " ") if win else date_str,
        "coverage": cov.group(1).strip() if cov else "",
        "signals": signals[:3],
        "actions": actions[:5],
        "sources": sources[:6],
    }


def refresh_homepage(date_str: str, snapshot: Path) -> bool:
    """刷新首页 README.md 的入口链接、今日精华、三条信号、行动速查与版本日期"""
    readme = WORKSPACE / "README.md"
    data = _parse_auto_report(date_str)
    if not readme.exists() or not data or not data["signals"]:
        print("  ⚠️  首页刷新跳过（README 或当日报告缺失）")
        return False

    s = orig = readme.read_text()
    visual = f"daily-reports/{date_str}-visual.md"
    auto = f"daily-reports/{date_str}-auto.md"

    # 1. 板块导览里的日期型入口
    s = re.sub(r"(\| 📅 \*\*每日日报\*\*.*?\[👉 进入\]\()[^)]+(\))", rf"\1{visual}\2", s)
    s = re.sub(r"(\| 📈 \*\*数据看板\*\*.*?\[👉 进入\]\()[^)]+(\))", rf"\1dashboard/{snapshot.name}\2", s)
    latest_event = _latest_by_date(list((WORKSPACE / "events").glob("auto-*.md")))
    if latest_event:
        s = re.sub(r"(\| 📅 \*\*行业议程\*\*.*?\[👉 进入\]\()[^)]+(\))",
                   rf"\1events/{latest_event.name}\2", s)

    # 2. 今日精华 + 三条信号 + 素材亮点
    sig_lines = []
    for i, sig in enumerate(data["signals"], 1):
        parts = [f"**{sig['title']}**"]
        if sig["fact"]:
            parts.append(f"——{sig['fact']}")
        if sig["insight"]:
            parts.append(f" HR 启示：{sig['insight']}")
        if sig["counter"]:
            parts.append(f"（反方：{sig['counter']}）")
        sig_lines.append(f"{i}. {''.join(parts)} [详情]({visual})")

    highlight = "\n".join([
        f"### 🔥 今日精华（{date_str}）",
        "",
        f"> 抓取窗口：{data['window']} · 信源覆盖：{data['coverage']}",
        f"> 完整阅读：[👉 可视化版]({visual}) · [👉 纯文字版]({auto})",
        "",
        "### 三条核心信号",
        "",
        *sig_lines,
        "",
        "### 高价值素材亮点",
        f"- {' · '.join(data['sources'])} · [完整 8 板块]({visual})" if data["sources"]
        else f"- [完整 8 板块]({visual})",
        "",
        "",
    ])
    s = re.sub(r"### 🔥 今日精华（.*?\n(?=---\n)", highlight, s, flags=re.S)

    # 3. 行动速查表
    if data["actions"]:
        rows = "\n".join("| " + " | ".join(a) + " |" for a in data["actions"])
        table = "\n".join([
            f"### 💼 本周 HR 行动速查（截至 {date_str[5:].replace('-', '-')}）",
            "",
            "| 优先级 | 行动 | 时间窗 | 依据 |",
            "|---|---|---|---|",
            rows,
            "",
            "",
        ])
        s = re.sub(r"### 💼 本周 HR 行动速查（.*?\n(?=---\n)", table, s, flags=re.S)

    # 4. 版本行日期
    s = re.sub(r"(\- \*\*版本\*\*：v[\d.]+（)\d{4}-\d{2}-\d{2}(）)", rf"\g<1>{date_str}\2", s)

    if s != orig:
        readme.write_text(s)
        print(f"  📌 首页 README.md 已刷新至 {date_str}")
        return True
    print("  ✅ 首页已是最新")
    return False


def main(date: str | None = None) -> dict:
    date_str = date or datetime.now().strftime("%Y-%m-%d")
    print(f"🧭 板块入口保鲜 · 基准日期 {date_str}")
    snapshot = ensure_snapshot(date_str)
    nav = refresh_navbar(snapshot)
    side = refresh_sidebar_dashboard(snapshot)
    readmes = refresh_module_readmes()
    home = refresh_homepage(date_str, snapshot)
    cases = run_track_cases(date_str)
    return {"snapshot": snapshot.name, "navbar_changed": nav,
            "sidebar_changed": side, "readmes_changed": readmes,
            "homepage_changed": home, "cases_tracked": cases["tracked"],
            "cases_new": cases["new_today"]}


if __name__ == "__main__":
    try:
        result = main(sys.argv[1] if len(sys.argv) > 1 else None)
        print(f"\n🎯 入口保鲜汇总: {result}")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
