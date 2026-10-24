import secrets
from dataclasses import dataclass
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from .models import User, EmailVerificationToken, PasswordResetToken
from .security import digest_one_time_secret


@dataclass(frozen=True)
class IssuedEmailVerification:
    record: EmailVerificationToken
    code: str
    token: str


@dataclass(frozen=True)
class IssuedPasswordReset:
    record: PasswordResetToken
    token: str

def generate_verification_code() -> str:
    return f"{secrets.randbelow(900000) + 100000:06d}"

def create_email_verification_token(user: User):
    code = generate_verification_code()
    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(hours=24)
    # Invalidate previous unused tokens for this user
    EmailVerificationToken.objects.filter(user=user, is_used=False).update(is_used=True)
    record = EmailVerificationToken.objects.create(
        user=user,
        code=digest_one_time_secret("email-code", code),
        token=digest_one_time_secret("email-verification", token),
        expires_at=expires_at,
    )
    return IssuedEmailVerification(record=record, code=code, token=token)

def send_verification_email(user: User, issued: IssuedEmailVerification):
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    verify_link = f"{frontend_url}/verify-email?token={issued.token}&email={user.email}"
    
    subject = "Verifica tu cuenta en ComunidadIA"
    message = f"""Hola {user.name},

¡Bienvenido a ComunidadIA!

Para completar tu registro y activar tu cuenta, utiliza el siguiente código de verificación:

  CODIGO: {issued.code}

O haz clic en el siguiente enlace para verificar tu cuenta automáticamente:
{verify_link}

Este código es válido por 24 horas.

Saludos,
El equipo de ComunidadIA
"""
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

def create_password_reset_token(user: User):
    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(minutes=30)
    # Invalidate previous tokens
    PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)
    record = PasswordResetToken.objects.create(
        user=user,
        token=digest_one_time_secret("password-reset", token),
        expires_at=expires_at,
    )
    return IssuedPasswordReset(record=record, token=token)

def send_password_reset_email(user: User, issued: IssuedPasswordReset):
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    reset_link = f"{frontend_url}/reset-password?token={issued.token}"
    
    subject = "Recuperacion de contrasena - ComunidadIA"
    message = f"""Hola {user.name},

Has solicitado restablecer tu contraseña en ComunidadIA.

Haz clic en el siguiente enlace para crear una nueva contraseña:
{reset_link}

Este enlace es de un solo uso y expirará en 30 minutos. Si no solicitaste este cambio, puedes ignorar este correo de forma segura.

Saludos,
El equipo de ComunidadIA
"""
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
