#!/usr/bin/env python3
"""Telegram gold price channel scraper (Task A).

Dùng Telethon (MTProto) — cần Telegram API credentials:
  1. Tạo app tại https://my.telegram.org/apps → API_ID, API_HASH
  2. export TELEGRAM_API_ID=... TELEGRAM_API_HASH=...
  3. Chạy lần đầu: nhập phone + OTP để tạo session (telegram.session)
  4. python scripts/telegram_gold_scraper.py goldpricevietnam --limit 200

Lưu ý: @goldpricevietnam hiện là user/bot (không phải public channel có
web preview), nên BẮT BUỘC dùng MTProto — HTTP scraping không đọc được.

Output: JSON report (số posts, tần suất, format giá, insight) +
filtered gold-price posts (Vàng nhẫn / tân đinh / SJC / mua-bán / rates).
"""

import argparse
import asyncio
import json
import os
import re
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

# Từ khóa lọc giá vàng (VI + CN + RU như đề bài)
GOLD_KEYWORDS = [
    "vàng", "vang", "gold", "tân đinh", "tan dinh", "sjc", "nhẫn", "nhan",
    "金价", "黄金", "куп", "золот", "mua", "bán", "ban ", "rate", "giá",
]
PRICE_PATTERN = re.compile(
    r"(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*(k|tr|triệu|nghìn|vnd|usd)?",
    re.I,
)


def is_gold_post(text: str) -> bool:
    lower = (text or "").lower()
    hits = sum(1 for kw in GOLD_KEYWORDS if kw in lower)
    return hits >= 2 and bool(PRICE_PATTERN.search(lower))


def extract_prices(text: str) -> list[dict]:
    """Trích xuất cặp giá mua/bán nếu có format 'X/Y' hoặc 'mua X bán Y'."""
    prices = []
    lower = text or ""
    # Format: 78.5/79.0 hoặc 78,5-79,0
    for m in re.finditer(
        r"(\d{1,3}(?:[.,]\d+)?)\s*(?:[/\\-]\s*|/\s*)(\d{1,3}(?:[.,]\d+)?)", lower
    ):
        prices.append({"raw": m.group(0).strip(),
                       "buy": m.group(1), "sell": m.group(2)})
    if not prices:
        for m in PRICE_PATTERN.finditer(lower):
            prices.append({"raw": m.group(0).strip()})
    return prices[:10]


async def scrape(channel: str, limit: int, output: str) -> dict:
    try:
        from telethon import TelegramClient
    except ImportError:
        sys.exit("Cần cài telethon: pip install telethon")

    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    async with TelegramClient("telegram", api_id, api_hash) as client:
        entity = await client.get_entity(channel)
        meta = {
            "name": getattr(entity, "title", None) or getattr(entity, "first_name", channel),
            "username": getattr(entity, "username", channel),
            "type": type(entity).__name__,
            "members": getattr(entity, "participants_count", None),
            "description": (getattr(entity, "about", "") or "")[:500],
        }
        posts = []
        async for msg in client.iter_messages(entity, limit=limit):
            if not msg.message:
                continue
            posts.append({
                "id": msg.id,
                "date": msg.date.isoformat() if msg.date else None,
                "text": msg.message,
                "is_gold": is_gold_post(msg.message),
                "prices": extract_prices(msg.message) if is_gold_post(msg.message) else [],
            })

    gold_posts = [p for p in posts if p["is_gold"]]
    dates = [datetime.fromisoformat(p["date"]) for p in posts if p["date"]]
    gold_dates = [datetime.fromisoformat(p["date"]) for p in gold_posts if p["date"]]

    span_days = ((max(dates) - min(dates)).days if len(dates) > 1 else 0) or 1
    report = {
        "channel": meta,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "total_posts": len(posts),
        "gold_posts": len(gold_posts),
        "post_frequency_per_day": round(len(posts) / span_days, 2),
        "gold_post_frequency_per_day": round(len(gold_posts) / span_days, 2),
        "date_range": {
            "from": min(dates).isoformat() if dates else None,
            "to": max(dates).isoformat() if dates else None,
        },
        "price_format_insight": {
            "common_units": dict(Counter(
                m.group(1).lower()
                for p in gold_posts for pr in p["prices"]
                for m in [re.search(r"(k|tr|triệu|nghìn|vnd|usd)$", pr["raw"], re.I)]
                if m).most_common(5)),
            "posts_with_buy_sell_pair": sum(
                1 for p in gold_posts if any("buy" in pr for pr in p["prices"])),
        },
        "gold_posts_detail": gold_posts[:100],
    }
    with open(output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Saved {output}: {len(posts)} posts, {len(gold_posts)} gold posts")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("channel", nargs="?", default="goldpricevietnam")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--output", default="gold_channel_report.json")
    args = parser.parse_args()
    asyncio.run(scrape(args.channel, args.limit, args.output))


if __name__ == "__main__":
    main()