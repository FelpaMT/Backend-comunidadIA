from rest_framework.permissions import BasePermission
from .models import Role

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "role", None) == Role.ADMIN

class IsOwnerEducatorObject(BasePermission):
    """
    Verifica que el recurso (Publication/Commentary) pertenezca al educator autenticado.
    Debe usarse en vistas que ya han resuelto el objeto.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        edu = getattr(user, "educator", None)
        if not edu:
            return False
        # Publication -> obj.educator ; Commentary -> obj.educator
        owner = getattr(obj, "educator", None)
        return owner and owner.id == edu.id
