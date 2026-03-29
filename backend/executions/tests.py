from subprocess import CompletedProcess
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from projects.models import Project, ProjectMember
from testcases.models import TestCase as TC
from .models import ExecutionLog, TestExecution
from .services import run_test_execution

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

    def test_execution_logs_requires_auth(self):
        resp = self.client.get('/api/execution-logs/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class TestExecutionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='exec_service_user', password='pass123456')
        self.user.profile.role = 'developer'
        self.user.profile.save()

        self.project = Project.objects.create(name='Service Project', description='', owner=self.user)
        self.tc = TC.objects.create(
            project=self.project,
            title='Runnable case',
            description='',
            steps='',
            expected_result='',
            created_by=self.user,
            test_type=TC.TestType.FUNCTIONAL,
            pytest_target='executions/tests.py::ExecutionLogApiTests::test_execution_logs_requires_auth',
        )

    @patch('executions.runners.PytestExecutionRunner.run')
    def test_functional_execution_uses_pytest_runner(self, run_mock):
        run_mock.return_value = CompletedProcess(
            args=['pytest'],
            returncode=0,
            stdout='1 passed in 0.10s',
            stderr='',
        )
        execution = TestExecution.objects.create(
            project=self.project,
            testcase=self.tc,
            triggered_by=self.user,
            status=TestExecution.Status.PENDING,
        )

        run_test_execution(execution=execution)
        execution.refresh_from_db()

        self.assertEqual(execution.status, TestExecution.Status.SUCCESS)
        self.assertEqual(execution.exit_code, 0)
        self.assertIn('1 passed', execution.result_summary)
        run_mock.assert_called_once()
        self.assertEqual(ExecutionLog.objects.filter(project=self.project).count(), 2)

    @patch('executions.runners.PytestExecutionRunner.run')
    def test_unsupported_test_type_marks_execution_failed(self, run_mock):
        self.tc.test_type = TC.TestType.SECURITY
        self.tc.save(update_fields=['test_type'])
        execution = TestExecution.objects.create(
            project=self.project,
            testcase=self.tc,
            triggered_by=self.user,
            status=TestExecution.Status.PENDING,
        )

        run_test_execution(execution=execution)
        execution.refresh_from_db()

        self.assertEqual(execution.status, TestExecution.Status.FAILED)
        self.assertEqual(execution.exit_code, 1)
        self.assertIn('not implemented yet', execution.result_summary)
        run_mock.assert_not_called()


class TestExecutionApiTests(APITestCase):
    def setUp(self):
        self.dev = User.objects.create_user(username='exec_dev', password='pass123456')
        self.dev.profile.role = 'developer'
        self.dev.profile.save()

        self.tester = User.objects.create_user(username='exec_tester', password='pass123456')
        self.tester.profile.role = 'tester'
        self.tester.profile.save()

        self.other_dev = User.objects.create_user(username='exec_other_dev', password='pass123456')
        self.other_dev.profile.role = 'developer'
        self.other_dev.profile.save()

        self.project = Project.objects.create(name='Execution Project', description='', owner=self.dev)
        self.other_project = Project.objects.create(name='Other Project', description='', owner=self.other_dev)

        self.tc = TC.objects.create(
            project=self.project,
            title='Runnable case',
            description='',
            steps='',
            expected_result='',
            created_by=self.dev,
        )
        self.other_tc = TC.objects.create(
            project=self.other_project,
            title='Hidden case',
            description='',
            steps='',
            expected_result='',
            created_by=self.other_dev,
        )

        ProjectMember.objects.create(project=self.project, user=self.tester, role_in_project='tester')

    def auth(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    @patch('executions.views.run_test_execution_task.delay')
    def test_run_execution_creates_pending_execution_and_dispatches_task(self, delay_mock):
        self.auth(self.dev)
        resp = self.client.post(
            '/api/executions/run/',
            {'project': self.project.id, 'testcase': self.tc.id},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        execution = TestExecution.objects.get(id=resp.data['id'])
        self.assertEqual(execution.project_id, self.project.id)
        self.assertEqual(execution.testcase_id, self.tc.id)
        self.assertEqual(execution.triggered_by_id, self.dev.id)
        self.assertEqual(execution.status, TestExecution.Status.PENDING)
        delay_mock.assert_called_once_with(execution.id)

    def test_run_execution_requires_auth(self):
        resp = self.client.post(
            '/api/executions/run/',
            {'project': self.project.id, 'testcase': self.tc.id},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tester_cannot_run_execution(self):
        self.auth(self.tester)
        resp = self.client.post(
            '/api/executions/run/',
            {'project': self.project.id, 'testcase': self.tc.id},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_developer_cannot_run_hidden_project_execution(self):
        self.auth(self.dev)
        resp = self.client.post(
            '/api/executions/run/',
            {'project': self.other_project.id, 'testcase': self.other_tc.id},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
