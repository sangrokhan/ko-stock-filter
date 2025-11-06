# GitHub Actions Workflows

이 디렉토리에는 CI/CD를 위한 GitHub Actions 워크플로우가 포함되어 있습니다.

## 워크플로우 목록

### 1. Unit Tests & Coverage (`unit-tests.yml`)

**목적**: PR 생성 시 단위 테스트와 코드 커버리지를 자동으로 체크합니다.

**실행 조건**:
- Push to: `main`, `develop`, `claude/*` 브랜치
- Pull request to: `main`, `develop` 브랜치
- 수동 실행 가능

**주요 기능**:
- ✅ 단위 테스트 실행 (통합 테스트 제외)
- ✅ 코드 커버리지 측정 및 리포트 생성
- ✅ 커버리지 임계값 체크 (70% 이상 권장)
- ✅ Codecov 자동 업로드
- ✅ HTML 커버리지 리포트 아티팩트 저장
- ✅ 코드 품질 검사 (Black, Flake8, MyPy, isort)

**특징**:
- **외부 의존성 불필요**: Mock을 사용하여 데이터베이스, Redis, 외부 API 없이 실행
- **빠른 실행**: 통합 테스트 제외로 빠른 피드백 (약 5-10분)
- **자세한 리포트**: HTML 커버리지 리포트를 아티팩트로 다운로드 가능

### 2. Integration Tests (`integration-tests.yml`)

**목적**: 전체 시스템 통합 테스트를 실행합니다.

**실행 조건**:
- Push to: `main`, `develop`, `claude/*` 브랜치
- Pull request to: `main`, `develop` 브랜치
- 수동 실행 가능

**주요 기능**:
- ✅ PostgreSQL 및 Redis 서비스 자동 설정
- ✅ Docker 기반 마이크로서비스 환경 구성
- ✅ E2E 워크플로우 테스트
- ✅ 서비스 간 통신 테스트
- ✅ 데이터베이스 CRUD 테스트
- ✅ 실패 시 서비스 로그 자동 출력

**특징**:
- **완전한 환경**: 실제 서비스와 유사한 환경에서 테스트
- **긴 실행 시간**: 전체 스택 테스트로 약 20-30분 소요
- **디버깅 지원**: 실패 시 모든 서비스 로그 제공

### 3. PR Quality Checks (`pr-checks.yml`)

**목적**: PR의 품질을 자동으로 확인합니다.

**실행 조건**:
- Pull request가 열리거나 업데이트될 때

**주요 기능**:
- ✅ PR 정보 요약
- ✅ 테스트 파일 변경 여부 체크
- ✅ 커버리지 변화 리포트
- ✅ 테스트 의존성 확인

## Mock 사용 정책

모든 단위 테스트는 **외부 의존성 없이 실행**되어야 합니다:

### 자동으로 Mock되는 항목

1. **데이터베이스**
   - SQLite in-memory 사용
   - 각 테스트마다 격리된 세션
   - 자동 롤백

2. **Redis**
   - `mock_redis` fixture 사용
   - 실제 Redis 서버 불필요

3. **외부 API**
   - `@patch` 데코레이터 사용
   - `mock_external_api` fixture 사용

4. **환경 변수**
   - `mock_environment_variables` fixture (autouse)
   - 테스트 모드 자동 설정

### 예시: Mock 사용법

```python
# 외부 API Mock
@patch('services.data_collector.price_collector.fdr.DataReader')
def test_fetch_price_data(mock_fdr, collector):
    mock_fdr.return_value = mock_data
    result = collector.fetch_price_data('005930')
    assert result is not None

# Redis Mock
def test_cache_operation(mock_redis):
    mock_redis.set('key', 'value')
    assert mock_redis.set.called

# 데이터베이스 (이미 in-memory)
def test_db_operation(test_db_session):
    stock = Stock(ticker='005930')
    test_db_session.add(stock)
    test_db_session.commit()
```

