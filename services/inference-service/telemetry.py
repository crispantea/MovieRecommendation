import os
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

_initialized = False


def init_metrics(service_name, otel_exporter_oltp_endpoint):
    """Call once per process, at startup."""
    global _initialized
    if _initialized:
        return
    resource = Resource.create({
        "service.name": service_name
    })
    exporter = OTLPMetricExporter(
        endpoint=otel_exporter_oltp_endpoint,
        insecure=True,
    )
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=15000)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))
    _initialized = True


def get_llm_duration_histogram(service_name):
    meter = metrics.get_meter(service_name)
    return meter.create_histogram(
        "llm.request.duration",
        unit="s",
        description="Duration of LLM recommendation generation requests",
    )