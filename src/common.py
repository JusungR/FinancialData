from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_watchlist(path):
    items = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            items.append(line)
    return items


def missing_dates(out_dir, days):
    """최근 days일 중 주말 제외, parquet 파일이 없는 날짜 목록 (오름차순)."""
    today = date.today()
    result = []
    for i in range(days, -1, -1):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        if not (Path(out_dir) / f"{d.isoformat()}.parquet").exists():
            result.append(d)
    return result


def save_daily(df, out_dir, d):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / f"{d.isoformat()}.parquet", index=False)
