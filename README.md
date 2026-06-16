# FinancialData

투자 분석용 한국·미국 주식 데이터 자동 수집 저장소. GitHub Actions가 주기적으로 무료 출처에서 데이터를 받아 Parquet 파일로 커밋한다.

## 수집 데이터

| 데이터 | 범위 | 주기 | 워크플로 |
|---|---|---|---|
| KR 시세(OHLCV) + 수급(외국인/기관/개인) | 전 종목 | 평일 18:00 KST | `collect-kr.yml` |
| US 시세(OHLCV) | `config/us_watchlist.txt` | 평일 US 장마감 후 | `collect-us.yml` |
| KR·US 재무제표 | watchlist | 매주 토요일 | `collect-fundamentals.yml` |
| 경제지표 (ECOS·KOSIS) | `config/macro_indicators.json` | 매월 5일 | `collect-macro.yml` |

출처·스키마·제약은 [docs/data-sources.md](docs/data-sources.md) 참고.

## 데이터 읽기

```python
import pandas as pd
prices = pd.read_parquet("data/kr/prices")        # 디렉토리 통째로 (전 일자)
samsung = pd.read_parquet("data/kr/fundamentals/005930.parquet")
cpi = pd.read_parquet("data/macro/ecos/cpi.parquet")
```

## 로컬 실행

```bash
pip install -r requirements.txt
KRX_ID=... KRX_PW=... python src/collect_kr.py --days 7  # 최근 7일 중 누락분만 수집 (멱등)
python src/collect_us.py --days 7
python src/collect_edgar.py            # 키 불필요
DART_API_KEY=... python src/collect_dart.py
ECOS_API_KEY=... KOSIS_API_KEY=... python src/collect_macro.py
```

## 초기 설정 (1회)

1. **KRX 계정**: [data.krx.co.kr](https://data.krx.co.kr) 회원가입 → repo Settings → Secrets and variables → Actions → `KRX_ID`, `KRX_PW` 등록
2. **DART 키**: [opendart.fss.or.kr](https://opendart.fss.or.kr) 가입 → 인증키 발급 → `DART_API_KEY` 등록
3. **ECOS 키**: [ecos.bok.or.kr](https://ecos.bok.or.kr) → OpenAPI 인증키 → `ECOS_API_KEY` 등록
4. **KOSIS 키**: [kosis.kr](https://kosis.kr) 공유서비스 → OpenAPI → `KOSIS_API_KEY` 등록
5. Settings → Actions → General → Workflow permissions = **Read and write**
6. Actions 탭에서 `smoke-test` 수동 실행 → 전부 통과 확인
7. `config/` watchlist·지표를 원하는 목록으로 편집

cron은 기본 브랜치에서만 동작하므로 이 브랜치를 기본 브랜치에 머지해야 자동화가 가동된다.
