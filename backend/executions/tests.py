from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from projects.models import Project
from testcases.models import TestCase as TC
from .models import ExecutionLog

User = get_user_model()


class ExecutionLogModelTests(TestCase):
    def test_create_execution_log(self):
        user = User.objects.create_user(username='exec_user', password='pass123456')
        project = Project.objects.create(name='Exec Project', description='', owner=user)
        tc = TC.objects.create(
            project=project,
            title='Sample case',
            description='',
            steps='',
            expected_result='',
            created_by=user,
        )

        log = ExecutionLog.objects.create(
            project=project,
            testcase=tc,
            level='info',
            message='execution started',
        )

        self.assertIsNotNone(log.id)
        self.assertEqual(log.project_id, project.id)
        self.assertEqual(log.testcase_id, tc.id)
        self.assertEqual(log.level, 'info')

class ExecutionLogApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='exec_api_user', password='pass123456')
        self.user.profile.role = 'developer'
        self.user.profile.save()

        self.project = Project.objects.create(name='Exec API Project', description='', owner=self.user)
        self.tc = TC.objects.create(
            project=self.project,
            title='TC1',
            description='',
            steps='',
            expected_result='',
            created_by=self.user,
        )
        ExecutionLog.objects.create(
            project=self.project,
            testcase=self.tc,
            level='info',
            message='started',
        )

    def auth(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_filter_execution_logs_by_project(self):
        self.auth()
        resp = self.client.get(f'/api/execution-logs/?project_id={self.project.id}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['project'], self.project.id)
