"""
Cloudflare Workers の /api/ingest にデータを送信するモジュール。
最大3回、指数バックオフでリトライする。
"""

import json
import time
import requests

MAX_RETRIES = 3
TIMEOUT = 30


def post_to_worker(
    worker_url: str,
    secret_token: str,
    scraped_at: str,
    snapshots: list[dict],
    transactions: list[dict],
) -> bool:
    """
    Returns:
        True on success, False on all retries failed.
    """
    payload = {
        "scraped_at": scraped_at,
        "snapshots": snapshots,
        "transactions": transactions,
    }
    headers = {
        "Authorization": f"Bearer {secret_token}",
        "Content-Type": "application/json",
    }
    url = worker_url.rstrip("/") + "/api/ingest"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
            if resp.status_code == 200:
                result = resp.json()
                print(
                    f"[ingest] 送信成功: snapshots={result.get('inserted_snapshots')}, "
                    f"transactions={result.get('inserted_transactions')}",
                    flush=True,
                )
                return True
            else:
                print(
                    f"[ingest] attempt {attempt}: HTTP {resp.status_code} - {resp.text[:200]}",
                    flush=True,
                )
        except requests.RequestException as e:
            print(f"[ingest] attempt {attempt}: リクエストエラー - {e}", flush=True)

        if attempt < MAX_RETRIES:
            wait = 2 ** attempt
            print(f"[ingest] {wait}秒後にリトライ...", flush=True)
            time.sleep(wait)

    print("[ingest] 全リトライ失敗", flush=True)
    return False
