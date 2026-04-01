import random
from django.core.mail import send_mail
from django.conf import settings

def generate_otp():
    return random.randint(100000, 999999)

def send_otp_email(email, otp):
    subject = 'Your OTP for Password Reset'
    message = f'Your OTP is {otp}. It is valid for 5 minutes.'
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )
