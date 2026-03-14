"""
べてるギフト (https://beterugift.jp/) スクレイパー

出品一覧はjQuery AJAXで取得: /home/load/<category_id>?_=<timestamp>
  amazon      -> category_id=1
  apple       -> category_id=2
  google_play -> category_id=3
レスポンスはHTML（JSONではない）。

【出品一覧テーブル】tbody tr の td 構成:
  td[0]: 空
  td[1]: 残り枚数 "1点"
  td[2]: 額面 "5,000 円"                        class="smartphone_hide center"
  td[3]: 価格・率 "4,225円 | 84.5% | 775円OFF"  class="smartphone_hide ft125 center"
  td[4]: エラー率
  td[5..]: スマホ用（重複）

【取引履歴テーブル】同ページの2番目のtable (heading="直近取引履歴")
  td[0]: class="table_pics" → img src末尾が "<category_id>.jpg" ならその券種
  td[1]: class="trlist" → 日時 "03/14 21:47"（JST, MM/DD HH:MM, 重複）
  td[2]: class="trlist" → 額面 "10,000円"（重複）
  td[3]: class="trlist" → 成立価格 "8,450円"（重複）
  td[4]: class="trlist" → 販売率 "84.5%"（重複）

割引率 = 100 - 販売率（84.5% → 15.5%）
"""

import re
import statistics
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup

SITE_NAME = "beterugift"
BASE_URL = "https://beterugift.jp"
TIMEOUT = 15
JST = timezone(timedelta(hours=9))

CATEGORIES: dict[str, int] = {
    "amazon": 1,
    "apple": 2,
    "google_play": 3,
}


def _fetch_soup(session: requests.Session, category_id: int) -> Optional[BeautifulSoup]:
    url = f"{BASE_URL}/home/load/{category_id}?_={int(time.time() * 1000)}"
    for attempt in range(1, 3):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as e:
            print(f"[{SITE_NAME}] attempt {attempt}: {e}", flush=True)
            if attempt < 2:
                time.sleep(1)
    return None


def _scrape_one(session: requests.Session, card_type: str, category_id: int) -> Optional[dict]:
    soup = _fetch_soup(session, category_id)
    if soup is None:
        return None

    discount_rates: list[float] = []
    for tr in soup.select("tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
        rate_td = tds[3]
        if "ft125" not in rate_td.get("class", []):
            continue
        text = rate_td.get_text(" ", strip=True)
        m = re.search(r"(\d+(?:\.\d+))\s*%", text)
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
    for card_type, category_id in CATEGORIES.items():
        data = _scrape_one(session, card_type, category_id)
        if data:
            results.append(data)
    return results


def scrape_transactions(session: requests.Session) -> list[dict]:
    """べてるギフトの直近取引履歴（全対応券種）を取得する。

    同ページの2番目の table から、td.table_pics の img src が
    "<category_id>.jpg" で終わる行だけを各券種ごとに抽出。
    日時は JST "MM/DD HH:MM" 形式 → 現在年を付加して UTC に変換。
    年跨ぎ対策: 変換後の日時が未来なら前年を使う。
    """
    all_results: list[dict] = []
    now_jst = datetime.now(JST)

    for card_type, category_id in CATEGORIES.items():
        soup = _fetch_soup(session, category_id)
        if soup is None:
            continue

        tables = soup.select("table")
        if len(tables) < 2:
            print(f"[{SITE_NAME}/{card_type}] 取引履歴テーブルが見つかりません", flush=True)
            continue

        history_table = tables[1]
        results: list[dict] = []

        for tr in history_table.select("tbody tr"):
            pics_td = tr.select_one("td.table_pics")
            if not pics_td:
                continue
            img = pics_td.select_one("img")
            if not img:
                continue
            src = img.get("src", "")
            if not src.endswith(f"{category_id}.jpg"):
                continue

            trlist_tds = tr.select("td.trlist")
            if len(trlist_tds) < 4:
                continue

            date_raw = trlist_tds[0].get_text(" ", strip=True)
            face_raw = trlist_tds[1].get_text(" ", strip=True)
            price_raw = trlist_tds[2].get_text(" ", strip=True)
            rate_raw = trlist_tds[3].get_text(" ", strip=True)

            m_date = re.search(r"(\d{2}/\d{2} \d{2}:\d{2})", date_raw)
            if not m_date:
                continue
            try:
                dt_jst = datetime.strptime(
                    f"{now_jst.year}/{m_date.group(1)}", "%Y/%m/%d %H:%M"
                ).replace(tzinfo=JST)
                if dt_jst > now_jst + timedelta(hours=1):
                    dt_jst = dt_jst.replace(year=dt_jst.year - 1)
                traded_at = dt_jst.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                continue

            m_face = re.search(r"([\d,]+)円", face_raw)
            if not m_face:
                continue
            try:
                face_value = int(m_face.group(1).replace(",", ""))
            except ValueError:
                continue

            m_price = re.search(r"([\d,]+)円", price_raw)
            if not m_price:
                continue
            try:
                traded_price = int(m_price.group(1).replace(",", ""))
            except ValueError:
                continue

            m_rate = re.search(r"(\d+(?:\.\d+)?)\s*%", rate_raw)
            if not m_rate:
                continue
            try:
                payment_rate = float(m_rate.group(1))
                if not (0 < payment_rate <= 100):
                    continue
                discount_rate = round(100 - payment_rate, 2)
            except ValueError:
                continue

            results.append({
                "site_name": SITE_NAME,
                "card_type": card_type,
                "traded_at": traded_at,
                "face_value": face_value,
                "traded_price": traded_price,
                "discount_rate": discount_rate,
            })

        print(f"[{SITE_NAME}/{card_type}] 取引履歴 {len(results)} 件取得", flush=True)
        all_results.extend(results)

    return all_results
