"""
ギフトイシュー (https://giftissue.com/) スクレイパー

出品一覧URL: /ja/category/amazonjp/
各出品要素: .giftList_cell-facevalue
  span[0] (クラスなし) -> "¥ 3,000"  (額面)
  span[1].giftList_rate -> "93.5 %"  (販売率 = 支払い割合)
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
LIST_URL = "https://giftissue.com/ja/category/amazonjp/"
TIMEOUT = 15


def scrape(session: requests.Session) -> Optional[dict]:
    for attempt in range(1, 3):
        try:
            resp = session.get(LIST_URL, timeout=TIMEOUT)
            resp.raise_for_status()
            break
        except requests.RequestException as e:
            print(f"[{SITE_NAME}] attempt {attempt}: {e}", flush=True)
            if attempt == 2:
                return None
            time.sleep(1)

    soup = BeautifulSoup(resp.text, "lxml")
    cells = soup.select(".giftList_cell-facevalue")

    if not cells:
        print(f"[{SITE_NAME}] .giftList_cell-facevalue が見つかりません", flush=True)
        return None

    discount_rates: list[float] = []
    for cell in cells:
        # スマホ用に重複している場合は .giftList_spText のみ使う
        rate_span = cell.select_one(".giftList_rate.giftList_spText")
        if not rate_span:
            rate_span = cell.select_one(".giftList_rate")
        if not rate_span:
            continue
        try:
            payment_rate = float(re.sub(r"[^\d.]", "", rate_span.get_text()))
            if not (0 < payment_rate <= 100):
                continue
            discount = round(100 - payment_rate, 2)
            discount_rates.append(discount)
        except ValueError:
            continue

    if not discount_rates:
        print(f"[{SITE_NAME}] 割引率データが取得できませんでした", flush=True)
        return None

    discount_rates.sort(reverse=True)
    return {
        "site_name": SITE_NAME,
        "listing_count": len(discount_rates),
        "best_discount_rate": round(discount_rates[0], 2),
        "worst_discount_rate": round(discount_rates[-1], 2),
        "avg_discount_rate": round(statistics.mean(discount_rates), 2),
        "median_discount_rate": round(statistics.median(discount_rates), 2),
    }
