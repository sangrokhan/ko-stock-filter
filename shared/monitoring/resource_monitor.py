"""
System Resource Monitoring Module

Monitors CPU, memory, disk, and network usage for system health tracking.
Provides alerts when resources exceed thresholds.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import psutil
from pydantic import BaseModel


class SystemResources(BaseModel):
    """System resource usage snapshot"""
    timestamp: datetime
    cpu_percent: float
    cpu_count: int
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_free_gb: float
    disk_total_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    load_average: List[float] = []


class ProcessInfo(BaseModel):
    """Individual process information"""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    status: str
    create_time: float


class ResourceThresholds(BaseModel):
    """Thresholds for resource alerting"""
    cpu_warning: float = 70.0
    cpu_critical: float = 90.0
    memory_warning: float = 75.0
    memory_critical: float = 90.0
    disk_warning: float = 80.0
    disk_critical: float = 95.0


@dataclass
class ResourceMonitor:
    """
    System resource monitor with alerting

    Usage:
        monitor = ResourceMonitor(
            service_name="trading_engine",
            thresholds=ResourceThresholds(cpu_warning=70.0)
        )

        # Get current resources
        resources = monitor.get_resources()

        # Check thresholds
        alerts = monitor.check_thresholds()

        # Start monitoring loop
        await monitor.start_monitoring(interval=60)
    """

    service_name: str
    thresholds: ResourceThresholds = field(default_factory=ResourceThresholds)
    history: List[SystemResources] = field(default_factory=list)
    max_history: int = 1000
    _monitoring: bool = False
    _monitoring_task: Optional[asyncio.Task] = None

    def get_resources(self) -> SystemResources:
        """Get current system resource usage"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # Memory usage
        memory = psutil.virtual_memory()
        memory_used_mb = memory.used / (1024 * 1024)
        memory_available_mb = memory.available / (1024 * 1024)
        memory_total_mb = memory.total / (1024 * 1024)

        # Disk usage
        disk = psutil.disk_usage('/')
        disk_used_gb = disk.used / (1024 * 1024 * 1024)
        disk_free_gb = disk.free / (1024 * 1024 * 1024)
        disk_total_gb = disk.total / (1024 * 1024 * 1024)

        # Network usage
        network = psutil.net_io_counters()

        # Process count
        process_count = len(psutil.pids())

        # Load average (Unix only)
        load_avg = []
        try:
            load_avg = list(psutil.getloadavg())
        except AttributeError:
            # Windows doesn't have getloadavg
            pass

        resources = SystemResources(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            cpu_count=cpu_count,
            memory_percent=memory.percent,
            memory_used_mb=memory_used_mb,
            memory_available_mb=memory_available_mb,
            memory_total_mb=memory_total_mb,
            disk_percent=disk.percent,
            disk_used_gb=disk_used_gb,
            disk_free_gb=disk_free_gb,
            disk_total_gb=disk_total_gb,
            network_bytes_sent=network.bytes_sent,
            network_bytes_recv=network.bytes_recv,
            process_count=process_count,
            load_average=load_avg
        )

        # Add to history
        self.history.append(resources)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        return resources

    def get_process_info(self, pid: Optional[int] = None) -> ProcessInfo:
        """
        Get information about a specific process

        Args:
            pid: Process ID (defaults to current process)

        Returns:
            ProcessInfo object
        """
        if pid is None:
            process = psutil.Process()
        else:
            process = psutil.Process(pid)

        with process.oneshot():
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            memory_percent = process.memory_percent()

            return ProcessInfo(
                pid=process.pid,
                name=process.name(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_mb=memory_mb,
                status=process.status(),
                create_time=process.create_time()
            )

    def get_top_processes(self, n: int = 10, sort_by: str = "cpu") -> List[ProcessInfo]:
        """
        Get top N processes by CPU or memory usage

        Args:
            n: Number of processes to return
            sort_by: Sort by "cpu" or "memory"

        Returns:
            List of ProcessInfo objects
        """
        processes = []

        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info', 'status', 'create_time']):
            try:
                pinfo = proc.info
                memory_mb = pinfo['memory_info'].rss / (1024 * 1024) if pinfo['memory_info'] else 0

                processes.append(ProcessInfo(
                    pid=pinfo['pid'],
                    name=pinfo['name'],
                    cpu_percent=pinfo['cpu_percent'] or 0,
                    memory_percent=pinfo['memory_percent'] or 0,
                    memory_mb=memory_mb,
                    status=pinfo['status'],
                    create_time=pinfo['create_time']
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # Sort processes
        if sort_by == "cpu":
            processes.sort(key=lambda x: x.cpu_percent, reverse=True)
        else:
            processes.sort(key=lambda x: x.memory_percent, reverse=True)

        return processes[:n]

    def check_thresholds(self, resources: Optional[SystemResources] = None) -> List[Dict[str, Any]]:
        """
        Check if resources exceed thresholds

        Args:
            resources: SystemResources to check (defaults to latest)

        Returns:
            List of alerts if thresholds exceeded
        """
        if resources is None:
            resources = self.get_resources()

        alerts = []

        # CPU checks
        if resources.cpu_percent >= self.thresholds.cpu_critical:
            alerts.append({
                "level": "critical",
                "resource": "cpu",
                "message": f"CPU usage critical: {resources.cpu_percent:.1f}%",
                "value": resources.cpu_percent,
                "threshold": self.thresholds.cpu_critical
            })
        elif resources.cpu_percent >= self.thresholds.cpu_warning:
            alerts.append({
                "level": "warning",
                "resource": "cpu",
                "message": f"CPU usage high: {resources.cpu_percent:.1f}%",
                "value": resources.cpu_percent,
                "threshold": self.thresholds.cpu_warning
            })

        # Memory checks
        if resources.memory_percent >= self.thresholds.memory_critical:
            alerts.append({
                "level": "critical",
                "resource": "memory",
                "message": f"Memory usage critical: {resources.memory_percent:.1f}%",
                "value": resources.memory_percent,
                "threshold": self.thresholds.memory_critical
            })
        elif resources.memory_percent >= self.thresholds.memory_warning:
            alerts.append({
                "level": "warning",
                "resource": "memory",
                "message": f"Memory usage high: {resources.memory_percent:.1f}%",
                "value": resources.memory_percent,
                "threshold": self.thresholds.memory_warning
            })

        # Disk checks
        if resources.disk_percent >= self.thresholds.disk_critical:
            alerts.append({
                "level": "critical",
                "resource": "disk",
                "message": f"Disk usage critical: {resources.disk_percent:.1f}%",
                "value": resources.disk_percent,
                "threshold": self.thresholds.disk_critical
            })
        elif resources.disk_percent >= self.thresholds.disk_warning:
            alerts.append({
                "level": "warning",
                "resource": "disk",
                "message": f"Disk usage high: {resources.disk_percent:.1f}%",
                "value": resources.disk_percent,
                "threshold": self.thresholds.disk_warning
            })

        return alerts

    def get_statistics(self, window_minutes: int = 60) -> Dict[str, Any]:
        """
        Get resource statistics over a time window

        Args:
            window_minutes: Time window in minutes

        Returns:
            Dictionary with min, max, avg statistics
        """
        if not self.history:
            return {}

        # Filter history to window
        cutoff_time = datetime.now().timestamp() - (window_minutes * 60)
        recent = [r for r in self.history if r.timestamp.timestamp() >= cutoff_time]

        if not recent:
            return {}

        cpu_values = [r.cpu_percent for r in recent]
        memory_values = [r.memory_percent for r in recent]
        disk_values = [r.disk_percent for r in recent]

        return {
            "window_minutes": window_minutes,
            "samples": len(recent),
            "cpu": {
                "min": min(cpu_values),
                "max": max(cpu_values),
                "avg": sum(cpu_values) / len(cpu_values)
            },
            "memory": {
                "min": min(memory_values),
                "max": max(memory_values),
                "avg": sum(memory_values) / len(memory_values)
            },
            "disk": {
                "min": min(disk_values),
                "max": max(disk_values),
                "avg": sum(disk_values) / len(disk_values)
            }
        }

    async def start_monitoring(
        self,
        interval: int = 60,
        callback: Optional[callable] = None
    ):
        """
        Start continuous resource monitoring

        Args:
            interval: Monitoring interval in seconds
            callback: Optional callback function for alerts
        """
        self._monitoring = True

        async def monitor_loop():
            while self._monitoring:
                try:
                    # Collect resources
                    resources = self.get_resources()

                    # Check thresholds
                    alerts = self.check_thresholds(resources)

                    # Call callback if provided
                    if callback and alerts:
                        await callback(alerts, resources)

                    # Wait for next interval
                    await asyncio.sleep(interval)

                except Exception as e:
                    print(f"Error in monitoring loop: {e}")
                    await asyncio.sleep(interval)

        self._monitoring_task = asyncio.create_task(monitor_loop())

    async def stop_monitoring(self):
        """Stop continuous monitoring"""
        self._monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

    def get_disk_usage_by_path(self, paths: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Get disk usage for specific paths

        Args:
            paths: List of paths to check

        Returns:
            Dictionary mapping path to usage info
        """
        result = {}

        for path in paths:
            try:
                usage = psutil.disk_usage(path)
                result[path] = {
                    "total_gb": usage.total / (1024 ** 3),
                    "used_gb": usage.used / (1024 ** 3),
                    "free_gb": usage.free / (1024 ** 3),
                    "percent": usage.percent
                }
            except Exception as e:
                result[path] = {"error": str(e)}

        return result

    def get_network_connections(self, kind: str = "inet") -> List[Dict[str, Any]]:
        """
        Get network connections

        Args:
            kind: Connection kind (inet, inet4, inet6, tcp, udp, unix, all)

        Returns:
            List of connection info
        """
        connections = []

        for conn in psutil.net_connections(kind=kind):
            connections.append({
                "fd": conn.fd,
                "family": str(conn.family),
                "type": str(conn.type),
                "local_address": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                "remote_address": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                "status": conn.status,
                "pid": conn.pid
            })

        return connections

    def export_metrics(self) -> Dict[str, Any]:
        """
        Export current metrics in Prometheus-compatible format

        Returns:
            Dictionary of metrics
        """
        resources = self.get_resources()
        process = self.get_process_info()

        return {
            "system_cpu_percent": resources.cpu_percent,
            "system_memory_percent": resources.memory_percent,
            "system_memory_used_bytes": resources.memory_used_mb * 1024 * 1024,
            "system_memory_available_bytes": resources.memory_available_mb * 1024 * 1024,
            "system_disk_percent": resources.disk_percent,
            "system_disk_used_bytes": resources.disk_used_gb * 1024 ** 3,
            "system_disk_free_bytes": resources.disk_free_gb * 1024 ** 3,
            "system_network_bytes_sent": resources.network_bytes_sent,
            "system_network_bytes_received": resources.network_bytes_recv,
            "system_process_count": resources.process_count,
            "process_cpu_percent": process.cpu_percent,
            "process_memory_percent": process.memory_percent,
            "process_memory_bytes": process.memory_mb * 1024 * 1024,
        }
