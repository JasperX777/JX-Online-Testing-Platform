from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from projects.models import Project
from .models import TestCase

User = get_user_model()


class TestCaseApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tc_user', password='pass123456')
        self.user.profile.role = 'developer'
        self.user.profile.save()

        self.project = Project.objects.create(
            name='TC Project',
            description='for testcase tests',
            owner=self.user,
        )

    def auth(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_testcases_requires_auth(self):
        resp = self.client.get('/api/testcases/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_testcase_success(self):
        self.auth()
        payload = {
            'project': self.project.id,
            'title': 'Login success',
            'description': 'desc',
            'steps': '1. input\n2. click',
            'expected_result': 'dashboard',
            'category': 'auth',
            'tags': ['smoke', 'login'],
            'priority': 'high',
            'status': 'ready',
        }
        resp = self.client.post('/api/testcases/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        obj = TestCase.objects.get(id=resp.data['id'])
        self.assertEqual(obj.created_by_id, self.user.id)

    def test_filter_by_project_and_category(self):
        self.auth()
        TestCase.objects.create(
            project=self.project,
            title='A',
            category='auth',
            tags=['login'],
            created_by=self.user,
        )
        TestCase.objects.create(
            project=self.project,
            title='B',
            category='payment',
            tags=['payment'],
            created_by=self.user,
        )

        resp = self.client.get(f'/api/testcases/?project_id={self.project.id}&category=auth')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['category'], 'auth')

    def test_filter_by_tag(self):
        self.auth()
        TestCase.objects.create(
            project=self.project,
            title='A',
            category='auth',
            tags=['smoke', 'login'],
            created_by=self.user,
        )
        TestCase.objects.create(
            project=self.project,
            title='B',
            category='auth',
            tags=['regression'],
            created_by=self.user,
        )

        resp = self.client.get('/api/testcases/?tag=login')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertIn('login', resp.data[0]['tags'])

    def test_tester_cannot_create_testcase(self):
        tester = User.objects.create_user(username='tc_tester', password='pass123456')
        tester.profile.role = 'tester'
        tester.profile.save()

        from projects.models import ProjectMember
        ProjectMember.objects.create(project=self.project, user=tester, role_in_project='tester')

        refresh = RefreshToken.for_user(tester)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        payload = {
            'project': self.project.id,
            'title': 'Tester create should fail',
            'description': '',
            'steps': '',
            'expected_result': '',
            'category': 'auth',
            'tags': ['login'],
            'priority': 'medium',
            'status': 'draft',
        }
        resp = self.client.post('/api/testcases/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_tester_cannot_update_or_delete_assigned_testcase(self):
        tester = User.objects.create_user(username='tc_tester2', password='pass123456')
        tester.profile.role = 'tester'
        tester.profile.save()

        from projects.models import ProjectMember
        ProjectMember.objects.create(project=self.project, user=tester, role_in_project='tester')

        tc = TestCase.objects.create(
            project=self.project,
            title='Owned by dev',
            description='',
            steps='',
            expected_result='',
            category='auth',
            tags=['login'],
            priority='medium',
            status='ready',
            created_by=self.user,
        )

        refresh = RefreshToken.for_user(tester)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        put_resp = self.client.put(
            f'/api/testcases/{tc.id}/',
            {
                'project': self.project.id,
                'title': 'tester changed',
                'description': '',
                'steps': '',
                'expected_result': '',
                'category': 'auth',
                'tags': ['login'],
                'priority': 'medium',
                'status': 'ready',
            },
            format='json',
        )
        self.assertEqual(put_resp.status_code, status.HTTP_403_FORBIDDEN)

        delete_resp = self.client.delete(f'/api/testcases/{tc.id}/')
        self.assertEqual(delete_resp.status_code, status.HTTP_403_FORBIDDEN)
