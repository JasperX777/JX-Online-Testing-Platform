from rest_framework.permissions import SAFE_METHODS, BasePermission


class CanManageExecution(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        role = getattr(getattr(request.user, 'profile', None), 'role', None)
        return request.user.is_superuser or role in {'admin', 'user'}

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        role = getattr(getattr(request.user, 'profile', None), 'role', None)
        if request.user.is_superuser or role == 'admin':
            return True

        # users can manage executions they triggered, or executions under projects they own.
        return obj.triggered_by_id == request.user.id or obj.project.owner_id == request.user.id
