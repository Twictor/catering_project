import asyncio
import uuid
import random

from typing import Literal
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel


OrderStatus = Literal["not_started", "cooking", "cooked", "completed"]
STORAGE: dict[str, OrderStatus] = {}


app = FastAPI()


class OrderItem(BaseModel):
    dish: str
    quantity: int

class OrderRequestBody(BaseModel):
    order: list[OrderItem]
    

async def update_order_status(order_id: str):
    ORDER_STATUSES: tuple[OrderStatus,...] = ("cooking", "cooked", "completed")
    for status in ORDER_STATUSES:
        await asyncio.sleep(random.uniform(1,2))
        STORAGE[order_id] = status


@app.post("/api/orders")
async def make_order(body: OrderRequestBody, background_tasks: BackgroundTasks):
    print(body)
    
    order_id = str(uuid.uuid4())
    STORAGE[order_id] = "not_started"
    background_tasks.add_task(update_order_status, order_id)
    
    return {
        "order_id": order_id,
        "status": STORAGE[order_id],
        "message": "Order has been placed and is being processed."
    }

@app.get("/api/orders/{order_id}")
async def get_orders(order_id: str):
    return {"id": order_id, "status": STORAGE.get(order_id)}