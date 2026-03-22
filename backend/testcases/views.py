from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from .models import TestCase
from .permissions import TestCaseAccessPermission
from .serializers import TestCaseSerializer
from .services import create_testcase, filter_testcases

class TestCaseViewSet(ModelViewSet):
    serializer_class = TestCaseSerializer
    permission_classes = [IsAuthenticated, TestCaseAccessPermission]

    def get_queryset(self):
        user = self.request.user
        role = getattr(getattr(user, 'profile', None), 'role', None)

        if user.is_superuser or role == 'admin':
            base_qs = TestCase.objects.all()
        elif role == 'developer':
            base_qs = TestCase.objects.filter(
                Q(project__owner=user) | Q(project__project_members__user=user)
            ).distinct()
        else:
            # tester: only assigned project testcases
            base_qs = TestCase.objects.filter(project__project_members__user=user).distinct()

        project_id = self.request.query_params.get('project_id')
        category = self.request.query_params.get('category')
        tag = self.request.query_params.get('tag')

        return filter_testcases(
            queryset=base_qs,
            project_id=project_id,
            category=category,
            tag=tag,
        )

    def perform_create(self, serializer):
        create_testcase(serializer=serializer, user=self.request.user)