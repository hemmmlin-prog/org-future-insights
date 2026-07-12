#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_daily.py · org-future-insights v0.1
每日抓取 50+ 信源 RSS / 网页摘要，存入 daily-raw/YYYY-MM-DD.json

用法：
    python3 fetch_daily.py                 # 抓取全部高优先级源
    python3 fetch_daily.py --priority 3    # 只抓 ⭐⭐⭐ 源
    python3 fetch_daily.py --dry-run       # 仅打印不写文件

由 launchd 在凌晨 6 点自动调用（com.emma.org-future-insights.plist）。
仅依赖 Python 标准库 + 可选 feedparser（macOS 自带 Python 通常未装，
脚本会自动降级用 urllib + 简易 XML 解析）。
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

# ---------- 路径配置 ----------
# v0.1.1：优先读环境变量 OFI_PROJECT_ROOT（用于 launchd 运行时迁出 Desktop 避开 macOS TCC 限制）
SCRIPT_DIR = Path(__file__).resolve().parent
_env_root = os.environ.get("OFI_PROJECT_ROOT")
if _env_root:
    PROJECT_ROOT = Path(_env_root).resolve()
else:
    SKILL_DIR = SCRIPT_DIR.parent  # .qoder/skills/org-future-insights/
    PROJECT_ROOT = SKILL_DIR.parent.parent.parent  # 组织演变/
RAW_DIR = PROJECT_ROOT / "daily-raw"
LOG_DIR = PROJECT_ROOT / "daily-raw" / "_logs"

RAW_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------- 信源池（v0.1.1：基于 2026-06-14 实测校正） ----------
# 格式：(类别, 名称, RSS_URL, 优先级)
# 校正方法：curl + grep '<rss|<feed' 实测 200 OK 且为合法 RSS/Atom
SOURCES = [
    # ── Tier-S：直连权威源（11 个，2026-06-14 实测全部 200 OK） ──
    ("consulting", "McKinsey", "https://www.mckinsey.com/insights/rss", 3),
    ("tech", "OpenAI", "https://openai.com/news/rss.xml", 3),
    ("tech", "GitHub Blog", "https://github.blog/feed/", 2),
    ("academia", "arXiv cs.AI", "https://export.arxiv.org/rss/cs.AI", 3),
    ("academia", "NBER WP", "https://www.nber.org/rss/new.xml", 3),
    ("academia", "HBS Working Knowledge", "https://hbswk.hbs.edu/rss/all.xml", 2),
    ("think_tank", "RAND", "https://www.rand.org/blog.xml", 2),
    ("vc", "Sequoia", "https://www.sequoiacap.com/feed/", 3),
    ("vc", "Y Combinator", "https://www.ycombinator.com/blog/rss.xml", 2),
    ("hr_media", "HBR", "http://feeds.harvardbusiness.org/harvardbusiness?format=xml", 3),
    ("china", "36Kr", "https://36kr.com/feed", 2),

    # ── Tier-A：Google News RSS 兜底（覆盖找不到直连 RSS 的关键机构）──
    # 当直连源被反爬 / 404 时，用 Google News 反向聚合该机构的近期报道
    ("consulting", "BCG (Google News)",
     "https://news.google.com/rss/search?q=%22Boston+Consulting+Group%22+future+of+work&hl=en-US&gl=US", 2),
    ("consulting", "Deloitte (Google News)",
     "https://news.google.com/rss/search?q=%22Deloitte%22+human+capital+trends&hl=en-US&gl=US", 2),
    ("consulting", "Accenture (Google News)",
     "https://news.google.com/rss/search?q=%22Accenture%22+talent+%22future+of+work%22&hl=en-US&gl=US", 2),
    ("vc", "a16z (Google News)",
     "https://news.google.com/rss/search?q=%22Andreessen+Horowitz%22+OR+%22a16z%22+AI+agent&hl=en-US&gl=US", 2),
    ("think_tank", "Brookings (Google News)",
     "https://news.google.com/rss/search?q=%22Brookings%22+AI+labor+market&hl=en-US&gl=US", 2),
    ("think_tank", "WEF (Google News)",
     "https://news.google.com/rss/search?q=%22World+Economic+Forum%22+%22future+of+jobs%22&hl=en-US&gl=US", 2),
    ("hr_media", "Mercer (Google News)",
     "https://news.google.com/rss/search?q=%22Mercer%22+total+rewards+OR+compensation&hl=en-US&gl=US", 2),
    ("hr_media", "WTW (Google News)",
     "https://news.google.com/rss/search?q=%22Willis+Towers+Watson%22+compensation+pay&hl=en-US&gl=US", 2),
    ("hr_media", "WorldatWork (Google News)",
     "https://news.google.com/rss/search?q=%22WorldatWork%22+pay+rewards&hl=en-US&gl=US", 1),
    ("academia", "MIT SMR (Google News)",
     "https://news.google.com/rss/search?q=%22MIT+Sloan+Management+Review%22&hl=en-US&gl=US", 1),
    ("tech", "DeepMind (Google News)",
     "https://news.google.com/rss/search?q=%22Google+DeepMind%22+research&hl=en-US&gl=US", 1),
    ("tech", "Anthropic (Google News)",
     "https://news.google.com/rss/search?q=%22Anthropic%22+Claude+enterprise&hl=en-US&gl=US", 1),
    ("china", "中国 HR Tech (Google News)",
     "https://news.google.com/rss/search?q=%E5%8C%97%E6%A3%AE+OR+Moka+OR+%E5%A4%AA%E5%92%8C%E9%A1%BE%E9%97%AE+%E4%BA%BA%E6%89%8D&hl=zh-CN&gl=CN", 1),
]

