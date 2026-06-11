"""한국 시세(OHLCV) + 수급(투자자별 순매수) 수집. 출처: pykrx (KRX)."""
import argparse
import sys
import time

import pandas as pd
from pykrx import stock

from common import REPO_ROOT, missing_dates, save_daily

PRICES_DIR = REPO_ROOT / "data" / "kr" / "prices"
FLOWS_DIR = REPO_ROOT / "data" / "kr" / "flows"

MARKETS = ("KOSPI", "KOSDAQ")
PRICE_COLUMNS = {
    "티커": "ticker", "시가": "open", "고가": "high", "저가": "low", "종가": "close",
    "거래량": "volume", "거래대금": "value", "등락률": "change_pct",
}
INVESTORS = {"외국인": "foreign", "기관합계": "institution", "개인": "individual"}
FLOW_COLUMNS = {
    "티커": "ticker",
    "매수거래량": "buy_volume", "매도거래량": "sell_volume", "순매수거래량": "net_volume",
    "매수거래대금": "buy_value", "매도거래대금": "sell_value", "순매수거래대금": "net_value",
}


def fetch_prices(d):
    """하루치 전 종목 OHLCV. 휴장일이면 None."""
    frames = []
    for market in MARKETS:
        df = stock.get_market_ohlcv(d.strftime("%Y%m%d"), market=market)
        time.sleep(1)
        if df.empty or (df["종가"] == 0).all():  # 휴장일은 빈 값 또는 0으로 반환됨
            return None
        df = df.reset_index().rename(columns=PRICE_COLUMNS)
        df.insert(0, "date", d.isoformat())
        df.insert(2, "market", market)
        frames.append(df[["date", "ticker", "market", "open", "high", "low",
                          "close", "volume", "value", "change_pct"]])
    return pd.concat(frames, ignore_index=True)


def fetch_flows(d):
    """하루치 투자자별(외국인/기관/개인) 종목 순매수."""
    ymd = d.strftime("%Y%m%d")
    frames = []
    for market in MARKETS:
        for kr_name, investor in INVESTORS.items():
            df = stock.get_market_net_purchases_of_equities(ymd, ymd, market, kr_name)
            time.sleep(1)
            if df.empty:
                raise RuntimeError(f"{market}/{investor} 수급 응답이 비어 있음")
            df = df.reset_index().rename(columns=FLOW_COLUMNS)
            df.insert(0, "date", d.isoformat())
            df.insert(2, "market", market)
            df.insert(3, "investor", investor)
            frames.append(df[["date", "ticker", "market", "investor",
                              "buy_volume", "sell_volume", "net_volume",
                              "buy_value", "sell_value", "net_value"]])
    return pd.concat(frames, ignore_index=True)


def collect_prices(days):
    ok, errors = 0, 0
    for d in missing_dates(PRICES_DIR, days):
        try:
            df = fetch_prices(d)
        except Exception as e:
            print(f"[prices] {d}: ERROR {e}")
            errors += 1
            continue
        if df is None:
            print(f"[prices] {d}: 휴장일, skip")
            continue
        save_daily(df, PRICES_DIR, d)
        print(f"[prices] {d}: {len(df)} rows 저장")
        ok += 1
    return ok, errors


def collect_flows(days):
    """수급 수집. 휴장일 판정은 시세 파일 존재 여부로 — 시세가 없으면 보류."""
    ok, errors = 0, 0
    for d in missing_dates(FLOWS_DIR, days):
        if not (PRICES_DIR / f"{d.isoformat()}.parquet").exists():
            print(f"[flows] {d}: 시세 없음(휴장일 또는 미수집), skip")
            continue
        try:
            df = fetch_flows(d)
        except Exception as e:
            print(f"[flows] {d}: ERROR {e}")
            errors += 1
            continue
        save_daily(df, FLOWS_DIR, d)
        print(f"[flows] {d}: {len(df)} rows 저장")
        ok += 1
    return ok, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="백필 대상 최근 N일")
    args = parser.parse_args()

    price_ok, price_err = collect_prices(args.days)
    flow_ok, flow_err = collect_flows(args.days)

    print(f"완료: prices {price_ok}일(오류 {price_err}), flows {flow_ok}일(오류 {flow_err})")
    if (price_ok == 0 and price_err > 0) or (flow_ok == 0 and flow_err > 0):
        sys.exit(1)


if __name__ == "__main__":
    main()
