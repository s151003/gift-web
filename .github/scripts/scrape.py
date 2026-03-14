"""
メインスクレイパー。4サイトを並列スクレイプし、Workers APIに送信する。

環境変数:
  INGEST_SECRET_TOKEN  - Workers APIのBearerトークン
  WORKER_URL           - WorkersのベースURL（例: https://gift-web-api.xxx.workers.dev）
"""

import os
import sys
import time
import importlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests

# sites/ ディレクトリをインポートパスに追加
sys.path.insert(0, os.path.dirname(__file__))

from post_to_worker import post_to_worker

SITES = ["ama_gift", "giftissue", "beterugift", "amaten"]
REQUEST_TIMEOUT = 15
MAX_RETRIES = 2
RETRY_WAIT = 1.0


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ja,en;q=0.9",
    })
    return session


def scrape_site_with_retry(module, session: requests.Session) -> tuple[str, object]:
    site_name = module.SITE_NAME
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = module.scrape(session)
            if result is not None:
                print(f"[{site_name}] 成功 (attempt {attempt})", flush=True)
                return site_name, result
            print(f"[{site_name}] attempt {attempt}: scrape() が None を返しました", flush=True)
        except Exception as e:
            print(f"[{site_name}] attempt {attempt}: 例外 - {e}", flush=True)
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_WAIT)
    print(f"[{site_name}] 全試行失敗", flush=True)
    return site_name, None


def main() -> int:
    worker_url = os.environ.get("WORKER_URL")
    secret_token = os.environ.get("INGEST_SECRET_TOKEN")

    if not worker_url or not secret_token:
        print("エラー: WORKER_URL と INGEST_SECRET_TOKEN 環境変数が必要です", file=sys.stderr)
        return 1

    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[scrape] 開始: {scraped_at}", flush=True)

    # モジュールをロード
    modules = {}
    for site in SITES:
        try:
            mod = importlib.import_module(f"sites.{site}")
            modules[site] = mod
        except ImportError as e:
            print(f"[{site}] モジュールロード失敗: {e}", flush=True)

    session = make_session()

    # 並列スクレイプ
    snapshots: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(scrape_site_with_retry, mod, session): site
            for site, mod in modules.items()
        }
        for future in as_completed(futures):
            site_name, result = future.result()
            if result is not None:
                snapshots.append(result)

    # 取引履歴（対応サイトのみ）
    transactions: list[dict] = []
    for site, mod in modules.items():
        if hasattr(mod, "scrape_transactions"):
            try:
                txs = mod.scrape_transactions(session)
                print(f"[{site}] 取引履歴: {len(txs)}件", flush=True)
                transactions.extend(txs)
            except Exception as e:
                print(f"[{site}] 取引履歴取得エラー: {e}", flush=True)

    print(f"[scrape] スナップショット: {len(snapshots)}/{len(modules)}サイト成功", flush=True)
    print(f"[scrape] 取引履歴: {len(transactions)}件", flush=True)

    # 全サイト失敗の場合はエラー終了
    if len(snapshots) == 0:
        print("[scrape] 全サイト失敗。送信しません。", file=sys.stderr)
        return 1

    # Workers に送信
    success = post_to_worker(
        worker_url=worker_url,
        secret_token=secret_token,
        scraped_at=scraped_at,
        snapshots=snapshots,
        transactions=transactions,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