# 浏览器级 User-Agent（实测：很多源对脚本 UA 返回 403）
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
TIMEOUT = 25  # 秒（Google News 较慢，需 ≥20s）
MAX_ITEMS_PER_SOURCE = 10  # 每源最多取 10 条最新

# ---------- 抓取核心 ----------
import re

def _regex_fallback(content: bytes) -> list[dict]:
    """当 ElementTree 解析失败时，用正则兑底抽取 title/link/description。
    适用于：arXiv RDF（RSS 1.0）/ NBER 含非法字符的 feed 等边缘情况。"""
    text = content.decode("utf-8", errors="replace")
    items = []
    # 匹配 <item ...>...</item> 或 <entry>...</entry>
    blocks = re.findall(r"<(?:item|entry)\b[^>]*>(.*?)</(?:item|entry)>", text, re.DOTALL | re.IGNORECASE)
    for b in blocks[:MAX_ITEMS_PER_SOURCE]:
        title_m = re.search(r"<title[^>]*>(.*?)</title>", b, re.DOTALL | re.IGNORECASE)
        link_m = re.search(r"<link[^>]*>(.*?)</link>", b, re.DOTALL | re.IGNORECASE)
        desc_m = re.search(r"<(?:description|summary)[^>]*>(.*?)</(?:description|summary)>", b, re.DOTALL | re.IGNORECASE)
        # arXiv RDF 的 link 在 <link> 文本中；Atom 是在 href="..." 中
        link = (link_m.group(1).strip() if link_m else "")
        if not link:
            href_m = re.search(r'<link[^>]*href="([^"]+)"', b)
            if href_m:
                link = href_m.group(1)
        items.append({
            "title": re.sub(r"<[^>]+>", "", (title_m.group(1) if title_m else "")).strip()[:300],
            "link": link,
            "pubDate": "",
            "summary": re.sub(r"<[^>]+>", "", (desc_m.group(1) if desc_m else "")).strip()[:500],
        })
    return items


