# from opentelemetry import trace
# from opentelemetry.sdk.resources import Resource
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import BatchSpanProcessor
# from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
#
# # Set up OpenTelemetry tracing
# resource = Resource.create({"service.name": "my-app"})
# provider = TracerProvider(resource=resource)
# processor = BatchSpanProcessor(
#     OTLPSpanExporter()
# )
# provider.add_span_processor(processor)
# trace.set_tracer_provider(provider)

from aiobotocore.session import get_session
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse


from ls_py_handler.api.routes.runs import router as runs_router
from ls_py_handler.config.settings import settings
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    default_response_class=ORJSONResponse,
)


# Include routers
app.include_router(runs_router)


@app.on_event("startup")
async def startup_event():
    """Initialize resources when the application starts."""
    # Create S3 bucket if it doesn't exist
    session = get_session()
    async with session.create_client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
    ) as s3:
        try:
            await s3.create_bucket(Bucket=settings.S3_BUCKET_NAME)
            print(f"Created S3 bucket: {settings.S3_BUCKET_NAME}")
        except Exception:
            print("Tried to create S3 bucket, but it already exists. No action taken.")


@app.get("/")
async def root():
    """
    Root endpoint to verify the API is running.
    """
    return {"message": settings.APP_TITLE + " API"}


FastAPIInstrumentor.instrument_app(app)
