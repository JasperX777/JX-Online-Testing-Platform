from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from .models import Project
from .permissions import IsProjectOwnerOrAdminForWrite
from .serializers import ProjectSerializer


class ProjectViewSet(ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsProjectOwnerOrAdminForWrite]

    def get_queryset(self):
        user = self.request.user
        role = getattr(getattr(user, 'profile', None), 'role', None)

        if user.is_superuser or role == 'admin':
            return Project.objects.all()

        # user role: only own projects
        return Project.objects.filter(owner=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
