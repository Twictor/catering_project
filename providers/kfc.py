from typing import Literal
import httpx
import os
from dataclasses import dataclass
from enum import Enum


class OrderStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass
class OrderItem:
    id: str
    quantity: int


OrderStatus = Literal["not_started", "cooking", "cooked", "completed"]


class KFC:
    def __init__(self) -> None:
        self.base_url = os.getenv("KFC_PROVIDER_URL")

    def make_order(self, order_items: list[OrderItem]) -> dict:
        order_data = [item.__dict__ for item in order_items]
        response = httpx.post(f"{self.base_url}/api/orders", json={"order": order_data})
        response.raise_for_status()
        return response.json()

    def get_order(self, order_id: str) -> dict:
        response = httpx.get(f"{self.base_url}/api/orders/{order_id}")
        response.raise_for_status()
        return response.json()


kfc_provider = KFC()