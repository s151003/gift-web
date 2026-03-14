# スクレイパー HTML 構造調査メモ

**調査日:** 2026-03-14
**調査方法:** Chrome MCP でリアルタイムに各サイトのDOM・ネットワークリクエストを確認

---

## 共通メモ

全サイトとも「割引率」ではなく **「販売率（支払い割合）%」** を表示している。

```
割引率 = 100 - 販売率
例: 販売率 84.5% → 割引率 15.5%
```

---

## 1. アマギフト（ama-gift.com）

### 調査URL

| 用途 | URL |
|------|-----|
| Amazon出品一覧 | `https://ama-gift.com/list.php?search_type=0` |
| トップ（取引履歴） | `https://ama-gift.com/` |

### レンダリング方式
**サーバーレンダリング** → `requests` で直接取得可能

### 出品一覧の HTML 構造

```html
<table class="sale_list">
  <tr>
    <th>券種</th>
    <th>残り</th>
    <th>額面</th>
    <th>販売価格</th>
    <th>販売率</th>
    <th></th>
  </tr>
  <tr>
    <td><img class="list_icon" ...></td>
    <td class="right"><span class="fln">1</span>枚</td>
    <td class="right"><span class="fln bl">7,250</span>円</td>   <!-- 額面 -->
    <td class="right"><span class="fln rd">6,815</span>円</td>   <!-- 販売価格 -->
    <td class="right"><span class="fln yl">94.0</span>％</td>    <!-- 販売率 -->
    <td class="right">
      <form action="" method="post">
        <input class="list_btn" type="submit" name="buy" value="購入する">
        <input type="hidden" name="vamo" value="7250">   <!-- 額面（数値） -->
        <input type="hidden" name="rate" value="94.0">   <!-- 販売率（数値） -->
        <input type="hidden" name="s_uid" value="20120"> <!-- 出品者ID -->
      </form>
    </td>
  </tr>
</table>
```

### パース方法

```python
table = soup.select_one("table.sale_list")
for form in table.select("form"):
    face   = int(form.select_one('input[name="vamo"]')["value"])
    p_rate = float(form.select_one('input[name="rate"]')["value"])
    discount_rate = round(100 - p_rate, 2)
```

### 取引履歴の HTML 構造（トップページ）

`article` > `ul` > `li` 内に `<p>` 要素が並ぶ

```
p.fix_first       → 空（アイコン）
p.fix_first.right → 枚数 "2枚"
p.right           → 額面 "5,000円"
p.right           → 成立価格 "4,225円"
p.fix_mid.right   → 販売率 "84.5％"
p                 → 日時 "03/14 17:52"（MM/DD HH:MM JST形式）
p.fix_last.right  → ステータス "取引成立" or "確認中"
```

⚠️ **注意:** トップページの取引履歴は全券種混在。Amazon のみフィルタする手段が不明なため、現状は取引履歴未取得。

---

## 2. ギフトイシュー（giftissue.com）

### 調査URL

| 用途 | URL |
|------|-----|
| Amazon出品一覧 | `https://giftissue.com/ja/category/amazonjp/` |
| トップ（カテゴリ一覧） | `https://giftissue.com/` |

### レンダリング方式
**サーバーレンダリング（jQuery）** → `requests` で直接取得可能

### 出品一覧の HTML 構造

```html
<!-- トップページ: カテゴリ別最安値表示 -->
<li class="categoryItemWithRate">
  <a href="/ja/category/amazonjp/" class="categoryItemWithRate_link">
    <span class="categoryItemWithRate_name">Amazonギフト</span>
  </a>
  <span class="categoryItemWithRate_discount">6.5% 0FF</span>  <!-- "OFF" でなく "0FF" に注意 -->
  <p class="categoryItem_count">
    <span class="fwb">95</span>商品
  </p>
</li>

<!-- Amazon出品一覧ページ: 各出品 -->
<div class="giftList_cell giftList_cell-facevalue giftList_cell-label giftList_cell-labelBold">
  <span>¥ 3,000</span>                                          <!-- 額面 -->
  <span class="giftList_rate giftList_spText">93.5 %</span>    <!-- 販売率（PC表示用） -->
  <span class="giftList_rate giftList_cell sp-hide">93.5 %</span> <!-- 販売率（スマホ非表示） -->
</div>
```

⚠️ **注意:** "OFF" が "0FF"（数字のゼロ）になっているタイポがある

### パース方法

```python
for cell in soup.select(".giftList_cell-facevalue"):
    rate_span = cell.select_one(".giftList_rate.giftList_spText") \
                or cell.select_one(".giftList_rate")
    payment_rate = float(re.sub(r"[^\d.]", "", rate_span.get_text()))
    discount_rate = round(100 - payment_rate, 2)
```

### ページネーション
デフォルト50件表示。全95件あり。URLパラメータで件数変更できるか未確認。

### 取引履歴
**なし**（確認できず）

---

## 3. べてるギフト（beterugift.jp）

### 調査URL

| 用途 | URL |
|------|-----|
| Amazon出品一覧（AJAX） | `https://beterugift.jp/home/load/1?_=<timestamp>` |

### カテゴリID

| ID | カテゴリ |
|----|---------|
| **1** | **Amazon** |
| 3 | Google Play |
| （他は未調査） | — |

### レンダリング方式
**jQuery AJAX → HTMLレスポンス（JSON ではない）**

トップページがロード時に `home/load/1?_=タイムスタンプ` をフェッチしてHTMLを埋め込む。
このエンドポイントを `requests` で直接叩けば出品データ取得可能。

