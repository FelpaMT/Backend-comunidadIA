# core/schema.py
from drf_spectacular.extensions import OpenApiAuthenticationExtension

class JWTAuthScheme(OpenApiAuthenticationExtension):
    """
    Mapea core.auth.JWTAuthenticationCustom -> esquema Bearer en OpenAPI.
    """
    target_class = 'core.auth.JWTAuthenticationCustom'  # ruta a tu clase
    name = 'BearerAuth'  # debe coincidir con SPECTACULAR_SETTINGS["COMPONENTS"]["securitySchemes"] key

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
