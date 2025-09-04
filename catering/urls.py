from django.urls import path
from . import views

urlpatterns = [
    path("active_deliveries/", views.active_deliveries, name="active_deliveries"),
    path("archived_orders/", views.archived_orders, name="archived_orders"),
    path("active_orders/", views.active_orders, name="active_orders"),
    path("ship/<str:provider>/<uuid:order_id>/", views.ship, name="ship"),
    path('webhooks/uber/', views.UberWebhook.as_view(), name='uber-webhook'),
]
