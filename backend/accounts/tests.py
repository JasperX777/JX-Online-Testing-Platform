from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class AccountsApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='acc_test_user',
            password='pass123456',
            email='acc@test.com',
        )
        self.user.profile.role = 'developer'
        self.user.profile.save()

    def auth(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_token_obtain_pair_success(self):
        resp = self.client.post(
            '/api/auth/token/',
            {'username': 'acc_test_user', 'password': 'pass123456'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)

    def test_me_requires_auth(self):
        resp = self.client.get('/api/auth/me/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_user_and_role(self):
        self.auth(self.user)
        resp = self.client.get('/api/auth/me/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['username'], 'acc_test_user')
        self.assertEqual(resp.data['role'], 'developer')
