
from celery import shared_task
from celery.utils.log import get_task_logger

from .enums import OrderStatus

logger = get_task_logger(__name__)


@shared_task(queue='high_priority')
def process_order(order_id):
    from .models import Order
    order = Order.objects.get(pk=order_id)
    logger.info(f"Processing order {order.id}")
    # TODO:
    order.status = OrderStatus.ACTIVE
    order.save()
    logger.info(f"Order {order.id} processed successfully")


@shared_task(queue='high_priority')
def process_kfc_webhook_data(data):
    logger.info(f"Processing KFC webhook data: {data}")
    # TODO:
    pass

def schedule_order(order):
    """
    Helper function to schedule order processing.
    """
    process_order.delay(order.id)

# TODO: Add other tasks like order_in_silpo, order_in_kfc, schedule_order if they exist
