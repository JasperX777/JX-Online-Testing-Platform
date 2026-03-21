from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from .models import Project
from .permissions import IsProjectOwnerOrAdminForWrite
from .serializers import ProjectSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import ProjectMember
from django.contrib.auth import get_user_model

User = get_user_model()


class ProjectViewSet(ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsProjectOwnerOrAdminForWrite]

    def get_queryset(self):
        user = self.request.user
        role = getattr(getattr(user, 'profile', None), 'role', None)

        if user.is_superuser or role == 'admin':
            return Project.objects.all()

        if role == 'developer':
            return Project.objects.filter(Q(owner=user) | Q(project_members__user=user)).distinct()

        # tester: can only see assigned projects
        return Project.objects.filter(project_members__user=user).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], url_path='assign-tester')
    def assign_tester(self, request, pk=None):
        project = self.get_object()
        if project.owner_id != request.user.id and getattr(request.user.profile, 'role', None) != 'admin':
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        tester_id = request.data.get('tester_id')
        tester = User.objects.filter(id=tester_id).first()
        if not tester:
            return Response({'detail': 'tester not found'}, status=status.HTTP_404_NOT_FOUND)
        if tester.profile.role != 'tester':
            return Response({'detail': 'user is not tester'}, status=status.HTTP_400_BAD_REQUEST)

        ProjectMember.objects.get_or_create(project=project, user=tester, defaults={'role_in_project': 'tester'})
        return Response({'detail': 'assigned'}, status=status.HTTP_200_OK)