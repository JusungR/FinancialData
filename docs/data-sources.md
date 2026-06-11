# 데이터 출처

## 한국 시세·수급 — pykrx

- **출처**: KRX 정보데이터시스템(data.krx.co.kr) 스크래핑. 무료, 키 불필요
- **호출 패턴**: 날짜별 일괄 조회 — `get_market_ohlcv(날짜, market)` 시장당 1회, 수급은 투자자 3종 × 시장 2 = 6회/일. 호출 간 1초 sleep
- **저장**: `data/kr/prices/{YYYY-MM-DD}.parquet`, `data/kr/flows/{YYYY-MM-DD}.parquet` (일별 파일, 한 번 쓰면 불변)
- **스키마 (prices)**: `date, ticker, market, open, high, low, close, volume, value, change_pct`
- **스키마 (flows)**: `date, ticker, market, investor(foreign/institution/individual), buy_volume, sell_volume, net_volume, buy_value, sell_value, net_value`
- **리스크**: 비공식 스크래핑이라 KRX 페이지 변경·해외 IP 차단 가능성 있음. smoke-test 워크플로로 검증. 차단 시 대안: (a) 재시도/실행 시각 변경, (b) self-hosted runner, (c) KR 시세만 FinanceDataReader(네이버)로 대체 — 단 **수급 데이터는 KRX 외 무료 대안이 사실상 없음**

## 미국 시세 — FinanceDataReader (+ yfinance fallback)

- **출처**: FinanceDataReader (무료). 실패 시 yfinance로 자동 재시도 — yfinance는 Yahoo의 비공식 엔드포인트 의존이라 2024년 이후 차단이 잦아 보조로만 사용
- **호출 패턴**: watchlist 종목별 시계열 조회 후 날짜별 파일로 분배. 종목 간 0.5초 sleep
- **저장/스키마**: `data/us/prices/{YYYY-MM-DD}.parquet` — `date, ticker, open, high, low, close, volume`

## 한국 재무제표 — DART OpenAPI (OpenDartReader)

- **출처**: 금융감독원 전자공시 [opendart.fss.or.kr](https://opendart.fss.or.kr). 무료 인증키, **일 20,000건 한도**
- **호출 패턴**: watchlist 종목별 `finstate_all` — 직전 2개 연도에서 가장 최근 보고서(사업>3분기>반기>1분기 순 탐색) 1건
- **저장**: `data/kr/fundamentals/{종목코드}.parquet` 덮어쓰기 (주 1회)
- **스키마**: DART 응답 원본(`account_nm, fs_div, thstrm_amount` 등) + `ticker, year, reprt_code, fetched_at`
- **확장**: 공시 목록이 필요하면 `dart.list(종목)` 함수 하나로 추가 가능 (현재는 재무 수치만)

## 미국 재무제표 — SEC EDGAR companyfacts

- **출처**: [SEC EDGAR API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces). 무료, 키 불필요. **10 req/s 한도, User-Agent 헤더(연락처) 필수**
- **호출 패턴**: `company_tickers.json`으로 ticker→CIK 매핑 후 `companyfacts/CIK{cik}.json`에서 주요 us-gaap 태그 12개만 추출. 요청 간 0.15초 sleep
- **저장**: `data/us/fundamentals/{ticker}.parquet` 덮어쓰기
- **스키마**: `ticker, tag, unit, fy, fp, form, end, filed, value, fetched_at`
- **참고**: ETF(SPY 등)는 companyfacts가 없어 자동 skip

## 경제지표 — ECOS + KOSIS (월간)

- **출처**: 한국은행 [ECOS OpenAPI](https://ecos.bok.or.kr) / 통계청 [KOSIS OpenAPI](https://kosis.kr). 둘 다 무료 키 필요
- **지표 정의**: `config/macro_indicators.json` — ECOS는 통계표코드/항목코드, KOSIS는 orgId/tblId/itmId. 코드는 ECOS 통계코드검색, KOSIS URL생성기에서 확인 후 추가/수정. **시드 코드는 최초 실행 시 웹 화면 값과 대조해 검증할 것**
- **저장**: `data/macro/{ecos|kosis}/{지표id}.parquet` — 매번 2000년 이후 전체 시계열 덮어쓰기 (과거 수치 정정 자동 반영)
- **스키마**: `indicator_id, name, period(YYYY-MM), value, unit, fetched_at`

## 공통 운영 정책

- **멱등 백필**: 시세/수급은 `--days N`(기본 7) 내 누락 날짜만 수집. 워크플로 실패 시 다음 실행에서 자동 복구. 휴장일은 파일 미생성
- **실패 정책**: 종목/날짜/지표 단위 오류는 로그 후 계속, 출처 전체 실패 시에만 exit 1 (GitHub 기본 알림). 부분 성공분은 `if: always()` 커밋으로 보존
- **저장소 크기**: KR 전 종목 일봉 연 ~25MB 수준. 수년 뒤 비대해지면 히스토리 squash 검토