### 出品一覧の HTML 構造

```
tbody > tr の td 構成（インデックス順）:

td[0]: class=""               → 空
td[1]: class="smartphone_hide center" → 残り "1点"
td[2]: class="smartphone_hide center" → 額面 "5,000 円"
td[3]: class="smartphone_hide ft125 center" → "4,225円 | 84.5% | 775円OFF"  ★ここから率を取得
td[4]: class="smartphone_hide center" → エラー率 "5,733/1,139,469 (0.5%)"
td[5]: class="hidePC center"  → 残り（スマホ用重複）
td[6]: class="hidePC center"  → 額面/価格（スマホ用重複）
td[7]: class="hidePC center"  → 率（スマホ用重複）
td[8]: class="hidePC center"  → エラー率（スマホ用重複）
td[9]: class="smartphone_hide ft125 center" → "買  う"ボタン
td[10]: class="hidePC ft125 center" → "買  う"ボタン（スマホ）
```

### パース方法

```python
for tr in soup.select("tbody tr"):
    tds = tr.find_all("td")
    if len(tds) < 4:
        continue
    rate_td = tds[3]
    if "ft125" not in rate_td.get("class", []):
        continue
    # "4,225円 | 84.5% | 775円OFF" から "84.5" を抽出
    m = re.search(r"(\d+(?:\.\d+))\s*%", rate_td.get_text(" ", strip=True))
    payment_rate = float(m.group(1))
    discount_rate = round(100 - payment_rate, 2)
```

### 取引履歴

**あり（実装済み）** — 同ページ（`/home/load/1`）の **2番目の `<table>`**（見出し: 直近取引履歴）に含まれる。

#### テーブル構造

```
tbody > tr の td 構成:

td[0]: class="table_pics"  → img[src] — ファイル名が "1.jpg" で終わればAmazon
td[1]: class="trlist"      → 日時  "03/14 21:47"（JST, MM/DD HH:MM）★PC用
td[2]: class="trlist"      → 額面  "10,000円"                        ★PC用
td[3]: class="trlist"      → 成立価格 "8,450円"                      ★PC用
td[4]: class="trlist"      → 販売率 "84.5%"                          ★PC用
td[5..]: class="trlist"    → モバイル用の重複セル（先頭4つのみ使用）
```

#### フィルタ・パース方法

```python
# Amazon判定
img = tr.select_one("td.table_pics img")
if not img or not img["src"].endswith("1.jpg"):
    continue

# 重複セルの先頭4つだけ使う
trlist_tds = tr.select("td.trlist")[:4]
date_text, face_text, price_text, rate_text = [td.get_text(strip=True) for td in trlist_tds]

# 日時: JST → UTC変換（年跨ぎ対策あり）
dt_jst = datetime.strptime(f"{now_jst.year}/{date_text}", "%Y/%m/%d %H:%M").replace(tzinfo=JST)
if dt_jst > now_jst + timedelta(hours=1):
    dt_jst = dt_jst.replace(year=dt_jst.year - 1)
traded_at = dt_jst.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

---

## 4. アマテン（amaten.com）

### 調査URL

| 用途 | URL |
|------|-----|
| Amazon出品一覧 | `https://amaten.com/exhibitions/amazon` |

### レンダリング方式
**サーバーレンダリング（Ruby on Rails）** → `requests` で直接取得可能
ただし JS でポップアップ等を制御しているため、ヘッダー設定推奨。

### 出品一覧の HTML 構造

```
tbody > tr の td 構成:

td（クラスなし）     → "ただいま品切れ中..." の場合あり（最安帯に品切れが挟まる）
td.ftlg13.ftmd13    → 枚数 "2 点"
td.ftlg20.ftmd20    → 額面 "50,000 円"   ★
td.ftlg22.ftmd22    → 販売価格 "47,500 円" ★
td.ftlg13.ftmd13    → 率・割引額 "95 % │ 2,500 円OFF"  ★ここから率を取得
td.ftlg13.ftmd13    → エラー/出品数 "1126 / 14379"
td.ftlg13.ftmd13.text-center → "自分の出品 残高不足 買 う"
```

### パース方法

```python
for tr in soup.select("tbody tr"):
    rate_td = tr.select_one("td.ftlg13")
    if not rate_td:
        continue
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", rate_td.get_text(" ", strip=True))
    payment_rate = float(m.group(1))
    discount_rate = round(100 - payment_rate, 2)
```

### 取引履歴
**ログイン必須** → 現状取得しない

---

## まとめ比較

| サイト | リクエスト方式 | 件数（調査時） | 取引履歴 |
|--------|--------------|--------------|---------|
| ama-gift | GET HTML | 多数（全Amazon出品） | △ 全券種混在で取得困難 |
| giftissue | GET HTML | 95件（ページネーションあり） | なし |
| beterugift | GET HTML（AJAXエンドポイント） | 複数件 | ✅ 同ページ2番目のtable、Amazon券で絞り込み |
| amaten | GET HTML | 350件 | ログイン必須 |

## スクレイパー変更履歴

| 日付 | 変更内容 |
|------|---------|
| 2026-03-14 | 初版：当て推量のセレクタで記述（`.discount-rate`等）→ 動作しない |
| 2026-03-14 | Chrome MCPでDOM調査後に全4サイトを正しいセレクタに書き直し |
| 2026-03-14 | beterugift: 取引履歴テーブルの構造を確認・実装済みに更新 |
