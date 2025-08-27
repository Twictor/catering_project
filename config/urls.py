from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView
)
from users.views import router as users_router
from catering.views import router as catering_router
from catering.views import kfc_webhook


urlpatterns = [
    path("admin/", admin.site.urls),
    path('auth/token/', TokenObtainPairView.as_view(), name='obtain_token'),
    path("users/", include("users.urls")),  # This line is important
    path("catering/", include(catering_router.urls)),
    path("food/", include("catering.urls")),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "webhooks/kfc/635179a5-caaa-41f8-84cc-ca5a40ee7044/", 
        kfc_webhook, 
        name="kfc_webhook",
        ),
    path('api/v1/', include('users.urls')),
    path('api/v1/catering/', include('catering.urls')),
]