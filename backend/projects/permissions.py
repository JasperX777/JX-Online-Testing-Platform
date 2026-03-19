from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsProjectOwnerOrAdminForWrite(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        # create
        if view.action == 'create':
            role = getattr(getattr(request.user, 'profile', None), 'role', None)
            return request.user.is_superuser or role in {'admin', 'developer'}

        return True

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        role = getattr(getattr(request.user, 'profile', None), 'role', None)
        if request.user.is_superuser or role == 'admin':
            return True

        # only project owner can update/delete
        return obj.owner_id == request.user.id
