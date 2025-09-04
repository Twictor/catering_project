
from dataclasses import dataclass, asdict, field
from time import sleep
from typing import Any

from config.celery import app as celery_app
from providers import uklon, silpo, kfc

from shared.cache import CacheService
from .data_classes import TrackingOrder
from .enums import OrderStatus
from .mapper import RESTAURANT_EXTERNAL_TO_INTERNAL
from .models import Order, OrderItem, Restaurant
from django.db.models import QuerySet


@dataclass
class TrackingOrder:
    """
    {
        17: {  // internal Order.id
            "restaurant": {
                "1": {  // internal restaurant id
                      status: NOT_STARTED, // internal
                      external_id: 13,
                      request_body: {...},
                },
                2: { // internal restaurant id
                    status: NOT_STARTED, // internal
                    external_id: 14,
                    request_body: {...},
                },
            },
            delivery: {
                status: NOT_STARTED, DELIVERY, DELIVERED 
                location: (..., ....)}
        },
        18: ...
    }
                
    """
    
    restaurants: dict = field(default_factory=dict)
    delivery_providers: dict = field(default_factory=dict)


def build_request_body(restaurant: Restaurant, items: QuerySet[OrderItem]) -> dict:
    """Builds a request body based on the restaurant."""
    if restaurant.name.lower() == "silpo":
        return {
            "items": [
                {"id": item.dish.external_id, "quantity": item.quantity}
                for item in items
            ]
        }
    elif restaurant.name.lower() == "kfc":
        return {
            "order": [
                {"dish": item.dish.name, "quantity": item.quantity} for item in items
            ]
        }
    return {}



def all_orders_cooked(order_id: int):
    """
    Checks if all parts of an order are cooked.
    If so, updates the main order status and triggers delivery.
    """
    from .models import Order  # Local import to prevent circular dependency

    cache = CacheService()
    tracking_order_data = cache.get(namespace="orders", key=str(order_id))

    if not tracking_order_data:
        print(f"No tracking order data found in cache for order_id: {order_id}")
        return

    tracking_order = TrackingOrder(**tracking_order_data)
    all_cooked = all(
        info["status"] == OrderStatus.COOKED.value
        for info in tracking_order.restaurants.values()
    )

    if all_cooked:
        print(f"All parts of order {order_id} are cooked. Updating status and starting delivery.")
        Order.objects.filter(pk=order_id).update(status=OrderStatus.COOKED)
        track_delivery.delay(order_id)
    else:
        print(f"Order {order_id} is not fully cooked yet. Current statuses: {tracking_order.restaurants}")


@celery_app.task(queue='default')
def order_delivery(order_id: int):
    '''
    Long polling requests to the delivery API
    get order from cache
    is external id
       no: make order
       yes: get order
    '''
    print(f"Starting delivery processing")

    provider = uklon.Client()
    cache = CasheService()
    order = Order.objects.get(pk=order_id)

    order_status = OrderStatus.DELIVERY_LOOKUP
    order.save()

    # prepare data for the first request
    addresses: list[str] = []
    comments: list[str] = []

    for rest_name, address in order.delivery_meta():
        addresses.append(f"{rest_name}, {address}")
        comments.append(f"Please deliver to {rest_name}")  
   
    #  NOTE: Only UKLON is currently supported so no selection in here
    order.status = Order.DELIVERY
    order.save()

    response: uklon.OrderResponse = provider.create_order(
        uklon.OrderRequestBody(
            adress=addresses,
            comment=comments,
            )
        )
    
    tracking_order = TrackingOrder(**cache.get(namespace="orders", key=str(order.pk)))
    tracking_order.delivery["status"] = OrderStatus.DELIVERY
    tracking_order.delivery["location"] = response.location

    current_status: uklon.OrderStaus = response.status

    while current_status != uklon.OrderStatus.DELIVERED:
        response = provider.get_order(response.id)

        print(f"Uklon [{response.status}]: {response.location}")

        if current_status == response.status:
            sleep(1)
            continue

        current_status = response.status  # DELIVERY, DELIVERED

        tracking_order.delivery["location"] = response.location

        # UPDATE CACHE WITH NEW STATUS
        cache.set("orders", str(order_id), asdict(tracking_order))
        print(f"Uklon [{response.status}]: {response.location}")

        # UPDETУ STORAGE
        order.objects.filter(pk=order_id).update(status=OrderStatus.DELIVERED)

        # update the cache
        tracking_order.delivery["status"] = OrderStatus.DELIVERED
        cache.set("orders", str(order_id), asdict(tracking_order))

        print("DONE with delivery")
        


