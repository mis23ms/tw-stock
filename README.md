# 盤後一頁式台股戰報（可分享網址 / 自動更新）

這個專案做什麼：
- 每天用 GitHub Actions 自動抓取資料，輸出到 `docs/data.json`
- GitHub Pages 前端讀 `docs/data.json` 來顯示表格（頁面 UI 不會因為爬蟲改法而變）
- 讓你有一個「盤後一頁式戰報」可分享網址，且每天自動更新

---

# 給一般使用者（不用寫程式，只要照做）

## 你要的 3 個來源（都照用）
1) 4 檔（2330/2317/3231/2382）：
   - 今日收盤價與漲跌
   - 5 類新聞（法說/營收/重大訊息/產能/美國出口管制）
   - 外資買賣超（**張數**，當日與前一營業日）
2) 富邦 MoneyDJ：ZGB 6 大券商（摩根大通/台灣摩根士丹利/新加坡商瑞銀/美林/花旗環球/美商高盛）
3) 富邦 MoneyDJ：ZGK_D（外資買賣超排行頁）

## 你要做的（不需要寫程式，只要照做）
### A. 建 GitHub repo
1. 下載本專案（zip），解壓縮
2. 建一個新的 GitHub repo
3. 把整個資料夾內容 push 上去（或用 GitHub 上傳檔案也行）

### B. 開啟 GitHub Pages（變成可分享網址）
1. 到 repo → **Settings** → **Pages**
2. Source 選 **Deploy from a branch**
3. Branch 選 **main**，Folder 選 **/docs**
4. Save
5. 之後你的網址會是：`https://<你的帳號>.github.io/<repo 名>/`

### C. 讓它每天盤後自動更新（GitHub Actions 已寫好）
1. 到 repo → **Actions** → 找到「Update data」
2. 第一次可按 **Run workflow** 手動跑一次（馬上產生 docs/data.json）
3. 之後會在平日台北時間 17:20 自動跑（排程在 `.github/workflows/update.yml`）

> 備註：抓不到富邦頁（例如偶發被擋）時，腳本會保留上一版 data.json，不會讓網頁整個壞掉。

---

