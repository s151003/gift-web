"""
アマギフト (https://ama-gift.com/) スクレイパー

出品一覧URL: /list.php?search_type=<N>
  amazon      -> search_type=0
  apple       -> search_type=1
  google_play -> search_type=2

テーブル: table.sale_list
各行の hidden input:
  name="vamo"  -> 額面（円）
  name="rate"  -> 販売率（%）例: 84.5 = 84.5%支払い -> 割引率 = 100 - 84.5 = 15.5%
"""

import re
import statistics
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

SITE_NAME = "ama-gift"
BASE_URL = "https://ama-gift.com/list.php"
TIMEOUT = 15

CATEGORIES: dict[str, int] = {
    "amazon": 0,
    "apple": 1,
    "google_play": 2,
}


def _scrape_one(session: requests.Session, card_type: str, search_type: int) -> Optional[dict]:
    url = f"{BASE_URL}?search_type={search_type}"
    for attempt in range(1, 3):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            break
        except requests.RequestException as e:
            print(f"[{SITE_NAME}/{card_type}] attempt {attempt}: {e}", flush=True)
            if attempt == 2:
                return None
            time.sleep(1)

    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.select_one("table.sale_list")
    if not table:
        print(f"[{SITE_NAME}/{card_type}] table.sale_list が見つかりません", flush=True)
        return None

    discount_rates: list[float] = []
    for form in table.select("form"):
        vamo = form.select_one('input[name="vamo"]')
        rate_input = form.select_one('input[name="rate"]')
        if not vamo or not rate_input:
            continue
        try:
            face = int(vamo["value"])
            payment_rate = float(rate_input["value"])
            if face <= 0 or not (0 < payment_rate <= 100):
                continue
            discount_rates.append(round(100 - payment_rate, 2))
        except (ValueError, KeyError):
            continue

    if not discount_rates:
        print(f"[{SITE_NAME}/{card_type}] 割引率データが取得できませんでした", flush=True)
        return None

    discount_rates.sort(reverse=True)
    return {
        "site_name": SITE_NAME,
        "card_type": card_type,
        "listing_count": len(discount_rates),
        "best_discount_rate": round(discount_rates[0], 2),
        "worst_discount_rate": round(discount_rates[-1], 2),
        "avg_discount_rate": round(statistics.mean(discount_rates), 2),
        "median_discount_rate": round(statistics.median(discount_rates), 2),
    }


def scrape(session: requests.Session) -> list[dict]:
    results = []
    for card_type, search_type in CATEGORIES.items():
        data = _scrape_one(session, card_type, search_type)
        if data:
            results.append(data)
    return results
