from __future__ import annotations
import asyncio
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from aegis.config import get_settings
from aegis.api.orchestration import router as orchestration_router
from aegis.api.commerce import router as commerce_router
from opentelemetry import trace
from pymongo import MongoClient

def create_app() -> FastAPI:
    app = FastAPI(title="Aegis Application Reliability API", version="1.0.0")
    app.include_router(orchestration_router)
    app.include_router(commerce_router)
    settings = get_settings()
    client = MongoClient(settings.mongodb_uri.get_secret_value(), serverSelectionTimeoutMS=5000)
    collection = client[settings.mongo_database]["mycollection"]
    tracer = trace.get_tracer("aegis.scenario")
    def has_search_index() -> bool:
        return any(any(key == "searchField" for key, _ in info.get("key", [])) for info in collection.index_information().values())
    @app.exception_handler(ValueError)
    async def invalid_value(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"code":"INVALID_INPUT","message":str(exc),"correlation_id":""})
    @app.get("/api/v1/health")
    @app.get("/health")
    def health() -> dict[str, object]: return {"status":"ok", "service":"aegis-api", "settings":get_settings().safe_summary()}
    @app.get("/api/v1/readiness")
    def readiness() -> dict[str, object]: return {"ready":True, "status":"ok", "service":"aegis-api"}
    @app.get("/search")
    async def search(q: str = "needle") -> dict[str, object]:
        started = time.perf_counter(); indexed = has_search_index()
        with tracer.start_as_current_span("mongodb.search") as span:
            span.set_attribute("db.system", "mongodb"); span.set_attribute("db.namespace", settings.mongo_database); span.set_attribute("db.collection.name", "mycollection"); span.set_attribute("db.operation.name", "find"); span.set_attribute("aegis.index_present", indexed)
            if not indexed: await asyncio.sleep(2.5)
            document = collection.find_one({"searchField": q}, {"_id": 0})
            if document is None: raise HTTPException(status_code=404, detail="document not found")
        context = trace.get_current_span().get_span_context()
        return {"query":q,"result":document,"index_present":indexed,"latency_ms":round((time.perf_counter()-started)*1000,2),"trace_id":format(context.trace_id,"032x") if context.is_valid else ""}
    @app.get("/readiness/remediation")
    def remediation_readiness() -> dict[str, object]: return {"database":settings.mongo_database,"collection":"mycollection","field":"searchField","index_present":has_search_index()}
    return app
