import os
import secrets
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from .models import User, EmailVerificationToken, PasswordResetToken

def generate_verification_code() -> str:
    return f"{secrets.randbelow(900000) + 100000:06d}"

def create_email_verification_token(user: User):
    code = generate_verification_code()
    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(hours=24)
    # Invalidate previous unused tokens for this user
    EmailVerificationToken.objects.filter(user=user, is_used=False).update(is_used=True)
    return EmailVerificationToken.objects.create(
        user=user,
        code=code,
        token=token,
        expires_at=expires_at,
    )

def send_verification_email(user: User, ver_token: EmailVerificationToken):
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    verify_link = f"{frontend_url}/verify-email?token={ver_token.token}&email={user.email}"
    
    subject = "Verifica tu cuenta en ComunidadIA"
    message = f"""Hola {user.name},

¡Bienvenido a ComunidadIA!

Para completar tu registro y activar tu cuenta, utiliza el siguiente código de verificación:

  CODIGO: {ver_token.code}

O haz clic en el siguiente enlace para verificar tu cuenta automáticamente:
{verify_link}

Este código es válido por 24 horas.

Saludos,
El equipo de ComunidadIA
"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error enviando correo de verificación: {e}")

def create_password_reset_token(user: User):
    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(minutes=30)
    # Invalidate previous tokens
    PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)
    return PasswordResetToken.objects.create(
        user=user,
        token=token,
        expires_at=expires_at,
    )

def send_password_reset_email(user: User, reset_token: PasswordResetToken):
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    reset_link = f"{frontend_url}/reset-password?token={reset_token.token}"
    
    subject = "Recuperacion de contrasena - ComunidadIA"
    message = f"""Hola {user.name},

Has solicitado restablecer tu contraseña en ComunidadIA.

Haz clic en el siguiente enlace para crear una nueva contraseña:
{reset_link}

Este enlace es de un solo uso y expirará en 30 minutos. Si no solicitaste este cambio, puedes ignorar este correo de forma segura.

Saludos,
El equipo de ComunidadIA
"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error enviando correo de recuperación: {e}")
