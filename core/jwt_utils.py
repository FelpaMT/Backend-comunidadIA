import jwt
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from .models import RefreshToken, User
import secrets

def _now():
    return timezone.now()

def generate_access_token(user: User):
    exp = _now() + settings.JWT_CONFIG["ACCESS_LIFETIME"]
    payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "exp": int(exp.timestamp()),
        "type": "access"
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token

def generate_and_store_refresh(user: User):
    exp = _now() + settings.JWT_CONFIG["REFRESH_LIFETIME"]
    token = secrets.token_urlsafe(64)
    RefreshToken.objects.update_or_create(
        user=user, defaults={"token": token, "expiry_date": exp}
    )
    return token, exp

def decode_any_token(token: str):
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

def invalidate_refresh(user: User):
    RefreshToken.objects.filter(user=user).delete()

def new_access_from_access(user: User) -> str:
    # Según tu regla: refresh recibe access_token y devuelve uno nuevo
    # (no estándar, pero lo permitimos usando el refresh guardado en DB)
    # Verificamos que tenga refresh válido:
    rt = RefreshToken.objects.filter(user=user, expiry_date__gt=_now()).first()
    if not rt:
        raise ValueError("No hay refresh válido")
    return generate_access_token(user)
