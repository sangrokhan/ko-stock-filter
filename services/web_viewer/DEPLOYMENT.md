# Web Viewer Deployment Guide

웹 뷰어 서비스를 배포하는 방법을 설명합니다.

## 전제 조건

- Docker 및 Docker Compose 설치
- 포트 8080이 사용 가능해야 함
- PostgreSQL 데이터베이스가 설정되어 있어야 함

## 배포 방법

### 1. Make를 사용한 배포 (권장)

프로젝트 루트 디렉토리에서:

```bash
# 1단계: Docker 이미지 빌드
make docker-build

# 2단계: 서비스 시작
make docker-up

# 서비스 상태 확인
make docker-ps

# 로그 확인
make docker-logs
```

#### 빌드 프로세스 설명

`make docker-build` 명령은 다음 단계를 수행합니다:

1. **베이스 이미지 빌드** (`stock-trading-base:latest`)
   - Python 3.12 기반
   - 공통 의존성 설치 (FastAPI, SQLAlchemy 등)
   - 공유 모듈 (`shared/`) 포함

2. **서비스 이미지 빌드** (web-viewer 포함)
   - 베이스 이미지를 기반으로 빌드
   - 서비스별 코드 복사
   - 서비스별 의존성 설치 (필요시)

### 2. Docker Compose 직접 사용

#### 전체 시스템 배포 (docker-compose.full.yml)

```bash
cd docker

# 베이스 이미지 빌드 (한 번만 실행)
docker build -t stock-trading-base:latest -f Dockerfile.base ..

# 모든 서비스 빌드
docker compose -f docker-compose.full.yml build

# 모든 서비스 시작
docker compose -f docker-compose.full.yml up -d

# 특정 서비스만 시작 (web-viewer와 필요한 의존성만)
docker compose -f docker-compose.full.yml up -d postgres db-migrate web-viewer
```

#### 개발용 배포 (docker-compose.yml)

개발 중 web-viewer만 빠르게 테스트하려면:

```bash
cd docker

# 베이스 이미지가 없다면 먼저 빌드
docker build -t stock-trading-base:latest -f Dockerfile.base ..

# 필요한 서비스만 시작
docker compose up -d postgres web-viewer
```

### 3. 서비스 확인

배포 후 다음 명령으로 서비스를 확인할 수 있습니다:

```bash
# 웹 브라우저에서 확인
# http://localhost:8080

# curl로 헬스 체크
curl http://localhost:8080/health

# 로그 확인
docker logs web-viewer

# 또는 make 명령 사용
make docker-logs
```

## 포트 매핑

Web Viewer 서비스는 다음 포트를 사용합니다:

- **8080**: Web Viewer HTTP API 및 웹 인터페이스

다른 서비스 포트:
- **5432**: PostgreSQL Database
- **6379**: Redis
- **8001**: Data Collector
- **8002**: Indicator Calculator
- **8003**: Stock Screener
- **8004**: Trading Engine
- **8005**: Risk Manager

포트 충돌이 발생하면 `docker-compose.yml` 또는 `docker-compose.full.yml`에서 포트 매핑을 수정할 수 있습니다.

## 환경 변수

Web Viewer는 다음 환경 변수를 사용합니다:

```bash
DATABASE_URL=postgresql://stock_user:stock_password@postgres:5432/stock_trading
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
LOG_LEVEL=INFO
```

환경 변수를 변경하려면:

1. 프로젝트 루트에 `.env` 파일 생성
2. 필요한 변수 설정
3. Docker Compose가 자동으로 로드

예시 `.env` 파일:
```env
POSTGRES_USER=my_user
POSTGRES_PASSWORD=my_secure_password
POSTGRES_DB=my_database
LOG_LEVEL=DEBUG
```

## 문제 해결

### 1. "stock-trading-base:latest" 이미지를 찾을 수 없음

```bash
# 베이스 이미지를 먼저 빌드하세요
docker build -t stock-trading-base:latest -f docker/Dockerfile.base .
```

### 2. 포트 8080이 이미 사용 중

`docker-compose.yml` 또는 `docker-compose.full.yml`에서 포트를 변경:

```yaml
web-viewer:
  ports:
    - "8090:8080"  # 호스트 포트를 8090으로 변경
```

### 3. 데이터베이스 연결 오류

```bash
# PostgreSQL 컨테이너가 실행 중인지 확인
docker ps | grep postgres

# 데이터베이스 마이그레이션 실행
docker compose -f docker-compose.full.yml up db-migrate

# 또는 make 명령 사용
make db-migrate
```

### 4. 웹 페이지가 로드되지 않음

```bash
# 컨테이너 로그 확인
docker logs web-viewer

# 컨테이너가 실행 중인지 확인
docker ps | grep web-viewer

# 컨테이너 재시작
docker restart web-viewer
```

### 5. 빌드 실패

```bash
# 모든 컨테이너 중지 및 정리
make docker-clean

# 또는
docker compose -f docker-compose.full.yml down -v
docker system prune -f

# 다시 빌드
make docker-build
```

## 로그 확인

```bash
# 모든 서비스 로그 (실시간)
make docker-logs

# web-viewer만
docker logs -f web-viewer

# 최근 100줄
docker logs --tail 100 web-viewer
```

## 서비스 중지

```bash
# Make 사용
make docker-down

# 또는 Docker Compose 직접 사용
cd docker
docker compose -f docker-compose.full.yml down

# 볼륨까지 삭제 (데이터베이스 데이터 포함)
make docker-clean
```

## 프로덕션 배포 권장사항

1. **환경 변수 보안**
   - `.env` 파일에 실제 데이터베이스 비밀번호 사용
   - `.env` 파일을 git에 커밋하지 않음 (`.gitignore`에 포함)

2. **리소스 제한**
   ```yaml
   web-viewer:
     deploy:
       resources:
         limits:
           cpus: '1'
           memory: 1G
         reservations:
           cpus: '0.5'
           memory: 512M
   ```

3. **헬스 체크 모니터링**
   - `/health` 엔드포인트를 정기적으로 확인
   - 실패 시 자동 재시작 설정 (이미 `restart: unless-stopped`로 설정됨)

4. **로그 로테이션**
   - Docker 로그 드라이버 설정 (이미 설정됨)
   - 로그 크기 제한: 10MB, 최대 3개 파일

5. **백업**
   ```bash
   make backup  # 데이터베이스 백업
   ```

6. **HTTPS 설정**
   - Nginx 또는 Traefik 리버스 프록시 사용
   - SSL/TLS 인증서 설정 (Let's Encrypt 권장)

## 업데이트 및 롤링 배포

```bash
# 코드 업데이트 후
git pull

# 롤링 업데이트
make rolling-update

# 또는 수동으로
docker compose -f docker-compose.full.yml build web-viewer
docker compose -f docker-compose.full.yml up -d --no-deps web-viewer
```

## 참고 자료

- [Docker Compose 문서](https://docs.docker.com/compose/)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)
- [프로젝트 메인 README](/README.md)
- [Web Viewer 서비스 README](/services/web_viewer/README.md)
