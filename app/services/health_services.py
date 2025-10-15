import statistics
import time
import asyncio
import aiohttp
import json
from typing import List, Optional


class HealthMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.request_times: List[float] = []
        self.error_count = 0
        self.total_requests = 0
        self.webhook_url: Optional[str] = None
        self.error_rate_threshold: float = 10.0  # 10% error rate threshold
        self.last_incident_time: float = 0
        self.incident_cooldown: float = 300  # 5 minutes cooldown between incidents

    def record_request(self, duration_ms: float, is_error: bool = False):
        self.total_requests += 1
        self.request_times.append(duration_ms)
        if is_error:
            self.error_count += 1
        if (len(self.request_times) > 1000):
            self.request_times.pop(0)
        
        # Check if we need to send an incident webhook
        current_error_rate = self.get_error_rate()
        if (current_error_rate > self.error_rate_threshold and 
            self.webhook_url and 
            time.time() - self.last_incident_time > self.incident_cooldown):
            asyncio.create_task(self._send_incident_webhook(current_error_rate))

    def get_uptime(self) -> float:
        return time.time() - self.start_time

    def get_error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.error_count / self.total_requests)*100

    def get_p95_latency(self) -> float:
        if not self.request_times:
            return 0.0
        return statistics.quantiles(self.request_times, n=20)[18]
    
    def configure_webhook(self, url: str, threshold: float = 10.0):
        """Configure webhook URL and error rate threshold for incidents."""
        self.webhook_url = url
        self.error_rate_threshold = threshold
    
    async def _send_incident_webhook(self, error_rate: float):
        """Send incident webhook when error rate exceeds threshold."""
        self.last_incident_time = time.time()
        
        incident_data = {
            "type": "incident",
            "severity": "high" if error_rate > 20 else "medium",
            "message": f"Error rate exceeded threshold: {error_rate:.2f}% > {self.error_rate_threshold}%",
            "timestamp": time.time(),
            "metrics": {
                "error_rate": error_rate,
                "threshold": self.error_rate_threshold,
                "total_requests": self.total_requests,
                "error_count": self.error_count,
                "uptime_seconds": self.get_uptime(),
                "p95_latency_ms": self.get_p95_latency()
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=incident_data,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        print(f"Incident webhook sent successfully: {error_rate:.2f}% error rate")
                    else:
                        print(f"Failed to send incident webhook: HTTP {response.status}")
        except Exception as e:
            print(f"Error sending incident webhook: {e}")


health_monitor = HealthMonitor()
