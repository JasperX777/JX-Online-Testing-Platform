from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from projects.models import Project

from .models import ExecutionLog, TestExecution
from .serializers import (
    ExecutionLogSerializer,
    TestExecutionRunSerializer,
    TestExecutionSerializer,
)
from .services import run_test_execution


class ExecutionAccessMixin:
    def get_project_visibility_filter(self):
        user = self.request.user
        role = getattr(getattr(user, 'profile', None), 'role', None)

        if user.is_superuser or role == 'admin':
            return Q()
        if role == 'developer':
            return Q(owner=user) | Q(project_members__user=user)
        return Q(project_members__user=user)

    def get_execution_visibility_filter(self):
        project_filter = self.get_project_visibility_filter()
        if not project_filter:
            return Q()
        return Q(project__in=Project.objects.filter(project_filter))


class ExecutionLogViewSet(ExecutionAccessMixin, ReadOnlyModelViewSet):
    serializer_class = ExecutionLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        visibility_filter = self.get_execution_visibility_filter()
        qs = ExecutionLog.objects.all() if not visibility_filter else ExecutionLog.objects.filter(visibility_filter).distinct()

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


class TestExecutionViewSet(ExecutionAccessMixin, ReadOnlyModelViewSet):
    serializer_class = TestExecutionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        visibility_filter = self.get_execution_visibility_filter()
        qs = TestExecution.objects.all() if not visibility_filter else TestExecution.objects.filter(visibility_filter).distinct()

        project_id = self.request.query_params.get('project_id')
        status_value = self.request.query_params.get('status')
        testcase_id = self.request.query_params.get('testcase_id')

        if project_id:
            qs = qs.filter(project_id=project_id)
        if status_value:
            qs = qs.filter(status=status_value)
        if testcase_id:
            qs = qs.filter(testcase_id=testcase_id)

        return qs


class RunTestExecutionView(ExecutionAccessMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TestExecutionRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = serializer.validated_data['project_obj']
        testcase = serializer.validated_data['testcase_obj']

        project_visibility_filter = self.get_project_visibility_filter()
        if project_visibility_filter and not Project.objects.filter(id=project.id).filter(project_visibility_filter).exists():
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        role = getattr(getattr(request.user, 'profile', None), 'role', None)
        if not (request.user.is_superuser or role in {'admin', 'developer'}):
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        execution = TestExecution.objects.create(
            project=project,
            testcase=testcase,
            triggered_by=request.user,
        )
        execution = run_test_execution(execution=execution)

        return Response(TestExecutionSerializer(execution).data, status=status.HTTP_201_CREATED)
