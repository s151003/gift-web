"""
アマテン (https://amaten.com/) スクレイパー

出品一覧URL:
  amazon      -> /exhibitions/amazon
  apple       -> /exhibitions/itunes
  google_play -> /exhibitions/google_play

サーバーレンダリング（requests で直接取得可能）

各 tbody tr のtd構造:
  td.ftlg13.ftmd13 [0] -> 枚数 "2 点"
  td.ftlg20.ftmd20     -> 額面 "50,000 円"
  td.ftlg22.ftmd22     -> 販売価格 "47,500 円"
  td.ftlg13.ftmd13 [1] -> 率・割引額 "95 % │ 2,500 円OFF"  ← ここから率を取得（2番目）
  td.ftlg13.ftmd13 [2] -> エラー/出品数 "1126 / 14379"
  td.ftlg13.ftmd13 [3] -> ボタン "買 う"

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
BASE_URL = "https://amaten.com"
TIMEOUT = 15

CATEGORIES: dict[str, str] = {
    "amazon": "/exhibitions/amazon",
    "apple": "/exhibitions/itunes",
    "google_play": "/exhibitions/google_play",
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
    discount_rates: list[float] = []
    for tr in soup.select("tbody tr"):
        ftlg13_tds = tr.select("td.ftlg13")
        if len(ftlg13_tds) < 2:
            continue
        text = ftlg13_tds[1].get_text(" ", strip=True)
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        if not m:
            continue
        try:
            payment_rate = float(m.group(1))
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
