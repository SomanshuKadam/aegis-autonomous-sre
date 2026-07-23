from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from aegis.control.read_models import incident_summary, overview
from aegis.integrations.signoz_links import context_links

def create_router(store: object) -> APIRouter:
    router = APIRouter(prefix="/api/v1/operations", tags=["operations"])
    @router.get("/overview")
    def get_overview() -> dict[str, object]: return overview(store.list())
    @router.get("/incidents")
    def list_incidents(cursor: int = 0, limit: int = 50) -> JSONResponse:
        values = store.list(cursor=cursor, limit=limit)
        return JSONResponse(content=jsonable_encoder({"items": [incident_summary(item) for item in values], "next_cursor": cursor + len(values) if len(values) == limit else None}), headers={"ETag": str(len(store.items))})
    @router.get("/incidents/{incident_id}")
    def incident_detail(incident_id: str, request: Request) -> dict[str, object]:
        try: incident = store.get(incident_id)
        except KeyError: raise HTTPException(status_code=404, detail="incident not found")
        trace_id = request.query_params.get("trace_id")
        incident["signoz"] = context_links(trace_id, "aegis-api") if trace_id else {"trace": {"url": None, "reason": "trace correlation unavailable"}}
        return {**incident, **store.records(incident_id)}
    return router
