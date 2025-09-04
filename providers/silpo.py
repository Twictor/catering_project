import enum
from dataclasses import dataclass, asdict, field

import httpx


class OrderStatus:
    NOT_STARTED = "not_started"
    COOKING = "cooking"
    COOKED = "cooked"
    FINISHED = "finished"


@dataclass
class OrderItem:
    dish: str    
    quantity: str


@dataclass
class OrderResponse:
    id: str    
    status: OrderStatus
    
    
@dataclass
class OrderRequestBody:    
    order: list[OrderItem]



class Client:
    BASE_URL = "http://localhost:8001/api/orders"
    
    @classmethod
    def create_order(cls, order_body: OrderRequestBody):
        response: httpx.Response = httpx.post(
            cls.BASE_URL, json=asdict(order_body)
        )
        response.raise_for_status()
        return OrderResponse(**response.json())
    
    
    
    @classmethod
    def get_order(cls, order_id: str) -> OrderResponse:
        response: httpx.Response = httpx.get(          f"{cls.BASE_URL}/{order_id}"
        )
        response.raise_for_status()
        return OrderResponse(**response.json())