"""미국 시세(OHLCV) 수집. 출처: FinanceDataReader 주력, yfinance fallback."""
import argparse
import sys
import time

import pandas as pd

from common import REPO_ROOT, load_watchlist, missing_dates, save_daily

PRICES_DIR = REPO_ROOT / "data" / "us" / "prices"
WATCHLIST = REPO_ROOT / "config" / "us_watchlist.txt"


def fetch_ticker(ticker, start):
    """start일 이후 일봉. FDR 실패 시 yfinance로 재시도."""
    try:
        import FinanceDataReader as fdr
        df = fdr.DataReader(ticker, start)
        if not df.empty:
            return df
        print(f"  {ticker}: FinanceDataReader 빈 결과, yfinance로 재시도")
    except Exception as e:
        print(f"  {ticker}: FinanceDataReader 실패 ({e}), yfinance로 재시도")
    import yfinance as yf
    df = yf.download(ticker, start=start, progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="백필 대상 최근 N일")
    args = parser.parse_args()

    dates = missing_dates(PRICES_DIR, args.days)
    if not dates:
        print("누락된 날짜 없음")
        return
    tickers = load_watchlist(WATCHLIST)
    start = dates[0].isoformat()

    frames, failed = [], []
    for ticker in tickers:
        try:
            df = fetch_ticker(ticker, start)
        except Exception as e:
            print(f"  {ticker}: 실패 ({e})")
            failed.append(ticker)
            continue
        if df.empty:
            failed.append(ticker)
            continue
        df = df.reset_index()
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
        df = df.rename(columns={"index": "date"})
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df.insert(1, "ticker", ticker)
        frames.append(df[["date", "ticker", "open", "high", "low", "close", "volume"]])
        time.sleep(0.5)

    if failed:
        print(f"실패 종목: {failed}")
    if not frames:
        print("전 종목 수집 실패")
        sys.exit(1)

    merged = pd.concat(frames, ignore_index=True)
    saved = 0
    for d in dates:
        day = merged[merged["date"] == d]
        if day.empty:  # 휴장일
            continue
        save_daily(day, PRICES_DIR, d)
        print(f"{d}: {len(day)} rows 저장")
        saved += 1
    print(f"완료: {saved}일 저장, {len(failed)}종목 실패")


if __name__ == "__main__":
    main()
