from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from projects.models import Project
from .models import TestCase

User = get_user_model()


def sample_steps():
    return [
        {
            'step_no': 1,
            'step_title': 'Launch browser',
            'description': '',
            'action': 'launch_browser',
            'target': '',
            'locator_type': 'css',
            'selector': '',
            'value': 'chromium',
            'note': '',
        },
        {
            'step_no': 2,
            'step_title': 'Open login page',
            'description': '',
            'action': 'open_page',
            'target': 'Login page',
            'locator_type': 'css',
            'selector': '',
            'value': '/login',
            'note': '',
        },
        {
            'step_no': 3,
            'step_title': 'Click sign in',
            'description': '',
            'action': 'click_button',
            'target': 'Sign in button',
            'locator_type': 'css',
            'selector': "button[type='submit']",
            'value': '',
            'note': '',
        },
    ]


class TestCaseApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tc_user', password='pass123456')
        self.user.profile.role = 'user'
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
            'description': 'Manual login validation',
            'module': 'Auth',
            'scenario': 'Login',
            'category': 'auth',
            'tags': ['smoke', 'login'],
            'steps_json': sample_steps(),
            'priority': 'high',
            'status': 'ready',
        }
        resp = self.client.post('/api/testcases/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        obj = TestCase.objects.get(id=resp.data['id'])
        self.assertEqual(obj.created_by_id, self.user.id)
        self.assertEqual(obj.module, 'Auth')
        self.assertEqual(obj.steps_json[0]['action'], 'open_page')

    def test_create_testcase_generates_title_when_missing(self):
        self.auth()
        resp = self.client.post(
            '/api/testcases/',
            {
                'project': self.project.id,
                'title': '',
                'module': 'Auth',
                'scenario': 'Password reset',
                'description': '',
                'category': 'auth',
                'tags': [],
                'steps_json': sample_steps(),
                'priority': 'medium',
                'status': 'draft',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['title'], 'Auth - Password reset')

    def test_create_testcase_rejects_invalid_steps(self):
        self.auth()
        resp = self.client.post(
            '/api/testcases/',
            {
                'project': self.project.id,
                'title': 'Broken case',
                'description': '',
                'category': 'auth',
                'tags': [],
                'steps_json': [{'step_no': 1, 'step_title': 'Broken', 'description': 'Broken step', 'action': 'invalid', 'target': 'Thing', 'locator_type': 'css', 'selector': '', 'value': '', 'note': ''}],
                'priority': 'medium',
                'status': 'draft',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('steps_json', resp.data)

    def test_create_testcase_rejects_missing_selector_for_non_open_page(self):
        self.auth()
        resp = self.client.post(
            '/api/testcases/',
            {
                'project': self.project.id,
                'title': 'Broken case',
                'description': '',
                'category': 'auth',
                'tags': [],
                'steps_json': [{'step_no': 1, 'step_title': 'Click submit', 'description': 'Click submit button', 'action': 'click_button', 'target': 'Submit', 'locator_type': 'css', 'selector': '', 'value': '', 'note': ''}],
                'priority': 'medium',
                'status': 'draft',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('steps_json', resp.data)

    def test_create_testcase_rejects_missing_human_readable_fields(self):
        self.auth()
        resp = self.client.post(
            '/api/testcases/',
            {
                'project': self.project.id,
                'title': 'Broken case',
                'description': '',
                'category': 'auth',
                'tags': [],
                'steps_json': [{'step_no': 1, 'step_title': '', 'description': '', 'action': 'open_page', 'target': 'Google', 'locator_type': 'css', 'selector': '', 'value': 'https://google.com', 'note': ''}],
                'priority': 'medium',
                'status': 'draft',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('steps_json', resp.data)

    def test_create_testcase_accepts_browser_alias(self):
        self.auth()
        resp = self.client.post(
            '/api/testcases/',
            {
                'project': self.project.id,
                'title': 'Chrome case',
                'description': '',
                'category': 'auth',
                'tags': [],
                'steps_json': [{'step_no': 1, 'step_title': 'Launch browser', 'description': '', 'action': 'launch_browser', 'target': '', 'locator_type': 'css', 'selector': '', 'value': 'chrome', 'note': ''}],
                'priority': 'medium',
                'status': 'draft',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_create_testcase_rejects_invalid_browser_name(self):
        self.auth()
        resp = self.client.post(
            '/api/testcases/',
            {
                'project': self.project.id,
                'title': 'Broken case',
                'description': '',
                'category': 'auth',
                'tags': [],
                'steps_json': [{'step_no': 1, 'step_title': 'Launch browser', 'description': '', 'action': 'launch_browser', 'target': '', 'locator_type': 'css', 'selector': '', 'value': 'opera', 'note': ''}],
                'priority': 'medium',
                'status': 'draft',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('steps_json', resp.data)

    def test_create_testcase_requires_value_for_press_key(self):
        self.auth()
        resp = self.client.post(
            '/api/testcases/',
            {
                'project': self.project.id,
                'title': 'Broken case',
                'description': '',
                'category': 'auth',
                'tags': [],
                'steps_json': [{'step_no': 1, 'step_title': 'Submit with key', 'description': '', 'action': 'press_key', 'target': '', 'locator_type': 'css', 'selector': '', 'value': '', 'note': ''}],
                'priority': 'medium',
                'status': 'draft',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('steps_json', resp.data)

    def test_create_testcase_rejects_empty_steps(self):
        self.auth()
        resp = self.client.post(
            '/api/testcases/',
            {
                'project': self.project.id,
                'title': 'Broken case',
                'description': '',
                'category': 'auth',
                'tags': [],
                'steps_json': [],
                'priority': 'medium',
                'status': 'draft',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('steps_json', resp.data)

    def test_user_cannot_create_testcase_in_other_users_project(self):
        other_user = User.objects.create_user(username='tc_other_dev', password='pass123456')
        other_user.profile.role = 'user'
        other_user.profile.save()
        hidden_project = Project.objects.create(name='Hidden', description='', owner=other_user)

        self.auth()
        resp = self.client.post(
            '/api/testcases/',
            {
                'project': hidden_project.id,
                'title': 'Should fail',
                'description': '',
                'module': 'Auth',
                'scenario': 'Login',
                'category': 'auth',
                'tags': ['login'],
                'steps_json': sample_steps(),
                'priority': 'medium',
                'status': 'draft',
            },
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('project', resp.data)

    def test_user_cannot_move_testcase_to_other_users_project(self):
        other_user = User.objects.create_user(username='tc_other_dev2', password='pass123456')
        other_user.profile.role = 'user'
        other_user.profile.save()
        hidden_project = Project.objects.create(name='Hidden', description='', owner=other_user)
        tc = TestCase.objects.create(
            project=self.project,
            title='Owned by user',
            description='',
            module='Auth',
            scenario='Login',
            category='auth',
            tags=['login'],
            steps_json=sample_steps(),
            priority='medium',
            status='ready',
            created_by=self.user,
        )

        self.auth()
        resp = self.client.patch(
            f'/api/testcases/{tc.id}/',
            {'project': hidden_project.id},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('project', resp.data)
        tc.refresh_from_db()
        self.assertEqual(tc.project_id, self.project.id)

    def test_filter_by_project_and_category(self):
        self.auth()
        TestCase.objects.create(
            project=self.project,
            title='A',
            category='auth',
            tags=['login'],
            module='Auth',
            scenario='Login',
            steps_json=sample_steps(),
            created_by=self.user,
        )
        TestCase.objects.create(
            project=self.project,
            title='B',
            category='payment',
            tags=['payment'],
            module='Billing',
            scenario='Refund',
            steps_json=sample_steps(),
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
            module='Auth',
            scenario='Login',
            steps_json=sample_steps(),
            created_by=self.user,
        )
        TestCase.objects.create(
            project=self.project,
            title='B',
            category='auth',
            tags=['regression'],
            module='Auth',
            scenario='Reset',
            steps_json=sample_steps(),
            created_by=self.user,
        )

        resp = self.client.get('/api/testcases/?tag=login')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertIn('login', resp.data[0]['tags'])
