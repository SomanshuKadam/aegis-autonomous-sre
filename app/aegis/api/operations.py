from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
import httpx
from aegis.config import get_settings
from aegis.control.read_models import incident_summary, overview
from aegis.integrations.signoz_links import context_links

def create_router(store: object) -> APIRouter:
    router = APIRouter(prefix="/api/v1/operations", tags=["operations"])
    settings = get_settings()

    def service_health(name: str, url: str) -> dict[str, object]:
        try:
            response = httpx.get(url, timeout=3)
            response.raise_for_status()
            return {"name": name, "available": True, "detail": response.json()}
        except httpx.HTTPError as exc:
            return {"name": name, "available": False, "detail": {"reason": str(exc)}}

    @router.get("/overview")
    def get_overview() -> dict[str, object]:
        services = {
            "inventory": service_health("Inventory", f"{settings.inventory_url.rstrip('/')}/health"),
            "worker": service_health("Worker", f"{settings.worker_url.rstrip('/')}/health"),
            "workload": service_health("Workload", "http://workload:8084/health"),
        }
        return overview(store.list(), services)
    @router.get("/incidents")
    def list_incidents(cursor: int = 0, limit: int = 50, state: str | None = None, category: str | None = None) -> JSONResponse:
        values = store.list(cursor=cursor, limit=limit)
        if state:
            values = [item for item in values if item.get("state") == state]
        if category:
            values = [item for item in values if item.get("category") == category]
        return JSONResponse(content=jsonable_encoder({"items": [incident_summary(item) for item in values], "next_cursor": cursor + len(values) if len(values) == limit else None}), headers={"ETag": str(len(store.items))})
    @router.get("/incidents/{incident_id}")
    def incident_detail(incident_id: str, request: Request) -> dict[str, object]:
        try: incident = store.get(incident_id)
        except KeyError: raise HTTPException(status_code=404, detail="incident not found")
        trace_id = request.query_params.get("trace_id") or str(incident.get("trace_id") or "")
        service = {"catalog_search": "aegis-api", "inventory_dependency": "aegis-inventory", "order_backlog": "aegis-worker"}.get(str(incident.get("category")), "aegis-api")
        incident["signoz"] = context_links(trace_id, service, settings.signoz_url.rstrip("/")) if trace_id else {"trace": {"url": None, "reason": "trace correlation unavailable"}, "logs": {"url": None, "reason": "trace correlation unavailable"}, "service": {"url": None, "reason": "trace correlation unavailable"}, "dashboard": {"url": None, "reason": "trace correlation unavailable"}}
        return {**incident, **store.records(incident_id)}
    return router
