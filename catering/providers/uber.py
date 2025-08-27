import httpx
from django.conf import settings
import logging
from enum import Enum


class DeliveryStatus(str, Enum):
    """
    Represents the possible statuses of a delivery from Uber.
    """
    PENDING = "pending"
    PICKING_UP = "picking_up"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    CANCELED = "canceled"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


logger = logging.getLogger(__name__)

async def create_uber_delivery(order_id: str, webhook_url: str):
    """
    Calls the Uber mock provider to start a delivery simulation.
    """
    uber_provider_url = settings.UBER_PROVIDER_URL
    if not uber_provider_url:
        logger.error("UBER_PROVIDER_URL is not configured in settings.")
        return None

    api_url = f"{uber_provider_url}/deliveries"
    payload = {
        "order_id": str(order_id),
        "webhook_url": webhook_url,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload, timeout=10.0)
            response.raise_for_status()  # Raise an error for bad responses
            
            response_data = response.json()
            logger.info(f"Successfully created Uber delivery for order {order_id}. Response: {response_data}")
            return response_data

    except httpx.RequestError as e:
        logger.error(f"Error calling Uber provider for order {order_id}: {e}")
        return None