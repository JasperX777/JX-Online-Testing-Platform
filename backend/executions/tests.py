from unittest.mock import patch

from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from config.asgi import application
from projects.models import Project
from testcases.models import TestCase as TC
from .models import ExecutionLog, ExecutionReport, ExecutionStepResult, TestExecution
from .reports import store_execution_report
from .services import initialize_execution, run_test_execution

User = get_user_model()

IN_MEMORY_CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}


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
            'step_title': 'Open Google',
            'description': '',
            'action': 'open_page',
            'target': 'Google homepage',
            'locator_type': 'css',
            'selector': '',
            'value': 'https://www.google.com',
            'note': '',
        },
        {
            'step_no': 3,
            'step_title': 'Enter keyword',
            'description': '',
            'action': 'input_text',
            'target': 'Search input',
            'locator_type': 'css',
            'selector': "textarea[name='q']",
            'value': 'OpenAI',
            'note': '',
        },
        {
            'step_no': 4,
            'step_title': 'Submit with Enter',
            'description': '',
            'action': 'press_key',
            'target': '',
            'locator_type': 'css',
            'selector': '',
            'value': 'Enter',
            'note': '',
        },
        {
            'step_no': 5,
            'step_title': 'Submit search',
            'description': '',
            'action': 'click_button',
            'target': 'Google search button',
            'locator_type': 'css',
            'selector': "input[name='btnK']",
            'value': '',
            'note': '',
        },
    ]


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class ExecutionLogModelTests(TestCase):
    def test_create_execution_log(self):
        user = User.objects.create_user(username='exec_user', password='pass123456')
        project = Project.objects.create(name='Exec Project', description='', owner=user)
        tc = TC.objects.create(
            project=project,
            title='Sample case',
            description='',
            module='Search',
            scenario='Google',
            steps_json=sample_steps(),
            created_by=user,
        )
        execution = TestExecution.objects.create(project=project, testcase=tc, triggered_by=user)

        log = ExecutionLog.objects.create(
            execution=execution,
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
class TestExecutionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='exec_service_user', password='pass123456')
        self.user.profile.role = 'user'
        self.user.profile.save()

        self.project = Project.objects.create(name='Service Project', description='', owner=self.user)
        self.tc = TC.objects.create(
            project=self.project,
            title='Automated case',
            description='',
            module='Search',
            scenario='Google',
            created_by=self.user,
            steps_json=sample_steps(),
        )

    def test_initialize_execution_creates_step_snapshot(self):
        execution = TestExecution.objects.create(
            project=self.project,
            testcase=self.tc,
            triggered_by=self.user,
            status=TestExecution.Status.PENDING,
        )

        initialize_execution(execution=execution)
        execution.refresh_from_db()

        self.assertEqual(execution.status, TestExecution.Status.PENDING)
        self.assertEqual(execution.current_step_no, 1)
        self.assertEqual(execution.step_results.count(), 5)
        self.assertEqual(execution.step_results.first().selector, '')
        self.assertEqual(execution.step_results.first().step_title, 'Launch browser')

    @patch('executions.services.execute_steps')
    def test_run_execution_marks_success_when_automation_passes(self, execute_steps_mock):
        def fake_execute_steps(*, execution, step_results, on_step_start, on_step_pass, on_step_fail):
            for step_result in step_results:
                on_step_start(step_result)
                on_step_pass(step_result)
            return None

        execute_steps_mock.side_effect = fake_execute_steps

        execution = TestExecution.objects.create(
            project=self.project,
            testcase=self.tc,
            triggered_by=self.user,
            status=TestExecution.Status.PENDING,
        )
        initialize_execution(execution=execution)

        run_test_execution(execution=execution)
        execution.refresh_from_db()

        self.assertEqual(execution.status, TestExecution.Status.SUCCESS)
        self.assertIsNone(execution.current_step_no)
        self.assertEqual(execution.step_results.filter(status=ExecutionStepResult.Status.PASSED).count(), 5)
        self.assertTrue(ExecutionReport.objects.filter(execution=execution).exists())

    @patch('executions.services.execute_steps')
    def test_run_execution_records_failure_and_screenshot(self, execute_steps_mock):
        def fake_execute_steps(*, execution, step_results, on_step_start, on_step_pass, on_step_fail):
            on_step_start(step_results[2])
            on_step_pass(step_results[2])
            on_step_start(step_results[3])
            on_step_fail(step_results[3], 'Input did not appear', '/tmp/failure.png')
            return 'Input did not appear'

        execute_steps_mock.side_effect = fake_execute_steps

        execution = TestExecution.objects.create(
            project=self.project,
            testcase=self.tc,
            triggered_by=self.user,
            status=TestExecution.Status.PENDING,
        )
        initialize_execution(execution=execution)

        run_test_execution(execution=execution)
        execution.refresh_from_db()

        failed_step = execution.step_results.get(step_no=4)
        self.assertEqual(execution.status, TestExecution.Status.FAILED)
        self.assertEqual(execution.failed_step_no, 4)
        self.assertEqual(failed_step.error_message, 'Input did not appear')
        self.assertEqual(failed_step.screenshot_path, '/tmp/failure.png')
        self.assertEqual(execution.step_results.get(step_no=5).status, ExecutionStepResult.Status.PENDING)

    @patch('executions.services.execute_steps')
    def test_store_execution_report_contains_selector_and_screenshot(self, execute_steps_mock):
        def fake_execute_steps(*, execution, step_results, on_step_start, on_step_pass, on_step_fail):
            on_step_start(step_results[0])
            on_step_fail(step_results[0], 'Dependency missing', '/tmp/missing.png')
            return 'Dependency missing'

        execute_steps_mock.side_effect = fake_execute_steps

        execution = TestExecution.objects.create(
            project=self.project,
            testcase=self.tc,
            triggered_by=self.user,
            status=TestExecution.Status.PENDING,
        )
        initialize_execution(execution=execution)
        run_test_execution(execution=execution)
        execution.refresh_from_db()

        report = store_execution_report(execution=execution)

        self.assertEqual(report.report_data['summary']['failed_steps'], 1)
        self.assertEqual(report.report_data['steps'][0]['step_title'], 'Launch browser')
        self.assertEqual(report.report_data['steps'][0]['selector'], '')
        self.assertEqual(report.report_data['steps'][0]['screenshot_path'], '/tmp/missing.png')


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class TestExecutionApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='exec_dev', password='pass123456')
        self.user.profile.role = 'user'
        self.user.profile.save()

        self.project = Project.objects.create(name='Execution Project', description='', owner=self.user)
        self.tc = TC.objects.create(
            project=self.project,
            title='Automated case',
            description='',
            module='Search',
            scenario='Google',
            created_by=self.user,
            steps_json=sample_steps(),
        )

    def auth(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    @patch('executions.views.dispatch_test_execution')
    def test_run_execution_creates_pending_execution_and_snapshot(self, dispatch_mock):
        self.auth()
        resp = self.client.post(
            '/api/executions/run/',
            {'project': self.project.id, 'testcase': self.tc.id},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        execution = TestExecution.objects.get(id=resp.data['id'])
        self.assertEqual(execution.status, TestExecution.Status.PENDING)
        self.assertEqual(execution.current_step_no, 1)
        self.assertEqual(execution.step_results.count(), 5)
        dispatch_mock.assert_called_once_with(execution.id)

    def test_run_execution_requires_steps(self):
        empty_case = TC.objects.create(
            project=self.project,
            title='Empty',
            description='',
            module='Search',
            scenario='Empty',
            created_by=self.user,
            steps_json=[],
        )
        self.auth()
        resp = self.client.post(
            '/api/executions/run/',
            {'project': self.project.id, 'testcase': empty_case.id},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('testcase', resp.data)

    @patch('executions.views.dispatch_test_execution')
    def test_same_testcase_can_be_executed_multiple_times(self, dispatch_mock):
        self.auth()
        first = self.client.post(
            '/api/executions/run/',
            {'project': self.project.id, 'testcase': self.tc.id},
            format='json',
        )
        second = self.client.post(
            '/api/executions/run/',
            {'project': self.project.id, 'testcase': self.tc.id},
            format='json',
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TestExecution.objects.filter(testcase=self.tc).count(), 2)
        self.assertEqual(dispatch_mock.call_count, 2)


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class ExecutionRealtimeTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = User.objects.create_user(username='ws_user', password='pass123456')
        self.user.profile.role = 'user'
        self.user.profile.save()
        self.project = Project.objects.create(name='Realtime Project', description='', owner=self.user)
        self.tc = TC.objects.create(
            project=self.project,
            title='WS Case',
            description='',
            module='Search',
            scenario='Google',
            created_by=self.user,
            steps_json=sample_steps(),
        )
        self.execution = TestExecution.objects.create(
            project=self.project,
            testcase=self.tc,
            triggered_by=self.user,
            status=TestExecution.Status.PENDING,
        )
        initialize_execution(execution=self.execution)

    @patch('executions.services.execute_steps')
    def test_execution_socket_receives_updates(self, execute_steps_mock):
        def fake_execute_steps(*, execution, step_results, on_step_start, on_step_pass, on_step_fail):
            on_step_start(step_results[0])
            on_step_pass(step_results[0])
            return None

        execute_steps_mock.side_effect = fake_execute_steps

        async def runner():
            refresh = RefreshToken.for_user(self.user)
            communicator = WebsocketCommunicator(
                application,
                f'/ws/executions/{self.execution.id}/?token={refresh.access_token}',
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            await sync_to_async(run_test_execution)(execution=self.execution)
            message = await communicator.receive_json_from()
            await communicator.disconnect()
            return message

        message = async_to_sync(runner)()
        self.assertIn('event', message)
