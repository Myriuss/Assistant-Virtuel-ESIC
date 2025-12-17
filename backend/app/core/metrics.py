from prometheus_client import Counter, Histogram

REQ_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQ_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency (seconds)",
    ["method", "path"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)

CHAT_FALLBACK = Counter(
    "chat_fallback_total",
    "Number of chat requests that ended in fallback",
)

CHAT_RESOLVED = Counter(
    "chat_resolved_total",
    "Number of chat requests that were resolved",
)
