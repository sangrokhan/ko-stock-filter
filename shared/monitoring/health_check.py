"""
Health Check Module

Provides standardized health check functionality for all services.
Includes checks for service health, database connectivity, Redis, and other dependencies.
"""

import asyncio
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import psutil
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from redis import Redis
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel


class HealthStatus(str, Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DependencyType(str, Enum):
    """Dependency type enumeration"""
    DATABASE = "database"
    CACHE = "cache"
    SERVICE = "service"
    EXTERNAL_API = "external_api"


class DependencyHealth(BaseModel):
    """Health status of a dependency"""
    name: str
    type: DependencyType
    status: HealthStatus
    response_time_ms: float
    message: Optional[str] = None
    last_check: datetime
    metadata: Dict[str, Any] = {}


class ServiceHealth(BaseModel):
    """Overall service health status"""
    service_name: str
    status: HealthStatus
    version: str
    uptime_seconds: float
    timestamp: datetime
    dependencies: List[DependencyHealth] = []
    system_resources: Dict[str, Any] = {}
    error_count: int = 0
    warning_count: int = 0


@dataclass
class HealthCheck:
    """
    Health check manager for services

    Usage:
        health = HealthCheck(
            service_name="trading_engine",
            version="1.0.0"
        )

        # Add dependency checks
        health.add_database_check(db_session)
        health.add_redis_check(redis_client)

        # Get health status
        status = await health.get_health()
    """

    service_name: str
    version: str = "1.0.0"
    start_time: float = field(default_factory=time.time)
    dependencies: Dict[str, callable] = field(default_factory=dict)
    error_count: int = 0
    warning_count: int = 0

    def add_dependency_check(
        self,
        name: str,
        check_func: callable,
        dependency_type: DependencyType = DependencyType.SERVICE
    ):
        """Add a custom dependency check"""
        self.dependencies[name] = {
            "func": check_func,
            "type": dependency_type
        }

    async def check_database(self, session: AsyncSession) -> DependencyHealth:
        """Check database connectivity and responsiveness"""
        start = time.time()
        try:
            # Simple query to check connectivity
            result = await session.execute(text("SELECT 1"))
            result.scalar()

            response_time = (time.time() - start) * 1000

            # Check if response time is acceptable
            if response_time > 1000:  # More than 1 second
                status = HealthStatus.DEGRADED
                message = f"Slow database response: {response_time:.2f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = "Database connection OK"

            return DependencyHealth(
                name="postgresql",
                type=DependencyType.DATABASE,
                status=status,
                response_time_ms=response_time,
                message=message,
                last_check=datetime.now(),
                metadata={
                    "database": str(session.bind.url.database) if hasattr(session.bind, 'url') else "unknown"
                }
            )
        except Exception as e:
            return DependencyHealth(
                name="postgresql",
                type=DependencyType.DATABASE,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start) * 1000,
                message=f"Database error: {str(e)}",
                last_check=datetime.now()
            )

    async def check_redis(self, redis_client: Redis) -> DependencyHealth:
        """Check Redis connectivity and responsiveness"""
        start = time.time()
        try:
            # Ping Redis
            redis_client.ping()

            response_time = (time.time() - start) * 1000

            # Check memory usage
            info = redis_client.info('memory')
            used_memory = info.get('used_memory_human', 'unknown')

            if response_time > 500:  # More than 500ms
                status = HealthStatus.DEGRADED
                message = f"Slow Redis response: {response_time:.2f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = "Redis connection OK"

            return DependencyHealth(
                name="redis",
                type=DependencyType.CACHE,
                status=status,
                response_time_ms=response_time,
                message=message,
                last_check=datetime.now(),
                metadata={
                    "used_memory": used_memory,
                    "connected_clients": info.get('connected_clients', 0)
                }
            )
        except Exception as e:
            return DependencyHealth(
                name="redis",
                type=DependencyType.CACHE,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start) * 1000,
                message=f"Redis error: {str(e)}",
                last_check=datetime.now()
            )

    def get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / (1024 * 1024),
                "memory_available_mb": memory.available / (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used / (1024 * 1024 * 1024),
                "disk_free_gb": disk.free / (1024 * 1024 * 1024)
            }
        except Exception as e:
            return {"error": str(e)}

    async def get_health(
        self,
        db_session: Optional[AsyncSession] = None,
        redis_client: Optional[Redis] = None
    ) -> ServiceHealth:
        """
        Get comprehensive health status of the service

        Args:
            db_session: Database session for DB health check
            redis_client: Redis client for cache health check

        Returns:
            ServiceHealth object with complete health information
        """
        dependencies_health = []

        # Check database if provided
        if db_session:
            db_health = await self.check_database(db_session)
            dependencies_health.append(db_health)

        # Check Redis if provided
        if redis_client:
            redis_health = await self.check_redis(redis_client)
            dependencies_health.append(redis_health)

        # Check custom dependencies
        for name, dep_info in self.dependencies.items():
            try:
                start = time.time()
                check_result = await dep_info["func"]()
                response_time = (time.time() - start) * 1000

                dep_health = DependencyHealth(
                    name=name,
                    type=dep_info["type"],
                    status=HealthStatus.HEALTHY if check_result else HealthStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    message="OK" if check_result else "Check failed",
                    last_check=datetime.now()
                )
                dependencies_health.append(dep_health)
            except Exception as e:
                dep_health = DependencyHealth(
                    name=name,
                    type=dep_info["type"],
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    message=f"Error: {str(e)}",
                    last_check=datetime.now()
                )
                dependencies_health.append(dep_health)

        # Determine overall status
        unhealthy_deps = [d for d in dependencies_health if d.status == HealthStatus.UNHEALTHY]
        degraded_deps = [d for d in dependencies_health if d.status == HealthStatus.DEGRADED]

        if unhealthy_deps:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_deps:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        # Get system resources
        system_resources = self.get_system_resources()

        # Calculate uptime
        uptime = time.time() - self.start_time

        return ServiceHealth(
            service_name=self.service_name,
            status=overall_status,
            version=self.version,
            uptime_seconds=uptime,
            timestamp=datetime.now(),
            dependencies=dependencies_health,
            system_resources=system_resources,
            error_count=self.error_count,
            warning_count=self.warning_count
        )


def create_health_router(health_check: HealthCheck) -> APIRouter:
    """
    Create FastAPI router with health check endpoints

    Args:
        health_check: HealthCheck instance

    Returns:
        APIRouter with /health and /ready endpoints
    """
    router = APIRouter(tags=["health"])

    @router.get("/health", response_model=ServiceHealth)
    async def health():
        """
        Health check endpoint

        Returns detailed health status of the service and its dependencies.
        """
        # Note: In actual usage, inject db_session and redis_client
        health_status = await health_check.get_health()

        # Return 503 if unhealthy
        if health_status.status == HealthStatus.UNHEALTHY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=health_status.dict()
            )

        return health_status

    @router.get("/ready")
    async def readiness():
        """
        Readiness check endpoint

        Returns 200 if service is ready to accept traffic, 503 otherwise.
        """
        health_status = await health_check.get_health()

        if health_status.status == HealthStatus.UNHEALTHY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"ready": False, "reason": "Service unhealthy"}
            )

        return {"ready": True, "status": health_status.status}

    @router.get("/liveness")
    async def liveness():
        """
        Liveness check endpoint

        Simple endpoint to check if the service is alive.
        """
        return {
            "alive": True,
            "service": health_check.service_name,
            "uptime_seconds": time.time() - health_check.start_time
        }

    return router
