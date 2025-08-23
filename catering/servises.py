
from dataclasses import dataclass, field, asdict
from .models import Order
from .cashe import CasheService
from .data_classes import TrackingOrder
from .enums import OrderStatus
from .tasks import order_in_silpo, order_in_kfc
from .models import Order, Restaurant, OrderItem
from django.db.models import QuerySet
from .shared.cache import CasheService
from config.celery import app as celery_app
from celery import shared_task

from .enums import OrderStatus
from .providers import silpo
from time import sleep
from .mapper import RESTAURANT_EXTERNAL_TO_INTERNAL


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
            delivery: {...}
        },
        18: ...
    }
                
    """
    
    restaurants: dict = field(default_factory=dict)
    delivery_providers: dict = field(default_factory=dict)


def all_orders_cooked(order_id: int) -> bool:
    cashe = CasheService()
    tracking_order = TrackingOrder(**cashe.get(namespace="orders", key=str(order_id)))
    print(f"Cheking if all orders are cooked: {tracking_order.restaurants}")

    result = all(
        payload["status"] == OrderStatus.COOKED
        for _, payload in tracking_order.restaurants.items()
    )
    return result

@celery_app.task(queue='high_priority')
def order_in_silpo(order_id: int, items: QuerySet[OrderItem] = None):
    '''
    Short polling requests to the Silpo API
    get order from cache
    is external id
       no: make order
       yes: get order
    '''
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
                print("Order is cooked")
                cooked = True
                
                                          
                # CHEK IF ALL ORDERS ARE COOKED
                if all_orders_cooked(order_id):
                    cache.set(
                        namespace="orders",
                        key=str(order_id),
                        value=asdict(tracking_order)
                    )

                # TODO  UPDATE DATABASE INSTANCE
    try:
        internal_status = get_internal_status(response.status)
        print(f"internal_status = {internal_status}")

        if internal_status == "success":
            order.status = Order.DELIVERED
        else:
            order.status = Order.FAILED
        order.save()
        return True
    except Exception as e:
        print(f"Error processing order {order.id}: {e}")
        return False

@celery_app.task(queue='high_priority')
def order_in_kfc(order_id: int, items):
    breakpoint() # TODO: Remove
    return


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



    cache.set(namespace="order", key=str(order.pk), value=asdict(tracking_order))

    
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
