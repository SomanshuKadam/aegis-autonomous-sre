from __future__ import annotations
import asyncio
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from aegis.config import get_settings
from aegis.api.orchestration import router as orchestration_router
from aegis.api.commerce import router as commerce_router
from aegis.api.operations import create_router as create_operations_router
from aegis.api.evaluation import router as evaluation_router
from aegis.api.orchestration import incidents
from opentelemetry import trace
from pymongo import MongoClient
from aegis.workload.service import WorkloadService

def create_app() -> FastAPI:
    app = FastAPI(title="Aegis Application Reliability API", version="1.0.0")
    app.include_router(orchestration_router)
    app.include_router(commerce_router)
    app.include_router(create_operations_router(incidents))
    app.include_router(evaluation_router)
    settings = get_settings()
    client = MongoClient(settings.mongodb_uri.get_secret_value(), serverSelectionTimeoutMS=5000)
    collection = client[settings.mongo_database]["mycollection"]
    products = client[settings.mongo_database]["products"]
    if products.estimated_document_count() == 0:
        products.insert_many([
            {"product_id": "product-001", "sku": "sku-001", "name": "Aegis Notebook", "search_text": "aegis notebook reliability", "price_minor": 1299},
            {"product_id": "product-002", "sku": "sku-002", "name": "Signal Mug", "search_text": "signal mug observability", "price_minor": 899},
        ])
    workload = WorkloadService()
    tracer = trace.get_tracer("aegis.scenario")
    def has_search_index() -> bool:
        return any(any(key == "searchField" for key, _ in info.get("key", [])) for info in collection.index_information().values())
    def has_catalog_index() -> bool:
        return "search_text_1" in products.index_information()
    @app.exception_handler(ValueError)
    async def invalid_value(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"code":"INVALID_INPUT","message":str(exc),"correlation_id":""})
    @app.exception_handler(KeyError)
    async def missing_resource(_: Request, exc: KeyError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"code":"NOT_FOUND","message":str(exc),"correlation_id":""})
    @app.get("/api/v1/health")
    @app.get("/health")
    def health() -> dict[str, object]: return {"status":"ok", "service":"aegis-api", "settings":get_settings().safe_summary()}
    @app.get("/api/v1/readiness")
    def readiness() -> dict[str, object]: return {"ready":True, "status":"ok", "service":"aegis-api"}
    @app.post("/api/v1/workloads")
    def start_workload(seed: int = 1, demo: bool = False) -> dict[str, object]:
        if demo and not settings.demo_workload_enabled: raise HTTPException(status_code=403, detail="demo workload is disabled")
        if not demo and not settings.normal_workload_enabled: raise HTTPException(status_code=403, detail="normal workload is disabled")
        return workload.start(seed, demo).__dict__
    @app.delete("/api/v1/workloads/{run_id}")
    def stop_workload(run_id: str) -> dict[str, object]: return workload.stop(run_id).__dict__
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
    @app.get("/api/v1/catalog/search")
    async def catalog_search(q: str = "aegis notebook reliability") -> dict[str, object]:
        started = time.perf_counter(); indexed = has_catalog_index()
        with tracer.start_as_current_span("catalog.search") as span:
            span.set_attribute("db.system", "mongodb"); span.set_attribute("db.namespace", settings.mongo_database); span.set_attribute("db.collection.name", "products"); span.set_attribute("db.operation.name", "find"); span.set_attribute("aegis.index_present", indexed); span.set_attribute("catalog.query", q)
            if not indexed:
                await asyncio.sleep(2.5)
            documents = list(products.find({"search_text": q}, {"_id": 0}).limit(20))
        context = trace.get_current_span().get_span_context()
        return {"query": q, "items": documents, "index_present": indexed, "latency_ms": round((time.perf_counter()-started)*1000, 2), "trace_id": format(context.trace_id, "032x") if context.is_valid else ""}
    @app.get("/readiness/remediation")
    def remediation_readiness() -> dict[str, object]: return {"database":settings.mongo_database,"collection":"products","field":"search_text","index_present":has_catalog_index()}
    return app
