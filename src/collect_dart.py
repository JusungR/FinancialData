"""한국 재무제표 수집. 출처: DART OpenAPI (OpenDartReader). env DART_API_KEY 필수."""
import os
import sys
import time
from datetime import date, datetime, timezone

import OpenDartReader

from common import REPO_ROOT, load_watchlist

OUT_DIR = REPO_ROOT / "data" / "kr" / "fundamentals"
WATCHLIST = REPO_ROOT / "config" / "kr_watchlist.txt"
# 보고서코드: 11011 사업, 11014 3분기, 11012 반기, 11013 1분기 (연내 최신순)
REPORT_CODES = ["11011", "11014", "11012", "11013"]


def fetch_latest(dart, code, year):
    """직전 2개 연도에서 가장 최근에 존재하는 보고서의 전체 재무제표."""
    for y in (year, year - 1):
        for reprt in REPORT_CODES:
            try:
                df = dart.finstate_all(code, y, reprt_code=reprt)
            except Exception:
                df = None
            time.sleep(0.3)
            if df is not None and not df.empty:
                df = df.copy()
                df["ticker"] = code
                df["year"] = y
                df["reprt_code"] = reprt
                df["fetched_at"] = datetime.now(timezone.utc).isoformat()
                return df
    return None


def main():
    key = os.environ.get("DART_API_KEY")
    if not key:
        print("환경변수 DART_API_KEY가 없습니다. opendart.fss.or.kr에서 키를 발급해 등록하세요.")
        sys.exit(1)

    dart = OpenDartReader(key)
    year = date.today().year
    ok, failed = 0, []
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for code in load_watchlist(WATCHLIST):
        df = fetch_latest(dart, code, year)
        if df is None:
            print(f"{code}: 재무제표 없음")
            failed.append(code)
            continue
        df.to_parquet(OUT_DIR / f"{code}.parquet", index=False)
        print(f"{code}: {df['year'].iat[0]}년 {df['reprt_code'].iat[0]} {len(df)} rows 저장")
        ok += 1

    print(f"완료: {ok}종목 저장, {len(failed)}종목 실패 {failed}")
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
