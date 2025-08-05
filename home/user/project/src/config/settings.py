from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_activation_email_task(user_email, subject, message):
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user_email],
        fail_silently=False,
    )