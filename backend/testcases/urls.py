from rest_framework.routers import DefaultRouter
from .views import TestCaseViewSet

router = DefaultRouter()
router.register(r'testcases', TestCaseViewSet, basename='testcases')

urlpatterns = router.urls