# Web Viewer Service - Tests

이 디렉토리에는 Web Viewer 서비스의 자동화된 테스트가 포함되어 있습니다.

## 테스트 구조

```
tests/
├── __init__.py           # 테스트 패키지 초기화
├── conftest.py          # Pytest fixtures 및 설정
├── test_api.py          # API 엔드포인트 테스트
├── test_edge_cases.py   # 에러 처리 및 엣지 케이스 테스트
├── requirements.txt     # 테스트 의존성
└── README.md           # 이 문서
```

## 테스트 범위

### 1. API 엔드포인트 테스트 (`test_api.py`)

#### Health Check
- ✅ 헬스 체크 성공 응답

#### 종목 리스트 (`/api/stocks`)
- ✅ 빈 데이터베이스에서 빈 배열 반환
- ✅ 활성 종목만 반환
- ✅ limit 파라미터 적용
- ✅ 종목 코드로 정렬

#### 종목 정보 (`/api/stocks/{ticker}/info`)
- ✅ 존재하는 종목 정보 조회
- ✅ 존재하지 않는 종목 404 반환
- ✅ 빈 데이터베이스에서 404 반환

#### 가격 데이터 (`/api/stocks/{ticker}/prices`)
- ✅ 데이터가 있는 경우 정상 반환
- ✅ 데이터가 없는 경우 빈 배열 반환
- ✅ 존재하지 않는 종목 404 반환
- ✅ 페이지네이션 동작 (1페이지, 2페이지, 마지막 페이지)
- ✅ 유효하지 않은 페이지 번호 처리
- ✅ 페이지 크기 제한 (min: 10, max: 500)
- ✅ 데이터 구조 검증
- ✅ 날짜순 오름차순 정렬 (오래된 데이터가 먼저)

#### 메인 페이지 (`/`)
- ✅ HTML 페이지 반환
- ✅ 필수 UI 요소 포함

### 2. 엣지 케이스 및 에러 처리 (`test_edge_cases.py`)

#### 데이터베이스 연결 오류
- ✅ 데이터베이스 연결 실패 시 적절한 에러 처리

#### 잘못된 입력값
- ✅ 음수 페이지 번호 (422 반환)
- ✅ 0 페이지 번호 (422 반환)
- ✅ 페이지 크기가 너무 작음 (422 반환)
- ✅ 페이지 크기가 너무 큼 (422 반환)
- ✅ 숫자가 아닌 페이지 파라미터 (422 반환)
- ✅ 과도한 limit 값 (422 반환)

#### 특수 문자 처리
- ✅ 종목 코드에 특수 문자 포함
- ✅ SQL 인젝션 시도 방어

#### 빈 데이터베이스
- ✅ 모든 엔드포인트가 빈 DB에서 정상 동작

#### 데이터 무결성
- ✅ total_records가 실제 레코드 수와 일치
- ✅ 페이지네이션에서 중복 레코드 없음
- ✅ 페이지네이션에서 누락된 레코드 없음

#### 비활성 종목
- ✅ 기본적으로 리스트에서 제외
- ✅ 직접 조회는 가능

#### 대용량 데이터
- ✅ 대량의 종목 데이터 처리
- ✅ limit 파라미터 정상 동작

#### 동시 접근
- ✅ 여러 동시 요청 처리

#### 숫자 정밀도
- ✅ 가격 데이터의 정확한 표현
- ✅ 양수 값 검증

## 설치 및 실행

### 1. 테스트 의존성 설치

프로젝트 루트에서:

```bash
# 기본 의존성 설치 (이미 설치되어 있다면 생략)
pip install -r requirements.txt

# 테스트 의존성 설치
pip install -r services/web_viewer/tests/requirements.txt
```

### 2. 테스트 실행

#### 모든 테스트 실행
```bash
# 프로젝트 루트에서
pytest services/web_viewer/tests/

# 또는 web_viewer 디렉토리에서
cd services/web_viewer
pytest tests/
```

