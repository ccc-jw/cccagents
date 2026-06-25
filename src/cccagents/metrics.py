"""In-process Prometheus metrics for the webhook server.

This module is deliberately dependency-free (no ``prometheus_client``) so it
can run in any Python 3.12 environment without a pip step.  The output
format is the standard Prometheus text exposition, scraped by an external
Prometheus or VictoriaMetrics on :8080/metrics.

Counters track webhook requests by handler and outcome.  Histograms track
end-to-end request latency.  Thread-safe via a single lock — we don't
expect hot-path contention because the per-request counter increments
are sub-microsecond.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from contextlib import contextmanager


class Metrics:
    """Minimal Prometheus-format metrics registry.

    All counters / histograms are labeled by ``handler`` and ``outcome``
    where appropriate.  We expose:

      - ``cccagents_webhook_requests_total{handler, outcome}`` — counter
      - ``cccagents_webhook_request_duration_seconds{handler, outcome}`` — histogram
      - ``cccagents_webhook_upstream_health{service}`` — gauge (1 = active, 0 = other)
      - ``cccagents_webhook_up{service}`` — gauge (1 = healthy, 0 = unhealthy)
    """

    BUCKETS_SECONDS: tuple[float, ...] = (
        0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
    )

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, str], int] = defaultdict(int)
        self._hist: dict[tuple[str, str], list[float]] = defaultdict(
            lambda: [0.0] * len(self.BUCKETS_SECONDS)
        )
        self._hist_count: dict[tuple[str, str], int] = defaultdict(int)
        self._hist_sum: dict[tuple[str, str], float] = defaultdict(float)
        self._gauges: dict[tuple[str, str, str], float] = {}

    def inc(self, handler: str, outcome: str, n: int = 1) -> None:
        with self._lock:
            self._counters[(handler, outcome)] += n

    @contextmanager
    def time(self, handler: str, outcome: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            with self._lock:
                key = (handler, outcome)
                self._hist_count[key] += 1
                self._hist_sum[key] += elapsed
                for i, bucket in enumerate(self.BUCKETS_SECONDS):
                    if elapsed <= bucket:
                        self._hist[key][i] += 1

    def set_gauge(self, name: str, service: str, value: float) -> None:
        with self._lock:
            self._gauges[(name, service, "")] = value

    def set_gauge_with_state(self, name: str, service: str, state: str, value: float) -> None:
        with self._lock:
            self._gauges[(name, service, state)] = value

    def render(self) -> str:
        """Render all metrics in Prometheus text exposition format."""
        with self._lock:
            counters = dict(self._counters)
            hist = {k: list(v) for k, v in self._hist.items()}
            hist_count = dict(self._hist_count)
            hist_sum = dict(self._hist_sum)
            gauges = dict(self._gauges)

        lines: list[str] = []

        # Counters
        lines.append("# HELP cccagents_webhook_requests_total Webhook requests by handler+outcome.")
        lines.append("# TYPE cccagents_webhook_requests_total counter")
        for (handler, outcome), value in sorted(counters.items()):
            labels = _label_str(handler=handler, outcome=outcome)
            lines.append(f"cccagents_webhook_requests_total{labels} {value}")

        # Histograms
        lines.append("# HELP cccagents_webhook_request_duration_seconds Request latency in seconds.")
        lines.append("# TYPE cccagents_webhook_request_duration_seconds histogram")
        for (handler, outcome), counts in sorted(hist.items()):
            cum = 0
            for i, bucket in enumerate(self.BUCKETS_SECONDS):
                cum = counts[i]
                labels = _label_str(handler=handler, outcome=outcome, le=str(bucket))
                lines.append(
                    f'cccagents_webhook_request_duration_seconds_bucket{labels} {cum}'
                )
            labels = _label_str(handler=handler, outcome=outcome, le="+Inf")
            lines.append(
                f'cccagents_webhook_request_duration_seconds_bucket{labels} {hist_count[(handler, outcome)]}'
            )
            lines.append(
                f'cccagents_webhook_request_duration_seconds_count{_label_str(handler=handler, outcome=outcome)} {hist_count[(handler, outcome)]}'
            )
            lines.append(
                f'cccagents_webhook_request_duration_seconds_sum{_label_str(handler=handler, outcome=outcome)} {hist_sum[(handler, outcome)]:.6f}'
            )

        # Gauges
        if gauges:
            lines.append("# HELP cccagents_webhook_upstream_health Upstream service health (1=active/healthy, 0=otherwise).")
            lines.append("# TYPE cccagents_webhook_upstream_health gauge")
            for (name, service, _state), value in sorted(gauges.items()):
                if name == "cccagents_webhook_upstream_health":
                    labels = _label_str(service=service)
                    lines.append(f"cccagents_webhook_upstream_health{labels} {value}")

        return "\n".join(lines) + "\n"


def _label_str(**kwargs: str) -> str:
    parts = [f'{k}="{v}"' for k, v in kwargs.items()]
    if not parts:
        return ""
    return "{" + ",".join(parts) + "}"


# Module-level singleton so the server can share it across requests.
METRICS = Metrics()


__all__ = ["Metrics", "METRICS"]
