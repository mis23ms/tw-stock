# 盤後一頁式台股戰報（可分享網址 / 自動更新）

你要的 3 個來源 **都照用**：
1) 4 檔（2330/2317/3231/2382）：今日收盤價與漲跌 + 5 類新聞（法說/營收/重大訊息/產能/美國出口管制）+ 外資買賣超（張數，當日與前一營業日）
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

## 本機測試（可選）
```
python -m venv .venv
source .venv/bin/activate   # Windows 用 .venv\Scripts\activate
pip install -r requirements.txt
python scripts/update_data.py
python -m http.server --directory docs 8000
```
打開 http://localhost:8000 就能看

# tw-stock 專案接手指引（給下一個 AI / 人類）

## 這個專案在做什麼
- 每天用 GitHub Actions 自動抓取資料，輸出到 `docs/data.json`
- GitHub Pages 前端讀 `docs/data.json` 來顯示表格（頁面 UI 不會因為爬蟲改法而變）

## 資料來源網址（重要）
1) 富邦：券商分點進出金額排行（ZGB）
- https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGB/ZGB.djhtm
- 特別用 Playwright（瀏覽器）抓，因為 requests 會被擋/或抓到不完整 HTML

2) 富邦：外資買賣超排行（ZGK_D）
- https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_D.djhtm
- 目前可用 requests + big5；若未來被擋，建議也改 Playwright

3) 證交所：個股日收盤（STOCK_DAY）
- https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date=YYYYMMDD&stockNo=2330

4) 證交所：三大法人（TWT38U）
- JSON: https://www.twse.com.tw/fund/TWT38U?response=json&date=YYYYMMDD
- CSV fallback: https://www.twse.com.tw/fund/TWT38U?response=csv&date=YYYYMMDD

5) Google News RSS（新聞）
- https://news.google.com/rss/search?q=關鍵字&hl=zh-TW&gl=TW&ceid=TW:zh-Hant

## 曾經踩過的坑（一定要看）
### 坑 1：富邦 ZGB 是「雙邊合併表格」
- 同一列可能同時含「買超」與「賣超」兩邊欄位（常見 8 欄）
- 不能只用 td[0..3]，要同時檢查左半與右半欄位，不然會抓到錯欄/怪數字

### 坑 2：富邦頁面用 requests 抓會失敗或抓到不完整
- 解法：ZGB 改用 Playwright 模擬瀏覽器，等網頁載完再從 DOM 讀表格

### 坑 3：GitHub Actions 會紅燈，但本機會綠燈
- 常見原因：Actions 沒裝 Playwright 的瀏覽器（Chromium）
- 解法：workflow 裡要加：
  `python -m playwright install --with-deps chromium`

### 坑 4：big5 編碼
- 某些富邦頁面用 big5，requests 讀取需指定 encoding="big5"

## 自動化流程（GitHub Actions）
- workflow: `.github/workflows/update.yml`
- 觸發：手動 workflow_dispatch + 排程 cron（以 repo 內設定為準）
- 內容：安裝 requirements → 執行 `python scripts/update_data.py` → 若 `docs/data.json` 有變更就 commit push

## 手動跑（本機）
- `pip install -r requirements.txt`
- 若要跑 Playwright：`python -m playwright install chromium`
- `python scripts/update_data.py`

