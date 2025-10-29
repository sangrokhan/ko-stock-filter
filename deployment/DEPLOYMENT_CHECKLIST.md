# Deployment Checklist

Use this checklist to ensure a smooth deployment of the Stock Trading System.

## Pre-Deployment

### Environment Setup

- [ ] Choose deployment method (Docker or Systemd)
- [ ] Verify system requirements are met
- [ ] Ensure sufficient disk space (20GB minimum)
- [ ] Verify network connectivity
- [ ] Obtain required API keys:
  - [ ] KRX API key
  - [ ] Korea Investment & Securities API key and secret

### Security

- [ ] Change all default passwords
- [ ] Generate strong database password
- [ ] Set up firewall rules
- [ ] Configure SSL/TLS certificates (if using HTTPS)
- [ ] Review and update security settings in `.env` file
- [ ] Restrict file permissions on configuration files (`chmod 600`)

### Configuration

- [ ] Copy `.env.production.template` to `.env`
- [ ] Update database credentials
- [ ] Add API keys
- [ ] Configure trading parameters
- [ ] Set timezone to Asia/Seoul
- [ ] Review log levels
- [ ] Configure backup retention
- [ ] Set email/notification settings (optional)

## Docker Deployment

### Installation

- [ ] Install Docker (20.10+)
- [ ] Install Docker Compose (2.0+)
- [ ] Verify Docker is running: `docker --version`
- [ ] Create required directories:
  ```bash
  mkdir -p logs backups data
  ```

### Configuration

- [ ] Review `docker/docker-compose.full.yml`
- [ ] Update environment variables in `.env`
- [ ] Configure volume mounts if needed
- [ ] Adjust resource limits (CPU/memory) if needed

### Deployment

- [ ] Build images: `make docker-build`
- [ ] Start services: `make docker-up`
- [ ] Verify all containers are running: `docker ps`
- [ ] Check logs: `make docker-logs`
- [ ] Run health check: `make health`

### Post-Deployment

- [ ] Verify database migrations completed
- [ ] Test service endpoints
- [ ] Configure log rotation
- [ ] Set up backup cron jobs
- [ ] Test backup and restore procedures
- [ ] Monitor resource usage

## Systemd Deployment

### Installation

- [ ] Install system dependencies:
  ```bash
  sudo apt update
  sudo apt install -y postgresql-15 redis-server python3.11
  ```
- [ ] Run installation script: `sudo make deploy-systemd`
- [ ] Verify installation completed successfully

### Configuration

- [ ] Configure database credentials
- [ ] Update environment files in `/etc/stock-trading/`
- [ ] Review and adjust service files if needed
- [ ] Configure PostgreSQL for production (connection pooling, memory)
- [ ] Configure Redis persistence settings

### Deployment

- [ ] Enable services:
  ```bash
  sudo systemctl enable stock-trading-orchestrator
  ```
- [ ] Start services:
  ```bash
  sudo systemctl start stock-trading-orchestrator
  ```
- [ ] Check service status:
  ```bash
  sudo systemctl status stock-trading-orchestrator
  ```
- [ ] View logs:
  ```bash
  sudo journalctl -u stock-trading-orchestrator -f
  ```

### Post-Deployment

- [ ] Set up log rotation: `make setup-logrotate`
- [ ] Configure cron jobs: `make setup-cron`
- [ ] Test graceful restart
- [ ] Test rolling update procedure
- [ ] Monitor system resources

## Database Setup

- [ ] Create database and user
- [ ] Run migrations: `make db-migrate`
- [ ] Verify tables created successfully
- [ ] Create initial database backup
- [ ] Test restore procedure
- [ ] Configure automated backups
- [ ] Set up connection pooling
- [ ] Configure query timeout settings

## Monitoring Setup

### Health Checks

- [ ] Run initial health check: `make health`
- [ ] Test all service endpoints:
  - [ ] `http://localhost:8001/health` - Data Collector
  - [ ] `http://localhost:8002/health` - Indicator Calculator
  - [ ] `http://localhost:8003/health` - Stock Screener
  - [ ] `http://localhost:8004/health` - Trading Engine
  - [ ] `http://localhost:8005/health` - Risk Manager
- [ ] Set up automated health checks (cron)

### Logging

- [ ] Verify log files are being created
- [ ] Test log rotation
- [ ] Configure log aggregation (optional)
- [ ] Set up log monitoring/alerting (optional)

### Metrics

