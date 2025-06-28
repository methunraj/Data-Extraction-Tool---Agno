"""
Monitoring and metrics collection for IntelliExtract.
"""

import time
import psutil
import os
from typing import Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque

from .core.logging import get_logger

logger = get_logger("monitoring")


class MetricsCollector:
    """Collect and store application metrics."""
    
    def __init__(self):
        self.start_time = time.time()
        self.request_counts = defaultdict(int)
        self.response_times = deque(maxlen=1000)  # Keep last 1000 response times
        self.error_rates = defaultdict(int)
        self.active_operations = set()
    
    def record_request(self, method: str, path: str):
        """Record an API request."""
        self.request_counts[f"{method} {path}"] += 1
    
    def record_response_time(self, duration_ms: float):
        """Record response time."""
        self.response_times.append(duration_ms)
    
    def record_error(self, error_type: str):
        """Record an error."""
        self.error_rates[error_type] += 1
    
    def add_active_operation(self, operation_id: str):
        """Add an active operation."""
        self.active_operations.add(operation_id)
    
    def remove_active_operation(self, operation_id: str):
        """Remove an active operation."""
        self.active_operations.discard(operation_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        uptime_seconds = time.time() - self.start_time
        
        # Calculate response time statistics
        response_times_list = list(self.response_times)
        avg_response_time = sum(response_times_list) / len(response_times_list) if response_times_list else 0
        
        # Get system metrics
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            memory_info = None
            cpu_percent = 0
        
        return {
            "uptime_seconds": uptime_seconds,
            "uptime_human": str(timedelta(seconds=int(uptime_seconds))),
            "requests": {
                "total": sum(self.request_counts.values()),
                "by_endpoint": dict(self.request_counts),
                "rate_per_minute": sum(self.request_counts.values()) / (uptime_seconds / 60) if uptime_seconds > 0 else 0
            },
            "response_times": {
                "average_ms": avg_response_time,
                "count": len(response_times_list),
                "min_ms": min(response_times_list) if response_times_list else 0,
                "max_ms": max(response_times_list) if response_times_list else 0
            },
            "errors": {
                "total": sum(self.error_rates.values()),
                "by_type": dict(self.error_rates),
                "rate_per_minute": sum(self.error_rates.values()) / (uptime_seconds / 60) if uptime_seconds > 0 else 0
            },
            "operations": {
                "active_count": len(self.active_operations),
                "active_operations": list(self.active_operations)
            },
            "system": {
                "memory_mb": memory_info.rss / 1024 / 1024 if memory_info else 0,
                "memory_percent": memory_info.rss / psutil.virtual_memory().total * 100 if memory_info else 0,
                "cpu_percent": cpu_percent,
                "disk_usage": self._get_disk_usage()
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    def _get_disk_usage(self) -> Dict[str, float]:
        """Get disk usage statistics."""
        try:
            # Get disk usage for the temp directory
            from .main import TEMP_DIR
            if os.path.exists(TEMP_DIR):
                usage = psutil.disk_usage(TEMP_DIR)
                return {
                    "total_gb": usage.total / (1024**3),
                    "used_gb": usage.used / (1024**3),
                    "free_gb": usage.free / (1024**3),
                    "percent_used": (usage.used / usage.total) * 100
                }
        except Exception as e:
            logger.warning(f"Could not get disk usage: {e}")
        
        return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent_used": 0}


# Global metrics collector
metrics_collector = MetricsCollector()


def get_health_status() -> Dict[str, Any]:
    """Get overall health status."""
    metrics = metrics_collector.get_metrics()
    
    # Determine health status based on metrics
    status = "healthy"
    issues = []
    
    # Check memory usage
    if metrics["system"]["memory_percent"] > 90:
        status = "warning"
        issues.append("High memory usage")
    
    # Check error rate
    error_rate = metrics["errors"]["rate_per_minute"]
    if error_rate > 10:  # More than 10 errors per minute
        status = "critical"
        issues.append("High error rate")
    elif error_rate > 5:
        status = "warning"
        issues.append("Elevated error rate")
    
    # Check response times
    avg_response_time = metrics["response_times"]["average_ms"]
    if avg_response_time > 5000:  # More than 5 seconds
        status = "critical"
        issues.append("Slow response times")
    elif avg_response_time > 2000:  # More than 2 seconds
        status = "warning"
        issues.append("Elevated response times")
    
    # Check disk usage
    disk_usage = metrics["system"]["disk_usage"]["percent_used"]
    if disk_usage > 95:
        status = "critical"
        issues.append("Disk space critical")
    elif disk_usage > 85:
        status = "warning"
        issues.append("Disk space low")
    
    return {
        "status": status,
        "issues": issues,
        "metrics": metrics
    }