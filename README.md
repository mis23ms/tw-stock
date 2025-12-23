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

# tw-stock 專案接手指引（給下一個 AI / 維護者）

## 這個專案在做什麼
- 透過 GitHub Actions 定時抓取台股相關資料
- 產生並更新 `docs/data.json`
- GitHub Pages 讀取 `docs/data.json` 顯示在網站上（前端通常不變，資料變）

---

## 資料來源網址（重點）
### 1) 富邦 eBrokerDJ：券商分點進出金額排行（ZGB）
- https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGB/ZGB.djhtm
- 本專案會抓「指定 6 家外資」的：買進金額 / 賣出金額 / 差額

指定券商（6 家）：
- 摩根大通
- 台灣摩根士丹利
- 新加坡商瑞銀
- 美林
- 花旗環球
- 美商高盛

### 2) 富邦 eBrokerDJ：外資買賣超排行（ZGK_D）或官股相關頁面
- https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_D.djhtm
- 專案會抓指定欄位（依程式碼實作為準）

> 若未來新增/修改資料來源：請直接到 `scripts/update_data.py` 最上方的 URL 常數區統一管理。

---

## 曾經遇過的坑（務必看）
### 坑 1：富邦網頁用 requests/BeautifulSoup 常常抓不到
原因：
- 富邦這類頁面常有動態渲染/框架/反爬，requests 抓到的是空殼 HTML
解法：
- 改用 Playwright 模擬真人瀏覽器，等網頁載入後用 DOM 讀表格

### 坑 2：ZGB 是「雙併表格」：買超表 + 賣超表並排
現象：
- 只用 `document.querySelectorAll("tr")` + `includes(name)` 很容易抓到「外層 tr」
- 外層 tr 可能包含整塊表格，導致抓到的 td 不是你以為的 4 欄，最後數字全部怪掉/重複
解法：
- 過濾條件一定要加：
  - `td` 數量 >= 4
  - 第 1 欄要像券商名字
  - 第 2~4 欄要像數字（含逗號與負號）

### 坑 3：編碼 Big5/UTF-8 不是核心問題
現象：
- 以前以為是 big5 才抓不到
真相：
- 真正原因是「動態渲染/反爬」導致 requests 拿不到資料
解法：
- Playwright + DOM 讀取，避開編碼困擾

### 坑 4：GitHub Pages/瀏覽器快取，會讓你以為沒更新
解法：
- Ctrl+F5 強制重整
- 無痕視窗
- 直接看 `docs/data.json` 的 generated_at 是否更新

---

## 目前自動化流程（GitHub Actions）
Workflow 檔：
- `.github/workflows/update.yml`

觸發方式：
1. 手動觸發：workflow_dispatch
2. 排程觸發：cron（以檔案內註解為準）
   - 目前設定：週一到週五固定時間跑（台北時間 vs UTC 需看註解換算）

流程：
- checkout
- 安裝 Python 套件（requirements.txt）
- 執行 `python scripts/update_data.py`
- 若 `docs/data.json` 有變：commit & push

---

## 本機測試方式（建議）
1) 安裝
- pip install -r requirements.txt
- playwright 需要瀏覽器：
  - python -m playwright install chromium

2) 執行
- python scripts/update_data.py

3) 檢查輸出
- 看 `docs/data.json` 是否更新
- 看裡面的 generated_at / fubon_zgb 是否正確

---

## 如果又壞了，第一時間看哪裡
1) GitHub Actions log：看 `python scripts/update_data.py` 是否報錯
2) `docs/data.json` 是否有被更新/commit
3) 富邦頁面結構是否改了（ZGB/ZGK_D）
