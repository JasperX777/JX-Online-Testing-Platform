from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Project

User = get_user_model()


class ProjectTests(APITestCase):
    def setUp(self):
        self.u1 = User.objects.create_user(username='u1_test', password='pass123456')
        self.u2 = User.objects.create_user(username='u2_test', password='pass123456')

    def auth(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_projects_requires_auth(self):
        resp = self.client.get('/api/projects/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_project_sets_owner(self):
        self.auth(self.u1)
        payload = {'name': 'Test Project', 'description': 'demo'}
        resp = self.client.post('/api/projects/', payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        obj = Project.objects.get(id=resp.data['id'])
        self.assertEqual(obj.owner_id, self.u1.id)

    def test_non_admin_cannot_access_others_project(self):
        p2 = Project.objects.create(name='u2 project', description='', owner=self.u2)
        self.auth(self.u1)

        resp = self.client.get(f'/api/projects/{p2.id}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)