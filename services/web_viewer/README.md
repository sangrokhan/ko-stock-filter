# Web Viewer Service

데이터베이스에 저장된 주식 데이터를 확인할 수 있는 웹 인터페이스를 제공하는 서비스입니다.

## 기능

### 주요 기능
- **종목 리스트 표시**: 데이터베이스에 저장된 모든 종목 코드를 좌측 사이드바에 표시
- **종목 검색**: 종목 코드, 한글명, 영문명으로 실시간 검색
- **가격 데이터 표시**: 선택한 종목의 가격 데이터를 테이블 형태로 표시
- **페이지네이션**: 대량의 데이터를 효율적으로 로드하고 표시 (페이지당 100개)
- **시간순 정렬**: 오래된 데이터가 위에, 최신 데이터가 아래에 표시되도록 정렬

### API 엔드포인트

#### GET `/`
메인 웹 페이지를 제공합니다.

#### GET `/health`
헬스 체크 엔드포인트
```json
{
  "status": "healthy",
  "service": "web_viewer",
  "timestamp": "2024-01-01T00:00:00"
}
```

#### GET `/api/stocks`
데이터베이스의 모든 종목 리스트를 반환합니다.

**Query Parameters:**
- `is_active` (boolean, default: true): 활성 종목만 조회
- `limit` (int, default: 1000, max: 5000): 최대 반환 종목 수

**Response:**
```json
[
  {
    "ticker": "005930",
    "name_kr": "삼성전자",
    "name_en": "Samsung Electronics",
    "market": "KOSPI",
    "sector": "전기전자"
  },
  ...
]
```

#### GET `/api/stocks/{ticker}/prices`
특정 종목의 가격 데이터를 페이지네이션과 함께 반환합니다.

**Path Parameters:**
- `ticker` (string): 종목 코드 (예: "005930")

**Query Parameters:**
- `page` (int, default: 1): 페이지 번호
- `page_size` (int, default: 100, min: 10, max: 500): 페이지당 데이터 개수

**Response:**
```json
{
  "ticker": "005930",
  "stock_name": "삼성전자",
  "total_records": 1500,
  "page": 1,
  "page_size": 100,
  "total_pages": 15,
  "data": [
    {
      "id": 1,
      "date": "2024-01-01T00:00:00",
      "open": 70000,
      "high": 71000,
      "low": 69500,
      "close": 70500,
      "volume": 15000000,
      "adjusted_close": 70500,
      "change_pct": 0.71
    },
    ...
  ]
}
```

#### GET `/api/stocks/{ticker}/info`
특정 종목의 상세 정보를 반환합니다.

**Path Parameters:**
- `ticker` (string): 종목 코드

**Response:**
```json
{
  "ticker": "005930",
  "name_kr": "삼성전자",
  "name_en": "Samsung Electronics",
  "market": "KOSPI",
  "sector": "전기전자"
}
```

## 설치 및 실행

### Docker Compose로 실행

프로젝트 루트 디렉토리에서:

```bash
# 전체 서비스 실행 (web-viewer 포함)
docker-compose -f docker/docker-compose.yml up -d

# web-viewer만 실행
docker-compose -f docker/docker-compose.yml up -d postgres web-viewer
```

### 로컬에서 직접 실행

```bash
# 프로젝트 루트 디렉토리에서
cd services/web_viewer

# 환경 변수 설정
export DATABASE_URL="postgresql://stock_user:stock_password@localhost:5432/stock_trading"

# 실행
python main.py
```

서비스는 기본적으로 `http://localhost:8080`에서 실행됩니다.

## 사용 방법

1. 웹 브라우저에서 `http://localhost:8080` 접속
2. 좌측 사이드바에서 종목 리스트 확인
3. 검색창을 사용하여 원하는 종목 검색
4. 종목을 클릭하여 선택
5. 우측에 해당 종목의 가격 데이터가 테이블로 표시됨
6. 페이지네이션 버튼을 사용하여 더 많은 데이터 탐색

## 기술 스택

- **Backend**: FastAPI
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Database**: PostgreSQL (via SQLAlchemy)
- **Deployment**: Docker

## 프로젝트 구조

```
services/web_viewer/
├── __init__.py
├── main.py              # FastAPI 애플리케이션 및 API 엔드포인트
├── static/              # 정적 파일
│   └── index.html       # 메인 웹 페이지 (HTML/CSS/JS)
└── README.md            # 이 문서
```

## 개발

### 새로운 API 엔드포인트 추가

`main.py` 파일에 FastAPI 라우트를 추가하세요:

```python
@app.get("/api/your-endpoint")
async def your_endpoint(db: Session = Depends(get_db)):
    # Your logic here
    return {"data": "your data"}
```

### 프론트엔드 수정

`static/index.html` 파일을 편집하여 UI를 수정할 수 있습니다. 이 파일에는 HTML, CSS, JavaScript가 모두 포함되어 있습니다.

## 문제 해결

### 종목 리스트가 표시되지 않음
- 데이터베이스에 종목 데이터가 있는지 확인
- `data-collector` 서비스가 실행 중인지 확인
- 데이터베이스 연결 확인

### 가격 데이터가 없음
- 선택한 종목에 대한 가격 데이터가 데이터베이스에 있는지 확인
- `data-collector` 서비스를 통해 가격 데이터 수집

### 포트 충돌
- 8080 포트가 이미 사용 중인 경우, `docker-compose.yml`에서 포트를 변경하거나 로컬 실행 시 `main.py`의 포트를 변경

## 라이선스

이 프로젝트는 상위 프로젝트의 라이선스를 따릅니다.
