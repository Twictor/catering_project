from typing import Any
from django.contrib.auth.hashers import make_password
from rest_framework import viewsets, routers, permissions, serializers, generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from .models import User
from .serializers import UserSerializer
from .utils import generate_activation_key, send_activation_email
import uuid
from django.conf import settings
from rest_framework.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "first_name",
            "last_name",
            "password",
            "role",
        ]

    def validate(self, attrs: dict[str, Any]):
        """Change the password for its hash to make Token-based authentication available."""

        attrs["password"] = make_password(attrs["password"])

        return super().validate(attrs=attrs)


class UsersAPIViewSet(viewsets.GenericViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """Return appropriate permissions based on the action."""
        if self.action == 'create':
            return [permissions.AllowAny()]  
        return super().get_permissions()  

    def list(self, request: Request):
        return Response(UserSerializer(request.user).data, status=200)

    def create(self, request: Request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(serializer.instance).data, status=201)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        logger.info(f"User created with id: {user.id}")  
        user.is_active = False  
        user.save()
        activation_key = generate_activation_key(user)
        logger.info(f"Activation key generated: {activation_key}")  
        send_activation_email(user, activation_key)
        
        # Store activation key in cache
        cache_key = f"activation_key:{user.id}"
        cache.set(cache_key, activation_key, timeout=settings.ACTIVATION_KEY_EXPIRATION_TIME)
        logger.info(f"Activation key saved to cache with key: {cache_key}")  

        return Response(
            {"message": "User registered successfully. Check your email to activate your account."},
            status=status.HTTP_201_CREATED,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def activate_user(request, activation_key):
    cache_key_prefix = "activation_key:"
    for user_id in cache.iter_keys(cache_key_prefix + "*"):
        cache_key = user_id
        cached_key = cache.get(cache_key)

        if cached_key == activation_key:
            user_id = cache_key.split(":")[1]
            user = get_object_or_404(User, pk=user_id)
            user.is_active = True
            user.save()
            cache.delete(cache_key)
            return Response({"message": "User activated successfully."}, status=status.HTTP_200_OK)

    return Response({"error": "Invalid activation key."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def resend_activation_email(request):
    email = request.data.get("email")
    if not email:
        return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

    if user.is_active:
        return Response({"message": "User is already active."}, status=status.HTTP_200_OK)

    activation_key = generate_activation_key(user)
    print("Sending activation email...") 
    send_activation_email(user, activation_key)

    return Response({"message": "Activation email resent successfully."}, status=status.HTTP_200_OK)


router = routers.DefaultRouter()
router.register(r"", UsersAPIViewSet, basename="user")