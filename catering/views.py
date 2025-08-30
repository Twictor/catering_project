
"""
=====================================
CREATE ORDER FLOW
=====================================
>>> HTTP Request
{
    "items": [
        {
            "dish": 3,
            "quantity": 2,
        },
        {
            "dish": 4,
            "quantity": 1,
        },
    ],
    "eta": "2025-07-10"
}

<<< HTTP Response
{
    "items": [
        {
            "dish": 3,
            "quantity": 2,
        },
        {
            "dish": 4,
            "quantity": 1,
        },
    ],
    "eta": "2025-07-10"
    "id": 10,
    "status": "not_started"
}
"""

import logging
import json
from datetime import datetime
from dataclasses import asdict
from typing import Any

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets, routers, pagination, permissions, serializers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Prefetch
from celery import shared_task

from users.models import Role, User
from .enums import OrderStatus
from .models import Restaurant, Dish, Order, OrderItem
from .pagination import DishesPagination
from .serializers import (
    RestaurantSerializer,
    CreateDishSerializer,
    OrderCreateSerializer,
    OrderSerializer,
)
from .tasks import schedule_order, process_kfc_webhook_data
from .shared.cache import CacheService
from .data_classes import TrackingOrder
from .mapper import DELIVERY_EXTERNAL_TO_INTERNAL
from .providers import uber


logger = logging.getLogger(__name__)


class DishPagination(PageNumberPagination):
    page_size = 10  # Number of items per page
    page_size_query_param = 'page_size'  # Parameter for changing the number of items on the page
    max_page_size = 100

class DishesPagination(pagination.LimitOffsetPagination):
    default_limit = 10
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 100

class DishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        exclude = ["restaurant"]
        fields = ["id", "name", "price"]


class CreateDishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        fields = ['name', 'price', 'restaurant']
        

class RestaurantSerializer(serializers.ModelSerializer):
    dishes = DishSerializer(many=True)

    class Meta:
        model = Restaurant
        fields = "__all__"


class OrderItemSerializer(serializers.Serializer):
    dish = serializers.PrimaryKeyRelatedField(queryset=Dish.objects.all())
    quantity = serializers.IntegerField(min_value=1, max_value=20)
    


class OrderSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    status = serializers.ChoiceField(OrderStatus.choices(), read_only=True)
    eta = serializers.DateField()
    total = serializers.IntegerField(min_value=1, read_only=True)     
    
    
class OrderCreateSerializer(serializers.Serializer):    
    items = OrderItemSerializer(many=True)
    eta = serializers.DateField()
    

class UberWebhookSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=uber.DeliveryStatus.choices(), required=False)
    location = serializers.CharField(required=False) # Assuming location is a string for simplicity


