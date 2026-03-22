from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import ExecutionLog
from .serializers import ExecutionLogSerializer


class ExecutionLogViewSet(ReadOnlyModelViewSet):
    serializer_class = ExecutionLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = getattr(getattr(user, 'profile', None), 'role', None)

        if user.is_superuser or role == 'admin':
            qs = ExecutionLog.objects.all()
        elif role == 'developer':
            qs = ExecutionLog.objects.filter(
                Q(project__owner=user) | Q(project__project_members__user=user)
            ).distinct()
        else:
            # tester
            qs = ExecutionLog.objects.filter(project__project_members__user=user).distinct()

        project_id = self.request.query_params.get('project_id')
        level = self.request.query_params.get('level')
        testcase_id = self.request.query_params.get('testcase_id')

        if project_id:
            qs = qs.filter(project_id=project_id)
        if level:
            qs = qs.filter(level=level)
        if testcase_id:
            qs = qs.filter(testcase_id=testcase_id)

        return qs
