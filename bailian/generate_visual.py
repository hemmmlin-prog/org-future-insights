"""
bailian/generate_visual.py — C 任务：将 auto.md 转为可视化 Docsify 增强页面

纯 Python 模板渲染，零 API 成本。

输入：daily-reports/YYYY-MM-DD-auto.md + daily-raw/YYYY-MM-DD.json
输出：daily-reports/YYYY-MM-DD-visual.md

用法：
    python3 -m bailian.generate_visual                  # 用最新 auto
    python3 -m bailian.generate_visual 2026-06-16       # 指定日期
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from bailian.generate_daily import WORKSPACE, RAW_DIR, REPORT_DIR


def find_auto_report(date_str: str | None = None) -> tuple[Path, str]:
    """找到 auto.md 并返回 (路径, 日期字符串)"""
    if date_str:
        p = REPORT_DIR / f"{date_str}-auto.md"
        if not p.exists():
            raise FileNotFoundError(f"❌ {p} 不存在")
        return p, date_str
    # 找最新的
    files = sorted(REPORT_DIR.glob("*-auto.md"), reverse=True)
    if not files:
        raise FileNotFoundError("❌ daily-reports/ 下没有 auto.md 文件")
    stem = files[0].stem.replace("-auto", "")
    return files[0], stem


def parse_signals(content: str) -> list[dict]:
    """解析 auto.md 中的三条核心信号"""
    signals = []
    # 匹配 ### 信号 N：标题
    pattern = r'### 信号 (\d+)：(.+?)(?=\n###|\n---|\Z)'
    matches = re.finditer(pattern, content, re.DOTALL)
    for m in matches:
        num = m.group(1)
        block = m.group(2)
        title_line = block.split('\n')[0].strip()
        # 提取各段
        fact = extract_section(block, '事实')
        hr_hint = extract_section(block, 'HR 启示')
        counter = extract_section(block, '反方对冲')
        china = extract_section(block, '中国语境映射')
        quote = extract_quote(block)
        signals.append({
            'num': num,
            'title': title_line,
            'fact': fact,
            'hr_hint': hr_hint,
            'counter': counter,
            'china': china,
            'quote': quote,
        })
    return signals


def extract_section(block: str, label: str) -> str:
    """从信号块中提取 **label**：后面的内容"""
    pattern = rf'\*\*{re.escape(label)}\*\*[：:]\s*(.+?)(?=\n\*\*|\n>|\Z)'
    m = re.search(pattern, block, re.DOTALL)
    return m.group(1).strip() if m else ""


def extract_quote(block: str) -> str:
    """提取引用金句"""
    m = re.search(r'> "(.+?)"', block)
    return m.group(1) if m else ""


def parse_consensus_matrix(content: str) -> list[dict]:
    """解析共识矩阵表格"""
    rows = []
    # 找到矩阵表格区域
    table_match = re.search(
        r'## 📊 跨源共识矩阵\s*\n\n\|.+?\|\n\|[-|]+\|\n(.+?)(?=\n---|\n##)',
        content, re.DOTALL
    )
    if not table_match:
        return rows
    for line in table_match.group(1).strip().split('\n'):
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if len(cells) >= 4:
            consensus_str = cells[3].replace('%', '').strip()
            try:
                consensus = int(consensus_str)
            except ValueError:
                consensus = 50
            rows.append({
                'topic': cells[0],
                'tech_stance': cells[1],
                'academic_stance': cells[2],
                'consensus': consensus,
            })
    return rows


def parse_actions(content: str) -> list[dict]:
    """解析 HR 行动速查表格"""
    actions = []
    table_match = re.search(
        r'## 💼 本周 HR 行动速查.+?\n\|.+?\|\n\|[-|]+\|\n(.+?)(?=\n---|\n##)',
        content, re.DOTALL
    )
    if not table_match:
        return actions
    for line in table_match.group(1).strip().split('\n'):
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if len(cells) >= 4:
            actions.append({
                'priority': cells[0],
                'action': cells[1],
                'window': cells[2],
                'signal': cells[3],
            })
    return actions


def parse_quotes(content: str) -> list[str]:
    """解析今日金句"""
    quotes = []
    section = re.search(r'## 💬 今日 5 条金句\s*\n(.+?)(?=\n---|\n##)', content, re.DOTALL)
    if section:
        for m in re.finditer(r'> "(.+?)"', section.group(1)):
            quotes.append(m.group(1))
    return quotes[:5]


def get_raw_stats(date_str: str) -> dict:
    """从 raw JSON 获取统计数据"""
    raw_path = RAW_DIR / f"{date_str}.json"
    if not raw_path.exists():
        # 尝试 workspace 下的 daily-raw
        raw_path = WORKSPACE / "daily-raw" / f"{date_str}.json"
    if not raw_path.exists():
        return {'sources': 0, 'items': 0, 'categories': []}
    raw = json.loads(raw_path.read_text())
    sources = raw.get('sources', [])
    success = [s for s in sources if s.get('items_count', 0) > 0]
    categories = list(set(s.get('category', '') for s in success))
    total_items = sum(s.get('items_count', 0) for s in success)
    return {
        'sources': len(success),
        'items': total_items,
        'categories': categories,
    }


def render_signal_card(signal: dict, color: str) -> str:
    """渲染单条信号为 HTML 卡片"""
    return f"""
