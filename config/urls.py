from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework.routers import DefaultRouter
from catering.views import FoodAPIViewSet, kfc_webhook, UberWebhook
from users.views import activate_user

router = DefaultRouter()
router.register(r'food', FoodAPIViewSet, basename='food')

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(router.urls)),
    path("api/kfc/webhook/", kfc_webhook, name="kfc_webhook"),
    path("api/uber/webhook/", UberWebhook.as_view(), name="uber_webhook"),
    path('activate/<str:activation_key>/', activate_user, name='activate_user'),
    path('api/users/', include('users.urls')),
    path('api/catering/', include('catering.urls')),
]

if settings.DEBUG:
    urlpatterns += [
        # Your stuff: custom schema view
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        # Optional UI:
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]
