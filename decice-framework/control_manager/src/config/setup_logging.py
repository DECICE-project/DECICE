import logging

from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from config.config import Settings


def setup_opentelemetry_logging(settings: Settings):
    """
    Configures OpenTelemetry logging based on the provided settings object.
    """
    if not settings.OTEL_EXPORTER_OTLP_LOGS_ENDPOINT:
        print(
            "WARNING: OTEL_EXPORTER_OTLP_LOGS_ENDPOINT is not set. OTel logs will not be exported."
        )
        logging.basicConfig(level="INFO")  # Basic fallback
        logging.getLogger(__name__).info(
            "OTel logging is disabled. Falling back to standard console logging."
        )
        return

    resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})

    # Parse headers from the settings string
    headers = {}
    if settings.OTEL_EXPORTER_OTLP_LOGS_HEADERS:
        headers = dict(
            item.split("=")
            for item in settings.OTEL_EXPORTER_OTLP_LOGS_HEADERS.split(",")
        )

    exporter = OTLPLogExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_LOGS_ENDPOINT, headers=headers
    )

    logger_provider = LoggerProvider(resource=resource)
    processor = BatchLogRecordProcessor(exporter)
    logger_provider.add_log_record_processor(processor)

    # Hijack the standard logging library
    handler = LoggingHandler(level="INFO", logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
    # Set the level on the root logger. Individual loggers can have different levels.
    logging.getLogger().setLevel("INFO")

    # Confirmation log
    logger = logging.getLogger(__name__)
    logger.info(
        "OpenTelemetry logging configured successfully",
        extra={
            "service.name": settings.OTEL_SERVICE_NAME,
            "otel.endpoint": settings.OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
        },
    )