@celery_app.task(queue='high_priority')
def order_in_silpo(order_id: int, items: QuerySet[OrderItem] = None):
    """Processes and tracks an order for the Silpo restaurant using short polling.

    This Celery task communicates with the Silpo API to manage a part of a larger order.
    It first checks the cache for an existing external order ID. If one is not found,
    it creates a new order with the provided items. It then repeatedly polls the
    Silpo API to get status updates. When the status changes, it updates the
    order's state in the cache. Once the order status becomes 'COOKED', it stops
    polling and calls `all_orders_cooked` to check if the entire multi-restaurant
    order is ready for the next stage (e.g., delivery).

    Args:
        order_id (int): The primary key of the internal `Order` being processed.
        items (QuerySet[OrderItem], optional): A QuerySet of `OrderItem` instances
            that belong to the Silpo portion of the order. This is used when
            creating the order for the first time. Defaults to None.

    Returns:
        None
    """
    client = silpo.Client()
    cache = CasheService()
    restaurant = Restaurant.objects.get(name="Silpo")
    order = Order.objects.get(pk=order_id)
    
    def get_internal_status(status: silpo.OrderStatus) -> OrderStatus:
        return RESTAURANT_EXTERNAL_TO_INTERNAL["silpo"][status]

    cooked = False
    while not cooked:
        sleep(1)
                
        tracking_order = TrackingOrder(
            **cache.get(namespace="order", key=str(order.pk))
        )
        silpo_order = tracking_order.restaurants.get(str(restaurant.pk))
        
        if not silpo_order:
            raise ValueError("No Silpo in order processing")

        # PRINT CURRENT STATUS
        print(f"CURRENT SILPO ORDER STATUS: {silpo_order['status']}")
        
        if not silpo_order["external_id"]:
            #  Make thу first request if not started
            response: silpo.OrderResponse = client.create_order(
                silpo.OrderRequestBody(
                    order=[
                        silpo.OrderItem(dish=item.dish.name, quantity=item.quantity)
                        for item in items
                    ]
                    )
            )
            internal_status: OrderStatus = get_internal_status(response.status)

            tracking_order.restaurants[str(restaurant.pk)] = {
                "external_id": response.id,
                "status": internal_status
            }

        # Update cache
            cache.set(
                namespace="order", 
                key=str(order.pk), 
                value=asdict(tracking_order)
                )
        else:
            # IF ALREADY HAVE EXTERNAL ID - JUST RETRIVE THE ORER
            # PASS EXTERNAL SILPO ORDER
            response = client.get_order(silpo_order["external_id"])
            internal_status = get_internal_status(response.status)
            print("Tracking for Silpo Order with HTTP GET /orders")
            
            if silpo_order["status"] != internal_status:
                tracking_order.restaurants[str(restaurant.pk)]["status"] = internal_status
                cache.set(
                    namespace="orders", 
                    key=str(order_id), 
                    value=asdict(tracking_order)
                )
            if internal_status == OrderStatus.COOKED:
                cooked = True
                all_orders_cooked(order.pk)


@celery_app.task(queue='high_priority')
def order_in_kfc(order_id: int, items):
    client = kfc.Client()
    cache = CasheService()
    restaurant = Restaurant.objects.get(name="KFC")

    def get_internal_status(status: kfc.OrderStatus) -> OrderStatus:
        return RESTAURANT_EXTERNAL_TO_INTERNAL["kfc"][status]

    # GER TRACKING ORDER FROM CACHE
    tracking_order = TrackingOrder(
        **cache.get(namespace="orders", key=str(order_id))
    )

    response: kfc.OrderResponse = client.create_order(
        kfc.OrderRequestBody(
            order=[
                kfc.OrderItem(dish=item.dish.name, quantity=item.quantity)
                for item in items
            ]
        )
    )
    internal_status = get_internal_status(response.status)

    #  UPDATE CACHE WITH EXTERNAL ID AND STATE
    tracking_order.restaurants[str(restaurant.pk)] = {
        "external_id": response.id,
        "status": internal_status,
    }

    print(f"Created KFC Order. External ID: {response.id}, Status: {internal_status}") 
    cache.set(
        namespace="orders", 
        key=str(order_id), 
        value=asdict(tracking_order)
    )
    # SAVE ANOTHER ITEM FORM MAPPING TO THE INTERNAL ORDER

    cache.set(
        namespace="kfc_orders",
        key=str(response.id),
        value={
            "internal_order_id": order_id,            
        }
    )

    
def build_request_body(restaurant, items):
    # Logic to build the request body for the specific restaurant
    pass


def schedule_order(order: Order):
    # Logic to schedule order processing
    cache = CasheService()
    tracking_order = TrackingOrder()
    
    items_by_restaurant = order.items_by_restaurant()
    for restaurant, items in items_by_restaurant.items():
        tracking_order.restaurants[str(restaurant.pk)] = {
            "external_id": None,
            "status": OrderStatus.NOT_STARTED,
            "request_body": build_request_body(restaurant, items)
        }



    cache.set(namespace="order", 
              key=str(order.pk), 
              value=asdict(tracking_order))

    
    for restaurant, items in items_by_restaurant.items():
        match restaurant.name.lower():
            case "silpo":
                order_in_silpo.delay(order.pk, items)
                # order_in_silpo.apply_async()
            case "kfc":
                order_in_kfc.delay(order.pk, items)
            case _:
                # It's good practice to have a default case
                print(f"Unknown restaurant: {restaurant.name}")
