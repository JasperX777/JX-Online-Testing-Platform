from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import PickerSessionDetailView, PickerSessionStartView, PickerSessionStopView, TestCaseViewSet

router = DefaultRouter()
router.register(r'testcases', TestCaseViewSet, basename='testcases')

urlpatterns = [
    *router.urls,
    path('testcases/picker/start/', PickerSessionStartView.as_view(), name='picker-session-start'),
    path('testcases/picker/<str:session_id>/', PickerSessionDetailView.as_view(), name='picker-session-detail'),
    path('testcases/picker/<str:session_id>/stop/', PickerSessionStopView.as_view(), name='picker-session-stop'),
]
