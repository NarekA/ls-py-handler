import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional

import asyncpg
import orjson
from aiobotocore.session import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import UUID4, BaseModel, Field

from ls_py_handler.config.settings import settings

from opentelemetry import trace
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.aiobotocore import AioBotocoreInstrumentor

AsyncPGInstrumentor().instrument()
AioBotocoreInstrumentor().instrument()

tracer = trace.get_tracer(__name__)

router = APIRouter(prefix="/runs", tags=["runs"])


class Run(BaseModel):
    id: Optional[UUID4] = Field(default_factory=uuid.uuid4)
    trace_id: UUID4
    name: str
    inputs: Dict[str, Any] = {}
    outputs: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}

async def get_db_conn():
    with tracer.start_as_current_span("get_db_conn"):
        conn = await asyncpg.connect(
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
        )
        try:
            yield conn
        finally:
            await conn.close()

async def get_s3_client():
    with tracer.start_as_current_span("get_s3_client"):
        session = get_session()
        async with session.create_client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        ) as client:
            yield client


async def create_run(
    run: Run,
    db: asyncpg.Connection = Depends(get_db_conn),
    s3: Any = Depends(get_s3_client),
):
    with tracer.start_as_current_span("create_run"):
        # Prepare the run data for insertion
        run_dict = run.model_dump()
        run_bytes = orjson.dumps(run_dict)
        object_key = f"runs/{run.id}.json"

        # S3 upload
        with tracer.start_as_current_span("s3_put_object"):
            await s3.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=object_key,
                Body=run_bytes,
                ContentType="application/json",
            )

            return run.id


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_runs(
    runs: List[Run],
    db: asyncpg.Connection = Depends(get_db_conn),
    s3: Any = Depends(get_s3_client),
):
    with tracer.start_as_current_span("create_runs"):
        if not runs:
            raise HTTPException(status_code=400, detail="No runs provided")


        run_builders = [create_run(run, db=db, s3=s3) for run in runs]
        results = await asyncio.gather(*run_builders)

        with tracer.start_as_current_span("db_insert_run"):
            # Prepare the record for insertion
            records = [
                (
                    run.id,
                    run.trace_id,
                    run.name,
                    f"s23://{settings.S3_BUCKET_NAME}/runs/{run.id}.json"  # Store S3 object key,
                )
                for run in runs
            ]

            # Copy records to the database
            await db.copy_records_to_table(
                'runs',
                records=records,
                columns=['id', 'trace_id', 'name', 'inputs']  # Optional: specify column order
            )

        return {"status": "created", "run_ids": results}


async def fetch_from_s3(bucket: str, key: str, s3: Any = Depends(get_s3_client)):

    if not bucket or not key:
        return None


    response = await s3.get_object(Bucket=bucket, Key=key)


    # Fetch only the required byte range
    async with response["Body"] as stream:
        data = await stream.read()
        return data


@router.get("/{run_id}", status_code=status.HTTP_200_OK)
async def get_run(
    run_id: UUID4,
    db: asyncpg.Connection = Depends(get_db_conn),
    s3: Any = Depends(get_s3_client),
):
    """
    Get a run by its ID.
    """
    with (tracer.start_as_current_span("get_run")):
        # Fetch the run from the PG
        with tracer.start_as_current_span("db_fetch_run"):
            row = await db.fetchrow(
                """
                SELECT id, trace_id, name, inputs, outputs, metadata
                FROM runs
                WHERE id = $1
                """,
                run_id,
            )

        if not row:
            raise HTTPException(status_code=404, detail=f"Run with ID {run_id} not found")

        object_key = f"runs/{run_id}.json"


        # S3 upload
        with tracer.start_as_current_span("s3_get_object"):
            data = await fetch_from_s3(bucket=settings.S3_BUCKET_NAME, key=object_key, s3=s3)


        return data
