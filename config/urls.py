from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
)
from users.views import router as users_router
from catering.views import router as catering_router


urlpatterns = [
    path("admin/", admin.site.urls),
    path('auth/token/', TokenObtainPairView.as_view(), name='obtain_token'),
    path("users/", include(users_router.urls)),
    path("catering/", include(catering_router.urls))
]