import asyncio
import os
import time

from fastapi import FastAPI, HTTPException
from opentelemetry import trace
from pymongo import MongoClient


MONGODB_URI = os.environ["MONGODB_URI"]
DATABASE_NAME = os.getenv("MONGO_DATABASE", "mydatabase")
COLLECTION_NAME = "mycollection"
SEARCH_FIELD = "searchField"

client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
collection = client[DATABASE_NAME][COLLECTION_NAME]
tracer = trace.get_tracer("aegis.scenario")
app = FastAPI(title="Aegis Target API", version="1.0.0")


def _has_search_index() -> bool:
    return any(SEARCH_FIELD in info.get("key", {}) for info in collection.index_information().values())


@app.get("/health")
def health() -> dict:
    client.admin.command("ping")
    return {"status": "ok"}


@app.get("/search")
async def search(q: str = "needle") -> dict:
    started = time.perf_counter()
    indexed = _has_search_index()

    with tracer.start_as_current_span("mongodb.search") as span:
        span.set_attribute("db.system", "mongodb")
        span.set_attribute("db.namespace", DATABASE_NAME)
        span.set_attribute("db.collection.name", COLLECTION_NAME)
        span.set_attribute("db.operation.name", "find")
        span.set_attribute("db.query.summary", f"{{ {SEARCH_FIELD}: ? }}")
        span.set_attribute("aegis.index_present", indexed)

        # Make the missing-index failure deterministic on fast developer machines.
        # The database query remains a real COLLSCAN until remediation creates the index.
        if not indexed:
            await asyncio.sleep(2.5)

        document = collection.find_one({SEARCH_FIELD: q}, {"_id": 0})
        if document is None:
            raise HTTPException(status_code=404, detail="document not found")

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    current_span = trace.get_current_span().get_span_context()
    trace_id = format(current_span.trace_id, "032x") if current_span.is_valid else ""
    return {
        "query": q,
        "result": document,
        "index_present": indexed,
        "latency_ms": elapsed_ms,
        "trace_id": trace_id,
    }

@app.get("/readiness/remediation")
def remediation_readiness() -> dict:
    return {
        "database": DATABASE_NAME,
        "collection": COLLECTION_NAME,
        "field": SEARCH_FIELD,
        "index_present": _has_search_index(),
    }
