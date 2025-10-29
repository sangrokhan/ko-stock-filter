# Stock Trading System - Deployment Guide

This directory contains all deployment configurations and scripts for the Korean Stock Trading System.

## Table of Contents

- [Overview](#overview)
- [Deployment Options](#deployment-options)
- [Quick Start](#quick-start)
- [Docker Deployment](#docker-deployment)
- [Linux Systemd Deployment](#linux-systemd-deployment)
- [Backup and Restore](#backup-and-restore)
- [Zero-Downtime Updates](#zero-downtime-updates)
- [Monitoring and Logs](#monitoring-and-logs)
- [Troubleshooting](#troubleshooting)

## Overview

The Stock Trading System consists of 10 microservices:

1. **Data Collector** (Port 8001) - Collects stock data from KRX APIs
2. **Indicator Calculator** (Port 8002) - Calculates technical indicators
3. **Stability Calculator** - Calculates stock stability scores
4. **Stock Scorer** - Multi-dimensional stock scoring
5. **Stock Screener** (Port 8003) - Filters stocks based on criteria
6. **Watchlist Manager** - Manages stock watchlists
7. **Price Monitor** - Real-time price monitoring
8. **Trading Engine** (Port 8004) - Executes trades
9. **Risk Manager** (Port 8005) - Manages portfolio risk
10. **Orchestrator** - Master controller coordinating all services

### Infrastructure Services

- **PostgreSQL** (Port 5432) - Primary database
- **Redis** (Port 6379) - Cache and pub/sub

## Deployment Options

### 1. Docker Deployment (Recommended for Development)

- Easy setup and teardown
- Consistent environment across machines
- Isolated networking
- Volume persistence

### 2. Linux Systemd Deployment (Recommended for Production)

- Native Linux service management
- Better resource control
- Easier debugging
- Direct access to logs via journalctl

## Quick Start

### Docker Deployment

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Edit environment variables
nano .env

# 3. Start all services
cd docker
docker compose -f docker-compose.full.yml up -d

# 4. Check service status
docker compose -f docker-compose.full.yml ps

# 5. View logs
docker compose -f docker-compose.full.yml logs -f orchestrator
```

### Systemd Deployment

```bash
# 1. Run installation script
sudo ./deployment/scripts/install-systemd.sh

# 2. Configure environment
sudo nano /etc/stock-trading/orchestrator.env

# 3. Start services
sudo systemctl start stock-trading-orchestrator

# 4. Check status
sudo systemctl status stock-trading-orchestrator

# 5. View logs
sudo journalctl -u stock-trading-orchestrator -f
```

## Docker Deployment

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 20GB disk space

### Directory Structure

```
docker/
├── docker-compose.full.yml      # Complete stack
├── docker-compose.yml           # Basic services
├── Dockerfile.base              # Base image
├── Dockerfile.data_collector    # Service-specific images
├── Dockerfile.orchestrator
└── ...
```

### Environment Configuration

Create `.env` file in project root:

```env
# Database
POSTGRES_USER=stock_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=stock_trading

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# API Keys
KRX_API_KEY=your_krx_api_key
KOREAINVESTMENT_API_KEY=your_api_key
KOREAINVESTMENT_API_SECRET=your_api_secret

# Trading
PAPER_TRADING=true
MAX_PORTFOLIO_RISK_PCT=2.0
MAX_POSITION_SIZE_PCT=10.0

# Logging
LOG_LEVEL=INFO
```

### Starting Services

```bash
# Start all services
docker compose -f docker/docker-compose.full.yml up -d

# Start specific services
docker compose -f docker/docker-compose.full.yml up -d postgres redis data-collector

# Scale a service
docker compose -f docker/docker-compose.full.yml up -d --scale trading-engine=2
```

### Monitoring Docker Services

```bash
# View all containers
docker compose -f docker/docker-compose.full.yml ps

# View logs
docker compose -f docker/docker-compose.full.yml logs -f [service_name]

# View resource usage
docker stats

# Execute command in container
docker compose -f docker/docker-compose.full.yml exec trading-engine bash
```

### Stopping Services

```bash
# Stop all services
docker compose -f docker/docker-compose.full.yml down

# Stop and remove volumes (DANGER: deletes data)
docker compose -f docker/docker-compose.full.yml down -v
```

## Linux Systemd Deployment

### Prerequisites

- Ubuntu 20.04+ or similar Linux distribution
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- sudo access

### Installation Steps

#### 1. Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install PostgreSQL
sudo apt install -y postgresql-15 postgresql-client-15

# Install Redis
sudo apt install -y redis-server

# Install Python and build tools
sudo apt install -y python3.11 python3.11-venv python3-pip
sudo apt install -y gcc g++ make libpq-dev
```

#### 2. Create Application User

```bash
sudo useradd -r -m -d /opt/stock-trading -s /bin/bash stocktrading
```

#### 3. Deploy Application

```bash
# Clone repository
sudo -u stocktrading git clone <repository_url> /opt/stock-trading
cd /opt/stock-trading

# Create virtual environment
sudo -u stocktrading python3.11 -m venv /opt/stock-trading/venv

# Install dependencies
sudo -u stocktrading /opt/stock-trading/venv/bin/pip install -r requirements.txt

# Create directories
sudo mkdir -p /opt/stock-trading/logs
sudo mkdir -p /opt/stock-trading/data
sudo mkdir -p /etc/stock-trading
sudo chown -R stocktrading:stocktrading /opt/stock-trading
```

#### 4. Configure Database

```bash
# Create database user and database
sudo -u postgres psql <<EOF
CREATE USER stock_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE stock_trading OWNER stock_user;
GRANT ALL PRIVILEGES ON DATABASE stock_trading TO stock_user;
EOF

# Run migrations
cd /opt/stock-trading
sudo -u stocktrading /opt/stock-trading/venv/bin/alembic upgrade head
```

#### 5. Install Systemd Services

```bash
# Copy service files
sudo cp deployment/systemd/*.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable stock-trading-postgres
sudo systemctl enable stock-trading-redis
sudo systemctl enable stock-trading-data-collector
sudo systemctl enable stock-trading-orchestrator
# ... enable other services as needed

# Start services
sudo systemctl start stock-trading-orchestrator
```

#### 6. Configure Log Rotation

```bash
# Install logrotate configuration
sudo cp deployment/logrotate/stock-trading /etc/logrotate.d/

# Test configuration
sudo logrotate -d /etc/logrotate.d/stock-trading
```

### Managing Systemd Services

```bash
# Start service
sudo systemctl start stock-trading-orchestrator

# Stop service
sudo systemctl stop stock-trading-orchestrator

# Restart service
sudo systemctl restart stock-trading-orchestrator

# Check status
sudo systemctl status stock-trading-orchestrator

# View logs
sudo journalctl -u stock-trading-orchestrator -f

# Enable auto-start on boot
sudo systemctl enable stock-trading-orchestrator
```

## Backup and Restore

### Database Backup

```bash
# Create backup
./deployment/scripts/backup-database.sh

# Create named backup
./deployment/scripts/backup-database.sh my_backup_name

# Backups are stored in: backups/
```

### Database Restore

```bash
# Restore from latest backup
./deployment/scripts/restore-database.sh

# Restore from specific backup
./deployment/scripts/restore-database.sh backup_20240115_120000.sql.gz
```

### Redis Backup

```bash
# Create Redis backup
./deployment/scripts/backup-redis.sh

# Backups are stored in: backups/redis/
```

### Automated Backups

Add to crontab for automated backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/stock-trading/deployment/scripts/backup-database.sh

# Add Redis backup every 6 hours
0 */6 * * * /opt/stock-trading/deployment/scripts/backup-redis.sh
```

## Zero-Downtime Updates

### Rolling Update (Systemd)

```bash
# Update all services one by one
sudo ./deployment/scripts/rolling-update.sh

# Update specific service
sudo ./deployment/scripts/rolling-update.sh trading-engine
```

### Rolling Update (Docker)

```bash
# Update all Docker services
./deployment/scripts/docker-rolling-update.sh

# Update specific service
./deployment/scripts/docker-rolling-update.sh trading-engine
```

### Graceful Restart

```bash
# Gracefully restart a service
sudo ./deployment/scripts/graceful-restart.sh trading-engine
```

### Quick Deploy

```bash
# Pull latest code and deploy
./deployment/scripts/quick-deploy.sh
```

## Monitoring and Logs

### Log Locations

#### Docker Logs

```bash
# Application logs
logs/*.log

# Container logs
docker logs <container_name>

# Follow logs
docker logs -f <container_name>
```

#### Systemd Logs

```bash
# Application logs
/opt/stock-trading/logs/*.log

# System logs
sudo journalctl -u stock-trading-orchestrator

# Follow logs
sudo journalctl -u stock-trading-orchestrator -f

# Logs since last boot
sudo journalctl -u stock-trading-orchestrator -b

# Logs from last hour
sudo journalctl -u stock-trading-orchestrator --since "1 hour ago"
```

### Health Checks

```bash
# Check service health
curl http://localhost:8001/health  # Data Collector
curl http://localhost:8002/health  # Indicator Calculator
curl http://localhost:8003/health  # Stock Screener
curl http://localhost:8004/health  # Trading Engine
curl http://localhost:8005/health  # Risk Manager

# Check database
psql -h localhost -U stock_user -d stock_trading -c "SELECT 1"

# Check Redis
redis-cli ping
```

### Monitoring Metrics

Services expose Prometheus metrics at `/metrics` endpoint:

```bash
curl http://localhost:8001/metrics
```

## Troubleshooting

### Common Issues

#### Services Won't Start

```bash
# Check logs
sudo journalctl -u stock-trading-orchestrator -n 100

# Check service status
sudo systemctl status stock-trading-orchestrator

# Check dependencies
sudo systemctl list-dependencies stock-trading-orchestrator
```

#### Database Connection Issues

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connectivity
psql -h localhost -U stock_user -d stock_trading -c "SELECT 1"

# Check connection pool
psql -h localhost -U stock_user -d stock_trading -c "SELECT count(*) FROM pg_stat_activity"
```

#### High Memory Usage

```bash
# Check Docker stats
docker stats

# Check system memory
free -h

# Check process memory
ps aux --sort=-%mem | head -10
```

#### Disk Space Issues

```bash
# Check disk usage
df -h

# Find large files
du -sh /opt/stock-trading/* | sort -h

# Clean Docker
docker system prune -a --volumes

# Clean old logs
find /opt/stock-trading/logs -name "*.log.*" -mtime +30 -delete
```

### Performance Tuning

#### PostgreSQL

Edit `/etc/postgresql/15/main/postgresql.conf`:

```ini
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 16MB
max_connections = 200
```

#### Redis

Edit `/etc/redis/stock-trading.conf`:

```ini
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## Security Considerations

1. **Change Default Passwords**: Update all default passwords in production
2. **Use HTTPS**: Configure reverse proxy (nginx) with SSL/TLS
3. **Firewall**: Restrict access to service ports
4. **API Keys**: Store API keys in environment files with restricted permissions
5. **Database**: Use strong passwords and restrict network access
6. **Updates**: Keep system and dependencies up to date

## Support

For issues and questions:

- GitHub Issues: https://github.com/sangrokhan/ko-stock-filter/issues
- Documentation: See project README.md

## License

See LICENSE file in project root.
