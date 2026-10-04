from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import Role

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "role", None) == Role.ADMIN or getattr(request.user, "is_staff", False)

class IsOwnerEducatorObject(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "role", None) == Role.ADMIN or getattr(user, "is_staff", False):
            return True
        edu = getattr(user, "educator", None)
        if not edu:
            return False
        owner = getattr(obj, "educator", None)
        return owner and owner.id == edu.id

class IsAuthorOrReadOnly(BasePermission):
    """
    Permite lectura libre (GET, HEAD, OPTIONS) pero exige ser el autor o ADMIN para editar/eliminar.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        if getattr(user, "role", None) == Role.ADMIN or getattr(user, "is_staff", False):
            return True

        me_edu = getattr(user, "educator", None)
        owner_edu = getattr(obj, "educator", None)
        return me_edu and owner_edu and me_edu.id == owner_edu.id
