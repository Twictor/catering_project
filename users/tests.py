from django.urls import reverse
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import User
import time
from django.core import mail
from django.conf import settings
from django.utils import timezone
import datetime
from users.utils import generate_activation_key # Импортируем функцию generate_activation_key
from django.dispatch import receiver
from django.db.models.signals import post_save


class UserActivationTest(APITestCase):
    def test_user_activation(self):
        # Create a test user
        user = User.objects.create_user(
            email='test@example.com',
            password='testpassword',
            first_name='Test',
            last_name='User',
        )
        user.is_active = False
        user.save()

        # Generate activation key and store it in cache
        activation_key = generate_activation_key(user)
        cache_key = f"activation_key:{user.id}"
        cache.set(cache_key, activation_key, timeout=300)  # Set a reasonable timeout

        # Get the activation key from Redis
        activation_key_from_cache = cache.get(cache_key)

        self.assertIsNotNone(activation_key_from_cache)

        # Construct the activation URL
        activation_url = reverse('activate', kwargs={'activation_key': activation_key_from_cache}) # Changed 'activate_user' to 'activate'

        # Activate the user
        response = self.client.get(activation_url)
        self.assertEqual(response.status_code, 200)

        # Check that the user is activated
        user.refresh_from_db()
        self.assertTrue(user.is_active)

        # Check that the activation key is deleted from Redis
        self.assertIsNone(cache.get(cache_key))

    def test_invalid_activation_key(self):
        # Construct an invalid activation URL
        activation_url = reverse('activate', kwargs={'activation_key': 'invalid-key'}) # Changed 'activate_user' to 'activate'

        # Attempt to activate the user with an invalid key
        response = self.client.get(activation_url)
        self.assertEqual(response.status_code, 400)

    def test_resend_activation_email(self):
        # 1. Register a new user
        registration_data = {
            'email': 'resend@example.com',
            'password': 'testpassword',
            'first_name': 'Resend',
            'last_name': 'User',
            'phone': '0987654321',
        }
        registration_url = reverse('register')
        
        # Clear the outbox before registration
        mail.outbox = []
        
        registration_response = self.client.post(registration_url, registration_data, format='json')
        if registration_response.status_code != status.HTTP_201_CREATED:
            print(f"Registration failed: {registration_response.status_code} - {registration_response.data}")
        self.assertEqual(registration_response.status_code, status.HTTP_201_CREATED)

        # 2. Get the user from the database
        user = User.objects.get(email='resend@example.com')
        self.assertFalse(user.is_active)

        # 3. Resend activation email
        resend_url = reverse('resend_activation_email')
        resend_data = {'email': 'resend@example.com'}
        
        # Clear the outbox before resending
        mail.outbox = []
        
        resend_response = self.client.post(resend_url, resend_data, format='json')
        self.assertEqual(resend_response.status_code, status.HTTP_200_OK)
        self.assertEqual(resend_response.data['message'], 'Activation email resent successfully.')

        # 4. Check that a new activation key is generated and stored in Redis
        cache_key = f"activation_key:{user.id}"
        new_activation_key = cache.get(cache_key)
        self.assertIsNotNone(new_activation_key)

        # 5. Check that an email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['resend@example.com'])

    def test_expired_activation_key(self):
        user = User.objects.create_user(email="expired@example.com", password="testpassword")
        activation_key = generate_activation_key(user)
        cache_key = f"activation_key:{user.id}"
        cache.set(cache_key, activation_key, timeout=1)
        time.sleep(2)  # Wait for the key to expire

        activation_url = reverse("activate", args=[activation_key])
        response = self.client.get(activation_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid activation key.")
