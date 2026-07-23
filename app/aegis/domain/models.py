from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class OrderState(StrEnum):
    CREATED = "CREATED"; RESERVED = "RESERVED"; QUEUED = "QUEUED"; PROCESSING = "PROCESSING"; COMPLETED = "COMPLETED"; FAILED = "FAILED"; CANCELLED = "CANCELLED"


class Product(BaseModel): product_id: str; sku: str; name: str; search_text: str; price_minor: int = Field(ge=0); currency: str = "USD"; active: bool = True
class InventoryItem(BaseModel): inventory_id: str; product_id: str; available: int = Field(ge=0); reserved: int = Field(ge=0); version: int = 1
class Reservation(BaseModel): reservation_id: str; product_id: str; order_id: str; quantity: int = Field(ge=1); state: str = "HELD"; expires_at: datetime
class Order(BaseModel): order_id: str; idempotency_key: str; state: OrderState = OrderState.CREATED; items: list[dict]; total_minor: int = Field(ge=0); currency: str = "USD"; trace_id: str | None = None
class QueueJob(BaseModel): job_id: str; order_id: str; state: str = "PENDING"; attempts: int = 0; available_at: datetime
class WorkerCapacity(BaseModel): scope: str = "order-worker"; desired: int = 1; minimum: int = 1; maximum: int = 4; version: int = 1
class WorkloadProfile(BaseModel): profile_id: str; version: int = 1; seed: int = 1; enabled: bool = True
class WorkloadRun(BaseModel): run_id: str; profile_id: str; state: str = "CREATED"; condition_markers: dict[str, str] = {}
