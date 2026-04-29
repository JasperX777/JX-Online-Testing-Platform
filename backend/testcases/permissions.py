from rest_framework.permissions import SAFE_METHODS, BasePermission


class TestCaseAccessPermission(BasePermission):
    """
    admin: full access
    user: can read/write testcases in visible projects, with owner restrictions for update/delete
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        if view.action == 'create':
            role = getattr(getattr(request.user, 'profile', None), 'role', None)
            return request.user.is_superuser or role in {'admin', 'user'}

        return True

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        role = getattr(getattr(request.user, 'profile', None), 'role', None)
        if request.user.is_superuser or role == 'admin':
            return True

        # user can modify only when owning the project
        return role == 'user' and obj.project.owner_id == request.user.id
