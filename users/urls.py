from .views import activate_user, resend_activation_email, RegisterView
from django.urls import path
urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("activate/<str:activation_key>/", activate_user, name="activate"),  # This line is important
    path("resend_activation_email/", resend_activation_email, name="resend_activation_email"),
]