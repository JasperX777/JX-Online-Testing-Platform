from subprocess import CompletedProcess
from unittest.mock import patch

from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from config.asgi import application
from projects.models import Project, ProjectMember
from testcases.models import TestCase as TC
from .models import ExecutionLog, ExecutionReport, TestExecution
from .realtime import broadcast_execution_event
from .reports import store_execution_report
from .services import run_test_execution

User = get_user_model()

IN_MEMORY_CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}


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


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
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
            pytest_target='executions/tests.py::ExecutionLogApiTests::test_execution_logs_requires_auth',
        )
        self.execution = TestExecution.objects.create(
            project=self.project,
            testcase=self.tc,
            triggered_by=self.user,
            status=TestExecution.Status.PENDING,
        )
        ExecutionLog.objects.create(
            execution=self.execution,
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

    def test_filter_execution_logs_by_execution(self):
        self.auth()
        resp = self.client.get(f'/api/execution-logs/?execution_id={self.execution.id}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['execution'], self.execution.id)

    def test_execution_logs_requires_auth(self):
        resp = self.client.get('/api/execution-logs/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
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
    def test_functional_execution_uses_pytest_runner_and_creates_report(self, run_mock):
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
        self.assertTrue(hasattr(execution, 'report'))
        self.assertEqual(execution.report.report_data['execution']['status'], TestExecution.Status.SUCCESS)
        self.assertEqual(execution.report.report_data['totals']['log_count'], 2)
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
        self.assertTrue(ExecutionReport.objects.filter(execution=execution).exists())
        run_mock.assert_not_called()


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
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
            pytest_target='executions/tests.py::ExecutionLogApiTests::test_execution_logs_requires_auth',
        )
        self.unconfigured_tc = TC.objects.create(
            project=self.project,
            title='Missing target',
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
            pytest_target='executions/tests.py::ExecutionLogApiTests::test_execution_logs_requires_auth',
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

    def test_run_execution_requires_testcase(self):
        self.auth(self.dev)
        resp = self.client.post(
            '/api/executions/run/',
            {'project': self.project.id},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('testcase', resp.data)

    def test_run_execution_rejects_functional_testcase_without_pytest_target(self):
        self.auth(self.dev)
        resp = self.client.post(
            '/api/executions/run/',
            {'project': self.project.id, 'testcase': self.unconfigured_tc.id},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('testcase', resp.data)

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

    def test_execution_report_endpoint_returns_saved_report(self):
        self.auth(self.dev)
        execution = TestExecution.objects.create(
            project=self.project,
            testcase=self.tc,
            triggered_by=self.dev,
            status=TestExecution.Status.SUCCESS,
            exit_code=0,
            result_summary='1 passed in 0.10s',
        )
        ExecutionLog.objects.create(
            execution=execution,
            project=self.project,
            testcase=self.tc,
            level=ExecutionLog.Level.INFO,
            message='Execution finished.',
        )
        report = store_execution_report(execution=execution)

        resp = self.client.get(f'/api/executions/{execution.id}/report/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['id'], report.id)
        self.assertEqual(resp.data['execution'], execution.id)
        self.assertEqual(resp.data['report_data']['execution']['status'], TestExecution.Status.SUCCESS)


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class ExecutionRealtimeTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ws_user', password='pass123456')
        self.user.profile.role = 'developer'
        self.user.profile.save()

        self.project = Project.objects.create(name='Realtime Project', description='', owner=self.user)
        self.testcase = TC.objects.create(
            project=self.project,
            title='Realtime case',
            description='',
            steps='',
            expected_result='',
            created_by=self.user,
            pytest_target='executions/tests.py::ExecutionLogApiTests::test_execution_logs_requires_auth',
        )
        self.execution = TestExecution.objects.create(
            project=self.project,
            testcase=self.testcase,
            triggered_by=self.user,
            status=TestExecution.Status.PENDING,
        )
        self.log = ExecutionLog.objects.create(
            execution=self.execution,
            project=self.project,
            testcase=self.testcase,
            level=ExecutionLog.Level.INFO,
            message='Realtime log message',
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)

    async def _exercise_execution_socket(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/executions/{self.execution.id}/?token={self.token}',
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        ready_payload = await communicator.receive_json_from()
        self.assertEqual(ready_payload['event'], 'connection.ready')
        self.assertEqual(ready_payload['execution_id'], self.execution.id)

        await sync_to_async(broadcast_execution_event, thread_sensitive=True)(
            event='execution.log',
            execution=self.execution,
            log=self.log,
        )

        event_payload = await communicator.receive_json_from()
        self.assertEqual(event_payload['event'], 'execution.log')
        self.assertEqual(event_payload['execution']['id'], self.execution.id)
        self.assertEqual(event_payload['log']['id'], self.log.id)

        await communicator.disconnect()

    def test_execution_websocket_streams_broadcast_events(self):
        async_to_sync(self._exercise_execution_socket)()
