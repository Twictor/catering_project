
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task(queue='low_priority')
def send_activation_email_task(subject, message, recipient_list):
    """
    Celery task to send an email asynchronously.
    """
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        fail_silently=False,
    )
