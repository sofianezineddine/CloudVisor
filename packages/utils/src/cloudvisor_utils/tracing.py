"""OpenTelemetry tracing and metrics configuration for CloudVisor services."""

from contextlib import contextmanager
from typing import Any, Iterator

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode


def setup_tracing(
    service_name: str,
    otlp_endpoint: str,
    enabled: bool = True,
) -> None:
    """Initialize OpenTelemetry tracing and metrics exporters."""
    if not enabled:
        return

    resource = Resource.create({"service.name": service_name, "service.version": "1.0.0"})

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True))
    )
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True),
        export_interval_millis=60000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)


def instrument_fastapi(app: Any) -> None:
    """Add OpenTelemetry instrumentation to FastAPI app."""
    FastAPIInstrumentor.instrument_app(app, excluded_urls="/health,/ready,/metrics")


def get_tracer(name: str = "cloudvisor") -> trace.Tracer:
    """Get an OpenTelemetry tracer."""
    return trace.get_tracer(name)


def get_meter(name: str = "cloudvisor") -> metrics.Meter:
    """Get an OpenTelemetry meter."""
    return metrics.get_meter(name)


@contextmanager
def span(
    name: str,
    attributes: dict[str, Any] | None = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
) -> Iterator[trace.Span]:
    """Context manager for creating a traced span."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name, kind=kind) as ctx_span:
        if attributes:
            for k, v in attributes.items():
                ctx_span.set_attribute(k, v)
        try:
            yield ctx_span
            ctx_span.set_status(Status(StatusCode.OK))
        except Exception as e:
            ctx_span.set_status(Status(StatusCode.ERROR, str(e)))
            ctx_span.record_exception(e)
            raise


def create_counter(
    name: str,
    description: str = "",
    unit: str = "1",
) -> metrics.Counter:
    """Create a metrics counter."""
    meter = get_meter()
    return meter.create_counter(name=name, description=description, unit=unit)


def create_histogram(
    name: str,
    description: str = "",
    unit: str = "1",
) -> metrics.Histogram:
    """Create a metrics histogram."""
    meter = get_meter()
    return meter.create_histogram(name=name, description=description, unit=unit)


def create_up_down_counter(
    name: str,
    description: str = "",
    unit: str = "1",
) -> metrics.UpDownCounter:
    """Create an up-down counter (for gauges)."""
    meter = get_meter()
    return meter.create_up_down_counter(name=name, description=description, unit=unit)
