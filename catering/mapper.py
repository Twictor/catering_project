from .enums import OrderStatus
from .providers import silpo, kfc, uber

RESTAURANT_EXTERNAL_TO_INTERNAL: dict[str, dict[str, OrderStatus]] = {
    "silpo": {
        silpo.OrderStatus.NOT_STARTED: OrderStatus.NOT_STARTED,
        silpo.OrderStatus.COOKING: OrderStatus.COOKING,
        silpo.OrderStatus.COOKED: OrderStatus.COOKED,        
    },
    "kfc": {
        kfc.OrderStatus.NOT_STARTED: OrderStatus.NOT_STARTED,
        kfc.OrderStatus.COOKING: OrderStatus.COOKING,
        kfc.OrderStatus.COOKED: OrderStatus.COOKED,        
    },
}


DELIVERY_EXTERNAL_TO_INTERNAL: dict[str, dict[str, OrderStatus]] = {
    "uber": {
        uber.DeliveryStatus.PENDING: OrderStatus.DELIVERY,
        uber.DeliveryStatus.PICKING_UP: OrderStatus.DELIVERY,
        uber.DeliveryStatus.IN_PROGRESS: OrderStatus.DELIVERY,
        uber.DeliveryStatus.DELIVERED: OrderStatus.DELIVERED,
        uber.DeliveryStatus.CANCELED: OrderStatus.NOT_DELIVERED, # Let's map this to a more generic "not delivered" status
    }
}