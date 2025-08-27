import asyncio
import random

import httpx
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class DeliveryRequest(BaseModel):
    order_id: str
    webhook_url: HttpUrl


async def send_location_updates(order_id: str, webhook_url: str):
    """
    Simulates sending location updates every second.
    """
    print(f"Uber Provider: Starting to send updates for order {order_id} to {webhook_url}")

    # Simulate 10 delivery steps
    for _ in range(10):
        await asyncio.sleep(1)
        location = {
            "lat": round(random.uniform(49.83, 49.85), 6),
            "lon": round(random.uniform(24.01, 24.03), 6),
        }
        payload = {"order_id": order_id, "location": location, "status": "in_progress"}
        try:
            async with httpx.AsyncClient() as client:
                await client.post(webhook_url, json=payload, timeout=5.0)
            print(f"Uber Provider: Update sent for order {order_id}")
        except httpx.RequestError as e:
            print(f"Uber Provider: Error sending update for order {order_id}: {e}")

    # Send final status after completion
    await asyncio.sleep(1)
    try:
        async with httpx.AsyncClient() as client:
            payload = {"order_id": order_id, "status": "delivered"}
            await client.post(webhook_url, json=payload, timeout=5.0)
        print(f"Uber Provider: Delivery for order {order_id} completed.")
    except httpx.RequestError as e:
        print(f"Uber Provider: Error sending final status for order {order_id}: {e}")


@app.post("/deliveries")
async def create_delivery(
    delivery_request: DeliveryRequest, background_tasks: BackgroundTasks
):
    """
    API endpoint to start delivery simulation.
    Accepts order ID and webhook URL.
    """
    external_id = f"uber-{random.randint(1000, 9999)}"
    print(f"Uber Provider: Received delivery request for order {delivery_request.order_id}. External ID: {external_id}")

    background_tasks.add_task(
        send_location_updates, delivery_request.order_id, str(delivery_request.webhook_url)
    )
    return {"message": "Delivery simulation started", "external_id": external_id}