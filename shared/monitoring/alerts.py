"""
Alerting Module

Sends alerts on errors, unusual activity, and risk threshold breaches.
Supports multiple channels: email, Slack, webhooks.
"""

import asyncio
import smtplib
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

import aiohttp
from pydantic import BaseModel


class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """Alert delivery channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    LOG = "log"


class Alert(BaseModel):
    """Alert message"""
    level: AlertLevel
    title: str
    message: str
    source: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}
    tags: List[str] = []


class AlertRule(BaseModel):
    """Alert rule configuration"""
    name: str
    condition: str  # Description of condition
    level: AlertLevel
    channels: List[AlertChannel]
    cooldown_minutes: int = 15  # Minimum time between same alerts
    enabled: bool = True


@dataclass
class AlertManager:
    """
    Alert manager for sending notifications

    Usage:
        alert_manager = AlertManager(
            email_config={
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "alerts@example.com",
                "password": "password",
                "from_email": "alerts@example.com",
                "to_emails": ["admin@example.com"]
            },
            slack_webhook_url="https://hooks.slack.com/services/..."
        )

        # Send alert
        await alert_manager.send_alert(
            Alert(
                level=AlertLevel.CRITICAL,
                title="Trading Halt",
                message="Portfolio drawdown exceeded 28%",
                source="risk_manager",
                timestamp=datetime.now(),
                metadata={"drawdown": 30.5}
            )
        )
    """

    # Email configuration
    email_config: Optional[Dict[str, Any]] = None

    # Slack configuration
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None

    # Webhook configuration
    webhook_urls: List[str] = field(default_factory=list)

    # Alert history for cooldown
    alert_history: Dict[str, datetime] = field(default_factory=dict)

    # Alert rules
    rules: List[AlertRule] = field(default_factory=list)

    # Alert statistics
    alerts_sent: Dict[AlertLevel, int] = field(default_factory=lambda: {
        AlertLevel.INFO: 0,
        AlertLevel.WARNING: 0,
        AlertLevel.ERROR: 0,
        AlertLevel.CRITICAL: 0
    })

    def add_rule(self, rule: AlertRule):
        """Add an alert rule"""
        self.rules.append(rule)

    def _should_send_alert(self, alert: Alert, cooldown_minutes: int = 15) -> bool:
        """
        Check if alert should be sent based on cooldown

        Args:
            alert: Alert to check
            cooldown_minutes: Cooldown period in minutes

        Returns:
            True if alert should be sent
        """
        # Create unique key for alert
        alert_key = f"{alert.source}:{alert.title}:{alert.level}"

        # Check if we've sent this alert recently
        if alert_key in self.alert_history:
            last_sent = self.alert_history[alert_key]
            cooldown_period = timedelta(minutes=cooldown_minutes)

            if datetime.now() - last_sent < cooldown_period:
                return False

        # Update history
        self.alert_history[alert_key] = datetime.now()
        return True

    async def send_alert(
        self,
        alert: Alert,
        channels: Optional[List[AlertChannel]] = None,
        cooldown_minutes: int = 15
    ):
        """
        Send alert to specified channels

        Args:
            alert: Alert to send
            channels: Channels to send to (defaults to all configured)
            cooldown_minutes: Cooldown period in minutes
        """
        # Check cooldown
        if not self._should_send_alert(alert, cooldown_minutes):
            return

        # Default to all configured channels
        if channels is None:
            channels = []
            if self.email_config:
                channels.append(AlertChannel.EMAIL)
            if self.slack_webhook_url:
                channels.append(AlertChannel.SLACK)
            if self.webhook_urls:
                channels.append(AlertChannel.WEBHOOK)

        # Send to each channel
        tasks = []
        if AlertChannel.EMAIL in channels and self.email_config:
            tasks.append(self._send_email(alert))

        if AlertChannel.SLACK in channels and self.slack_webhook_url:
            tasks.append(self._send_slack(alert))

        if AlertChannel.WEBHOOK in channels and self.webhook_urls:
            for url in self.webhook_urls:
                tasks.append(self._send_webhook(alert, url))

        # Execute all sends concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Update statistics
        self.alerts_sent[alert.level] += 1

    async def _send_email(self, alert: Alert):
        """Send alert via email"""
        try:
            config = self.email_config

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert.level.value.upper()}] {alert.title}"
            msg['From'] = config['from_email']
            msg['To'] = ', '.join(config['to_emails'])

            # Create HTML body
            html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .alert {{ padding: 20px; border-radius: 5px; }}
                    .info {{ background-color: #d1ecf1; border: 1px solid #bee5eb; }}
                    .warning {{ background-color: #fff3cd; border: 1px solid #ffeeba; }}
                    .error {{ background-color: #f8d7da; border: 1px solid #f5c6cb; }}
                    .critical {{ background-color: #f8d7da; border: 2px solid #c00; color: #c00; }}
                    .metadata {{ margin-top: 15px; padding: 10px; background-color: #f8f9fa; }}
                </style>
            </head>
            <body>
                <div class="alert {alert.level.value}">
                    <h2>{alert.title}</h2>
                    <p><strong>Level:</strong> {alert.level.value.upper()}</p>
                    <p><strong>Source:</strong> {alert.source}</p>
                    <p><strong>Time:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Message:</strong></p>
                    <p>{alert.message}</p>

                    {f'''
                    <div class="metadata">
                        <h3>Additional Information</h3>
                        <pre>{json.dumps(alert.metadata, indent=2)}</pre>
                    </div>
                    ''' if alert.metadata else ''}

                    {f'''
                    <p><strong>Tags:</strong> {', '.join(alert.tags)}</p>
                    ''' if alert.tags else ''}
                </div>
            </body>
            </html>
            """

            msg.attach(MIMEText(html, 'html'))

            # Send email
            with smtplib.SMTP(config['smtp_host'], config['smtp_port']) as server:
                server.starttls()
                server.login(config['username'], config['password'])
                server.send_message(msg)

        except Exception as e:
            print(f"Error sending email alert: {e}")

    async def _send_slack(self, alert: Alert):
        """Send alert to Slack"""
        try:
            # Color based on level
            color_map = {
                AlertLevel.INFO: "#36a64f",
                AlertLevel.WARNING: "#ff9900",
                AlertLevel.ERROR: "#ff0000",
                AlertLevel.CRITICAL: "#990000"
            }

            # Create Slack message
            payload = {
                "channel": self.slack_channel,
                "username": "Alert Bot",
                "icon_emoji": ":rotating_light:",
                "attachments": [
                    {
                        "color": color_map[alert.level],
                        "title": alert.title,
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Level",
                                "value": alert.level.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Source",
                                "value": alert.source,
                                "short": True
                            },
                            {
                                "title": "Time",
                                "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                "short": False
                            }
                        ],
                        "footer": "Stock Trading System",
                        "ts": int(alert.timestamp.timestamp())
                    }
                ]
            }

            # Add metadata fields
            if alert.metadata:
                for key, value in alert.metadata.items():
                    payload["attachments"][0]["fields"].append({
                        "title": key,
                        "value": str(value),
                        "short": True
                    })

            # Add tags
            if alert.tags:
                payload["attachments"][0]["fields"].append({
                    "title": "Tags",
                    "value": ", ".join(alert.tags),
                    "short": False
                })

            # Send to Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.slack_webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status != 200:
                        print(f"Error sending Slack alert: {response.status}")

        except Exception as e:
            print(f"Error sending Slack alert: {e}")

    async def _send_webhook(self, alert: Alert, webhook_url: str):
        """Send alert to webhook"""
        try:
            # Create webhook payload
            payload = {
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "source": alert.source,
                "timestamp": alert.timestamp.isoformat(),
                "metadata": alert.metadata,
                "tags": alert.tags
            }

            # Send to webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status not in [200, 201, 204]:
                        print(f"Error sending webhook alert: {response.status}")

        except Exception as e:
            print(f"Error sending webhook alert: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        return {
            "alerts_sent": dict(self.alerts_sent),
            "total_alerts": sum(self.alerts_sent.values()),
            "active_rules": len([r for r in self.rules if r.enabled]),
            "total_rules": len(self.rules)
        }

    def clear_history(self):
        """Clear alert history (useful for testing)"""
        self.alert_history.clear()