# 本機測試（可選：真的想自己跑才需要）
```bash
python -m venv .venv
source .venv/bin/activate   # Windows 用 .venv\Scripts\activate
pip install -r requirements.txt
python scripts/update_data.py
python -m http.server --directory docs 8000
````

打開 [http://localhost:8000](http://localhost:8000) 就能看

---

# tw-stock 專案接手指引（給下一個 AI / 人類）

> 這段是「維護用」。一般使用者不用看，但下一個 AI 需要。

## 這個專案在做什麼

* 每天用 GitHub Actions 自動抓取資料，輸出到 `docs/data.json`
* GitHub Pages 前端讀 `docs/data.json` 來顯示表格（頁面 UI 不會因為爬蟲改法而變）

---

## 資料來源網址（重要）

1. 富邦：券商分點進出金額排行（ZGB）

* [https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGB/ZGB.djhtm](https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGB/ZGB.djhtm)
* 特別用 Playwright（瀏覽器）抓，因為 requests 會被擋/或抓到不完整 HTML

2. 富邦：外資買賣超排行（ZGK_D）

* [https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_D.djhtm](https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_D.djhtm)
* 目前可用 requests + big5；若未來被擋，建議也改 Playwright

3. 證交所：個股日收盤（STOCK_DAY）

* [https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date=YYYYMMDD&stockNo=2330](https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date=YYYYMMDD&stockNo=2330)

4. 證交所：三大法人（TWT38U）

* JSON: [https://www.twse.com.tw/fund/TWT38U?response=json&date=YYYYMMDD](https://www.twse.com.tw/fund/TWT38U?response=json&date=YYYYMMDD)
* CSV fallback: [https://www.twse.com.tw/fund/TWT38U?response=csv&date=YYYYMMDD](https://www.twse.com.tw/fund/TWT38U?response=csv&date=YYYYMMDD)

5. Google News RSS（新聞）

* [https://news.google.com/rss/search?q=關鍵字&hl=zh-TW&gl=TW&ceid=TW:zh-Hant](https://news.google.com/rss/search?q=關鍵字&hl=zh-TW&gl=TW&ceid=TW:zh-Hant)

---

## 重要資料單位／欄位備註（必讀：容易做錯）

### 備註 1：外資買賣超「張」不是「股」

* TWT38U 的欄位 `買賣超股數` 是「股」（shares），不是「張」
* 本專案前端顯示「外資買賣超(張)」，因此後端輸出前會把股數轉成張數：

  * **1 張 = 1000 股**
  * 會把股數除以 1000 後四捨五入成整張
* 如果你看到像 2,144,442 這種數字，那是「股」，代表又回到錯誤狀態了（應該是約 2,144 張）

### 備註 2：ZGK_D「資料日期」原頁常只有月日（例如 12/24）

* 富邦 ZGK_D 原頁常見只有「日期：12/24」，沒有年份
* 本專案輸出 `docs/data.json` 時會補成 `YYYYMMDD`
* 年份使用「當次抓資料時的年份」（實作上用 `latest_trading_day` 的年份最穩）
* 跨年保護：若抓到的月日看起來比今天月日還晚，視為去年（避免 1 月抓到 12/31 被補成年份錯）

---

## 曾經踩過的坑（一定要看）

### 坑 1：富邦 ZGB 是「雙邊合併表格」

* 同一列可能同時含「買超」與「賣超」兩邊欄位（常見 8 欄）
* 不能只用 td[0..3]，要同時檢查左半與右半欄位，不然會抓到錯欄/怪數字

### 坑 2：富邦頁面用 requests 抓會失敗或抓到不完整

* 解法：ZGB 改用 Playwright 模擬瀏覽器，等網頁載完再從 DOM 讀表格

### 坑 3：GitHub Actions 會紅燈，但本機會綠燈

* 常見原因：Actions 沒裝 Playwright 的瀏覽器（Chromium）
* 解法：workflow 裡要加：
  `python -m playwright install --with-deps chromium`

### 坑 4：big5 編碼

* 某些富邦頁面用 big5，requests 讀取需指定 encoding="big5"

---

## 自動化流程（GitHub Actions）

* workflow: `.github/workflows/update.yml`
* 觸發：手動 workflow_dispatch + 排程 cron（以 repo 內設定為準）
* 內容：安裝 requirements → 執行 `python scripts/update_data.py` → 若 `docs/data.json` 有變更就 commit push

---

## 手動跑（本機，給維護者）

* `pip install -r requirements.txt`
* 若要跑 Playwright：`python -m playwright install chromium`
* `python scripts/update_data.py`

---

# 故障排除（下一個 AI 最常用）

> 目標：用最少時間定位 Actions 為什麼紅燈。

1. **先看 Actions log 的最後幾行**

* 只看 Summary 那個「exit code 1」沒用
* 要點進去失敗的 job → 展開 `Run python scripts/update_data.py` 的 log
* 通常會有 `ERROR: ...` 的直接原因（網路、來源格式變更、Playwright、或資料日找不到）

2. **若是 Playwright/Chromium 錯誤**

* 99% 是 workflow 沒裝瀏覽器
* 確認有：

  * `python -m playwright install --with-deps chromium`

3. **若是找不到最近兩個交易日**

* 可能遇到連假/資料源延遲/證交所 API 當天資料還沒出
* 做法：

  * 把 lookback 加大（例如 15 → 25）
  * 或把「找交易日」改成更保守（例如只要抓到 latest 就先產出、prev 允許缺值）
  * 但這屬於需求取捨：要不要「寧可出舊資料也不紅燈」

4. **若是富邦頁被擋**

* ZGB 已用 Playwright，比較穩
* ZGK_D 若被擋，可以改 Playwright 或加強 headers/等待 DOM
* 若抓不到就應該「保留上一版 data.json」避免前端整個壞

---

# 版權與免責

* 本專案資料來源為公開網站/公開 API，僅供學習與個人研究
* 請自行評估資料正確性與使用風險

```


