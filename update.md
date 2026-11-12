# 如何每三小時更新「都柏林活動雷達」

這個資料夾是一份不需建置步驟的靜態網站：用瀏覽器打開 `index.html`，或用任何靜態伺服器即可。活動與新店資料放在 `data.json`；`index.html` 裡另有一份內嵌備份，所以即使用「從磁碟直接打開」（`file://`）也能顯示。圖片放在 `images/`，卡片用相對路徑引用，不外連熱鏈。

## 檔案

| 檔案 | 用途 |
| --- | --- |
| `data.json` | 唯一的資料來源。更新活動時只改這份。 |
| `index.html` | 網站本體（HTML / CSS / JS 全寫在同一檔）。 |
| `images/` | 各則活動／新店的參考圖（約 800px 寬的 webp/jpg），以及分類示意圖 `placeholder-食.webp` 等。 |
| `fetch_images.py` | 從出處頁抓 og:image 或活動海報，縮圖後存進 `images/`；找不到該活動的真實圖片時才寫分類示意。 |
| `build.py` | 先跑圖片抓取，再把 `data.json` 注入 `index.html` 的內嵌備份。 |
| `update.md` | 本說明。 |

## `data.json` 結構

```json
{
  "lastUpdated": "2026-11-12T01:21",
  "timezone": "Europe/Dublin",
  "items": [ { "...一則活動或新店..." } ]
}
```

- `lastUpdated`：資料實際查核完成的時間，格式 `YYYY-MM-DDTHH:MM`，時區必須是 `Europe/Dublin`（11–3 月為 GMT / UTC+0，夏令時間為 IST / UTC+1）。頁面上的「最後更新」會原樣顯示並標「都柏林時間」。
- `timezone`：固定為 `Europe/Dublin`。
- `today` / 本週 / 本週末 **不必** 寫進 JSON。網頁會依瀏覽當下的都柏林日期自行計算「今天、本週末、本週、之後」。

每一則 `items` 必填：

| 欄位 | 說明 |
| --- | --- |
| `id` | 穩定唯一識別，例如 `elk-agent`、`ms-wild-lights`、`open-banba`。同一活動下次更新請沿用同一 id。 |
| `kind` | `event`（活動）或 `opening`（新店情報）。 |
| `tier` | `mainstream`（主流重點：大型演唱會、劇場、體育、節慶、燈飾、大展）或 `niche`（小眾獵奇）。 |
| `name` | 活動或店名，專有名詞保持原文（通常是英文或愛爾蘭語）。 |
| `category` | `食` / `衣` / `住` / `行` / `育` / `樂` 其中一個。 |
| `start` | `YYYY-MM-DD`。活動開始日；新店用開業日、宣布日或預計開業日（標籤要誠實說明）。 |
| `end` | 選填。跨日活動或展覽的結束日。 |
| `dateLabel` | 給讀者看的中文日期，例如「11月14日（六） 20:10 開賽」。 |
| `venue` / `area` | 場地名稱與地區，場地名保持原文。 |
| `price` | 已知票價；未知就寫「票價見來源」或「詳見來源」，不要編造。新店可用「—」。 |
| `hook` | 一句繁體中文，說明為什麼值得去。 |
| `rating` | 獵奇度 1–5 的整數（編輯判斷；主流活動通常較低）。 |
| `source` / `sourceName` | 可點的原始出處網址，與來源名稱。 |
| `sources` | 選填。額外出處陣列，例如 Instagram 貼文：`{"url":"https://www.instagram.com/...","name":"Instagram @handle","kind":"instagram"}`。主來源仍用 `source`。有 Instagram 出處的卡片會顯示小徽章。 |
| `image` | 相對路徑，例如 `images/ms-wild-lights.webp` 或 `images/placeholder-樂.webp`。 |
| `imageKind` | `source`（出處頁的真實圖片）或 `placeholder`（分類示意）。 |
| `imageCredit` | 給讀者看的圖片出處，例如「圖片來源：Dublin Zoo」或「分類示意（無活動官方圖片）」。 |
| `imageOrigin` | 選填。下載時用的原始圖片網址，方便下次更新比對，不必顯示在頁面上。 |
| `note` | 選填。例如「已售罄」「18+」。 |
| `openingStatus` | 新店選填：`已開業` / `即將開業` / `重新開業`。 |
| `shopType` | 新店選填，例如「咖啡」「餐廳」。 |