class UberWebhook(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = UberWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data
        order_id = validated_data["order_id"]
        external_status = validated_data.get("status")
        location = validated_data.get("location")

        try:
            internal_status = DELIVERY_EXTERNAL_TO_INTERNAL["uber"][external_status]
            
            order = Order.objects.get(pk=order_id)
            order.status = internal_status
            order.save(update_fields=["status"])

            # Update cache
            cache = CacheService()
            tracking_order_data = cache.get(namespace="orders", key=str(order.pk))
            if tracking_order_data:
                tracking_order = TrackingOrder(**tracking_order_data)
                tracking_order.delivery["status"] = internal_status
                cache.set("orders", str(order.pk), asdict(tracking_order))

            logger.info(f"Uber webhook: Order {order_id} status updated to {internal_status}")
            return Response(status=status.HTTP_200_OK)

        except (Order.DoesNotExist, KeyError) as e:
            logger.error(f"Error processing Uber webhook for order {order_id}: {e}")
            return Response(status=status.HTTP_400_BAD_REQUEST)


class FoodAPIViewSet(viewsets.ViewSet):
    pagination_class = DishPagination # Add this line
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['dishes__name'] # Search by dish name
    
    @action(methods=["get"], detail=False, url_path="restaurants")
    def all_restaurants(self, request: Request) -> Response:
        """
        Get all restaurants with pagination.
        """
        queryset = Restaurant.objects.all()
        paginator = DishesPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = RestaurantSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(methods=["get"], detail=False, permission_classes=[permissions.IsAdminUser])
    def dishes(self, request: Request) -> Response:
        logger.info("Dishes endpoint was hit!")
        logger.info(f"Dishes endpoint called. Authorization header: {request.headers.get('Authorization')}")
        """
        Retrieve all dishes grouped by restaurant.
        """
        queryset = Restaurant.objects.prefetch_related(
            Prefetch(
                'dishes',
                queryset=Dish.objects.all()
            )
        ).all()

        search_term = request.query_params.get('name', None)
        if search_term:
            queryset = Restaurant.objects.filter(dishes__name__icontains=search_term).prefetch_related(
                Prefetch(
                    'dishes',
                    queryset=Dish.objects.filter(name__icontains=search_term)
                )
            ).distinct()

        paginator = DishesPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = RestaurantSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(methods=["post"], detail=False, url_path="dishes", permission_classes=[IsAdminUser])
    def create_dish(self, request: Request) -> Response:
        """
        Create a new dish. Only available for admin users.
        """
        logger.info(f"User role: {request.user.role}")
        if request.user.role != Role.ADMIN:
            return Response({"error": "Only admin users can create dishes."}, 
                            status=status.HTTP_403_FORBIDDEN)

        serializer = CreateDishSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["post"], detail=False, url_path="orders", 
            permission_classes=[IsAuthenticated])
    def create_order(self, request: Request) -> Response:
        """
        Create a new order for the authenticated user.
        """
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        items = validated_data["items"]
        eta = validated_data["eta"]

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                status=OrderStatus.NOT_STARTED,
                eta=eta,
            )

            total_price = 0
            order_items = []
            for item_data in items:
                dish = item_data["dish"]
                quantity = item_data["quantity"]
                total_price += dish.price * quantity
                order_items.append(
                    OrderItem(order=order, dish=dish, quantity=quantity)
                )

            OrderItem.objects.bulk_create(order_items)
            order.total = total_price
            order.save()

        schedule_order.delay(order.pk)

        response_serializer = OrderSerializer(order)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=["get"], detail=True, url_path="orders", 
            permission_classes=[IsAuthenticated])
    def get_order(self, request: Request, pk: int = None) -> Response:
        """
        Get a specific order by its ID.
        """
        order = get_object_or_404(Order, pk=pk, user=request.user)
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path="orders", 
            permission_classes=[IsAuthenticated])
    def list_orders(self, request: Request) -> Response:
        """
        List all orders for the authenticated user.
        """
        orders = Order.objects.filter(user=request.user)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


    @action(methods=["get", "post" ], detail=False, url_path=r"orders/(?P<id>\d+)")
    def orders(self, request: Request, id: int) -> Response:
        if request.method == "POST":
            # Handle POST request for creating a new order
            return self.create_order(request)
        else:
            # Handle GET request for retrieving an existing order
            return self.all_orders(request, id)

    @action(methods=["post"], detail=False, url_path=r"webhooks/kfc/")
    def kfc_webhook(self, request: Request) -> Response:
        """
        Handle KFC webhook notifications.
        """
        data = request.data
        process_kfc_webhook_data.delay(data)
        return Response({"message": "Webhook received"})


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])  # Add permission class if needed
# def providers(request):
#     providers = DeliveryProvider.objects.all()
#     serializers = DeliveryProviderSerializer(providers, many=True)
#     return Response({"providers": serializers.data })


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def active_deliveries(request):
#     deliveries = Delivery.objects.filter(status=DeliveryStatus.ACTIVE)
#     serializers = DeliverySerializer(deliveries, many=True)
#     return Response({"active_deliveries": serializers.data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def archived_orders(request):
    # The 'ARCHIVED' status does not exist in your OrderStatus enum yet.
    # This will cause an error later. For now, we leave it to fix the current import error.
    orders = Order.objects.filter(status=OrderStatus.ARCHIVED)
    serializers = OrderSerializer(orders, many=True)
    return Response({"archived_orders": serializers.data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def active_orders(request):
    # The 'ACTIVE' status does not exist in your OrderStatus enum yet.
    # This will cause an error later. For now, we leave it to fix the current import error.
    orders = Order.objects.filter(status=OrderStatus.ACTIVE)
    serializers = OrderSerializer(orders, many=True)
    return Response({"active_orders": serializers.data})

@api_view(['POST'])  # Assuming it's a POST request
@permission_classes([IsAuthenticated])
def ship(request, provider, order_id):
    shipment = get_object_or_404(Order, id=order_id)
    if shipment.status != OrderStatus.NOT_STARTED:
        return Response({"error": "Order is not in a state that can be shipped."}, status=status.HTTP_400_BAD_REQUEST)
    # TODO: Implement shipping logic
    return Response({"message": f"Shipping order {order_id} via {provider}"})

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

@shared_task(queue='high_priority')
def process_order_in_background(order_id):
    # Your order processing logic here
    logger.info(f"Processing order {order_id} in the background.")
    # Example: Change order status
    try:
        order = Order.objects.get(id=order_id)
        order.status = OrderStatus.COOKING
        order.save()
        logger.info(f"Order {order_id} status updated to COOKING.")
    except Order.DoesNotExist:
        logger.error(f"Order with id {order_id} not found.")


@api_view(["POST"])
@permission_classes([])
def kfc_webhook(request: Request):
    """
    This is a webhook for KFC provider
    """
    process_kfc_webhook_data.delay(request.data)
    return JsonResponse({}, status=200)


class FoodAPIViewSet(viewsets.ViewSet):
    def dishes(self, request):
        return Response({"message": "Dishes endpoint"})


@api_view(['GET'])
def active_deliveries(request):
    return JsonResponse({"message": "Active deliveries endpoint"})

@api_view(['GET'])
def archived_orders(request):
    return JsonResponse({"message": "Archived orders endpoint"})

@api_view(['GET'])
def active_orders(request):
    return JsonResponse({"message": "Active orders endpoint"})

@api_view(['POST'])
def ship(request, provider, order_id):
    return JsonResponse({"message": f"Shipping order {order_id} with {provider}"})


@api_view(['GET'])
def providers(request):    
    return JsonResponse({"message": "Providers endpoint is active"})

@csrf_exempt   
def kfc_webhook(request):
    """Process KFC Order webhooks"""
    data: dict = json.loads(json.dumps(request.POST))

    cache = CacheService()
    restaurant = Restaurant.objects.get(name="kfc")
    kfc_cahe_order = cache.get("kfc_orders", key=data["id"])

    # get internal order from mapping
    # add logging if order wasn't found
    order: Order = Order.objects.get(id=kfc_cahe_order["internal_order_id"])
    tracking_order = TrackingOrder(**cache.get(namespace="orders", key=str(order.pk)))
    tracking_order.restaurants[str(restaurant.pk)] |= {
        "external_id": data["id"],
        "status": OrderStatus.COOKED,
    
    }
    
    cache.set(
        namespace="orders", 
        key=str(order.pk), 
        value=asdict(tracking_order)
    )

    all_orders_cooked(order.pk)
    #     # because KFC return webhok only when order is cooked
    #     order.status = OrderStatus.COOKED
    #     order.save()
    #     print("All orders are cooked")
    # else:
    #     print("Not all orders are cooked yet")

    # print(f"KFC Webhook received data: {data}")

    return JsonResponse({"message": "ok from GitHub Actions!"})

router = routers.DefaultRouter()
router.register(r'food', FoodAPIViewSet, basename='food')
