import asyncio
import uuid
import random

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, Field


ORDER_STATUSES = ("not_started", "delivery", "delivered")
STORAGE: dict[str, dict] = {}


app = FastAPI()


class OrderRequestBody(BaseModel):
    address: list[str] = Field(min_length=1)
    comments: list[str] = Field(min_length=1)
    

async def delivery(order_id: str):
    for _ in range(5):
        STORAGE[order_id]["location"] = (random.random(), random.random())
        
    for address in STORAGE[order_id]["address"]:
        await asyncio.sleep(1)
        for _ in range(5):
            STORAGE[order_id]["location"] = (random.random(), random.random())
            await asyncio.sleep(0.5)
            
        print(f"Delivered to {address}")
        
async def update_order_status(order_id: str):
    start_location = (random.random(), random.random())

    for status in ORDER_STATUSES[1:]:
        STORAGE[order_id]["location"] = (random.random(), random.random())
        await asyncio.sleep(random.uniform(1,2))
        
        
        if status == "delivery":
            await delivery(order_id)
            
        STORAGE[order_id]["status"] = status
        print(f"UKLON: [{order_id}] --> {status}")


@app.post("/driver/orders")
async def make_order(body: OrderRequestBody, background_tasks: BackgroundTasks):
    print(body)
    order_id = str(uuid.uuid4())
    STORAGE[order_id] = {
        "id": order_id,
        "status": "not_started",
        "location": (random.random(), random.random()),
        "address": body.address,
        "comments": body.comments
    }
    background_tasks.add_task(update_order_status, order_id)

    return STORAGE.get(order_id, {"error": "No such order found"})

@app.get("/driver/orders/{order_id}")
async def get_orders(order_id: str):
    return STORAGE.get(order_id, {"error": "No such order found"})