from django.db.models import Q
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from projects.models import Project

from .models import ExecutionLog, TestExecution
from .permissions import CanManageExecution
from .serializers import (
    ExecutionLogSerializer,
    ExecutionReportSerializer,
    TestExecutionRunSerializer,
    TestExecutionSerializer,
)
from .services import cleanup_execution_media, initialize_execution
from .tasks import dispatch_test_execution


class ExecutionAccessMixin:
    def get_project_visibility_filter(self):
        user = self.request.user
        role = getattr(getattr(user, 'profile', None), 'role', None)

        if user.is_superuser or role == 'admin':
            return Q()
        return Q(owner=user)

    def get_execution_visibility_filter(self):
        user = self.request.user
        role = getattr(getattr(user, 'profile', None), 'role', None)

        if user.is_superuser or role == 'admin':
            return Q()
        return Q(triggered_by=user)


class ExecutionLogViewSet(ExecutionAccessMixin, ReadOnlyModelViewSet):
    serializer_class = ExecutionLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = getattr(getattr(user, 'profile', None), 'role', None)
        if user.is_superuser or role == 'admin':
            qs = ExecutionLog.objects.all()
        else:
            qs = ExecutionLog.objects.filter(execution__triggered_by=user).distinct()

        project_id = self.request.query_params.get('project_id')
        level = self.request.query_params.get('level')
        testcase_id = self.request.query_params.get('testcase_id')
        execution_id = self.request.query_params.get('execution_id')

        if project_id:
            qs = qs.filter(project_id=project_id)
        if level:
            qs = qs.filter(level=level)
        if testcase_id:
            qs = qs.filter(testcase_id=testcase_id)
        if execution_id:
            qs = qs.filter(execution_id=execution_id)

        return qs


class TestExecutionViewSet(
    ExecutionAccessMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = TestExecutionSerializer
    permission_classes = [IsAuthenticated, CanManageExecution]

    def get_queryset(self):
        visibility_filter = self.get_execution_visibility_filter()
        base_qs = TestExecution.objects.select_related('project', 'testcase', 'triggered_by', 'report').prefetch_related('step_results')
        qs = base_qs.all() if not visibility_filter else base_qs.filter(visibility_filter).distinct()

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

    def perform_destroy(self, instance):
        cleanup_execution_media(execution=instance)
        instance.delete()

    @action(detail=True, methods=['get'], url_path='report')
    def report(self, request, pk=None):
        execution = self.get_object()
        if not hasattr(execution, 'report'):
            return Response({'detail': 'Report not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ExecutionReportSerializer(execution.report).data)


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
        if not (request.user.is_superuser or role in {'admin', 'user'}):
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        execution = TestExecution.objects.create(
            project=project,
            testcase=testcase,
            triggered_by=request.user,
            status=TestExecution.Status.PENDING,
        )
        initialize_execution(execution=execution)
        dispatch_test_execution(execution.id)

        return Response(TestExecutionSerializer(execution).data, status=status.HTTP_201_CREATED)
