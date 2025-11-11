# Scripts

This directory contains utility scripts for the Korean Stock Trading System.

## Available Scripts

### seed_stock_data.py

데이터베이스에 한국 주식 데이터를 채우는 스크립트입니다.

**기능:**
- 대표적인 한국 주식 종목(KOSPI, KOSDAQ) 데이터 수집
- 과거 가격 데이터 수집 (기본값: 365일)
- 재무 지표 데이터 수집
- 기술적 지표 계산을 위한 충분한 데이터 확보
  - SMA 200: 최소 200일 필요
  - MACD: 최소 26일 필요
  - RSI: 최소 14일 필요

**사용법:**

기본 사용 (35개 대표 종목, 1년치 데이터):
```bash
python scripts/seed_stock_data.py
```

다른 기간 지정 (예: 200일):
```bash
python scripts/seed_stock_data.py --days 200
```

특정 종목만 수집:
```bash
python scripts/seed_stock_data.py --tickers "005930,000660,035420"
```

드라이런 (실제 수집 없이 테스트):
```bash
python scripts/seed_stock_data.py --dry-run
```

가격 데이터만 건너뛰기:
```bash
python scripts/seed_stock_data.py --skip-prices
```

재무 지표만 건너뛰기:
```bash
python scripts/seed_stock_data.py --skip-fundamentals
```

**옵션:**
- `--days DAYS`: 수집할 과거 데이터 일수 (기본값: 365)
- `--tickers TICKERS`: 쉼표로 구분된 종목 코드 리스트 (기본 리스트 대체)
- `--dry-run`: 실제 수집 없이 동작 확인만
- `--skip-prices`: 가격 데이터 수집 건너뛰기
- `--skip-fundamentals`: 재무 지표 수집 건너뛰기

**기본 수집 종목 (35개):**

KOSPI 대형주:
- 005930 (삼성전자)
- 000660 (SK하이닉스)
- 035420 (NAVER)
- 051910 (LG화학)
- 035720 (카카오)
- 005380 (현대자동차)
- 068270 (셀트리온)
- 006400 (삼성SDI)
- 012330 (현대모비스)
- 207940 (삼성바이오로직스)
- 105560 (KB금융)
- 055550 (신한지주)
- 086790 (하나금융지주)
- 015760 (한국전력)
- 096770 (SK이노베이션)
- 017670 (SK텔레콤)
- 032830 (삼성생명)
- 033780 (KT&G)
- 003550 (LG)
- 028260 (삼성물산)

KOSPI 중형주:
- 018260 (삼성SDS)
- 271560 (오리온)
- 034730 (SK)
- 011170 (롯데케미칼)
- 028050 (삼성엔지니어링)

KOSDAQ 성장주:
- 247540 (에코프로비엠)
- 086520 (에코프로)
- 357780 (솔루스첨단소재)
- 196170 (알테오젠)
- 293490 (카카오게임즈)
- 095340 (ISC)
- 112040 (위메이드)
- 263750 (펄어비스)
- 328130 (루첸텍)
- 214150 (클래시스)

**다음 단계:**

데이터 시딩 후 다음 서비스를 실행하여 지표를 계산하세요:
1. Indicator Calculator 서비스 - 기술적 지표 계산
2. Stock Scorer 서비스 - 종합 점수 계산
3. Stability Calculator 서비스 - 안정성 점수 계산

**참고사항:**
- 외부 API 호출이 포함되어 있어 실행 시간이 오래 걸릴 수 있습니다 (약 10-30분)
- Rate limiting이 적용되어 있어 API 제한을 피합니다
- 네트워크 오류 시 자동으로 재시도합니다
- 이미 존재하는 데이터는 건너뛰거나 업데이트됩니다

**예제 워크플로우:**

```bash
# 1. 데이터베이스 준비
docker-compose up -d postgres redis

# 2. 데이터베이스 마이그레이션
alembic upgrade head

# 3. 데이터 시딩 (1년치 데이터)
python scripts/seed_stock_data.py --days 365

# 4. 기술적 지표 계산
# (indicator_calculator 서비스 실행)

# 5. 점수 계산
# (stock_scorer 및 stability_calculator 서비스 실행)
```
