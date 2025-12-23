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
