import hashlib
import hmac

from django.conf import settings


def digest_one_time_secret(purpose: str, value: str) -> str:
    """Return a keyed digest suitable for indexing high-entropy one-time secrets."""
    key = settings.SECRET_KEY.encode("utf-8")
    message = f"comunidadia:{purpose}:{value}".encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()
