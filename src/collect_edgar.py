"""미국 재무제표 수집. 출처: SEC EDGAR companyfacts API (키 불필요)."""
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from common import REPO_ROOT, load_watchlist

OUT_DIR = REPO_ROOT / "data" / "us" / "fundamentals"
WATCHLIST = REPO_ROOT / "config" / "us_watchlist.txt"
HEADERS = {"User-Agent": "FinancialData yhwsr92@gmail.com"}  # SEC 필수 요건
TAGS = [
    "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
    "GrossProfit", "OperatingIncomeLoss", "NetIncomeLoss",
    "Assets", "Liabilities", "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
    "NetCashProvidedByUsedInOperatingActivities",
    "EarningsPerShareDiluted", "CommonStockSharesOutstanding",
]


def load_cik_map():
    res = requests.get("https://www.sec.gov/files/company_tickers.json",
                       headers=HEADERS, timeout=30)
    res.raise_for_status()
    return {v["ticker"]: f"{v['cik_str']:010d}" for v in res.json().values()}


def fetch_facts(ticker, cik):
    res = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                       headers=HEADERS, timeout=60)
    if res.status_code == 404:  # ETF 등 companyfacts 미제공
        return pd.DataFrame()
    res.raise_for_status()
    gaap = res.json()["facts"].get("us-gaap", {})
    rows = []
    for tag in TAGS:
        for unit, items in gaap.get(tag, {}).get("units", {}).items():
            for it in items:
                rows.append({
                    "ticker": ticker, "tag": tag, "unit": unit,
                    "fy": it.get("fy"), "fp": it.get("fp"), "form": it.get("form"),
                    "end": it.get("end"), "filed": it.get("filed"), "value": it.get("val"),
                })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return df


def main():
    cik_map = load_cik_map()
    ok, failed = 0, []
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ticker in load_watchlist(WATCHLIST):
        cik = cik_map.get(ticker.replace("-", "."))  # SEC는 BRK.B 형식
        if cik is None:
            cik = cik_map.get(ticker)
        if cik is None:
            print(f"{ticker}: CIK 없음 (ETF 등 비상장기업), skip")
            continue
        try:
            df = fetch_facts(ticker, cik)
        except Exception as e:
            print(f"{ticker}: 실패 ({e})")
            failed.append(ticker)
            continue
        time.sleep(0.15)  # 10 req/s 한도 준수
        if df.empty:
            print(f"{ticker}: us-gaap 데이터 없음, skip")
            continue
        df.to_parquet(OUT_DIR / f"{ticker}.parquet", index=False)
        print(f"{ticker}: {len(df)} rows 저장")
        ok += 1

    print(f"완료: {ok}종목 저장, {len(failed)}종목 실패 {failed}")
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
