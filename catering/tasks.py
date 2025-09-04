import logging
import json
from celery import shared_task
from shared.cache import CacheService
from .servises import all_orders_cooked
from .mapper import RESTAURANT_EXTERNAL_TO_INTERNAL
from .data_classes import TrackingOrder
from .enums import OrderStatus


logger = logging.getLogger(__name__)


@shared_task(queue='high_priority')
def process_kfc_webhook_data(data: dict):
    """
    Processes webhook data from KFC, updates order status in cache,
    and checks if the entire order is ready for delivery.
    """
    logger.info(f"Processing KFC webhook data: {data}")
    cache = CacheService()
    
    external_order_id = data.get("id")
    external_status = data.get("status")

    if not external_order_id or not external_status:
        logger.error(f"Invalid data received in KFC webhook: {data}")
        return

    # --- Optimized search ---
    # Get internal order ID directly from cache
    order_info_json = cache.get("external_to_internal_map", str(external_order_id))
    if not order_info_json:
        logger.warning(f"Could not find internal order for KFC external_id: {external_order_id}")
        return

    order_info = json.loads(order_info_json)
    internal_order_id = order_info.get("order_id")
    internal_restaurant_id = order_info.get("restaurant_id")
    # --- End of optimized search ---
            
    if not internal_order_id:
        logger.warning(f"Could not find internal order for KFC external_id: {external_order_id}")
        return

    # Update the status in the cache
    tracking_order_dict = cache.get("orders", str(internal_order_id))
    if not tracking_order_dict:
        logger.error(f"Tracking data for order {internal_order_id} not found in cache.")
        return
        
    tracking_order = TrackingOrder(**tracking_order_dict)

    internal_status = RESTAURANT_EXTERNAL_TO_INTERNAL["kfc"][external_status]
    # Ensure restaurant_id is a string, as in TrackingOrder
    tracking_order.restaurants[str(internal_restaurant_id)]["status"] = internal_status
    
    cache.set("orders", str(internal_order_id), tracking_order.to_dict())
    logger.info(f"Updated order {internal_order_id} for restaurant {internal_restaurant_id} to status {internal_status}")

    # Check if all parts of the order are cooked
    all_orders_cooked(internal_order_id)


@shared_task(queue='high_priority')
def process_order(order_id):
    from .models import Order
    order = Order.objects.get(pk=order_id)
    logger.info(f"Processing order {order.id}")
    # TODO:
    order.status = OrderStatus.ACTIVE
    order.save()
    logger.info(f"Order {order.id} processed successfully")


# You can add other tasks like schedule_order here if they exist
@shared_task
def schedule_order(order_id: int):
    # Placeholder for schedule_order logic if needed
    logger.info(f"Scheduling order {order_id}")
    pass

