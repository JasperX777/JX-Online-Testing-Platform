from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .picker import get_picker_session, start_picker_session, stop_picker_session
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


class PickerSessionStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        url = (request.data.get('url') or '').strip()
        browser_name = (request.data.get('browser_name') or 'chromium').strip().lower()

        if not url:
            return Response({'detail': 'A page URL is required.'}, status=status.HTTP_400_BAD_REQUEST)

        session = start_picker_session(url=url, browser_name=browser_name or 'chromium')
        return Response(session, status=status.HTTP_201_CREATED)


class PickerSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id: str):
        session = get_picker_session(session_id)
        if session is None:
            return Response({'detail': 'Picker session not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(session)


class PickerSessionStopView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id: str):
        session = stop_picker_session(session_id)
        if session is None:
            return Response({'detail': 'Picker session not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(session)
