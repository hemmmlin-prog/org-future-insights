"""
bailian/update_sidebar.py — D 任务：自动更新 _sidebar.md 挂载今日报告

将今日日报条目插入「📅 每日日报」分组最顶端，去重。

用法：
    python3 -m bailian.update_sidebar                   # 用最新日期
    python3 -m bailian.update_sidebar 2026-06-16        # 指定日期
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from bailian.generate_daily import WORKSPACE, REPORT_DIR


SIDEBAR_PATH = WORKSPACE / "_sidebar.md"


def update_sidebar(date_str: str | None = None) -> bool:
    """
    在 _sidebar.md 的「📅 每日日报」分组顶部插入今日条目。
    返回是否有实际变更。
    """
    if not date_str:
        # 从最新 auto 推断
        autos = sorted(REPORT_DIR.glob("*-auto.md"), reverse=True)
        if not autos:
            print("⚠️  无 auto.md，跳过侧边栏更新")
            return False
        date_str = autos[0].stem.replace("-auto", "")

    if not SIDEBAR_PATH.exists():
        print(f"⚠️  {SIDEBAR_PATH} 不存在，跳过")
        return False

    content = SIDEBAR_PATH.read_text()

    # 要插入的条目
    entries_to_add = []

    auto_entry = f"  - [{date_str} · 自动版](daily-reports/{date_str}-auto.md)"
    visual_path = REPORT_DIR / f"{date_str}-visual.md"
    visual_entry = f"  - [{date_str} · 可视化](daily-reports/{date_str}-visual.md)"

    # 去重：检查是否已存在
    if date_str not in content or f"{date_str}-auto.md" not in content:
        entries_to_add.append(auto_entry)
    if visual_path.exists() and f"{date_str}-visual.md" not in content:
        entries_to_add.append(visual_entry)

    if not entries_to_add:
        print(f"✅ 侧边栏已含 {date_str} 条目，无需更新")
        return False

    # 定位「📅 每日日报」标记后插入
    marker = "- 📅 每日日报"
    marker_pos = content.find(marker)
    if marker_pos == -1:
        print("⚠️  未找到「📅 每日日报」标记，跳过")
        return False

    # 找到标记行结尾
    line_end = content.find("\n", marker_pos)
    if line_end == -1:
        line_end = len(content)

    # 插入新条目
    insert_text = "\n" + "\n".join(entries_to_add)
    new_content = content[:line_end] + insert_text + content[line_end:]

    SIDEBAR_PATH.write_text(new_content)
    print(f"📌 已更新侧边栏: 新增 {len(entries_to_add)} 条 ({date_str})")
    return True


def main(date: str | None = None) -> bool:
    return update_sidebar(date)


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        changed = main(date=date)
        sys.exit(0)
    except Exception as e:
        print(f"❌ 侧边栏更新失败: {e}", file=sys.stderr)
        sys.exit(1)
