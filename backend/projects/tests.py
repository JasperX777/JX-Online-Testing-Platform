from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Project, ProjectMember

User = get_user_model()


class ProjectApiTests(APITestCase):
    def setUp(self):
        self.dev = User.objects.create_user(username='dev_test', password='pass123456')
        self.tester = User.objects.create_user(username='tester_test', password='pass123456')
        self.admin = User.objects.create_user(username='admin_test', password='pass123456')

        self.dev.profile.role = 'user'
        self.dev.profile.save()

        self.tester.profile.role = 'user'
        self.tester.profile.save()

        self.admin.profile.role = 'admin'
        self.admin.profile.save()

    def auth(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_projects_requires_auth(self):
        resp = self.client.get('/api/projects/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_create_project(self):
        self.auth(self.dev)
        resp = self.client.post(
            '/api/projects/',
            {'name': 'Dev Project', 'description': 'owned by dev'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        obj = Project.objects.get(id=resp.data['id'])
        self.assertEqual(obj.owner_id, self.dev.id)

    def test_user_can_create_project_for_second_user(self):
        self.auth(self.tester)
        resp = self.client.post(
            '/api/projects/',
            {'name': 'Tester Project', 'description': 'should fail'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_user_cannot_read_other_users_project_even_if_assigned(self):
        project = Project.objects.create(name='P1', description='', owner=self.dev)
        ProjectMember.objects.create(project=project, user=self.tester, role_in_project='user')

        self.auth(self.tester)
        resp = self.client.get(f'/api/projects/{project.id}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_cannot_update_other_users_project_even_if_assigned(self):
        project = Project.objects.create(name='P1', description='', owner=self.dev)
        ProjectMember.objects.create(project=project, user=self.tester, role_in_project='user')

        self.auth(self.tester)
        resp = self.client.put(
            f'/api/projects/{project.id}/',
            {'name': 'Changed by tester', 'description': 'x'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_cannot_delete_other_users_project_even_if_assigned(self):
        project = Project.objects.create(name='P1', description='', owner=self.dev)
        ProjectMember.objects.create(project=project, user=self.tester, role_in_project='user')

        self.auth(self.tester)
        resp = self.client.delete(f'/api/projects/{project.id}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_view_all_projects(self):
        project = Project.objects.create(name='P1', description='', owner=self.dev)

        self.auth(self.admin)
        resp = self.client.get(f'/api/projects/{project.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
