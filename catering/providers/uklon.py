import enum
from dataclasses import dataclass, asdict

import httpx


class OrderStatus:
    NOT_STARTED = "not_started"
    DELIVRY = "delivery"
    DELIVERED = "delivered"    


@dataclass
class OrderRequestBody:    
    adress: list[str]
    comment: list[str]

@dataclass
class OrderResponse:
    id: str    
    status: OrderStatus
    location: tuple[float, float]
    adress: list[str]
    comment: list[str]



class Client:
    BASE_URL = "http://localhost:8003/drivers/orders"
    
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