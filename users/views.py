from typing import Any
from django.contrib.auth.hashers import make_password
from rest_framework import viewsets, routers, permissions, serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import User


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


router = routers.DefaultRouter()
router.register(r"", UsersAPIViewSet, basename="user")