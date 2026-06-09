from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from config.asgi import application
from projects.models import Project
from testcases.models import TestCase as TC
from .models import ExecutionLog, ExecutionReport, ExecutionSchedule, ExecutionStepResult, TestExecution
from .automation import (
    UnsupportedAutomationActionError,
    _build_screenshot_path,
    _build_video_dir,
    _capture_failure_screenshot,
    _collect_video_path,
    _ensure_browser_session,
    _get_browser_launcher,
    _pause_for_recording,
    _run_step,
)
from .reports import store_execution_report
from .services import create_execution, initialize_execution, run_test_execution
from .tasks import dispatch_due_execution_schedules, run_test_execution_task

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


class AutomationHelperTests(TestCase):
    def test_browser_aliases_and_session_creation(self):
        chromium_launcher = MagicMock()
        webkit_launcher = MagicMock()
        browser = chromium_launcher.launch.return_value
        context = browser.new_context.return_value
        page = context.new_page.return_value
        playwright = SimpleNamespace(chromium=chromium_launcher, webkit=webkit_launcher)

        launcher, browser_name = _get_browser_launcher(playwright, 'chrome')
        self.assertIs(launcher, chromium_launcher)
        self.assertEqual(browser_name, 'chromium')
        self.assertEqual(_get_browser_launcher(playwright, 'safari')[1], 'webkit')
        with self.assertRaises(UnsupportedAutomationActionError):
            _get_browser_launcher(playwright, 'opera')

        created = _ensure_browser_session(
            playwright=playwright,
            browser_name='chrome',
            execution_id=12,
            browser=None,
            context=None,
            page=None,
        )
        self.assertEqual(created, (browser, context, page))
        chromium_launcher.launch.assert_called_once_with(headless=True)
        self.assertEqual(
            _ensure_browser_session(
                playwright=playwright,
                browser_name='chrome',
                execution_id=12,
                browser=browser,
                context=context,
                page=page,
            ),
            (browser, context, page),
        )

    def test_run_step_supports_structured_browser_actions_and_input_fallback(self):
        page = MagicMock()
        locator = page.locator.return_value

        _run_step(page, SimpleNamespace(action='launch_browser', selector='', value='chromium'))
        _run_step(page, SimpleNamespace(action='open_page', selector='', value='https://example.com'))
        page.goto.assert_called_once_with('https://example.com', wait_until='domcontentloaded')

        _run_step(page, SimpleNamespace(action='input_text', selector='#name', value='Jasper'))
        locator.click.assert_called()
        locator.fill.assert_called_once_with('')
        locator.press_sequentially.assert_called_once_with('Jasper', delay=45)

        locator.press_sequentially.side_effect = AttributeError
        _run_step(page, SimpleNamespace(action='input_text', selector='#name', value='Fallback'))
        page.keyboard.type.assert_called_once_with('Fallback', delay=45)

        _run_step(page, SimpleNamespace(action='click_button', selector='#submit', value=''))
        _run_step(page, SimpleNamespace(action='press_key', selector='', value='Enter'))
        _run_step(page, SimpleNamespace(action='verify_element', selector='#result', value=''))
        page.keyboard.press.assert_called_once_with('Enter')
        page.locator.return_value.wait_for.assert_called_once_with(state='visible')

        with self.assertRaises(UnsupportedAutomationActionError):
            _run_step(page, SimpleNamespace(action='unknown', selector='', value=''))

    def test_media_helpers_capture_and_find_latest_video(self):
        with TemporaryDirectory() as temp_dir:
            media_root = Path(temp_dir)
            screenshot_dir = media_root / 'screenshots'
            video_dir = media_root / 'videos'
            page = MagicMock()

            with override_settings(EXECUTION_SCREENSHOT_DIR=screenshot_dir, EXECUTION_VIDEO_DIR=video_dir):
                screenshot_path = _capture_failure_screenshot(page, execution_id=4, step_no=2)
                self.assertEqual(Path(screenshot_path), _build_screenshot_path(execution_id=4, step_no=2))
                self.assertTrue(_build_video_dir(execution_id=4).exists())
                page.screenshot.assert_called_once_with(path=screenshot_path, full_page=True)

                page.video.path.return_value = '/tmp/video.webm'
                self.assertEqual(_collect_video_path(page, execution_id=4), '/tmp/video.webm')
                _pause_for_recording(page, milliseconds=25)
                page.wait_for_timeout.assert_called_once_with(25)


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

    def test_create_execution_creates_pending_snapshot(self):
        execution = create_execution(project=self.project, testcase=self.tc, triggered_by=self.user)

        self.assertEqual(execution.status, TestExecution.Status.PENDING)
        self.assertEqual(execution.current_step_no, 1)
        self.assertEqual(execution.step_results.count(), len(sample_steps()))

    @patch('executions.services.execute_steps')
    def test_run_execution_marks_success_when_automation_passes(self, execute_steps_mock):
        execute_steps_mock.return_value = {
            'video_path': '/tmp/execution.webm',
            'outcomes': [
                {'step_no': step['step_no'], 'status': 'passed', 'error_message': '', 'screenshot_path': ''}
                for step in sample_steps()
            ],
        }

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
        self.assertEqual(execution.video_path, '/tmp/execution.webm')
        self.assertEqual(execution.step_results.filter(status=ExecutionStepResult.Status.PASSED).count(), 5)
        self.assertTrue(ExecutionReport.objects.filter(execution=execution).exists())

    @patch('executions.services.execute_steps')
    def test_run_execution_records_failure_and_video(self, execute_steps_mock):
        execute_steps_mock.return_value = {
            'video_path': '/tmp/execution.webm',
            'outcomes': [
                {'step_no': 3, 'status': 'passed', 'error_message': '', 'screenshot_path': ''},
                {'step_no': 4, 'status': 'failed', 'error_message': 'Input did not appear', 'screenshot_path': ''},
            ],
        }

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
        self.assertEqual(execution.video_path, '/tmp/execution.webm')
        self.assertEqual(failed_step.error_message, 'Input did not appear')
        self.assertEqual(failed_step.screenshot_path, '')
        self.assertEqual(execution.step_results.get(step_no=5).status, ExecutionStepResult.Status.PENDING)

    @patch('executions.services.execute_steps')
    def test_store_execution_report_contains_selector_and_video(self, execute_steps_mock):
        execute_steps_mock.return_value = {
            'video_path': '/tmp/missing.webm',
            'outcomes': [
                {'step_no': 1, 'status': 'failed', 'error_message': 'Dependency missing', 'screenshot_path': ''},
            ],
        }

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
        self.assertEqual(report.report_data['execution']['video_path'], '/tmp/missing.webm')
        self.assertEqual(report.report_data['steps'][0]['step_title'], 'Launch browser')
        self.assertEqual(report.report_data['steps'][0]['selector'], '')
        self.assertEqual(report.report_data['steps'][0]['screenshot_path'], '')


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

    @patch('executions.views.dispatch_test_execution', side_effect=ConnectionError('broker unavailable'))
    def test_dispatch_failure_is_recorded_and_returns_service_unavailable(self, dispatch_mock):
        self.auth()

        response = self.client.post(
            '/api/executions/run/',
            {'project': self.project.id, 'testcase': self.tc.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        execution = TestExecution.objects.get(id=response.data['id'])
        self.assertEqual(execution.status, TestExecution.Status.FAILED)
        self.assertIn('broker unavailable', execution.failure_reason)
        self.assertTrue(execution.logs.filter(level=ExecutionLog.Level.ERROR).exists())
        self.assertTrue(ExecutionReport.objects.filter(execution=execution).exists())
        dispatch_mock.assert_called_once_with(execution.id)

    def test_delete_execution_removes_media_files(self):
        with TemporaryDirectory() as temp_dir:
            media_root = Path(temp_dir)
            video_dir = media_root / 'execution_videos' / 'execution_99'
            screenshot_dir = media_root / 'execution_screenshots'
            video_dir.mkdir(parents=True)
            screenshot_dir.mkdir(parents=True)
            video_path = video_dir / 'run.webm'
            screenshot_path = screenshot_dir / 'failure.png'
            video_path.write_bytes(b'video')
            screenshot_path.write_bytes(b'image')

            with override_settings(
                MEDIA_ROOT=media_root,
                EXECUTION_VIDEO_DIR=media_root / 'execution_videos',
                EXECUTION_SCREENSHOT_DIR=screenshot_dir,
            ):
                execution = TestExecution.objects.create(
                    project=self.project,
                    testcase=self.tc,
                    triggered_by=self.user,
                    status=TestExecution.Status.SUCCESS,
                    video_path=str(video_path),
                )
                initialize_execution(execution=execution)
                execution.video_path = str(video_path)
                execution.save(update_fields=['video_path'])
                step = execution.step_results.first()
                step.screenshot_path = str(screenshot_path)
                step.save(update_fields=['screenshot_path'])

                self.auth()
                resp = self.client.delete(f'/api/executions/{execution.id}/')

                self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
                self.assertFalse(video_path.exists())
                self.assertFalse(video_dir.exists())
                self.assertFalse(screenshot_path.exists())


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class ExecutionScheduleApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='schedule_user', password='pass123456')
        self.other_user = User.objects.create_user(username='schedule_other', password='pass123456')
        self.project = Project.objects.create(name='Schedule Project', description='', owner=self.user)
        self.other_project = Project.objects.create(name='Other Project', description='', owner=self.other_user)
        self.tc = TC.objects.create(
            project=self.project,
            title='Scheduled case',
            module='Search',
            scenario='Scheduled Google',
            created_by=self.user,
            steps_json=sample_steps(),
        )
        self.other_tc = TC.objects.create(
            project=self.other_project,
            title='Other case',
            module='Search',
            scenario='Other Google',
            created_by=self.other_user,
            steps_json=sample_steps(),
        )

    def auth(self, user=None):
        refresh = RefreshToken.for_user(user or self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_create_and_cancel_future_schedule(self):
        self.auth()
        response = self.client.post(
            '/api/execution-schedules/',
            {
                'project': self.project.id,
                'testcase': self.tc.id,
                'scheduled_for': (timezone.now() + timedelta(hours=1)).isoformat(),
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], ExecutionSchedule.Status.PENDING)

        cancel_response = self.client.post(f"/api/execution-schedules/{response.data['id']}/cancel/", {}, format='json')
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_response.data['status'], ExecutionSchedule.Status.CANCELLED)

    def test_rejects_past_schedule_and_project_mismatch(self):
        self.auth()
        past_response = self.client.post(
            '/api/execution-schedules/',
            {
                'project': self.project.id,
                'testcase': self.tc.id,
                'scheduled_for': (timezone.now() - timedelta(minutes=1)).isoformat(),
            },
            format='json',
        )
        mismatch_response = self.client.post(
            '/api/execution-schedules/',
            {
                'project': self.project.id,
                'testcase': self.other_tc.id,
                'scheduled_for': (timezone.now() + timedelta(hours=1)).isoformat(),
            },
            format='json',
        )

        self.assertEqual(past_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('scheduled_for', past_response.data)
        self.assertEqual(mismatch_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('testcase', mismatch_response.data)

    def test_user_cannot_schedule_or_view_another_users_project(self):
        hidden_schedule = ExecutionSchedule.objects.create(
            project=self.other_project,
            testcase=self.other_tc,
            created_by=self.other_user,
            scheduled_for=timezone.now() + timedelta(hours=1),
        )
        self.auth()
        create_response = self.client.post(
            '/api/execution-schedules/',
            {
                'project': self.other_project.id,
                'testcase': self.other_tc.id,
                'scheduled_for': (timezone.now() + timedelta(hours=1)).isoformat(),
            },
            format='json',
        )
        list_response = self.client.get('/api/execution-schedules/')

        self.assertEqual(create_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn(hidden_schedule.id, [item['id'] for item in list_response.data])


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class ExecutionScheduleTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='schedule_task_user', password='pass123456')
        self.project = Project.objects.create(name='Task Project', description='', owner=self.user)
        self.tc = TC.objects.create(
            project=self.project,
            title='Due case',
            module='Search',
            scenario='Due Google',
            created_by=self.user,
            steps_json=sample_steps(),
        )

    @patch('executions.tasks.dispatch_test_execution')
    def test_dispatches_due_schedule_once_and_skips_cancelled_schedule(self, dispatch_mock):
        due = ExecutionSchedule.objects.create(
            project=self.project,
            testcase=self.tc,
            created_by=self.user,
            scheduled_for=timezone.now() - timedelta(minutes=1),
        )
        ExecutionSchedule.objects.create(
            project=self.project,
            testcase=self.tc,
            created_by=self.user,
            scheduled_for=timezone.now() - timedelta(minutes=1),
            status=ExecutionSchedule.Status.CANCELLED,
        )

        first_result = dispatch_due_execution_schedules()
        second_result = dispatch_due_execution_schedules()
        due.refresh_from_db()

        self.assertEqual(len(first_result), 1)
        self.assertEqual(second_result, [])
        self.assertEqual(due.status, ExecutionSchedule.Status.DISPATCHED)
        self.assertIsNotNone(due.execution)
        self.assertEqual(due.execution.step_results.count(), len(sample_steps()))
        dispatch_mock.assert_called_once_with(due.execution_id)

    @patch('executions.tasks.run_test_execution', side_effect=RuntimeError('permanent worker failure'))
    def test_execution_task_records_failure_after_maximum_retries(self, run_mock):
        execution = create_execution(project=self.project, testcase=self.tc, triggered_by=self.user)

        with patch.object(run_test_execution_task.request, 'retries', run_test_execution_task.max_retries):
            with self.assertRaises(RuntimeError):
                run_test_execution_task._orig_run(execution.id)
        execution.refresh_from_db()

        run_mock.assert_called_once()
        self.assertEqual(execution.status, TestExecution.Status.FAILED)
        self.assertIn('failed after 4 attempts', execution.failure_reason)
        self.assertTrue(execution.logs.filter(level=ExecutionLog.Level.ERROR).exists())

    @patch('executions.tasks.dispatch_test_execution', side_effect=ConnectionError('redis unavailable'))
    def test_marks_schedule_and_execution_failed_when_dispatch_fails(self, dispatch_mock):
        due = ExecutionSchedule.objects.create(
            project=self.project,
            testcase=self.tc,
            created_by=self.user,
            scheduled_for=timezone.now() - timedelta(minutes=1),
        )

        result = dispatch_due_execution_schedules()
        due.refresh_from_db()

        self.assertEqual(result, [])
        self.assertEqual(due.status, ExecutionSchedule.Status.FAILED)
        self.assertIn('redis unavailable', due.failure_reason)
        self.assertEqual(due.execution.status, TestExecution.Status.FAILED)
        self.assertTrue(due.execution.logs.filter(level=ExecutionLog.Level.ERROR).exists())
        dispatch_mock.assert_called_once_with(due.execution_id)


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class ExecutionAnalyticsApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='analytics_user', password='pass123456')
        self.other_user = User.objects.create_user(username='analytics_other', password='pass123456')
        self.project = Project.objects.create(name='Analytics Project', description='', owner=self.user)
        self.other_project = Project.objects.create(name='Other Analytics', description='', owner=self.other_user)
        self.tc = TC.objects.create(project=self.project, title='Case', created_by=self.user, steps_json=sample_steps())
        self.other_tc = TC.objects.create(project=self.other_project, title='Other', created_by=self.other_user, steps_json=sample_steps())

        for execution_status in [TestExecution.Status.SUCCESS, TestExecution.Status.SUCCESS, TestExecution.Status.FAILED]:
            TestExecution.objects.create(
                project=self.project,
                testcase=self.tc,
                triggered_by=self.user,
                status=execution_status,
            )
        TestExecution.objects.create(
            project=self.other_project,
            testcase=self.other_tc,
            triggered_by=self.other_user,
            status=TestExecution.Status.FAILED,
        )

    def test_analytics_calculates_trend_and_hides_other_users_executions(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = self.client.get('/api/executions/analytics/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 3)
        self.assertEqual(response.data['status_counts']['success'], 2)
        self.assertEqual(response.data['status_counts']['failed'], 1)
        self.assertEqual(response.data['pass_rate'], 66.7)
        self.assertEqual(len(response.data['trend']), 7)
        self.assertEqual(response.data['trend'][-1]['total'], 3)


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
        execute_steps_mock.return_value = {
            'video_path': '/tmp/ws.webm',
            'outcomes': [
                {'step_no': 1, 'status': 'passed', 'error_message': '', 'screenshot_path': ''},
            ],
        }

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
