"""
bailian/pipeline.py — A+B+C+D+E 全流程自动化

设计：
- A 失败不阻塞 B；B 失败不阻塞 C/D/E
- 每个阶段独立计时 + 独立日志
- 退出码：0 全成功 / 1 全失败 / 2 部分失败（仍可用）

阶段：
- A: 全自动日报（百炼 qwen-max）
- B: 8 板块分流（百炼 qwen-max）
- C: 可视化页面生成（本地模板，零成本）
- D: 侧边栏自动更新（本地文件操作）
- E: 质量审计（本地 regex 检测）

用法：
    python3 -m bailian.pipeline                    # 全流程
    python3 -m bailian.pipeline 2026-06-14
    python3 -m bailian.pipeline --model qwen-plus
    python3 -m bailian.pipeline --skip-classify    # 跳过 B
    python3 -m bailian.pipeline --skip-daily       # 跳过 A
    python3 -m bailian.pipeline --skip-visual      # 跳过 C
    python3 -m bailian.pipeline --skip-audit       # 跳过 E
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

from bailian.client import DEFAULT_MODEL
from bailian.generate_daily import main as run_daily, LOG_DIR
from bailian.classify_to_modules import main as run_classify
from bailian.generate_visual import main as run_visual
from bailian.update_sidebar import main as run_sidebar
from bailian.quality_audit import main as run_audit


def write_pipeline_log(entry: dict):
    log_file = LOG_DIR / "bailian.pipeline.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run(date: str | None, model: str, skip_daily: bool, skip_classify: bool,
        skip_visual: bool = False, skip_audit: bool = False) -> int:
    started = datetime.now()
    summary: dict = {
        "started_at": started.isoformat(timespec="seconds"),
        "date": date,
        "model": model,
        "daily": {"status": "skipped"},
        "classify": {"status": "skipped"},
        "visual": {"status": "skipped"},
        "sidebar": {"status": "skipped"},
        "audit": {"status": "skipped"},
    }

    daily_ok = True
    classify_ok = True

    # === A: 日报 ===
    if not skip_daily:
        print("=" * 60)
        print("🔵 阶段 A：全自动日报")
        print("=" * 60)
        t0 = time.time()
        try:
            report_path = run_daily(date=date, model=model)
            summary["daily"] = {
                "status": "ok",
                "report": str(report_path),
                "elapsed_sec": round(time.time() - t0, 2),
            }
        except Exception as e:
            daily_ok = False
            summary["daily"] = {
                "status": "fail",
                "error": f"{type(e).__name__}: {str(e)[:300]}",
                "elapsed_sec": round(time.time() - t0, 2),
            }
            print(f"❌ 日报生成失败: {e}", file=sys.stderr)

    # === B: 分流 ===
    if not skip_classify:
        print()
        print("=" * 60)
        print("🟢 阶段 B：8 板块分流")
        print("=" * 60)
        t0 = time.time()
        try:
            module_summary = run_classify(date=date, model=model)
            summary["classify"] = {
                "status": "ok",
                "module_counts": module_summary,
                "elapsed_sec": round(time.time() - t0, 2),
            }
        except Exception as e:
            classify_ok = False
            summary["classify"] = {
                "status": "fail",
                "error": f"{type(e).__name__}: {str(e)[:300]}",
                "elapsed_sec": round(time.time() - t0, 2),
            }
            print(f"❌ 分流失败: {e}", file=sys.stderr)

    # === C: 可视化 ===
    visual_ok = True
    if not skip_visual:
        print()
        print("=" * 60)
        print("🎨 阶段 C：可视化页面生成")
        print("=" * 60)
        t0 = time.time()
        try:
            visual_path = run_visual(date=date)
            summary["visual"] = {
                "status": "ok",
                "report": str(visual_path),
                "elapsed_sec": round(time.time() - t0, 2),
            }
        except Exception as e:
            visual_ok = False
            summary["visual"] = {
                "status": "fail",
                "error": f"{type(e).__name__}: {str(e)[:300]}",
                "elapsed_sec": round(time.time() - t0, 2),
            }
            print(f"⚠️  可视化生成失败: {e}", file=sys.stderr)

    # === D: 侧边栏更新 ===
    print()
    print("=" * 60)
    print("📌 阶段 D：侧边栏自动更新")
    print("=" * 60)
    t0 = time.time()
    try:
        changed = run_sidebar(date=date)
        summary["sidebar"] = {
            "status": "ok",
            "changed": changed,
            "elapsed_sec": round(time.time() - t0, 2),
        }
    except Exception as e:
        summary["sidebar"] = {
            "status": "fail",
            "error": f"{type(e).__name__}: {str(e)[:300]}",
            "elapsed_sec": round(time.time() - t0, 2),
        }
        print(f"⚠️  侧边栏更新失败: {e}", file=sys.stderr)

    # === E: 质量审计 ===
    audit_result = None
    if not skip_audit:
        print()
        print("=" * 60)
        print("🔍 阶段 E：质量审计")
        print("=" * 60)
        t0 = time.time()
        try:
            audit_result = run_audit(date=date)
            summary["audit"] = {
                "status": "ok",
                "pass_count": audit_result["pass_count"],
                "total_checks": audit_result["total_checks"],
                "all_passed": audit_result["all_passed"],
                "elapsed_sec": round(time.time() - t0, 2),
            }
        except Exception as e:
            summary["audit"] = {
                "status": "fail",
                "error": f"{type(e).__name__}: {str(e)[:300]}",
                "elapsed_sec": round(time.time() - t0, 2),
            }
            print(f"⚠️  质量审计失败: {e}", file=sys.stderr)

    summary["finished_at"] = datetime.now().isoformat(timespec="seconds")
    summary["total_elapsed_sec"] = round((datetime.now() - started).total_seconds(), 2)

    write_pipeline_log(summary)

    print()
    print("=" * 60)
    print("🏁 Pipeline 总结")
    print("=" * 60)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    # 下一步提示
    print()
    print("─" * 60)
    print("🎉 全流程完成！下一步可选：")
    print("  1) /org-future-insights --review  → 出 PM 精读版")
    print("  2) /org-future-insights --share   → 打包分享")
    print("  3) 直接打开 http://localhost:3000 查看可视化版")
    print("─" * 60)

    if daily_ok and classify_ok and visual_ok:
        return 0
    if not daily_ok and not classify_ok:
        return 1
    return 2


if __name__ == "__main__":
    args = sys.argv[1:]
    date = None
    model = DEFAULT_MODEL
    skip_daily = False
    skip_classify = False
    skip_visual = False
    skip_audit = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--model" and i + 1 < len(args):
            model = args[i + 1]
            i += 2
        elif a == "--skip-daily":
            skip_daily = True
            i += 1
        elif a == "--skip-classify":
            skip_classify = True
            i += 1
        elif a == "--skip-visual":
            skip_visual = True
            i += 1
        elif a == "--skip-audit":
            skip_audit = True
            i += 1
        else:
            date = a
            i += 1

    sys.exit(run(
        date=date, model=model,
        skip_daily=skip_daily, skip_classify=skip_classify,
        skip_visual=skip_visual, skip_audit=skip_audit,
    ))
