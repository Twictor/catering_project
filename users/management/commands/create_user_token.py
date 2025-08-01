import os
import django
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from django.core.exceptions import ObjectDoesNotExist


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


django.setup()

User = get_user_model()


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class Command(BaseCommand):
    help = 'Creates a test user and generates JWT token'

    def handle(self, *args, **options):
        email = "test_user@example.com"
        password = "very_secure_password_123"

        logger.info(f"Checking if user {email} exists...")
        try:
            user = User.objects.get(email=email)
            logger.info("User already exists.")
        except ObjectDoesNotExist:
            logger.info(f"Creating user {email}...")
            try:
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    phone="+1234567890",
                    first_name="Test",
                    last_name="User"
                )
                logger.info(f"Created user: {user.email}")
            except Exception as e:
                logger.error(f"Error creating user: {e}")
                return

        try:
            logger.info("Generating token...")
            token = AccessToken.for_user(user)
            logger.info(f"Auth successful. Token: {str(token)}")

            logger.info("Decoding token...")
            decoded = token.payload
            logger.info(f"Decoded token: {decoded}")

        except Exception as e:
            logger.error(f"Error generating or decoding token: {e}")