不要發明活動、日期、票價或連結。年份對不上、頁面 404、或來源看起來是套版活動的條目，請捨棄。

圖片規則：

- 必須使用**該則活動／店家自己的**出處頁圖片（og:image、twitter:image、官方海報或主視覺）。
- 下載到 `images/{id}.webp`（必要時 jpg），縮到約 800px 寬後用相對路徑引用，並標明出處。
- 多場活動的總覽頁（例如 Nialler9 週報、Totally Dublin 活動列表）的封面圖，**不能**當作其中任何一場的圖片。
- 網站 logo、或其他活動的海報，一律不用。
- 若出處頁沒有屬於這則活動的真實圖片，才用 `images/placeholder-{類別}.webp`。不要借用別場活動的照片來充數。

## 一次更新的建議步驟

1. 用都柏林當下日期，查未來約三週的活動，以及近約四週／即將開業的店。同時收錄主流大型活動（約 15–25 則：演唱會、劇場、橄欖球／足球／GAA、節慶、耶誕市集與燈飾、大展）與小眾獵奇選項。略過找不到出處的項目。
2. 建議來源：官方場館與主辦頁（3Arena、Aviva、Bord Gáis、Gaiety、Gate、Abbey、Helix、Dublin Zoo、TwinkleTown、RDS 等）、Nialler9、Totally Dublin、The Irish Times 餐飲、All The Food、Lovin Dublin、Every Pub in Dublin、IMAGE.ie、Eventbrite、Meetup、Luma、Resident Advisor、Temple Bar、Visit Dublin、Dublin.ie、District Magazine、Dublin Inquirer、Fever、Reddit r/Dublin，以及公開的 X 貼文。每則必須能連回真實來源。
3. 編輯 `data.json`：更新仍有效的條目、刪掉已結束的、加入新找到的，並標好 `tier`。改完後把 `lastUpdated` 設成這次查核完成的都柏林時間。
4. 在本資料夾執行：

   ```bash
   python3 build.py
   ```

   預設會呼叫 `fetch_images.py`：已有可用的出處圖片就沿用，缺圖或仍是示意圖的項目會再試一次抓取。之後檢查必要欄位與圖片檔是否存在，再把完整 JSON 寫進 `index.html` 裡 `<!-- DATA:START -->` 與 `<!-- DATA:END -->` 之間的 `<script type="application/json" id="fallback-data">`。JSON 中的 `<` 會被寫成 `\u003c`，以免破壞 script 標籤。

   常用參數：

   ```bash
   python3 build.py --skip-images      # 只驗證既有圖片並注入 HTML
   python3 build.py --refresh-images   # 強制重新下載出處圖片
   python3 fetch_images.py             # 只更新 pictures / data.json 的 image 欄位
   ```

5. 用瀏覽器打開 `index.html`（或起一個靜態伺服器再打開），確認「最後更新」、焦點切換（全部／主流重點／小眾獵奇）、「重點活動」橫幅、縮圖、篩選、搜尋與來源連結都正常。經由 http 載入時會優先 `fetch('data.json')`；失敗或 `file://` 時自動改用內嵌備份。
6. 確認無誤後，把更新推上 GitHub（含 `images/`）。Render 會在 `main` 有新 commit 時自動部署，不必再手動觸發，也不必同步 Canvas。

## 發佈位置

線上站是 Render 的免費靜態網站（starter），來源是公開 GitHub 倉庫，根目錄直接上線，建置指令只是 `echo ok`（沒有前端打包步驟）。

| 項目 | 值 |
| --- | --- |
| GitHub 倉庫 | https://github.com/aki5202-hash/dublin-radar |
| 預設分支 | `main` |
| 線上網址 | https://dublin-radar.onrender.com |
| Render 服務 ID | `srv-dbqh2abrjlhs738988sg` |
| Render 工作區 | Trevor's workspace（`tea-dbqc763bc2fs73cvjlg0`） |
| 自動部署 | 開啟（push 到 `main` 即部署） |

**不要**再維護或同步 Canvas 頁面。這個專案的對外版本是上述靜態網站。

## 排程更新時如何 push（已驗證可重複使用）

