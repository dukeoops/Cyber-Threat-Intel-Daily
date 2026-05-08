#!/usr/bin/env python3
"""
fetch_intel.py - 网络安全威胁情报数据采集脚本

用于从各大安全媒体 RSS 源和勒索情报网站爬取当日内容。
支持 13 个 RSS 源（中英文）+ 0.zone 勒索情报平台。

用法：
  python3 fetch_intel.py --date 20260508 --output /tmp/intel_raw_20260508.json

依赖：Python 3.8+ 标准库（无需额外安装）
"""

import sys
import json
import time
import hashlib
import argparse
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET
from typing import Optional


# ─── RSS 数据源配置 ───────────────────────────────────────────────────────────
# 可在此处添加、删除或修改数据源
RSS_SOURCES = {
    # 中文来源
    "安全圈":       "https://wechat2rss.xlab.app/feed/d568d6fca93d750898111f09cc3c551e7a62f7ab.xml",
    "看雪论坛":     "https://wechat2rss.xlab.app/feed/0e026637254d450ae84c59f87d4e4fb4616651ca.xml",
    "FreeBuf":      "https://www.freebuf.com/feed",
    "嗅学安全":     "https://wechat2rss.xlab.app/feed/b15a925f83a4b108b957f8dd0e8030b6caa7da5e.xml",
    # 英文来源
    "Krebs on Security":    "https://krebsonsecurity.com/feed/",
    "Threatpost":           "https://threatpost.com/feed/",
    "Dark Reading":         "https://www.darkreading.com/rss_simple.asp",
    "Schneier on Security": "https://www.schneier.com/feed/atom/",
    "CISA":                 "https://www.cisa.gov/news-events/cybersecurity-advisories/rss",
    "Ars Technica Security":"https://arstechnica.com/security/feed/",
    "The Register":         "https://www.theregister.com/security/headlines.atom",
    "Wired Security":       "https://www.wired.com/feed/category/security/latest/rss",
    "Microsoft Security":   "https://www.microsoft.com/en-us/security/blog/feed/",
}