<div class="signal-card" style="border-left: 4px solid {color}; background: #fafbfc; border-radius: 8px; padding: 16px 20px; margin: 12px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">

**🔥 信号 {signal['num']}：{signal['title']}**

📋 **事实**：{signal['fact']}

💡 **HR 启示**：{signal['hr_hint']}

⚖️ **反方对冲**：{signal['counter']}

🇨🇳 **中国映射**：{signal['china']}

{f'> "_{signal["quote"]}_"' if signal['quote'] else ''}

</div>
"""


def render_consensus_bar(row: dict) -> str:
    """渲染单行共识度进度条"""
    pct = row['consensus']
    if pct >= 80:
        bar_color = '#52c41a'
    elif pct >= 60:
        bar_color = '#faad14'
    else:
        bar_color = '#f5222d'
    return f"""<div style="margin: 8px 0;">
<div style="display: flex; align-items: center; gap: 10px;">
<span style="min-width: 200px; font-weight: 500;">{row['topic']}</span>
<div style="flex: 1; background: #f0f0f0; border-radius: 4px; height: 20px; overflow: hidden;">
<div style="width: {pct}%; background: {bar_color}; height: 100%; border-radius: 4px; transition: width 0.3s;"></div>
</div>
<span style="min-width: 45px; text-align: right; font-weight: bold; color: {bar_color};">{pct}%</span>
</div>
<div style="font-size: 12px; color: #666; margin-left: 210px;">资本/科技: {row['tech_stance']} | 学术/智库: {row['academic_stance']}</div>
</div>"""


def render_action_card(action: dict) -> str:
    """渲染 HR 行动为卡片"""
    priority = action['priority']
    return f"""<div style="background: white; border-radius: 8px; padding: 12px 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); border-top: 3px solid {'#ff4d4f' if '🔴' in priority else '#faad14' if '🟠' in priority else '#52c41a' if '🟢' in priority else '#d9d9d9'};">
<div style="font-size: 12px; color: #888;">{priority} · {action['window']}</div>
<div style="font-weight: 500; margin: 4px 0;">{action['action']}</div>
<div style="font-size: 12px; color: #1890ff;">{action['signal']}</div>
</div>"""


def generate_visual_page(date_str: str, auto_content: str, stats: dict) -> str:
    """生成完整的可视化页面"""
    signals = parse_signals(auto_content)
    consensus = parse_consensus_matrix(auto_content)
    actions = parse_actions(auto_content)
    quotes = parse_quotes(auto_content)

    signal_colors = ['#1890ff', '#722ed1', '#13c2c2']

    # KPI 面板
    avg_consensus = round(sum(r['consensus'] for r in consensus) / max(len(consensus), 1))
    kpi_html = f"""
