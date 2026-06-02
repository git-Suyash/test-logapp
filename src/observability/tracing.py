from opentelemetry import trace

from opentelemetry.sdk.trace import TracerProvider

from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)


provider = TracerProvider()


processor = BatchSpanProcessor(
    OTLPSpanExporter(
        endpoint="http://localhost:4317",
        insecure=True
    )
)


provider.add_span_processor(processor)

trace.set_tracer_provider(provider)

tracer = trace.get_tracer("logApp")