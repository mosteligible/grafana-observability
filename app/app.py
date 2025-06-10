import os
import logging
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
# from opentelemetry.exporter.prometheus import PrometheusMetricReader # <--- REMOVE THIS
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
# Use PeriodicExportingMetricReader for OTLP push
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

from opentelemetry import trace, metrics

app_name = "fastapi-app"
app_version = "1.0.0"

resource = Resource.create({
    "service.name": app_name,
    "service.version": app_version,
    "application.name": "my-cool-fastapi-app",
})

######### TRACE PROVIDER
trace.set_tracer_provider(
    TracerProvider(resource=resource)
)
otlp_span_exporter = OTLPSpanExporter(
    endpoint="http://10.0.0.217:4317"
)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_span_exporter))

# METRICS TRACKING
otlp_metric_exporter = OTLPMetricExporter(endpoint="http://10.0.0.217:4317", insecure=True)
metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter, export_interval_millis=5000)
# Create a MeterProvider
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
# Set the global MeterProvider
metrics.set_meter_provider(meter_provider)

#### LOG EXPORTS
logger = logging.getLogger(name="this-logger")
logger.setLevel(logging.INFO)

from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# class FormattedLoggingHandler(LoggingHandler):
#     def emit(self, record: logging.LogRecord) -> None:
#         msg = self.format(record)
#         record.msg = msg
#         record.args = None
#         self._logger.emit(self._translate(record))


logger_provider = LoggerProvider(resource=resource)
set_logger_provider(logger_provider)
log_exporter = OTLPLogExporter(endpoint="http://10.0.0.217:4318")
logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

otel_log_handler = LoggingHandler(logger_provider=logger_provider)
LoggingInstrumentor().instrument()
logFormatter = logging.Formatter("%(pathname)s:%(funcName)s:%(lineno)d:%(levelname)s:%(message)s")
otel_log_handler.setFormatter(logFormatter)
logging.getLogger().addHandler(otel_log_handler)

# --- 4. Configure Python Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

app = FastAPI(title=app_name)

class Pb(BaseModel):
    name: str
    age: int


def is_valid(person: Pb) -> bool:
    if person.age <= 0 or person.age > 150:
        return True
    return False


@app.get("/")
def home():
    logger.info("getting home page")
    return {"home": "page"}


@app.post("/do-sth")
def do_sth(person: Pb):
    if is_valid(person):
        return {"person": "invalid"}
    return {"person": "valid"}


@app.get("/exp")
def exception():
    raise Exception("some rando exception!")


@app.get("/ping-google")
def ping_google():
    response = requests.get("https://www.google.com")
    logger.error(f"pinged google.com: {response.status_code}")
    return {"pinged": "ok"}

FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()
