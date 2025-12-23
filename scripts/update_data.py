#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

STOCKS = [
    ("2330", "台積電"),
    ("2317", "鴻海"),
    ("3231", "緯創"),
    ("2382", "廣達"),
]

FUBON_ZGB_URL = "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGB/ZGB.djhtm"
FUBON_ZGK_D_URL = "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_D.djhtm"

ZGB_BROKERS = [
    "摩根大通",
    "台灣摩根士丹利",
    "新加坡商瑞銀",
    "美林",
    "花旗環球",
    "美商高盛",
]

TWSE_STOCK_DAY = "https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date}&stockNo={stock}"
TWSE_TWT38U_JSON = "https://www.twse.com.tw/fund/TWT38U?response=json&date={date}"
TWSE_TWT38U_CSV = "https://www.twse.com.tw/fund/TWT38U?response=csv&date={date}"

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"

NEWS_CATEGORIES = {
    "法說": ["法說", "法說會", "法說摘要", "財報電話會議", "線上法說"],
    "營收": ["營收", "月營收", "合併營收", "營收公布", "營收年增", "營收月增"],
    "重大訊息": ["重大訊息", "重訊", "公告", "暫停交易", "處置", "違約", "減資", "增資"],
    "產能": ["產能", "擴產", "投產", "產線", "產量", "CoWoS", "先進封裝", "capex", "資本支出"],
    "美國出口管制": ["出口管制", "美國", "禁令", "制裁", "管制", "BIS", "晶片禁令", "Entity List", "實體清單"],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

TAIPEI_TZ = timezone(timedelta(hours=8))


def fetch_text(url: str, *, encoding: Optional[str] = None, timeout: int = 25) -> str:
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    if encoding:
        r.encoding = encoding
    return r.text


def try_parse_int(s: str) -> Optional[int]:
    s = s.strip().replace(",", "")
    if not s or s in {"--", "-"}:
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def try_parse_float(s: str) -> Optional[float]:
    s = s.strip().replace(",", "")
    if not s or s in {"--", "-"}:
        return None
    try:
        return float(s)
    except Exception:
        return None


def iso_now() -> str:
    return datetime.now(TAIPEI_TZ).replace(microsecond=0).isoformat()


def yyyymmdd(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")


def to_iso_date(yyyymmdd_s: str) -> str:
    return f"{yyyymmdd_s[0:4]}-{yyyymmdd_s[4:6]}-{yyyymmdd_s[6:8]}"


def fetch_twt38u_json(date_yyyymmdd: str) -> Dict[str, Any]:
    # JSON first
    try:
        txt = fetch_text(TWSE_TWT38U_JSON.format(date=date_yyyymmdd))
        return json.loads(txt)
    except Exception:
        # fallback to CSV
        txt = fetch_text(TWSE_TWT38U_CSV.format(date=date_yyyymmdd))
        lines = [line for line in txt.splitlines() if line.strip()]
        header_idx = None
        for i, line in enumerate(lines[:40]):
            if "證券代號" in line and "買賣超股數" in line:
                header_idx = i
                break
        if header_idx is None:
            raise RuntimeError("CSV header not found")
        reader = csv.reader(lines[header_idx:])
        rows = list(reader)
        fields = rows[0]
        data = rows[1:]
        return {"stat": "OK", "fields": fields, "data": data, "date": date_yyyymmdd}


def twt38u_has_data(payload: Dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False
    stat = payload.get("stat")
    if stat and str(stat).upper() not in {"OK", "SUCCESS"}:
        return False
    data = payload.get("data")
    return isinstance(data, list) and len(data) > 0


def find_last_two_trading_days(max_lookback_days: int = 15) -> Tuple[str, str]:
    today = datetime.now(TAIPEI_TZ).date()
    found: List[str] = []
    for i in range(max_lookback_days):
        d = datetime.combine(today - timedelta(days=i), datetime.min.time(), tzinfo=TAIPEI_TZ)
        ds = yyyymmdd(d)
        try:
            payload = fetch_twt38u_json(ds)
            if twt38u_has_data(payload):
                found.append(ds)
                if len(found) == 2:
                    return found[0], found[1]
        except Exception:
            continue
    raise RuntimeError("找不到最近兩個有資料的交易日（資料源異常或 lookback 太短）")


def extract_foreign_net_shares_for_stocks(date_yyyymmdd: str, tickers: List[str]) -> Dict[str, Optional[int]]:
    payload = fetch_twt38u_json(date_yyyymmdd)
    if not twt38u_has_data(payload):
        raise RuntimeError(f"TWT38U 無資料：{date_yyyymmdd}")
    fields = payload.get("fields") or []
    data = payload.get("data") or []

    def find_idx(name: str) -> int:
        for i, f in enumerate(fields):
            if str(f).strip() == name:
                return i
        raise RuntimeError(f"欄位不存在：{name}")

    idx_code = find_idx("證券代號")
    idx_net = find_idx("買賣超股數")

    out: Dict[str, Optional[int]] = {t: None for t in tickers}
    for row in data:
        if not isinstance(row, list) or len(row) <= max(idx_code, idx_net):
            continue
        code = str(row[idx_code]).strip()
        if code in out:
            out[code] = try_parse_int(str(row[idx_net]))
    return out


def fetch_stock_close_and_change(ticker: str, date_hint: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    url = TWSE_STOCK_DAY.format(date=date_hint, stock=ticker)
    payload = json.loads(fetch_text(url))
    rows = payload.get("data") or []
    if len(rows) < 2:
        return None, None, None
    last = rows[-1]
    prev = rows[-2]
    close = try_parse_float(last[6]) if len(last) > 6 else None
    prev_close = try_parse_float(prev[6]) if len(prev) > 6 else None
    if close is None or prev_close is None:
        return close, None, None
    change = close - prev_close
    pct = (change / prev_close * 100.0) if prev_close else None
    pct_str = f"{pct:+.2f}%" if pct is not None else None
    return close, change, pct_str


import re
from playwright.async_api import async_playwright

TARGET_BROKERS = ["摩根大通", "台灣摩根士丹利", "新加坡商瑞銀", "美林", "花旗環球", "美商高盛"]
FUBON_ZGB_URL = "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGB/ZGB.djhtm"

async def parse_fubon_zgb() -> dict:
    """
    富邦 ZGB（券商分點進出金額排行）
    為什麼不用 requests/bs4？
    - 這頁常有動態載入/反爬，requests 抓到的 HTML 可能是空殼 → 你網站上就會全是 '-'
    所以改用 Playwright：
    - 模擬真人打開瀏覽器
    - 等資料真的渲染出來後，直接從 DOM 的表格 td 讀值
    """

    async with async_playwright() as p:
        # headless=True：背景跑，不開視窗（GitHub Actions 必須）
        browser = await p.chromium.launch(headless=True)

        # user_agent：裝得像真人瀏覽器，降低被擋機率
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
            locale="zh-TW",
        )
        page = await context.new_page()

        # networkidle：等「主要請求」結束。
        # 但富邦有時候表格會晚一拍才塞進去，所以後面再額外等一下（很重要，不然會讀到半成品）
        await page.goto(FUBON_ZGB_URL, wait_until="networkidle", timeout=60_000)
        await page.wait_for_selector("table", timeout=30_000)
        await page.wait_for_timeout(1500)  # 為什麼要等 1.5 秒：避免表格「剛出現但數字還沒填好」

        result = await page.evaluate(
            """(targets) => {
                // 判斷像不像數字（允許：逗號、負號）
                const looksNumber = (s) => {
                    s = (s || "").trim();
                    return /^-?\\d{1,3}(,\\d{3})*$/.test(s) || /^-?\\d+$/.test(s);
                };

                // 這頁「雙併表格」很容易抓到外層 tr（裡面包含整塊表格的文字）
                // 所以我們只接受「td >= 4」且「第 2~4 欄看起來像數字」的列，避免誤抓。
                const rows = Array.from(document.querySelectorAll("tr"));

                function findBrokerRow(name) {
                    for (const r of rows) {
                        const tds = Array.from(r.querySelectorAll("td"));
                        if (tds.length < 4) continue;

                        const c0 = (tds[0].innerText || "").trim();
                        const c1 = (tds[1].innerText || "").trim();
                        const c2 = (tds[2].innerText || "").trim();
                        const c3 = (tds[3].innerText || "").trim();

                        // 券商名稱通常在第一欄；並且後面欄位要像數字才算「真的資料列」
                        if (c0.includes(name) && (looksNumber(c1) || looksNumber(c2) || looksNumber(c3))) {
                            return { name: c0, buy: c1, sell: c2, diff: c3 };
                        }
                    }
                    return { name, buy: "-", sell: "-", diff: "-" };
                }

                return targets.map(findBrokerRow);
            }""",
            TARGET_BROKERS,
        )

        # 取資料日期 / 單位：不賭 selector，用整頁文字 regex 抓比較耐用
        page_text = await page.evaluate("() => document.body.innerText || ''")
        m_date = re.search(r"資料日期\\s*[:：]\\s*(\\d{8})", page_text)
        m_unit = re.search(r"單位\\s*[:：]\\s*([\\u4e00-\\u9fa5]+)", page_text)

        await browser.close()

        return {
            "date": m_date.group(1) if m_date else None,
            "unit": m_unit.group(1) if m_unit else None,
            "brokers": result,
        }



def parse_fubon_zgk_d(limit: int = 50) -> Dict[str, Any]:
    try:
        html = fetch_text(FUBON_ZGK_D_URL, encoding="big5")
        m = re.search(r"資料日期：\s*(\d{8})", html)
        date = m.group(1) if m else None

        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table")
        if table is None:
            raise RuntimeError("找不到 ZGK_D 表格")

        buy_rows = []
        sell_rows = []
        for tr in table.find_all("tr"):
            cols = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if not cols or "名次" in " ".join(cols):
                continue
            if len(cols) < 10:
                continue
            if cols[0].isdigit():
                buy_rows.append({"rank": cols[0], "stock": cols[1], "net": cols[2], "close": cols[3], "change": cols[4]})
            if cols[5].isdigit():
                sell_rows.append({"rank": cols[5], "stock": cols[6], "net": cols[7], "close": cols[8], "change": cols[9]})

        return {"date": date, "buy": buy_rows[:limit], "sell": sell_rows[:limit]}
    except Exception as e:
        return {"date": None, "buy": [], "sell": [], "error": str(e)}


def fetch_rss_items(query: str, limit: int = 30) -> List[Dict[str, str]]:
    url = GOOGLE_NEWS_RSS.format(q=quote_plus(query))
    xml = fetch_text(url)
    soup = BeautifulSoup(xml, "xml")
    items = []
    for it in soup.find_all("item")[:limit]:
        title = (it.title.get_text() if it.title else "").strip()
        link = (it.link.get_text() if it.link else "").strip()
        pub = (it.pubDate.get_text() if it.pubDate else "").strip()
        desc = (it.description.get_text() if it.description else "").strip()
        items.append({"title": title, "link": link, "date": pub, "desc": desc})
    return items


def classify_news(items: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    out = {k: [] for k in NEWS_CATEGORIES.keys()}
    for it in items:
        text = f"{it.get('title','')} {it.get('desc','')}"
        for cat, kws in NEWS_CATEGORIES.items():
            if any(kw in text for kw in kws):
                out[cat].append({"title": it["title"], "link": it["link"], "date": it["date"]})
                break
    for k in list(out.keys()):
        out[k] = out[k][:8]
    return out


def main() -> None:
    latest, prev = find_last_two_trading_days()
    tickers = [t for t, _ in STOCKS]

    foreign_latest = extract_foreign_net_shares_for_stocks(latest, tickers)
    foreign_prev = extract_foreign_net_shares_for_stocks(prev, tickers)

    stocks_out = []
    for ticker, name in STOCKS:
        close, change, pct = fetch_stock_close_and_change(ticker, latest)
        items = fetch_rss_items(f"{ticker} {name}")
        news = classify_news(items)
        stocks_out.append({
            "ticker": ticker,
            "name": name,
            "price": {"close": close, "change": change, "change_pct": pct},
            "foreign_net_shares": {"D0": foreign_latest.get(ticker), "D1": foreign_prev.get(ticker)},
            "news": news,
        })

    out = {
        "generated_at": iso_now(),
        "latest_trading_day": to_iso_date(latest),
        "prev_trading_day": to_iso_date(prev),
        "stocks": stocks_out,
        "fubon_zgb": parse_fubon_zgb(),
        "fubon_zgk_d": parse_fubon_zgk_d(limit=50),
    }

    with open("docs/data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("OK: docs/data.json updated")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