- [ ] Verify Prometheus metrics endpoint: `http://localhost:8001/metrics`
- [ ] Set up metrics collection (optional)
- [ ] Configure alerting rules (optional)

## Backup & Recovery

- [ ] Test database backup: `make backup`
- [ ] Verify backup file created
- [ ] Test database restore: `make restore`
- [ ] Set up automated daily backups
- [ ] Configure backup retention policy
- [ ] Test Redis backup
- [ ] Document recovery procedures
- [ ] Store backups in remote location (recommended)

## Security Hardening

- [ ] Change default passwords
- [ ] Configure firewall:
  ```bash
  sudo ufw allow 22/tcp    # SSH
  sudo ufw allow 80/tcp    # HTTP (if needed)
  sudo ufw allow 443/tcp   # HTTPS (if needed)
  sudo ufw enable
  ```
- [ ] Restrict database access to localhost only
- [ ] Restrict Redis access to localhost only
- [ ] Set up fail2ban (optional)
- [ ] Configure SELinux/AppArmor (optional)
- [ ] Enable audit logging
- [ ] Restrict file permissions
- [ ] Disable debug mode in production
- [ ] Review CORS settings

## Performance Tuning

### PostgreSQL

- [ ] Adjust `shared_buffers` based on available RAM
- [ ] Configure `effective_cache_size`
- [ ] Set `work_mem` appropriately
- [ ] Tune `max_connections`
- [ ] Enable query logging for slow queries
- [ ] Configure connection pooling

### Redis

- [ ] Set `maxmemory` limit
- [ ] Configure eviction policy
- [ ] Enable persistence (AOF or RDB)
- [ ] Adjust save intervals

### Application

- [ ] Tune worker threads
- [ ] Configure database pool size
- [ ] Set appropriate request timeouts
- [ ] Enable caching where appropriate

## Testing

- [ ] Run health checks: `make health`
- [ ] Test all API endpoints
- [ ] Verify data collection is working
- [ ] Test trading engine (paper trading mode)
- [ ] Verify risk management is active
- [ ] Test orchestrator scheduling
- [ ] Simulate service failure and recovery
- [ ] Test rolling update procedure
- [ ] Load testing (optional)

## Documentation

- [ ] Document deployment configuration
- [ ] Record all custom settings
- [ ] Document API keys and credentials (securely)
- [ ] Create runbook for common operations
- [ ] Document backup/restore procedures
- [ ] Document troubleshooting steps
- [ ] Update team on deployment

## Go-Live

- [ ] Final health check
- [ ] Verify all services running
- [ ] Monitor logs for errors
- [ ] Monitor resource usage
- [ ] Set up alerts/notifications
- [ ] Enable paper trading mode initially
- [ ] Monitor for 24 hours before enabling real trading
- [ ] Document any issues encountered
- [ ] Create post-deployment report

## Post-Deployment

### First 24 Hours

- [ ] Monitor all services continuously
- [ ] Check logs every 2 hours
- [ ] Verify data collection is working
- [ ] Monitor database performance
- [ ] Monitor memory usage
- [ ] Monitor disk usage
- [ ] Test backup creation

### First Week

- [ ] Review all logs
- [ ] Check backup success
- [ ] Verify automated tasks (cron jobs)
- [ ] Monitor trading performance (paper trading)
- [ ] Review and optimize performance
- [ ] Address any warnings or errors
- [ ] Update documentation with lessons learned

### Ongoing Maintenance

- [ ] Weekly backup verification
- [ ] Monthly security updates
- [ ] Quarterly performance review
- [ ] Regular dependency updates
- [ ] Log review and analysis
- [ ] Capacity planning

## Emergency Procedures

### Rollback Plan

- [ ] Document current deployment state
- [ ] Keep previous version available
- [ ] Test rollback procedure
- [ ] Document rollback steps
- [ ] Maintain pre-deployment backup

### Contact Information

- [ ] Database administrator contact
- [ ] System administrator contact
- [ ] API provider support
- [ ] Emergency contact list

## Sign-off

- [ ] Technical lead approval
- [ ] Security review completed
- [ ] Stakeholder notification sent
- [ ] Documentation completed
- [ ] Deployment successful

---

**Deployment Date:** _________________

**Deployed By:** _________________

**Reviewed By:** _________________

**Production Ready:** [ ] Yes [ ] No

**Notes:**

_______________________________________
_______________________________________
_______________________________________
