from rest_framework.permissions import SAFE_METHODS, BasePermission


class TestCaseAccessPermission(BasePermission):
    """
    admin: full access
    developer: can read/write testcases in visible projects
    tester: read-only in visible projects
    """

    def has_permission(self, request, view):
        role = getattr(getattr(request.user, 'profile', None), 'role', None)

        if request.method in SAFE_METHODS:
            return True

        if request.method == 'POST':
            return request.user.is_superuser or role in {'admin', 'developer'}

        # PUT/PATCH/DELETE -> object permission handles final check
        return True

    def has_object_permission(self, request, view, obj):
        role = getattr(getattr(request.user, 'profile', None), 'role', None)

        if request.user.is_superuser or role == 'admin':
            return True

        if request.method in SAFE_METHODS:
            return True

        # tester cannot modify
        if role == 'tester':
            return False

        # developer can modify only when owning the project
        return obj.project.owner_id == request.user.id
