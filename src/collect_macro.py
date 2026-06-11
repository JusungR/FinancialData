"""경제지표 수집 (월간). 출처: ECOS(한국은행) + KOSIS(통계청) OpenAPI.

env ECOS_API_KEY, KOSIS_API_KEY 필수. 지표 정의는 config/macro_indicators.json.
"""
import json
import os
import sys
import time
from datetime import date, datetime, timezone

import pandas as pd
import requests

from common import REPO_ROOT

CONFIG = REPO_ROOT / "config" / "macro_indicators.json"
OUT_DIR = REPO_ROOT / "data" / "macro"
START_MONTH = "200001"


def fetch_ecos(key, ind, end_month):
    url = (f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/10000/"
           f"{ind['stat_code']}/{ind['cycle']}/{START_MONTH}/{end_month}/{ind['item_code1']}")
    res = requests.get(url, timeout=30).json()
    if "StatisticSearch" not in res:
        raise RuntimeError(res.get("RESULT", res))
    rows = res["StatisticSearch"]["row"]
    return pd.DataFrame({
        "indicator_id": ind["id"],
        "name": ind["name"],
        "period": [f"{r['TIME'][:4]}-{r['TIME'][4:6]}" for r in rows],
        "value": pd.to_numeric([r["DATA_VALUE"] for r in rows], errors="coerce"),
        "unit": [r.get("UNIT_NAME") or "" for r in rows],
    })


def fetch_kosis(key, ind, end_month):
    params = {
        "method": "getList", "apiKey": key, "format": "json", "jsonVD": "Y",
        "orgId": ind["org_id"], "tblId": ind["tbl_id"], "itmId": ind["itm_id"],
        "objL1": ind.get("obj_l1", "ALL"),
        "prdSe": ind.get("prd_se", "M"),
        "startPrdDe": START_MONTH, "endPrdDe": end_month,
    }
    res = requests.get("https://kosis.kr/openapi/Param/statisticsParameterData.do",
                       params=params, timeout=30).json()
    if isinstance(res, dict):  # 정상이면 list, 오류면 {"err": ..., "errMsg": ...}
        raise RuntimeError(res)
    return pd.DataFrame({
        "indicator_id": ind["id"],
        "name": ind["name"],
        "period": [f"{r['PRD_DE'][:4]}-{r['PRD_DE'][4:6]}" for r in res],
        "value": pd.to_numeric([r.get("DT") for r in res], errors="coerce"),
        "unit": [r.get("UNIT_NM") or "" for r in res],
    })


def collect(source, fetch, key, indicators, end_month):
    ok, errors = 0, 0
    out_dir = OUT_DIR / source
    out_dir.mkdir(parents=True, exist_ok=True)
    for ind in indicators:
        try:
            df = fetch(key, ind, end_month)
        except Exception as e:
            print(f"[{source}] {ind['id']}: 실패 ({e})")
            errors += 1
            continue
        time.sleep(0.5)
        df["fetched_at"] = datetime.now(timezone.utc).isoformat()
        df.to_parquet(out_dir / f"{ind['id']}.parquet", index=False)
        print(f"[{source}] {ind['id']}: {len(df)} rows 저장 (최근 {df['period'].iat[-1]})")
        ok += 1
    return ok, errors


def main():
    ecos_key = os.environ.get("ECOS_API_KEY")
    kosis_key = os.environ.get("KOSIS_API_KEY")
    if not ecos_key or not kosis_key:
        print("환경변수 ECOS_API_KEY / KOSIS_API_KEY가 없습니다. "
              "ecos.bok.or.kr, kosis.kr에서 키를 발급해 등록하세요.")
        sys.exit(1)

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    end_month = date.today().strftime("%Y%m")
    ecos_ok, ecos_err = collect("ecos", fetch_ecos, ecos_key, config["ecos"], end_month)
    kosis_ok, kosis_err = collect("kosis", fetch_kosis, kosis_key, config["kosis"], end_month)

    print(f"완료: ecos {ecos_ok}건(오류 {ecos_err}), kosis {kosis_ok}건(오류 {kosis_err})")
    if (ecos_ok == 0 and ecos_err > 0) or (kosis_ok == 0 and kosis_err > 0):
        sys.exit(1)


if __name__ == "__main__":
    main()
