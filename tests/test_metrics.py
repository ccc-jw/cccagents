"""Tests for the in-process Prometheus metrics module."""

from cccagents.metrics import METRICS, Metrics


def test_counter_increments():
    m = Metrics()
    m.inc("approval", "ok")
    m.inc("approval", "ok", n=4)
    m.inc("message", "fail")
    out = m.render()
    assert 'cccagents_webhook_requests_total{handler="approval",outcome="ok"} 5' in out
    assert 'cccagents_webhook_requests_total{handler="message",outcome="fail"} 1' in out


def test_timer_records_histogram():
    import time

    m = Metrics()
    with m.time("approval", "ok"):
        time.sleep(0.005)
    out = m.render()
    # Histogram format: _bucket{le="..."} <cumulative count>
    assert 'cccagents_webhook_request_duration_seconds_count{handler="approval",outcome="ok"} 1' in out
    assert 'cccagents_webhook_request_duration_seconds_sum{handler="approval",outcome="ok"}' in out
    # The cumulative bucket at +Inf must be 1 (it always equals count).
    assert 'cccagents_webhook_request_duration_seconds_bucket{handler="approval",outcome="ok",le="+Inf"} 1' in out
    # Every standard bucket must appear with the right label set.
    for bucket in ("0.005", "0.01", "0.025", "0.05", "0.1", "0.25", "0.5", "1.0", "2.5", "5.0", "10.0"):
        assert (
            f'cccagents_webhook_request_duration_seconds_bucket{{handler="approval",outcome="ok",le="{bucket}"}}'
            in out
        )


def test_gauge_renders():
    m = Metrics()
    m.set_gauge("cccagents_webhook_upstream_health", "nginx", 1.0)
    m.set_gauge("cccagents_webhook_upstream_health", "cccagents-pm-scheduler", 0.0)
    out = m.render()
    assert 'cccagents_webhook_upstream_health{service="nginx"} 1.0' in out
    assert 'cccagents_webhook_upstream_health{service="cccagents-pm-scheduler"} 0.0' in out


def test_render_is_prometheus_format():
    m = Metrics()
    m.inc("approval", "ok")
    out = m.render()
    # Required Prometheus exposition format markers.
    assert "# HELP cccagents_webhook_requests_total" in out
    assert "# TYPE cccagents_webhook_requests_total counter" in out
    assert "# TYPE cccagents_webhook_request_duration_seconds histogram" in out


def test_thread_safety_smoke():
    """Concurrent inc() calls must not lose updates."""
    import threading

    m = Metrics()
    n_threads = 20
    per_thread = 1000
    barrier = threading.Barrier(n_threads)

    def worker() -> None:
        barrier.wait()
        for _ in range(per_thread):
            m.inc("approval", "ok")

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    out = m.render()
    expected = n_threads * per_thread
    assert f'cccagents_webhook_requests_total{{handler="approval",outcome="ok"}} {expected}' in out


def test_module_singleton_present():
    """The module-level METRICS singleton is the one the server uses."""
    assert METRICS is not None
    METRICS.inc("test_marker_unique", "ok")
    # It's a singleton — re-importing the module doesn't reset state.
    out = METRICS.render()
    assert 'handler="test_marker_unique"' in out
