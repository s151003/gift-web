"""
べてるギフト (https://beterugift.jp/) スクレイパー

出品一覧はjQuery AJAXで取得: /home/load/1?_=<timestamp>
（Amazon = カテゴリID 1）
レスポンスはHTML（JSONではない）。

テーブル構造（tbody tr の td インデックス）:
  td[0]: 空
  td[1]: 残り枚数 "1点"
  td[2]: 額面 "5,000 円"                        class="smartphone_hide center"
  td[3]: 価格・率 "4,225円 | 84.5% | 775円OFF"  class="smartphone_hide ft125 center"
  td[4]: エラー率
  td[5..]: スマホ用（重複）

割引率 = 100 - 販売率（84.5% → 15.5%）
"""

import re
import statistics
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

SITE_NAME = "beterugift"
BASE_URL = "https://beterugift.jp"
TIMEOUT = 15
AMAZON_CATEGORY_ID = 1


def scrape(session: requests.Session) -> Optional[dict]:
    url = f"{BASE_URL}/home/load/{AMAZON_CATEGORY_ID}?_={int(time.time() * 1000)}"
    for attempt in range(1, 3):
        try:
            resp = session.get(url, timeout=TIMEOUT)
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
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
        rate_td = tds[3]
        # "smartphone_hide ft125 center" であることを確認
        if "ft125" not in rate_td.get("class", []):
            continue
        text = rate_td.get_text(" ", strip=True)
        # "4,225円 | 84.5% | 775円OFF" から "84.5" を抽出
        m = re.search(r"(\d+(?:\.\d+))\s*%", text)
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
