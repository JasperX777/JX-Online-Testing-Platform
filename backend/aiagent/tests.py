from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from executions.models import TestExecution
from projects.models import Project
from testcases.models import TestCase

from .models import AIAgentMessage, AIAgentSession

User = get_user_model()


class AIAgentApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ai_user', password='pass123456')
        self.user.profile.role = 'user'
        self.user.profile.save()
        self.project = Project.objects.create(
            name='Login Project',
            description='Browser authentication checks',
            owner=self.user,
        )

        self.other_user = User.objects.create_user(username='other_ai_user', password='pass123456')
        self.other_user.profile.role = 'user'
        self.other_user.profile.save()
        self.other_project = Project.objects.create(name='Hidden Project', description='', owner=self.other_user)

    def auth(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    @patch('aiagent.services.dispatch_test_execution')
    def test_chat_generates_and_runs_testcases_when_requested(self, dispatch_mock):
        self.auth()
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(
            '/api/ai-agent/chat/',
            {'message': 'Generate login test cases for Login Project and run them'},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['needs_project_confirmation'])
        self.assertTrue(resp.data['auto_run'])
        self.assertEqual(resp.data['matched_project']['id'], self.project.id)
        self.assertEqual(len(resp.data['generated_testcases']), 3)
        self.assertEqual(len(resp.data['executions']), 3)
        self.assertEqual(TestCase.objects.filter(project=self.project, created_by=self.user).count(), 3)
        self.assertEqual(TestExecution.objects.filter(project=self.project, triggered_by=self.user).count(), 3)
        self.assertEqual(dispatch_mock.call_count, 3)

    def test_generated_login_case_uses_configured_target_base_url(self):
        self.auth()
        with self.settings(AI_AGENT_TARGET_BASE_URL='http://nginx'):
            resp = self.client.post(
                '/api/ai-agent/chat/',
                {'message': 'Generate login test cases for Login Project'},
                format='json',
            )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        first_case = resp.data['generated_testcases'][0]
        self.assertEqual(first_case['steps_json'][1]['value'], 'http://nginx/login')
        self.assertEqual(first_case['steps_json'][2]['selector'], 'input:not([type])')
        self.assertEqual(first_case['steps_json'][3]['selector'], "input[type='password']")

    def test_search_case_can_target_google_platform(self):
        self.auth()
        resp = self.client.post(
            '/api/ai-agent/chat/',
            {'message': 'Generate search test cases for Google platform in Login Project'},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        first_case = resp.data['generated_testcases'][0]
        self.assertEqual(first_case['module'], 'Search')
        self.assertEqual(first_case['steps_json'][1]['value'], 'https://www.google.com/')

    def test_search_case_uses_explicit_url(self):
        self.auth()
        resp = self.client.post(
            '/api/ai-agent/chat/',
            {'message': 'Generate search test cases for https://www.example.com/catalog in Login Project'},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        first_case = resp.data['generated_testcases'][0]
        self.assertEqual(first_case['steps_json'][1]['value'], 'https://www.example.com/catalog/')

    def test_chat_asks_for_project_when_missing(self):
        self.auth()
        resp = self.client.post(
            '/api/ai-agent/chat/',
            {'message': 'Generate login test cases'},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['needs_project_confirmation'])
        self.assertEqual(resp.data['project_candidates'][0]['id'], self.project.id)
        self.assertFalse(TestCase.objects.exists())

    @patch('aiagent.services.dispatch_test_execution')
    def test_project_confirmation_uses_pending_request(self, dispatch_mock):
        self.auth()
        first = self.client.post('/api/ai-agent/chat/', {'message': 'Generate login test cases and run them'}, format='json')
        session_id = first.data['session']['id']

        with self.captureOnCommitCallbacks(execute=True):
            second = self.client.post(
                '/api/ai-agent/chat/',
                {'session_id': session_id, 'message': 'Login Project'},
                format='json',
            )

        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertFalse(second.data['needs_project_confirmation'])
        self.assertTrue(second.data['auto_run'])
        self.assertEqual(TestCase.objects.filter(project=self.project).count(), 3)
        dispatch_mock.assert_called()

    def test_chat_does_not_match_invisible_project(self):
        self.auth()
        resp = self.client.post(
            '/api/ai-agent/chat/',
            {'message': 'Generate login test cases for Hidden Project'},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['needs_project_confirmation'])
        self.assertNotIn(self.other_project.id, [item['id'] for item in resp.data['project_candidates']])

    def test_session_history_is_persisted(self):
        self.auth()
        self.client.post('/api/ai-agent/chat/', {'message': 'Generate login test cases'}, format='json')

        resp = self.client.get('/api/ai-agent/sessions/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(len(resp.data[0]['messages']), 2)
        self.assertEqual(AIAgentSession.objects.count(), 1)
        self.assertEqual(AIAgentMessage.objects.count(), 2)

    def test_delete_session_removes_own_history(self):
        self.auth()
        created = self.client.post('/api/ai-agent/chat/', {'message': 'Generate login test cases'}, format='json')
        session_id = created.data['session']['id']

        resp = self.client.delete(f'/api/ai-agent/sessions/{session_id}/')

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AIAgentSession.objects.filter(id=session_id).exists())
        self.assertEqual(AIAgentMessage.objects.count(), 0)
