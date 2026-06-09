from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ExecutionAnalyticsView,
    ExecutionLogViewSet,
    ExecutionScheduleViewSet,
    RunTestExecutionView,
    TestExecutionViewSet,
)

router = DefaultRouter()
router.register(r'execution-logs', ExecutionLogViewSet, basename='executionlog')
router.register(r'executions', TestExecutionViewSet, basename='execution')
router.register(r'execution-schedules', ExecutionScheduleViewSet, basename='execution-schedule')

urlpatterns = [
    path('executions/run/', RunTestExecutionView.as_view(), name='execution-run'),
    path('executions/analytics/', ExecutionAnalyticsView.as_view(), name='execution-analytics'),
] + router.urls
