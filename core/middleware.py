import time, threading, collections
from django.utils.deprecation import MiddlewareMixin

_METRICS_LOCK = threading.Lock()
REQUESTS_TOTAL = collections.Counter()
ERRORS_TOTAL = collections.Counter()
LATENCY_SUMMARY = collections.defaultdict(float)
LATENCY_COUNT = collections.Counter()


class RequestMetricsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._t0 = time.perf_counter()

    def process_response(self, request, response):
        path = getattr(request, "path", "unknown")
        code = getattr(response, "status_code", 0)
        dt = max(0.0, time.perf_counter() - getattr(request, "_t0", time.perf_counter()))
        with _METRICS_LOCK:
            REQUESTS_TOTAL[path] += 1
            LATENCY_SUMMARY[path] += dt
            LATENCY_COUNT[path] += 1
            if code >= 500:
                ERRORS_TOTAL[path] += 1
        return response