#### 특정 테스트 파일 실행
```bash
pytest services/web_viewer/tests/test_api.py
pytest services/web_viewer/tests/test_edge_cases.py
```

#### 특정 테스트 클래스 실행
```bash
pytest services/web_viewer/tests/test_api.py::TestStockPricesEndpoint
```

#### 특정 테스트 함수 실행
```bash
pytest services/web_viewer/tests/test_api.py::TestStockPricesEndpoint::test_get_prices_with_data
```

#### Verbose 모드로 실행
```bash
pytest services/web_viewer/tests/ -v
```

#### 코드 커버리지 확인
```bash
pytest services/web_viewer/tests/ --cov=services/web_viewer --cov-report=html
```

커버리지 리포트는 `htmlcov/index.html`에서 확인할 수 있습니다.

### 3. Docker에서 테스트 실행

```bash
# Docker 컨테이너 내에서 테스트 실행
docker-compose -f docker/docker-compose.test.yml run --rm web-viewer-test pytest
```

## 테스트 작성 가이드

### 새로운 테스트 추가하기

1. **적절한 파일 선택**
   - API 기능 테스트: `test_api.py`
   - 에러 처리/엣지 케이스: `test_edge_cases.py`

2. **테스트 클래스 구조**
```python
class TestFeatureName:
    """Tests for feature description."""

    def test_specific_behavior(self, client, fixtures):
        """Test that specific behavior works correctly."""
        # Arrange
        # Act
        # Assert
```

3. **Fixture 사용**
   - `client`: FastAPI TestClient
   - `test_db`: 테스트용 데이터베이스 세션
   - `sample_stocks`: 샘플 종목 데이터
   - `sample_prices`: 샘플 가격 데이터
   - `empty_stock`: 가격 데이터가 없는 종목

4. **새로운 Fixture 추가**
   필요한 경우 `conftest.py`에 새로운 fixture를 추가하세요.

### 테스트 모범 사례

1. **명확한 테스트 이름**: 테스트가 무엇을 검증하는지 이름에서 알 수 있어야 함
2. **독립성**: 각 테스트는 다른 테스트에 의존하지 않아야 함
3. **AAA 패턴**: Arrange(준비), Act(실행), Assert(검증) 패턴 사용
4. **명확한 Assertion**: 실패 시 원인을 쉽게 파악할 수 있도록
5. **엣지 케이스**: 정상 케이스뿐만 아니라 경계 조건도 테스트

## CI/CD 통합

이 테스트들은 CI/CD 파이프라인에 통합되어 자동으로 실행됩니다:

- Pull Request 생성 시 자동 실행
- Main 브랜치 머지 전 필수 통과
- 테스트 실패 시 머지 차단

## 문제 해결

### 테스트 실패 시

1. **에러 메시지 확인**: pytest는 상세한 에러 정보를 제공합니다
2. **개별 테스트 실행**: 실패한 테스트만 개별적으로 실행
3. **디버그 모드**: `pytest -vv --pdb` 로 디버거 사용
4. **로그 확인**: `pytest -s` 로 print 문 출력 확인

### 일반적인 문제

**ImportError**
```bash
# PYTHONPATH 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest services/web_viewer/tests/
```

**Database fixture errors**
```bash
# 테스트는 in-memory SQLite를 사용하므로 PostgreSQL 불필요
# conftest.py의 설정 확인
```

## 테스트 통계

- **총 테스트 수**: 50+개
- **커버리지 목표**: 80% 이상
- **평균 실행 시간**: ~5초

## 기여하기

새로운 기능을 추가할 때는 반드시 해당 기능에 대한 테스트를 함께 작성해주세요:
1. 정상 동작 테스트
2. 에러 케이스 테스트
3. 엣지 케이스 테스트

## 참고 자료

- [pytest 공식 문서](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)
