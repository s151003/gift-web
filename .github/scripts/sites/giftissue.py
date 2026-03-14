"""
ギフトイシュー (https://giftissue.com/) スクレイパー

出品一覧URL:
  amazon      -> /ja/category/amazonjp/
  apple       -> /ja/category/itunes/
  google_play -> /ja/category/google-play/

各出品要素: .giftList_cell-facevalue
  span.giftList_rate.giftList_spText -> "93.5 %" (販売率)
割引率 = 100 - 販売率

サーバーレンダリング（requests で直接取得可能）
"""

import re
import statistics
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

SITE_NAME = "giftissue"
BASE_URL = "https://giftissue.com"
TIMEOUT = 15

CATEGORIES: dict[str, str] = {
    "amazon": "/ja/category/amazonjp/",
    "apple": "/ja/category/itunes/",
    "google_play": "/ja/category/google-play/",
}


def _scrape_one(session: requests.Session, card_type: str, path: str) -> Optional[dict]:
    url = BASE_URL + path
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
    cells = soup.select(".giftList_cell-facevalue")
    if not cells:
        print(f"[{SITE_NAME}/{card_type}] .giftList_cell-facevalue が見つかりません", flush=True)
        return None

    discount_rates: list[float] = []
    for cell in cells:
        rate_span = cell.select_one(".giftList_rate.giftList_spText") or cell.select_one(".giftList_rate")
        if not rate_span:
            continue
        try:
            payment_rate = float(re.sub(r"[^\d.]", "", rate_span.get_text()))
            if not (0 < payment_rate <= 100):
                continue
            discount_rates.append(round(100 - payment_rate, 2))
        except ValueError:
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
    for card_type, path in CATEGORIES.items():
        data = _scrape_one(session, card_type, path)
        if data:
            results.append(data)
    return results
