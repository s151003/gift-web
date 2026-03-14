# 実装進捗ドキュメント
## ギフト券取引価格履歴確認システム

**開始日:** 2026-03-14

---

## 実装フェーズ一覧

| # | フェーズ | 状態 | 完了日 |
|---|---------|------|--------|
| 1 | Cloudflare D1 データベース作成 | ✅ 完了 | 2026-03-14 |
| 2 | D1 スキーマ適用（テーブル作成） | ✅ 完了 | 2026-03-14 |
| 3 | Cloudflare Workers API 実装 | ✅ 完了 | 2026-03-14 |
| 4 | React フロントエンド実装 | ✅ 完了 | 2026-03-14 |
| 5 | GitHub Actions スクレイパー実装 | ✅ 完了 | 2026-03-14 |
| 6 | デプロイ CI ワークフロー作成 | ✅ 完了 | 2026-03-14 |
| 7 | Workers デプロイ・シークレット設定 | 🔲 未着手（手動作業が必要） | — |
| 8 | 各サイトのスクレイパーをHTMLに合わせて調整 | 🔲 未着手 | — |

---

## Cloudflare リソース

| リソース | 名前 / ID | 備考 |
|---------|----------|------|
| D1 Database | gift-web-db | APAC リージョン |
| D1 Database ID | `1e0e3556-ac72-4526-8022-eedeba78ecf6` | |
| Cloudflare Account ID | `b492c78e54ae6fd7144719bcc5799bd3` | |
| Workers | gift-web-api | `wrangler deploy` で公開 |
| Pages | gift-web-frontend | GitHub Actions で自動デプロイ |

---

## ディレクトリ構造

```
gift-web/
├── アーキテクチャ設計書.md
├── PROGRESS.md               ← このファイル
├── worker/                   ← Cloudflare Workers API
│   ├── src/
│   │   └── index.ts          ← 全エンドポイント実装済み
│   ├── wrangler.toml         ← D1バインディング設定済み
│   ├── package.json
│   └── tsconfig.json
├── frontend/                 ← React (Vite) フロントエンド
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx           ← メイン画面
│   │   ├── api.ts            ← API クライアント
│   │   ├── types.ts          ← 型定義
│   │   ├── index.css
│   │   └── components/
│   │       ├── SummaryCard.tsx      ← 取引所サマリーカード
│   │       ├── PriceChart.tsx       ← ApexCharts 時系列グラフ
│   │       └── TransactionsTable.tsx ← 取引履歴テーブル
│   ├── .env.example
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── postcss.config.js
└── .github/
    ├── workflows/
    │   ├── scrape.yml              ← 毎時スクレイプ（cron）
    │   ├── deploy-worker.yml       ← Workers 自動デプロイ
    │   └── deploy-frontend.yml     ← Pages 自動デプロイ
    └── scripts/
        ├── scrape.py               ← メインスクレイパー
        ├── post_to_worker.py       ← Workers API 送信（リトライ付き）
        └── sites/
            ├── ama_gift.py
            ├── giftissue.py
            ├── beterugift.py       ← JSON エンドポイント対応
            └── amaten.py           ← 取引履歴取得対応
```

---

## 次に必要な手動作業

### 1. Workers をデプロイする
```bash
cd worker
npm install
npx wrangler deploy
# Workers の URL をメモしておく（例: https://gift-web-api.xxx.workers.dev）
```

### 2. Workers の環境変数（シークレット）を設定する
```bash
# Ingest API のトークン（任意の文字列でOK）
npx wrangler secret put INGEST_SECRET_TOKEN

# フロントエンドのオリジン（Pages デプロイ後に設定）
npx wrangler secret put FRONTEND_ORIGIN
# 例: https://gift-web-frontend.pages.dev
```

### 3. フロントエンドの .env を設定する
```bash
cd frontend
cp .env.example .env
# VITE_API_BASE_URL に Workers の URL を記入
```

### 4. GitHub リポジトリのシークレットを設定する
GitHub リポジトリの Settings > Secrets and variables > Actions に以下を追加:

| シークレット名 | 値 |
|---|---|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API トークン（Workers/Pages デプロイ権限） |
| `INGEST_SECRET_TOKEN` | Workersに設定したのと同じトークン |
| `WORKER_URL` | Workers の URL |
| `VITE_API_BASE_URL` | Workers の URL |

### 5. Cloudflare Pages プロジェクトを作成する
```bash
cd frontend
npm run build
npx wrangler pages project create gift-web-frontend
npx wrangler pages deploy dist --project-name gift-web-frontend
```

### 6. 各サイトのスクレイパーを実際のHTMLに合わせて調整する
- 各サイトの HTML 構造を手動で確認
- `.github/scripts/sites/*.py` のCSSセレクタを修正
- ローカルで動作確認 → スクレイパーのみ単体テスト可能

---

## 詳細ログ

### 2026-03-14
- 設計書確認・実装開始
- PROGRESS.md 作成
- Cloudflare アカウント確認 (ID: b492c78e54ae6fd7144719bcc5799bd3)
- D1 データベース作成 (gift-web-db, APAC, ID: 1e0e3556-ac72-4526-8022-eedeba78ecf6)
- D1 スキーマ適用（price_snapshots, transactions テーブル + インデックス）
- Cloudflare Workers API 実装完了（全5エンドポイント + バリデーション + CORS）
- React フロントエンド実装完了（SummaryCard, PriceChart, TransactionsTable）
- GitHub Actions スクレイパー実装完了（4サイト並列 + リトライ + 部分失敗許容）
- CI/CD ワークフロー作成（Workers デプロイ, Pages デプロイ, スクレイプ cron）

---

## 未決事項（設計書 §9 より）

| 項目 | 状態 |
|------|------|
| 各サイトの取引履歴有無の確認 | 🔲 スクレイパー調整時に確認 |
| beterugift の JSON エンドポイント確認 | 🔲 実装済み（フォールバックあり）、実動作確認が必要 |
| `traded_at` のタイムゾーン | 🔲 amaten は JST→UTC 変換実装済み、他サイトは確認後対応 |
