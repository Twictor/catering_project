import uuid
from django.core.cache import cache
from django.conf import settings
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)

def generate_activation_key(user):
    key = uuid.uuid4().hex
    cache_key = f"activation_key:{user.id}"
    try:
        cache.set(cache_key, key, settings.ACTIVATION_KEY_EXPIRATION_TIME)
    except Exception as e:
        logger.error(f"Error saving activation key to cache: {e}")
    print(f"Generated activation key: {key} for user {user.id}")  # Add this line
    return key

def send_activation_email(user, activation_key):
    subject = "Activate your account"
    message = f"Please click the following link to activate your account: http://localhost:8000/users/activate/{activation_key}"  # adjust url

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
