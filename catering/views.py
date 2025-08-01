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

from django.shortcuts import get_object_or_404
from .enums import OrderStatus
from rest_framework import viewsets, serializers, routers, status, permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.db.models import Prefetch
from users.models import Role, User
from .models import Restaurant, Dish, Order, OrderItem
import logging

logger = logging.getLogger(__name__)


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
    
    

class FoodAPIViewSet(viewsets.GenericViewSet):
    @action(methods=["get"], detail=False, permission_classes=[AllowAny])
    def dishes(self, request: Request) -> Response:
        logger.info("Dishes endpoint was hit!")
        logger.info(f"Dishes endpoint called. Authorization header: {request.headers.get('Authorization')}")
        """
        Retrieve all dishes grouped by restaurant.
        """
        restaurants = Restaurant.objects.prefetch_related(
            Prefetch('dishes', queryset=Dish.objects.all())
        ).all()
        serializer = RestaurantSerializer(restaurants, many=True)
        return Response(data=serializer.data)

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

        assert isinstance(request.user, User)

        order = Order.objects.create(
            status="OrderStatus.NOT_STARTED",
            user=request.user,
            delivery_provider="Uklon",
            eta=serializer.validated_data["eta"],
        )

        items = serializer.validated_data["items"]
        total = 0

        for dish_order in items:
            instance = OrderItem.objects.create(
                dish=dish_order["dish"],
                quantity=dish_order["quantity"],
                order=order
            )
            total += instance.dish.price * instance.quantity
            print(f"New Dish Order Item is created: {instance.pk}")

        order.total = total
        order.save()

        print(f"New Food Order is created: {order.pk}. ETA: {order.eta}")

        # TODO: Run scheduler

        return Response(OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )

    @action(methods=["get"], detail=False, url_path=r"orders/(?P<id>\d+)", permission_classes=[IsAuthenticated])
    def retrieve_order(self, request: Request, id: int) -> Response:
        """
        Retrieve a specific order by its ID.
        """
        order = get_object_or_404(Order, id=id)        
        serializer = OrderSerializer(order)        
        return Response(data=serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Add permission class if needed
def providers(request):
    providers = DeliveryProvider.objects.all()
    serializers = DeliveryProviderSerializer(providers, many=True)
    return Response({"providers": serializers.data })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def active_deliveries(request):
    deliveries = Delivery.objects.filter(status=DeliveryStatus.ACTIVE)
    serializers = DeliverySerializer(deliveries, many=True)
    return Response({"active_deliveries": serializers.data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def archived_orders(request):
    orders = Order.objects.filter(status=OrderStatus.ARCHIVED)
    serializers = OrderSerializer(orders, many=True)
    return Response({"archived_orders": serializers.data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def active_orders(request):
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

router = routers.DefaultRouter()
router.register(prefix="", viewset=FoodAPIViewSet, basename="food")