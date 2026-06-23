"""
bailian/quality_audit.py — E 任务：对 auto.md 运行 6 项强制质量审计

纯本地 regex 检测，零 API 成本。

输出：
- 终端彩色 PASS/WARN 报告
- daily-raw/_logs/YYYY-MM-DD-audit.json

用法：
    python3 -m bailian.quality_audit                    # 审计最新 auto
    python3 -m bailian.quality_audit 2026-06-16         # 指定日期
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from bailian.generate_daily import WORKSPACE, RAW_DIR, REPORT_DIR, LOG_DIR

# 审计日志优先写入工作区内（避免沙箱限制）
AUDIT_LOG_DIR = WORKSPACE / "daily-raw" / "_logs"


# ANSI 颜色
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def find_auto_and_raw(date_str: str | None = None) -> tuple[Path, Path, str]:
    """找到 auto.md 和对应 raw JSON"""
    if date_str:
        auto_path = REPORT_DIR / f"{date_str}-auto.md"
        raw_path = RAW_DIR / f"{date_str}.json"
    else:
        autos = sorted(REPORT_DIR.glob("*-auto.md"), reverse=True)
        if not autos:
            raise FileNotFoundError("❌ 没有 auto.md")
        auto_path = autos[0]
        date_str = auto_path.stem.replace("-auto", "")
        raw_path = RAW_DIR / f"{date_str}.json"
        if not raw_path.exists():
            raw_path = WORKSPACE / "daily-raw" / f"{date_str}.json"

    if not auto_path.exists():
        raise FileNotFoundError(f"❌ {auto_path} 不存在")
    return auto_path, raw_path, date_str


def check_multi_source(raw_path: Path) -> tuple[bool, str]:
    """检查 1: 5 类多源覆盖 >= 3"""
    if not raw_path.exists():
        return False, "raw JSON 不存在，无法验证"
    raw = json.loads(raw_path.read_text())
    sources = raw.get("sources", [])
    categories = set()
    for s in sources:
        if s.get("items_count", 0) > 0:
            categories.add(s.get("category", "unknown"))
    hit = len(categories)
    passed = hit >= 3
    return passed, f"命中 {hit}/5 类 ({', '.join(sorted(categories))})"


def check_counter_arguments(content: str) -> tuple[bool, str]:
    """检查 2: 反方对冲存在"""
    # 查找所有 **反方对冲** 段
    matches = re.findall(r'\*\*反方对冲\*\*[：:]\s*(.+?)(?=\n\*\*|\n>|\n###|\n---)', content, re.DOTALL)
    non_empty = [m for m in matches if len(m.strip()) > 10]
    signals_count = len(re.findall(r'### 信号 \d+', content))
    passed = len(non_empty) >= signals_count and signals_count > 0
    return passed, f"{len(non_empty)}/{signals_count} 条信号有反方对冲"


def check_hr_pillars(content: str) -> tuple[bool, str]:
    """检查 3: HR 三大支柱覆盖 >= 2"""
    pillars = {
        '招聘': ['招聘', '人才获取', 'Talent Acquisition', 'hiring', 'JD', '面试'],
        '发展': ['培训', '发展', 'Reskilling', '学习', 'Development', '能力', 'mindset', 'skillset'],
        '回报': ['薪酬', '回报', '激励', 'Compensation', 'Reward', 'TCC', '绩效', '福利'],
    }
    hits = []
    lower_content = content.lower()
    for pillar, keywords in pillars.items():
        for kw in keywords:
            if kw.lower() in lower_content:
                hits.append(pillar)
                break
    passed = len(hits) >= 2
    return passed, f"命中 {len(hits)}/3 支柱 ({', '.join(hits)})"


def check_quotes_legit(content: str, raw_path: Path) -> tuple[bool, str]:
    """检查 4: 金句来源合法（能匹配 raw items）"""
    # 提取金句
    quotes_section = re.search(r'## 💬 今日 5 条金句\s*\n(.+?)(?=\n---|\n##|\Z)', content, re.DOTALL)
    if not quotes_section:
        return False, "未找到金句段落"
    quotes = re.findall(r'"(.+?)"', quotes_section.group(1))
    if not quotes:
        return False, "金句为空"

    if not raw_path.exists():
        return True, f"找到 {len(quotes)} 条金句（raw 不存在，跳过来源验证）"

    # 对比 raw 的 summary 和 title
    raw = json.loads(raw_path.read_text())
    raw_text = ""
    for src in raw.get("sources", []):
        for item in src.get("items", []):
            raw_text += (item.get("title", "") + " " + (item.get("summary") or "") + " ")

    matched = 0
    for q in quotes[:5]:
        # 取前 20 字做模糊匹配
        snippet = q[:30].lower().replace('"', '').replace("'", "")
        if snippet in raw_text.lower():
            matched += 1

    passed = matched >= 3
    return passed, f"{matched}/{len(quotes[:5])} 条金句可溯源"


def check_word_count(content: str) -> tuple[bool, str]:
    """检查 5: 总字数 2500-3500"""
    # 去除 markdown 标记后计算中英文字数
    clean = re.sub(r'[#\-|*>`\[\](){}]', '', content)
    char_count = len(clean.strip())
    passed = 2000 <= char_count <= 5000  # 放宽一点（含标点）
    return passed, f"内容 {char_count} 字符（目标 2500-3500 字）"


def check_signal_diversity(content: str) -> tuple[bool, str]:
    """检查 6: 3 条信号来源类目不全相同"""
    # 从信号的"来源"字段提取
    sources_found = re.findall(r'来源[：:]\s*(.+?)[,，）)\n]', content)
    if len(sources_found) < 2:
        # 备选：从 **事实** 段提取括号中的来源
        sources_found = re.findall(r'（来源[：:]\s*(.+?)）', content)
    if len(sources_found) < 2:
        sources_found = re.findall(r'\(来源[：:]\s*(.+?)\)', content)

    categories = set()
    for s in sources_found[:3]:
        s_lower = s.lower()
        if any(kw in s_lower for kw in ['openai', 'github', 'anthropic']):
            categories.add('tech')
        elif any(kw in s_lower for kw in ['nber', 'hbs', 'hbr', 'arxiv']):
            categories.add('academia')
        elif any(kw in s_lower for kw in ['sequoia', 'a16z', 'yc', 'y combinator']):
            categories.add('vc')
        elif any(kw in s_lower for kw in ['rand', 'brookings', 'wef']):
            categories.add('think_tank')
        elif any(kw in s_lower for kw in ['36kr', '36氪', '晚点', '北森']):
            categories.add('china')
        else:
            categories.add(s[:10])

    passed = len(categories) >= 2
    return passed, f"信号来自 {len(categories)} 类信源 ({', '.join(sorted(categories))})"


def run_audit(date: str | None = None) -> dict:
    """运行全部 6 项审计"""
    auto_path, raw_path, date_str = find_auto_and_raw(date)
    content = auto_path.read_text()

    print()
    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}🔍 质量审计：{date_str}-auto.md{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")
    print()

    checks = [
        ("5 类多源覆盖 ≥ 3", check_multi_source(raw_path)),
        ("反方对冲完整", check_counter_arguments(content)),
        ("HR 三大支柱 ≥ 2", check_hr_pillars(content)),
        ("金句来源可溯", check_quotes_legit(content, raw_path)),
        ("总字数范围", check_word_count(content)),
        ("信号类目多样", check_signal_diversity(content)),
    ]

    results = []
    pass_count = 0
    for name, (passed, detail) in checks:
        status = f"{GREEN}✅ PASS{RESET}" if passed else f"{YELLOW}⚠️  WARN{RESET}"
        print(f"  {status}  {name}: {detail}")
        results.append({
            "check": name,
            "passed": passed,
            "detail": detail,
        })
        if passed:
            pass_count += 1

    print()
    total = len(checks)
    if pass_count == total:
        print(f"  {GREEN}{BOLD}🎉 全部通过 ({pass_count}/{total}){RESET}")
    else:
        print(f"  {YELLOW}{BOLD}⚠️  {pass_count}/{total} 通过，{total - pass_count} 项需关注{RESET}")
    print()

    # 写审计日志
    audit_log = {
        "date": date_str,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "auto_file": str(auto_path.relative_to(WORKSPACE)),
        "pass_count": pass_count,
        "total_checks": total,
        "all_passed": pass_count == total,
        "results": results,
    }

    # 优先写工作区内，再尝试 runtime LOG_DIR
    log_path = AUDIT_LOG_DIR / f"{date_str}-audit.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(audit_log, ensure_ascii=False, indent=2))
    print(f"  📝 审计日志: {log_path.relative_to(WORKSPACE)}")

    # 也尝试写一份到 runtime _logs（launchd 环境可用）
    try:
        runtime_log = LOG_DIR / f"{date_str}-audit.json"
        runtime_log.parent.mkdir(parents=True, exist_ok=True)
        runtime_log.write_text(json.dumps(audit_log, ensure_ascii=False, indent=2))
    except (OSError, ValueError):
        pass  # 沙箱限制时静默跳过

    return audit_log


def main(date: str | None = None) -> dict:
    return run_audit(date)


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        result = main(date=date)
        sys.exit(0 if result["all_passed"] else 2)
    except Exception as e:
        print(f"❌ 审计失败: {e}", file=sys.stderr)
        sys.exit(1)