<div class="kpi-panel" style="display: flex; gap: 16px; flex-wrap: wrap; margin: 20px 0;">
<div style="flex: 1; min-width: 120px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 20px; color: white; text-align: center;">
<div style="font-size: 28px; font-weight: bold;">{stats['sources']}</div>
<div style="font-size: 13px; opacity: 0.9;">命中信源</div>
</div>
<div style="flex: 1; min-width: 120px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 12px; padding: 20px; color: white; text-align: center;">
<div style="font-size: 28px; font-weight: bold;">{stats['items']}</div>
<div style="font-size: 13px; opacity: 0.9;">抓取条目</div>
</div>
<div style="flex: 1; min-width: 120px; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); border-radius: 12px; padding: 20px; color: white; text-align: center;">
<div style="font-size: 28px; font-weight: bold;">{len(signals)}</div>
<div style="font-size: 13px; opacity: 0.9;">核心信号</div>
</div>
<div style="flex: 1; min-width: 120px; background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); border-radius: 12px; padding: 20px; color: white; text-align: center;">
<div style="font-size: 28px; font-weight: bold;">{avg_consensus}%</div>
<div style="font-size: 13px; opacity: 0.9;">平均共识度</div>
</div>
</div>
"""

    # 信号卡片
    signal_cards = ""
    for i, sig in enumerate(signals):
        color = signal_colors[i % len(signal_colors)]
        signal_cards += render_signal_card(sig, color)

    # 共识度可视化
    consensus_html = ""
    for row in consensus:
        consensus_html += render_consensus_bar(row)

    # 行动网格
    action_grid = '<div class="action-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; margin: 16px 0;">\n'
    for act in actions:
        action_grid += render_action_card(act) + '\n'
    action_grid += '</div>'

    # 金句
    quotes_html = ""
    for q in quotes:
        quotes_html += f'\n> *"{q}"*\n'

    # 类目标签
    cat_badges = " ".join(
        f'<span style="display:inline-block; background:#e6f7ff; color:#1890ff; padding:2px 8px; border-radius:10px; font-size:12px; margin:2px;">{c}</span>'
        for c in stats.get('categories', [])
    )

    # 8 板块联动
    modules_links = f"""
| 板块 | 今日聚合 |
|---|---|
| 🏢 公司 & 关键人 | [companies/auto-{date_str}.md](../companies/auto-{date_str}.md) |
| 🎓 报告 & 研究 | [research/auto-{date_str}.md](../research/auto-{date_str}.md) |
| 📊 转型案例 | [cases/auto-{date_str}.md](../cases/auto-{date_str}.md) |
| 📚 延伸阅读 | [readings/auto-{date_str}.md](../readings/auto-{date_str}.md) |
| 📈 数据看板 | [dashboard/auto-{date_str}.md](../dashboard/auto-{date_str}.md) |
| 📅 行业议程 | [events/auto-{date_str}.md](../events/auto-{date_str}.md) |
"""

    # 组装完整页面
    page = f"""# 📊 {date_str} HR 洞察日报 · 可视化版

> 📅 **日期**：{date_str} | **渲染时间**：{datetime.now().strftime('%H:%M')} | **类型**：Docsify 增强页面
>
> **信源类目**：{cat_badges}

---

## 📈 今日数据概览

{kpi_html}

---

## 🔥 三条核心信号

{signal_cards}

---

## 📊 跨源共识度

{consensus_html}

---

## 💼 HR 行动速查

{action_grid}

---

## 💬 今日金句

{quotes_html}

---

## 🔗 8 板块联动

{modules_links}

---

> 📐 本页由 `bailian/generate_visual.py` 基于当日 auto.md 自动渲染，零 API 成本。
> 📄 纯文字版：[{date_str}-auto.md]({date_str}-auto.md)
"""
    return page


def main(date: str | None = None) -> Path:
    auto_path, date_str = find_auto_report(date)
    print(f"📂 读取 auto: {auto_path.name}")
    auto_content = auto_path.read_text()

    stats = get_raw_stats(date_str)
    print(f"📊 raw 统计: {stats['sources']} 源 / {stats['items']} items / {len(stats['categories'])} 类目")

    page = generate_visual_page(date_str, auto_content, stats)

    output_path = REPORT_DIR / f"{date_str}-visual.md"
    output_path.write_text(page)
    print(f"🎨 已写入: {output_path.relative_to(WORKSPACE)}")
    return output_path


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        main(date=date)
        sys.exit(0)
    except Exception as e:
        print(f"❌ 失败: {e}", file=sys.stderr)
        sys.exit(1)
