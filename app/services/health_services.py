import statistics
import time
from typing import List


class HealthMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.request_times: List[float] = []
        self.error_count = 0
        self.total_requests = 0

    def record_request(self, duration_ms: float, is_error: bool = False):
        self.total_requests += 1
        self.request_times.append(duration_ms)
        if is_error:
            self.error_count += 1
        if (len(self.request_times) > 1000):
            self.request_times.pop(0)

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


health_monitor = HealthMonitor()
