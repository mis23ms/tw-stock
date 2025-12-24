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

TAIPEI_TZ = timezone(timedelta(hours=8))

TWSE_STOCK_DAY = "https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date}&stockNo={stock}"

TWSE_TWT38U_JSON = "https://www.twse.com.tw/fund/TWT38U?response=json&date={date}"
TWSE_TWT38U_CSV = "https://www.twse.com.tw/fund/TWT38U?response=csv&date={date}"

FUBON_ZGB_URL = "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGB/ZGB.djhtm"
FUBON_ZGK_D_URL = "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_D.djhtm"

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"

NEWS_CATEGORIES = {
    "法說": ["法說", "法人說明", "法說會", "線上法說"],
    "營收": ["營收", "月營收"],
    "重大訊息": ["重大訊息", "重大訊息公告", "重訊"],
    "產能": ["擴產", "產能", "產線", "新廠", "投資建廠", "量產", "產能利用率"],
    "美國出口管制": ["出口管制", "美國禁令", "禁運", "實體清單", "EAR", "BIS"],
}


def iso_now() -> str:
    return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")


def yyyymmdd(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")


def to_iso_date(yyyymmdd_s: str) -> str:
    return f"{yyyymmdd_s[0:4]}-{yyyymmdd_s[4:6]}-{yyyymmdd_s[6:8]}"


def fetch_text(url: str, *, encoding: Optional[str] = None, timeout: int = 25) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; tw-stock-bot/1.0; +https://github.com/)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    if encoding:
        r.encoding = encoding
        return r.text
    return r.text


def try_parse_int(s: str) -> Optional[int]:
    s = s.strip().replace(",", "")
    if not s or s in {"--", "-", "N/A"}:
        return None
    # 可能含括號或其他雜字
    m = re.search(r"[-+]?\d+", s)
    if not m:
        return None
    try:
        return int(m.group(0))
    except Exception:
        return None


def try_parse_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip().replace(",", "")
    if not s or s in {"--", "-", "N/A"}:
        return None
    try:
        return float(s)
    except Exception:
        return None


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
            return {"stat": "NO_DATA", "fields": [], "data": []}
        reader = csv.reader(lines[header_idx:])
        rows = list(reader)
        fields = rows[0]
        data = rows[1:]
        return {"stat": "OK", "fields": fields, "data": data}


def twt38u_has_data(payload: Dict[str, Any]) -> bool:
    stat = str(payload.get("stat") or "").upper()
    if stat != "OK":
        return False
    data = payload.get("data") or []
    return isinstance(data, list) and len(data) > 0


def find_last_two_trading_days(max_lookback_days: int = 20) -> Tuple[str, str]:
    """
    找最近兩個「有 TWT38U 資料」的交易日（包含今天往回）。
    """
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


def _shares_to_lots(v: Optional[int]) -> Optional[int]:
    """Convert shares (股) to lots (張). 1 張 = 1000 股."""
    if v is None:
        return None
    # 四捨五入成整張，避免小數（資料源本來就是整股）
    return int(round(v / 1000.0))


def extract_foreign_net_lots_for_stocks(date_yyyymmdd: str, tickers: List[str]) -> Dict[str, Optional[int]]:
    """從 TWSE TWT38U 取得『外資買賣超』，並回傳『張』(lots) 而非股數(shares)。"""
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
    idx_net = find_idx("買賣超股數")  # 資料源是『股數』

    out: Dict[str, Optional[int]] = {t: None for t in tickers}
    for row in data:
        if not isinstance(row, list) or len(row) <= max(idx_code, idx_net):
            continue
        code = str(row[idx_code]).strip()
        if code in out:
            out[code] = _shares_to_lots(try_parse_int(str(row[idx_net])))
    return out


def fetch_stock_close_and_change(ticker: str, date_hint: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    url = TWSE_STOCK_DAY.format(date=date_hint, stock=ticker)
    payload = json.loads(fetch_text(url))
    data = payload.get("data") or []
    if not isinstance(data, list) or len(data) == 0:
        return None, None, None
    rows = payload.get("data") or []
    if len(rows) < 2:
        return None, None, None
    last = rows[-1]
    prev = rows[-2]
    close = try_parse_float(last[6]) if len(last) > 6 else None
    prev_close = try_parse_float(prev[6]) if len(prev) > 6 else None
    if close is None or prev

