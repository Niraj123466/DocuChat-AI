"""Observability subsystem: Prometheus metrics exporter and OpenTelemetry distributed tracing."""
from __future__ import annotations

import time
import threading
from contextlib import contextmanager
from typing import Dict, Any, Optional, Generator

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("telemetry")

class PrometheusMetrics:
    """Zero-dependency, high-speed Prometheus metrics registry and exporter."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Counters: { (metric_name, tuple(sorted(labels.items()))): float }
        self.counters: Dict[tuple, float] = {}
        # Histograms: { (metric_name, tuple(sorted(labels.items()))): list_of_observations }
        self.histograms: Dict[tuple, list] = {}
        self.buckets = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]

    def inc_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        label_key = tuple(sorted((labels or {}).items()))
        with self._lock:
            key = (name, label_key)
            self.counters[key] = self.counters.get(key, 0.0) + value

    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        label_key = tuple(sorted((labels or {}).items()))
        with self._lock:
            key = (name, label_key)
            if key not in self.histograms:
                self.histograms[key] = []
            self.histograms[key].append(value)
            # Keep at most last 1,000 observations per label set to prevent memory unbounded growth
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-500:]

    def generate_scrape_text(self) -> str:
        """Serializes current metrics into the official Prometheus / OpenMetrics plain text format."""
        lines = []

        with self._lock:
            # 1. Output Counters
            for (name, label_pairs), count in sorted(self.counters.items()):
                label_str = ""
                if label_pairs:
                    label_str = "{" + ",".join(f'{k}="{v}"' for k, v in label_pairs) + "}"
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name}{label_str} {count}")

            # 2. Output Histograms
            for (name, label_pairs), observations in sorted(self.histograms.items()):
                base_label_dict = dict(label_pairs)
                count = len(observations)
                total_sum = sum(observations)

                lines.append(f"# TYPE {name} histogram")
                # Output bucket counts
                for b in self.buckets:
                    b_count = sum(1 for o in observations if o <= b)
                    b_labels = base_label_dict.copy()
                    b_labels["le"] = str(b)
                    lbl = "{" + ",".join(f'{k}="{v}"' for k, v in sorted(b_labels.items())) + "}"
                    lines.append(f"{name}_bucket{lbl} {b_count}")

                inf_labels = base_label_dict.copy()
                inf_labels["le"] = "+Inf"
                inf_lbl = "{" + ",".join(f'{k}="{v}"' for k, v in sorted(inf_labels.items())) + "}"
                lines.append(f"{name}_bucket{inf_lbl} {count}")

                raw_lbl = "{" + ",".join(f'{k}="{v}"' for k, v in sorted(base_label_dict.items())) + "}" if base_label_dict else ""
                lines.append(f"{name}_sum{raw_lbl} {total_sum:.4f}")
                lines.append(f"{name}_count{raw_lbl} {count}")

        return "\n".join(lines) + "\n"

# Global Prometheus metrics registry
metrics = PrometheusMetrics()


# OpenTelemetry Tracing Layer
class DummySpan:
    def set_attribute(self, key: str, value: Any) -> None:
        pass
    def record_exception(self, exception: Exception) -> None:
        pass

@contextmanager
def trace_span(name: str, attributes: Optional[Dict[str, Any]] = None) -> Generator[Any, None, None]:
    """Creates an OpenTelemetry span, with graceful fallback if OTEL is unconfigured."""
    start = time.perf_counter()
    try:
        from opentelemetry import trace
        tracer = trace.get_tracer("docuchat")
        with tracer.start_as_current_span(name) as span:
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, str(v))
            yield span
    except Exception:
        # Fallback dummy span
        span = DummySpan()
        yield span
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        # Record into Prometheus latency metrics
        metrics.observe_histogram("docuchat_span_latency_seconds", duration_ms / 1000.0, labels={"span": name})
