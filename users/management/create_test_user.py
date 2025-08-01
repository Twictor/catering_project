from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a test user and generates JWT token'

    def handle(self, *args, **options):
        email = "test_user@example.com"
        password = "very_secure_password_123"
        
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING("User already exists."))
            user = User.objects.get(email=email)
        else:
            user = User.objects.create_user(
                email=email,
                password=password,
                phone="+1234567890",
                first_name="Test",
                last_name="User"
            )
            self.stdout.write(self.style.SUCCESS(f"Created user: {user.email}"))

        token = AccessToken.for_user(user)
        self.stdout.write(self.style.SUCCESS(f"Auth successful. Token: {str(token)}"))

        decoded = token.payload
        self.stdout.write(f"Decoded token: {decoded}")