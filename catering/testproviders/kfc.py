import asyncio
import uuid
import random
import httpx

from typing import Literal
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel


OrderStatus = Literal["not_started", "cooking", "cooked", "completed"]
STORAGE: dict[str, OrderStatus] = {}
CATERING_API_WEBHOOK_URL = "https://localhost:8000/webhook/kfc"


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
        
        async with httpx.AsyncClient() as client:
            try:
                await client.post(
                    CATERING_API_WEBHOOK_URL, data={"id": order_id, "status": status}
                )
            except httpx.ConnectError as e:
                print("API connection failed")
            else:
                print(f"KFC: {CATERING_API_WEBHOOK_URL} notified about {status}")


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
    return STORAGE.get(order_id, {"error": "No such order found"})