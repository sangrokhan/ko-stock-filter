# Quick Start Guide - Stock Trading System

Get the Stock Trading System up and running in minutes!

## Choose Your Deployment Method

### Option 1: Docker (Recommended for Quick Start)

Perfect for testing and development. Get everything running with just a few commands.

```bash
# 1. Copy and edit environment file
cp .env.example .env
nano .env  # Add your API keys

# 2. Start all services
make docker-up

# 3. Check status
make health

# That's it! Services are now running.
```

**Access Points:**
- Data Collector: http://localhost:8001
- Indicator Calculator: http://localhost:8002
- Stock Screener: http://localhost:8003
- Trading Engine: http://localhost:8004
- Risk Manager: http://localhost:8005

### Option 2: Linux Systemd (Production)

For production deployments on Linux servers.

```bash
# 1. Run installation script
sudo make deploy-systemd

# 2. Configure environment
sudo nano /etc/stock-trading/orchestrator.env
# Add your API keys and configuration

# 3. Start the system
sudo systemctl start stock-trading-orchestrator

# 4. Check status
sudo systemctl status stock-trading-orchestrator
```

## Essential Configuration

### Required Environment Variables

Edit your `.env` file (Docker) or `/etc/stock-trading/*.env` (Systemd):

```env
# API Keys (REQUIRED)
KRX_API_KEY=your_api_key_here
KOREAINVESTMENT_API_KEY=your_api_key
KOREAINVESTMENT_API_SECRET=your_api_secret

# Database (change password!)
POSTGRES_PASSWORD=change_this_password

# Trading Mode
PAPER_TRADING=true  # Start with paper trading!
```

### Important First Steps

1. **Change Default Password**: Update `POSTGRES_PASSWORD` in `.env`
2. **Add API Keys**: Get keys from KRX and Korea Investment
3. **Start in Paper Trading**: Keep `PAPER_TRADING=true` initially
4. **Monitor Logs**: Watch for any errors

## Common Commands

### Docker Deployment

```bash
# Start services
make docker-up

# Stop services
make docker-down

# View logs
make docker-logs

# Health check
make health

# Backup database
make backup

# Restart specific service
docker restart trading-engine
```

### Systemd Deployment

```bash
# Start service
sudo systemctl start stock-trading-orchestrator

# Stop service
sudo systemctl stop stock-trading-orchestrator

# View logs
sudo journalctl -u stock-trading-orchestrator -f

# Health check
make health

# Graceful restart
sudo ./deployment/scripts/graceful-restart.sh orchestrator
```

## Verify Everything is Working

### 1. Health Check

```bash
make health
```

All checks should pass (green).

### 2. Check Individual Services

```bash
# Test each service endpoint
curl http://localhost:8001/health  # Data Collector
curl http://localhost:8002/health  # Indicator Calculator
curl http://localhost:8003/health  # Stock Screener
curl http://localhost:8004/health  # Trading Engine
curl http://localhost:8005/health  # Risk Manager
```

Each should return: `{"status": "healthy"}` or similar.

### 3. Check Database

```bash
# Docker
docker exec -it stock-trading-db psql -U stock_user -d stock_trading -c "\dt"

# Systemd
psql -U stock_user -d stock_trading -c "\dt"
```

Should list database tables.

### 4. Check Logs

```bash
# Docker
docker logs orchestrator

# Systemd
sudo journalctl -u stock-trading-orchestrator -n 50
```

Look for startup messages and no errors.

## Next Steps

### Enable Paper Trading

The system starts in paper trading mode by default. Monitor it for 24 hours:

```bash
# Watch logs
make docker-logs  # or sudo journalctl -u stock-trading-orchestrator -f

# Check trading activity
curl http://localhost:8004/api/v1/trades
```

### Set Up Backups

```bash
# Create backup
make backup

# Test restore
make restore

# Set up automated backups
sudo make setup-cron
```

### Configure Monitoring

```bash
# Set up health check cron
sudo make setup-cron

# Check service status regularly
watch -n 30 'make health'
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
make docker-logs  # Docker
sudo journalctl -xe  # Systemd

# Check resource usage
docker stats  # Docker
htop  # Systemd

# Verify configuration
cat .env  # Docker
cat /etc/stock-trading/*.env  # Systemd
```

### Database Connection Issues

```bash
# Check database is running
docker ps | grep postgres  # Docker
sudo systemctl status postgresql  # Systemd

# Test connection
psql -h localhost -U stock_user -d stock_trading -c "SELECT 1"
```

### API Connection Issues

```bash
# Verify API keys are set
env | grep KRX
env | grep KOREAINVESTMENT

# Check network connectivity
curl -I https://krx.com
```

### High Resource Usage

```bash
# Check resource usage
docker stats  # Docker
htop  # Systemd

# Check disk space
df -h

# Clean up logs
find logs/ -name "*.log" -mtime +7 -delete
```

## Stopping the System

### Docker

```bash
# Stop all services
make docker-down

# Stop and remove all data (WARNING!)
docker compose -f docker/docker-compose.full.yml down -v
```

### Systemd

```bash
# Stop orchestrator (stops all managed services)
sudo systemctl stop stock-trading-orchestrator

# Stop individual service
sudo systemctl stop stock-trading-trading-engine
```

## Getting Help

### Check Documentation

- Full deployment guide: `deployment/README.md`
- Deployment checklist: `deployment/DEPLOYMENT_CHECKLIST.md`
- Main README: `README.md`

### Common Issues

1. **Port already in use**: Change port in `.env` or `docker-compose.full.yml`
2. **Permission denied**: Run with `sudo` or check file permissions
3. **API errors**: Verify API keys are correct and valid
4. **Database errors**: Check database is running and credentials are correct

### Logs Location

- Docker: `logs/` directory + `docker logs <container>`
- Systemd: `/opt/stock-trading/logs/` + `journalctl`

### Support

- GitHub Issues: https://github.com/sangrokhan/ko-stock-filter/issues
- Documentation: See `docs/` directory

## Production Checklist

Before going to production:

- [ ] Change all default passwords
- [ ] Add all API keys
- [ ] Test in paper trading mode for 1 week
- [ ] Set up automated backups
- [ ] Configure monitoring and alerts
- [ ] Set up firewall rules
- [ ] Enable HTTPS (if exposing to internet)
- [ ] Review security settings
- [ ] Create disaster recovery plan
- [ ] Document custom configuration

See `deployment/DEPLOYMENT_CHECKLIST.md` for complete checklist.

## Quick Reference

| Task | Docker | Systemd |
|------|--------|---------|
| Start | `make docker-up` | `sudo systemctl start stock-trading-orchestrator` |
| Stop | `make docker-down` | `sudo systemctl stop stock-trading-orchestrator` |
| Logs | `make docker-logs` | `sudo journalctl -u stock-trading-orchestrator -f` |
| Health | `make health` | `make health` |
| Backup | `make backup` | `make backup` |
| Restart | `docker restart <service>` | `sudo systemctl restart stock-trading-<service>` |

---

**Need more help?** Check the full documentation in `deployment/README.md`