# ─── XML 命名空间 ─────────────────────────────────────────────────────────────
NS_MAP = {
    "atom":    "http://www.w3.org/2005/Atom",
    "media":   "http://search.yahoo.com/mrss/",
    "dc":      "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


def make_request(url: str, timeout: int = 15) -> Optional[bytes]:
    """发送 HTTP 请求，返回原始字节内容；失败返回 None"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (URLError, HTTPError, Exception) as e:
        print(f"  [WARN] 请求失败 {url}: {e}", file=sys.stderr)
        return None


def parse_date(date_str: str) -> Optional[datetime]:
    """解析多种 RSS 日期格式，返回 UTC aware datetime"""
    if not date_str:
        return None
    date_str = date_str.strip()
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def is_today_or_recent(pub_date: Optional[datetime], target_date: datetime, days: int = 1) -> bool:
    """判断文章是否在 target_date 当天或近 days 天内"""
    if pub_date is None:
        return True  # 无法判断时默认保留
    delta = abs((target_date.date() - pub_date.date()).days)
    return delta <= days


def extract_text(element, *paths: str) -> str:
    """尝试多个 XPath 路径，返回第一个非空文本"""
    for path in paths:
        node = element.find(path, NS_MAP)
        if node is not None and node.text:
            return node.text.strip()
    return ""


def strip_html(text: str) -> str:
    """简单去除 HTML 标签"""
    import re
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_rss_feed(content: bytes, source_name: str, target_date: datetime) -> list:
    """解析 RSS/Atom 内容，返回符合日期的文章列表"""
    articles = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"  [WARN] XML 解析错误 ({source_name}): {e}", file=sys.stderr)
        return articles

    tag = root.tag.lower()
    is_atom = "atom" in tag or root.tag == "{http://www.w3.org/2005/Atom}feed"

    if is_atom:
        items = root.findall("atom:entry", NS_MAP) or root.findall(
            "{http://www.w3.org/2005/Atom}entry"
        )
    else:
        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else root.findall(".//item")

    for item in items:
        if is_atom:
            title = extract_text(item, "atom:title", "{http://www.w3.org/2005/Atom}title")
            link_node = item.find("atom:link", NS_MAP) or item.find(
                "{http://www.w3.org/2005/Atom}link"
            )
            link = ""
            if link_node is not None:
                link = link_node.get("href", link_node.text or "")
            pub_str = extract_text(
                item,
                "atom:published", "atom:updated",
                "{http://www.w3.org/2005/Atom}published",
                "{http://www.w3.org/2005/Atom}updated",
            )
            summary = extract_text(
                item,
                "atom:summary", "atom:content",
                "{http://www.w3.org/2005/Atom}summary",
                "{http://www.w3.org/2005/Atom}content",
            )
        else:
            title   = extract_text(item, "title")
            link    = extract_text(item, "link")
            pub_str = extract_text(item, "pubDate", "dc:date")
            summary = extract_text(item, "description", "content:encoded")

        pub_date = parse_date(pub_str)
        if not is_today_or_recent(pub_date, target_date, days=1):
            continue

        summary = strip_html(summary)[:500]
        articles.append({
            "source":   source_name,
            "title":    title,
            "link":     link,
            "pub_date": pub_date.isoformat() if pub_date else "",
            "summary":  summary,
        })

    return articles


def fetch_all_rss(target_date: datetime, extra_feeds: dict = None) -> list:
    """抓取所有 RSS 源（含可选的自定义源）"""
    sources = dict(RSS_SOURCES)
    if extra_feeds:
        sources.update(extra_feeds)

    all_articles = []
    for name, url in sources.items():
        print(f"  抓取 {name} ...", file=sys.stderr)
        content = make_request(url)
        if content:
            articles = parse_rss_feed(content, name, target_date)
            print(f"    → 获取 {len(articles)} 条", file=sys.stderr)
            all_articles.extend(articles)
        time.sleep(0.3)  # 礼貌性延迟，避免过快请求

    return all_articles


def fetch_ransomware_intel(date_str: str) -> list:
    """
    爬取 0.zone 勒索情报页面
    date_str 格式: YYYYMMDD，如 20260508
    """
    url = f"https://0.zone/article/{date_str}"
    print(f"  抓取勒索情报 {url} ...", file=sys.stderr)

    content = make_request(url)
    if not content:
        return []

    try:
        html = content.decode("utf-8", errors="replace")
    except Exception:
        return []

    import re

    items = []
    pattern_link = re.compile(
        r'<a[^>]+href="(/article/[^"]+)"[^>]*>\s*(.*?)\s*</a>', re.DOTALL
    )

    seen = set()
    for m in pattern_link.finditer(html):
        href, text = m.groups()
        text = strip_html(text).strip()
        if not text or len(text) < 5:
            continue
        full_url = f"https://0.zone{href}"
        key = hashlib.md5(full_url.encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        items.append({
            "source":   "0.zone 勒索情报",
            "title":    text,
            "link":     full_url,
            "pub_date": date_str,
            "summary":  "",
        })

    # fallback：若正则未命中，提取段落文本
    if not items:
        text_blocks = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL)
        for block in text_blocks[:20]:
            text = strip_html(block).strip()
            if text and len(text) > 20:
                items.append({
                    "source":   "0.zone 勒索情报",
                    "title":    text[:100],
                    "link":     url,
                    "pub_date": date_str,
                    "summary":  text[:300],
                })

    print(f"    → 获取 {len(items)} 条勒索情报", file=sys.stderr)
    return items


def main():
    parser = argparse.ArgumentParser(
        description="爬取网络安全威胁情报（RSS + 0.zone 勒索情报）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 抓取今日情报
  python3 fetch_intel.py --output /tmp/intel_raw.json

  # 抓取指定日期
  python3 fetch_intel.py --date 20260508 --output /tmp/intel_raw_20260508.json

  # 只抓取 RSS，跳过勒索情报
  python3 fetch_intel.py --no-ransomware --output /tmp/intel_raw.json
        """
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y%m%d"),
        help="目标日期，格式 YYYYMMDD（默认今天）",
    )
    parser.add_argument(
        "--output", "-o",
        default="-",
        help="输出 JSON 文件路径，默认 stdout（-）",
    )
    parser.add_argument(
        "--no-ransomware",
        action="store_true",
        help="跳过 0.zone 勒索情报抓取",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="可选：config.json 路径，用于加载自定义 RSS 源",
    )
    args = parser.parse_args()

    date_str = args.date
    target_date = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)

    print(f"\n[fetch_intel] 目标日期: {date_str}", file=sys.stderr)
    print("=" * 50, file=sys.stderr)

    # 加载自定义 RSS 源
    extra_feeds = {}
    if args.config:
        import os
        config_path = os.path.expanduser(args.config)
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as f:
                cfg = json.load(f)
            for feed in cfg.get("sources", {}).get("custom_rss_feeds", []):
                if feed.get("name") and feed.get("url"):
                    extra_feeds[feed["name"]] = feed["url"]

    # 抓取 RSS
    rss_articles = fetch_all_rss(target_date, extra_feeds)

    # 抓取勒索情报
    ransomware_items = []
    if not args.no_ransomware:
        ransomware_items = fetch_ransomware_intel(date_str)

    result = {
        "date":             date_str,
        "fetched_at":       datetime.now(timezone.utc).isoformat(),
        "rss_articles":     rss_articles,
        "ransomware_intel": ransomware_items,
        "stats": {
            "rss_count":        len(rss_articles),
            "ransomware_count": len(ransomware_items),
            "total":            len(rss_articles) + len(ransomware_items),
        },
    }

    print(f"\n[fetch_intel] 共抓取 {result['stats']['total']} 条情报", file=sys.stderr)

    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output == "-":
        print(output_json)
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"[fetch_intel] 已保存至 {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