## 로컬에서 테스트 실행

### 단위 테스트만 실행

```bash
# 기본 실행
pytest tests/ --ignore=tests/integration/

# 커버리지 포함
pytest tests/ --ignore=tests/integration/ \
  --cov=services \
  --cov=shared \
  --cov-report=html \
  --cov-report=term-missing

# 특정 파일만
pytest tests/test_price_collector.py -v

# 실패한 테스트만 재실행
pytest tests/ --lf --ignore=tests/integration/
```

### 통합 테스트 실행

```bash
# Docker 환경 필요
cd tests/integration
./run_tests.sh
```

### 코드 품질 체크

```bash
# 포매팅 체크
black --check services/ shared/ tests/

# 린팅
flake8 services/ shared/ tests/ --max-line-length=100

# 타입 체크
mypy services/ shared/ --ignore-missing-imports

# Import 정렬
isort --check-only services/ shared/ tests/
```

## 커버리지 리포트 보기

### GitHub Actions에서

1. Actions 탭으로 이동
2. 완료된 워크플로우 선택
3. "Artifacts" 섹션에서 `coverage-report-*` 다운로드
4. `htmlcov/index.html` 열기

### 로컬에서

```bash
pytest tests/ --ignore=tests/integration/ --cov=services --cov=shared --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 커버리지 목표

| 항목 | 목표 | 현재 |
|------|------|------|
| 전체 라인 커버리지 | 80% | 측정 중 |
| 단위 테스트 커버리지 | 85% | 측정 중 |
| 통합 테스트 커버리지 | 70% | 측정 중 |
| 서비스 커버리지 | 9/11 (81.8%) | ✅ 달성 |

## 문제 해결

### 테스트 실패 시

1. **Import 에러**
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-cov pytest-asyncio pytest-mock
   ```

2. **의존성 문제**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

3. **환경 변수 문제**
   - `conftest.py`의 `mock_environment_variables`가 자동으로 설정함
   - 필요시 `.env.test` 파일 생성

### GitHub Actions 실패 시

1. **Workflow 로그 확인**
   - Actions 탭에서 실패한 워크플로우 클릭
   - 실패한 단계의 로그 확인

2. **아티팩트 다운로드**
   - 커버리지 리포트
   - 테스트 결과 (junit.xml)
   - 서비스 로그 (통합 테스트)

3. **로컬 재현**
   ```bash
   # 같은 명령어로 로컬에서 실행
   pytest tests/ --ignore=tests/integration/ -v
   ```

## 기여 가이드

### 새 테스트 추가 시

1. **적절한 Mock 사용**
   - 외부 API는 `@patch` 사용
   - Redis는 `mock_redis` fixture 사용
   - 데이터베이스는 `test_db_session` 사용

2. **테스트 네이밍**
   - 파일명: `test_*.py`
   - 클래스명: `Test*`
   - 함수명: `test_*`

3. **Docstring 작성**
   ```python
   def test_something():
       """Test that something works correctly."""
       pass
   ```

4. **커버리지 확인**
   - 새 기능 추가 시 테스트도 함께 작성
   - 커버리지가 낮아지지 않도록 주의

### PR 제출 전 체크리스트

- [ ] 모든 단위 테스트 통과
- [ ] 새 기능에 대한 테스트 추가
- [ ] 코드 포매팅 적용 (Black)
- [ ] Import 정렬 (isort)
- [ ] 린팅 통과 (Flake8)
- [ ] 타입 체크 통과 (MyPy, optional)
- [ ] 커버리지 70% 이상 유지

## 추가 리소스

- [Pytest 공식 문서](https://docs.pytest.org/)
- [pytest-cov 문서](https://pytest-cov.readthedocs.io/)
- [unittest.mock 가이드](https://docs.python.org/3/library/unittest.mock.html)
- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [Codecov 문서](https://docs.codecov.com/)
