from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ExecutionLogViewSet,
    RunTestExecutionView,
    TestExecutionViewSet,
)

router = DefaultRouter()
router.register(r'execution-logs', ExecutionLogViewSet, basename='executionlog')
router.register(r'executions', TestExecutionViewSet, basename='execution')

urlpatterns = [
    path('executions/run/', RunTestExecutionView.as_view(), name='execution-run'),
] + router.urls
