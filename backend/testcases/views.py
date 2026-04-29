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
        else:
            # user role: only test cases created by self
            base_qs = TestCase.objects.filter(created_by=user)

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