def fetch_rss(url: str) -> list[dict]:
    """抓取并解析 RSS / Atom feed，返回标题+链接+摘要列表。失败返回空列表。"""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            content = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:  # OSError 涵盖 Py3.9 的 socket.timeout，避免单源超时崩溃整个抓取进程
        return [{"_error": f"fetch fail: {e}"}]

    items = []
    parse_err = None
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        parse_err = str(e)
        root = None

    if root is not None:
        # 兼容 RSS 2.0 和 Atom
        for item in root.iter("item"):
            items.append({
                "title": (item.findtext("title") or "").strip(),
                "link": (item.findtext("link") or "").strip(),
                "pubDate": (item.findtext("pubDate") or "").strip(),
                "summary": (item.findtext("description") or "").strip()[:500],
            })
            if len(items) >= MAX_ITEMS_PER_SOURCE:
                break

        if not items:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
                title = entry.find("atom:title", ns)
                link_el = entry.find("atom:link", ns)
                summary_el = entry.find("atom:summary", ns) or entry.find("atom:content", ns)
                updated = entry.find("atom:updated", ns)
                items.append({
                    "title": (title.text or "").strip() if title is not None else "",
                    "link": link_el.get("href", "") if link_el is not None else "",
                    "pubDate": (updated.text or "").strip() if updated is not None else "",
                    "summary": ((summary_el.text or "")[:500].strip()) if summary_el is not None else "",
                })
                if len(items) >= MAX_ITEMS_PER_SOURCE:
                    break

    # 正则兑底：ElementTree 失败或解析出来是空的（如 arXiv RDF / NBER）
    if not items:
        items = _regex_fallback(content)
        if not items and parse_err:
            return [{"_error": f"parse fail: {parse_err}"}]

    return items


def main():
    parser = argparse.ArgumentParser(description="Daily fetcher for org-future-insights")
    parser.add_argument("--priority", type=int, default=2, choices=[1, 2, 3],
                        help="最低优先级（默认 2，即抓⭐⭐及以上）")
    parser.add_argument("--dry-run", action="store_true", help="不写文件")
    args = parser.parse_args()

    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    out_path = RAW_DIR / f"{today}.json"
    log_path = LOG_DIR / f"{today}.log"

    # 过滤源
    filtered = [s for s in SOURCES if s[3] >= args.priority]
    print(f"[{datetime.now().isoformat()}] 开始抓取 {len(filtered)} 个源 (priority>={args.priority})")

    bundle = {
        "snapshot_time": datetime.now(timezone.utc).astimezone().isoformat(),
        "fetcher_version": "0.1",
        "sources_count": len(filtered),
        "sources": [],
    }

    success, failure = 0, 0
    for category, name, url, priority in filtered:
        print(f"  抓 [{category}] {name} ... ", end="", flush=True)
        items = fetch_rss(url)
        if items and "_error" not in items[0]:
            bundle["sources"].append({
                "category": category,
                "name": name,
                "url": url,
                "priority": priority,
                "items": items,
                "items_count": len(items),
            })
            success += 1
            print(f"OK ({len(items)} items)")
        else:
            err = items[0].get("_error", "unknown") if items else "no items"
            bundle["sources"].append({
                "category": category,
                "name": name,
                "url": url,
                "priority": priority,
                "items": [],
                "items_count": 0,
                "error": err,
            })
            failure += 1
            print(f"FAIL ({err})")

    bundle["success_count"] = success
    bundle["failure_count"] = failure

    # 写文件
    if args.dry_run:
        print(f"\n[DRY RUN] 不写文件。会写入：{out_path}")
        print(json.dumps({"sources_count": len(filtered), "success": success, "failure": failure}, indent=2))
    else:
        out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n✅ 已写入 {out_path}（成功 {success} / 失败 {failure}）")

        # 简易 log
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} success={success} failure={failure}\n")

    # 自动归档：保留最近 30 天，老的移到 archive/
    archive_old_files()

    return 0 if success > 0 else 1


def archive_old_files():
    """保留最近 30 天 daily-raw 文件，老的移到 archive/。"""
    archive_dir = RAW_DIR / "archive"
    archive_dir.mkdir(exist_ok=True)
    today = datetime.now()
    for f in RAW_DIR.glob("*.json"):
        try:
            file_date = datetime.strptime(f.stem, "%Y-%m-%d")
            if (today - file_date).days > 30:
                f.rename(archive_dir / f.name)
        except ValueError:
            pass  # 不是日期格式的文件，跳过


if __name__ == "__main__":
    sys.exit(main())
