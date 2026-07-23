from fastapi import FastAPI, Header, HTTPException
from time import perf_counter, sleep
import os
from opentelemetry import trace
from pydantic import BaseModel, Field
from aegis.config import get_settings
from aegis.inventory.store import InventoryStore
from aegis.control.service_state import ServiceState

app = FastAPI(title="Aegis Inventory")
inventory = InventoryStore()
capacity = ServiceState("inventory", {"desired": 1, "previous": 1, "healthy": True, "maximum": 4, "in_flight": 0})
tracer = trace.get_tracer("aegis.inventory")

class ReservationRequest(BaseModel):
    sku: str
    quantity: int = Field(ge=1, le=20)
    order_id: str


@app.get("/health")
def health() -> dict[str, object]:
    state = capacity.read()
    metrics = inventory.metrics()
    return {"status": "ok" if state["healthy"] else "degraded", "service": "aegis-inventory", "capacity": state["desired"], "maximum": state["maximum"], "in_flight": state.get("in_flight", 0), "resource_saturated": int(state.get("in_flight", 0)) >= int(state["desired"]), "metrics": metrics}

@app.post("/reservations")
def reserve(payload: ReservationRequest, traceparent: str | None = Header(default=None)) -> dict[str, object]:
    started = perf_counter()
    if not capacity.acquire_slot():
        latency = round((perf_counter() - started) * 1000, 3)
        inventory.record_operation(False, latency, "capacity_exhausted")
        raise HTTPException(status_code=503, detail="inventory dependency capacity is exhausted")
    try:
        with tracer.start_as_current_span("inventory.reserve") as span:
            span.set_attribute("inventory.sku", payload.sku)
            span.set_attribute("inventory.capacity", capacity.read()["desired"])
            span.set_attribute("inventory.trace_context_received", bool(traceparent))
            sleep(float(os.getenv("AEGIS_INVENTORY_OPERATION_SECONDS", "0.15")))
            reservation = inventory.reserve(payload.sku, payload.quantity, payload.order_id)
    except ValueError:
        latency = round((perf_counter() - started) * 1000, 3)
        inventory.record_operation(False, latency, "reservation_rejected")
        raise HTTPException(status_code=503, detail="inventory reservation is unavailable")
    finally:
        capacity.release_slot()
    latency = round((perf_counter() - started) * 1000, 3)
    inventory.record_operation(True, latency)
    return {**reservation, "trace_context_received": bool(traceparent), "latency_ms": latency, "capacity": capacity.read()["desired"]}

@app.post("/reservations/{reservation_id}/commit")
def commit(reservation_id: str) -> dict[str, object]:
    return inventory.commit(reservation_id)

@app.post("/control/capacity")
def set_capacity(desired: int, authorization: str | None = Header(default=None), x_aegis_rollback: str | None = Header(default=None)) -> dict[str, object]:
    if authorization != f"Bearer {get_settings().runner_token.get_secret_value()}": raise HTTPException(status_code=401, detail="invalid runner credentials")
    if not 1 <= desired <= 4: raise HTTPException(status_code=422, detail="capacity is outside the approved range")
    return {**capacity.update_capacity(desired), "state": "SUCCEEDED", "rollback": x_aegis_rollback == "true"}
