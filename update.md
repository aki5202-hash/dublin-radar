# 如何每三小時更新「都柏林小眾獵奇雷達」

這個資料夾是一份不需建置步驟的靜態網站：用瀏覽器打開 `index.html`，或用任何靜態伺服器即可。活動與新店資料放在 `data.json`；`index.html` 裡另有一份內嵌備份，所以即使用「從磁碟直接打開」（`file://`）也能顯示。

## 檔案

| 檔案 | 用途 |
| --- | --- |
| `data.json` | 唯一的資料來源。更新活動時只改這份。 |
| `index.html` | 網站本體（HTML / CSS / JS 全寫在同一檔）。 |
| `build.py` | 把 `data.json` 注入 `index.html` 的內嵌備份。 |
| `update.md` | 本說明。 |

## `data.json` 結構

```json
{
  "lastUpdated": "2026-11-12T00:58",
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
| `id` | 穩定唯一識別，例如 `elk-agent`、`open-banba`。同一活動下次更新請沿用同一 id。 |
| `kind` | `event`（活動）或 `opening`（新店情報）。 |
| `name` | 活動或店名，專有名詞保持原文（通常是英文或愛爾蘭語）。 |
| `category` | `食` / `衣` / `住` / `行` / `育` / `樂` 其中一個。 |
| `start` | `YYYY-MM-DD`。活動開始日；新店用開業日、宣布日或預計開業日（標籤要誠實說明）。 |
| `end` | 選填。跨日活動或展覽的結束日。 |
| `dateLabel` | 給讀者看的中文日期，例如「11月14日（六） 23:00」。 |
| `venue` / `area` | 場地名稱與地區，場地名保持原文。 |
| `price` | 已知票價；未知就寫「票價見來源」或「詳見來源」，不要編造。新店可用「—」。 |
| `hook` | 一句繁體中文，說明為什麼值得去。 |
| `rating` | 獵奇度 1–5 的整數（編輯判斷）。 |
| `source` / `sourceName` | 可點的原始出處網址，與來源名稱。 |
| `note` | 選填。例如「已售罄」「18+」。 |
| `openingStatus` | 新店選填：`已開業` / `即將開業` / `重新開業`。 |
| `shopType` | 新店選填，例如「咖啡」「餐廳」。 |

不要發明活動、日期、票價或連結。年份對不上、頁面 404、或來源看起來是套版活動的條目，請捨棄。

## 一次更新的建議步驟

1. 用都柏林當下日期，查未來約三週的活動，以及近約四週／即將開業的店。優先小眾、好玩、獵奇；略過純觀光行程。
2. 建議來源：Nialler9、Totally Dublin、The Irish Times 餐飲、All The Food、Lovin Dublin、Every Pub in Dublin、IMAGE.ie、Eventbrite、Meetup、Luma、Resident Advisor、Temple Bar、Visit Dublin、District Magazine、Dublin Inquirer、Fever、Reddit r/Dublin，以及公開的 X 貼文。每則必須能連回真實來源。
3. 編輯 `data.json`：更新仍有效的條目、刪掉已結束的、加入新找到的。改完後把 `lastUpdated` 設成這次查核完成的都柏林時間。
4. 在本資料夾執行：

   ```bash
   python3 build.py
   ```

   腳本會檢查必要欄位，然後把完整 JSON 寫進 `index.html` 裡 `<!-- DATA:START -->` 與 `<!-- DATA:END -->` 之間的 `<script type="application/json" id="fallback-data">`。JSON 中的 `<` 會被寫成 `\u003c`，以免破壞 script 標籤。
5. 用瀏覽器打開 `index.html`（或起一個靜態伺服器再打開），確認「最後更新」、篩選、搜尋與來源連結都正常。經由 http 載入時會優先 `fetch('data.json')`；失敗或 `file://` 時自動改用內嵌備份。

6. 確認無誤後，把更新推上 GitHub。Render 會在 `main` 有新 commit 時自動部署，不必再手動觸發，也不必同步 Canvas。

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
gh repo create dublin-radar --public --description "都柏林小眾獵奇雷達 — niche and quirky Dublin events static site" --remote origin --source . --push
```

之後每次資料更新，重複這組指令即可（這是實際成功的方法）：

```bash
cd /workspace/dublin-radar
python3 build.py
git add data.json index.html update.md
git status
git commit -m "Refresh Dublin radar listings"
git push origin main
```

- 只提交網站檔案。`screenshot.png` 與 `*.zip` 已在 `.gitignore`，不要加入。
- 不要用 `git push --force`。
- 不要在自動部署已開啟時再另外呼叫 Render `trigger_deploy`；push 之後等新 deploy 變成 `live` 即可。
- 若這台機器還沒 clone，先 `gh repo clone aki5202-hash/dublin-radar`，再依上面步驟。
- cursor-github 連接器沒有建立倉庫或推檔工具；請繼續用 box 上已登入的 `gh` / `git`，不要改用其他帳號。

## 注意

- 先改 `data.json`，再跑 `build.py`。若只改 HTML 裡的備份、忘記改 JSON，下一次注入會把備份蓋掉。
- 不要手改 `<!-- DATA:START -->` / `<!-- DATA:END -->` 這兩行標記本身。
- 網站沒有打包步驟，也不需要 npm。
