"""
アマテン (https://amaten.com/) スクレイパー

出品一覧URL: /exhibitions/amazon
サーバーレンダリング（requests で直接取得可能）

各 tbody tr のtd構造:
  td.ftlg20.ftmd20 -> 額面 "50,000 円"
  td.ftlg22.ftmd22 -> 販売価格 "47,500 円"
  td.ftlg13.ftmd13 -> 率・割引額 "95 % │ 2,500 円OFF"  ← ここから率を取得

割引率 = 100 - 販売率（95% → 5%）

注: 取引履歴はログイン必須のため取得しない
"""

import re
import statistics
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

SITE_NAME = "amaten"
LIST_URL = "https://amaten.com/exhibitions/amazon"
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

    discount_rates: list[float] = []
    for tr in soup.select("tbody tr"):
        # 販売率セル: "95 % │ 2,500 円OFF" のようなテキストを含む td.ftlg13
        rate_td = tr.select_one("td.ftlg13")
        if not rate_td:
            continue
        text = rate_td.get_text(" ", strip=True)
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        if not m:
            continue
        try:
            payment_rate = float(m.group(1))
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
