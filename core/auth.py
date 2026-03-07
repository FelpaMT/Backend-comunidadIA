# core/auth.py
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework import exceptions
from django.utils.translation import gettext_lazy as _
from .models import User
from .jwt_utils import decode_any_token
from rest_framework_simplejwt.authentication import JWTAuthentication

class JWTAuthenticationCustom(BaseAuthentication):
    """
    Lee Authorization: Bearer <token> y autentica al usuario.
    No obliga a que el header exista (para endpoints públicos).
    """
    www_authenticate_realm = 'api'

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth:
            return None  # sin header => DRF seguirá como anónimo si la vista lo permite

        if auth[0].lower() != b'bearer':
            return None

        if len(auth) == 1:
            raise exceptions.AuthenticationFailed(_('Invalid Authorization header. No credentials provided.'))
        elif len(auth) > 2:
            raise exceptions.AuthenticationFailed(_('Invalid Authorization header. Token string should not contain spaces.'))

        token = auth[1].decode('utf-8')

        try:
            payload = decode_any_token(token)
        except Exception:
            raise exceptions.AuthenticationFailed(_('Invalid or expired token.'))

        user_id = payload.get('sub')
        if not user_id:
            raise exceptions.AuthenticationFailed(_('Invalid token payload.'))

        user = User.objects.filter(id=user_id).first()
        if not user:
            raise exceptions.AuthenticationFailed(_('User not found.'))

        return (user, None)

    def authenticate_header(self, request):
        return 'Bearer realm="%s"' % self.www_authenticate_realm