# Predefined alert templates

def create_error_alert(
    source: str,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> Alert:
    """Create alert for an error"""
    return Alert(
        level=AlertLevel.ERROR,
        title=f"Error in {source}",
        message=f"{type(error).__name__}: {str(error)}",
        source=source,
        timestamp=datetime.now(),
        metadata=context or {},
        tags=["error", source]
    )


def create_risk_alert(
    violation_type: str,
    current_value: float,
    threshold: float,
    context: Optional[Dict[str, Any]] = None
) -> Alert:
    """Create alert for risk violation"""
    level = AlertLevel.CRITICAL if current_value > threshold * 1.1 else AlertLevel.WARNING

    return Alert(
        level=level,
        title=f"Risk Threshold Breach: {violation_type}",
        message=f"{violation_type} exceeded threshold. Current: {current_value:.2f}, Threshold: {threshold:.2f}",
        source="risk_manager",
        timestamp=datetime.now(),
        metadata={
            "violation_type": violation_type,
            "current_value": current_value,
            "threshold": threshold,
            **(context or {})
        },
        tags=["risk", violation_type]
    )


def create_trading_halt_alert(
    reason: str,
    drawdown: float,
    context: Optional[Dict[str, Any]] = None
) -> Alert:
    """Create alert for trading halt"""
    return Alert(
        level=AlertLevel.CRITICAL,
        title="TRADING HALT",
        message=f"Trading halted due to {reason}. Current drawdown: {drawdown:.2f}%",
        source="risk_manager",
        timestamp=datetime.now(),
        metadata={
            "reason": reason,
            "drawdown": drawdown,
            **(context or {})
        },
        tags=["trading_halt", "critical"]
    )


def create_performance_alert(
    operation: str,
    duration_ms: float,
    threshold_ms: float,
    context: Optional[Dict[str, Any]] = None
) -> Alert:
    """Create alert for slow performance"""
    return Alert(
        level=AlertLevel.WARNING,
        title=f"Slow Performance: {operation}",
        message=f"Operation '{operation}' took {duration_ms:.0f}ms (threshold: {threshold_ms:.0f}ms)",
        source="performance_monitor",
        timestamp=datetime.now(),
        metadata={
            "operation": operation,
            "duration_ms": duration_ms,
            "threshold_ms": threshold_ms,
            **(context or {})
        },
        tags=["performance", operation]
    )


def create_resource_alert(
    resource_type: str,
    usage_percent: float,
    threshold: float,
    context: Optional[Dict[str, Any]] = None
) -> Alert:
    """Create alert for resource usage"""
    level = AlertLevel.CRITICAL if usage_percent >= 95 else AlertLevel.WARNING

    return Alert(
        level=level,
        title=f"High {resource_type.upper()} Usage",
        message=f"{resource_type.upper()} usage is {usage_percent:.1f}% (threshold: {threshold:.1f}%)",
        source="resource_monitor",
        timestamp=datetime.now(),
        metadata={
            "resource_type": resource_type,
            "usage_percent": usage_percent,
            "threshold": threshold,
            **(context or {})
        },
        tags=["resource", resource_type]
    )