本資料夾 `/workspace/dublin-radar` 已是 git 倉庫，`origin` 指向 `https://github.com/aki5202-hash/dublin-radar.git`。box 上的 `gh` / `git` 以 GitHub 帳號 `aki5202-hash`、HTTPS 協定登入（`gh auth status` 可檢查）。第一次建立倉庫與推送用的是：

```bash
# 僅第一次：建立公開倉庫並推送 main（已完成，排程更新不要再跑 repo create）
cd /workspace/dublin-radar
git init -b main
# … add / commit …
gh repo create dublin-radar --public --description "都柏林活動雷達 — mainstream and niche Dublin events static site" --remote origin --source . --push
```

之後每次資料更新，重複這組指令即可（這是實際成功的方法）：

```bash
cd /workspace/dublin-radar
python3 build.py
git add data.json index.html build.py fetch_images.py update.md images
git status
git commit -m "Refresh Dublin radar listings"
git push origin main
```

- 只提交網站檔案。`screenshot.png` 與 `*.zip` 已在 `.gitignore`，不要加入。
- 不要用 `git push --force`。
- Render 服務已開自動部署，但若 push 後一兩分鐘 `list_deploys` 仍沒有新的 deploy，請手動 `trigger_deploy`（先前已發生過 webhook 沒有觸發的情況）。
- 若這台機器還沒 clone，先 `gh repo clone aki5202-hash/dublin-radar`，再依上面步驟。
- cursor-github 連接器沒有建立倉庫或推檔工具；請繼續用 box 上已登入的 `gh` / `git`，不要改用其他帳號。

## 注意

- 先改 `data.json`，再跑 `build.py`。若只改 HTML 裡的備份、忘記改 JSON，下一次注入會把備份蓋掉。
- 不要手改 `<!-- DATA:START -->` / `<!-- DATA:END -->` 這兩行標記本身。
- 網站沒有打包步驟，也不需要 npm。
- 刷新時一定要跑圖片抓取（或確認每則都已有 `image` 檔）；不要留下沒圖的卡片。

## 不用登入的 Instagram 蒐集法（已驗證）

Instagram 不需帳號、也不用瀏覽器登入，就能讀到單則貼文的公開 og 標籤。刷新活動時可依這兩步做：

1. **找貼文網址**  
   用 DuckDuckGo HTML 搜尋，限定帳號路徑，例如：

   ```text
   site:instagram.com/<handle>/
   ```

   或加上活動關鍵字與年份（`Wild Lights Dublin Zoo 2026`）。從結果裡收 `https://www.instagram.com/<handle>/p/<shortcode>/` 或 `/reel/<shortcode>/`。不要只存首頁或探索頁。

2. **讀 og:description 與 og:image**  
   用 User-Agent `facebookexternalhit/1.1` 抓貼文頁（這一組 UA 才能穩定拿到 og 標籤；一般瀏覽器 UA 常常得到登入牆或空頁）：

   ```bash
   curl -sL -A "facebookexternalhit/1.1" "https://www.instagram.com/p/<shortcode>/"
   ```

   從 HTML 讀 `og:title`、`og:description`、`og:image`。**不要熱鏈 Instagram CDN 圖片**：`scontent-*.cdninstagram.com` 的網址會過期。若這則卡片要用這張圖（例如目前是分類示意、沒有該活動自己的官方圖），請立刻下載、縮到約 800px，存進 `images/{id}.webp`，並在 `imageCredit` 寫「圖片來源：Instagram @handle」。已有官方海報的條目只需把貼文加進 `sources`，不必覆蓋原圖。

同一場活動若已在 `data.json`，只加 Instagram 為額外來源，不要複製成新條目。日期、票價仍以官方頁為準；貼文沒寫的事實不要補上。

已用上述方法成功讀到公開貼文的帳號：

- `@comconireland`（Comic Con Ireland）
- `@dccireland`（Irish Design Week / DCCI）
- `@3arenadublin`（Joanne McNally 等場館檔期）
- `@dublinzoo_official`（Wild Lights）
- `@98fmdublin`
- `@discoverdublin`
- `@oi.irlanda`
- `@alternativedublin`
- `@banbadublin`
- `@eatdrinkdub`
- `@missjonesireland`

`fetch_images.py` 碰到 `instagram.com` 或 `cdninstagram.com` 時會自動改用 `facebookexternalhit/1.1`。
