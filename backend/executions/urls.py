from rest_framework.routers import DefaultRouter
from .views import ExecutionLogViewSet

router = DefaultRouter()
router.register(r'execution-logs', ExecutionLogViewSet, basename='executionlog')

urlpatterns = router.urls
