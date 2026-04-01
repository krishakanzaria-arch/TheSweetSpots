from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class DashboardAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user('staff', password='pass')
        self.staff.is_staff = True
        self.staff.save()
        self.user = User.objects.create_user('user', password='pass')

    def test_anonymous_gets_redirect_to_signin(self):
        resp = self.client.get(reverse('dashboard:home'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('auth-signin', resp['Location'])

    def test_non_staff_forbidden(self):
        self.client.login(username='user', password='pass')
        resp = self.client.get(reverse('dashboard:home'))
        self.assertEqual(resp.status_code, 403)

    def test_staff_can_access(self):
        self.client.login(username='staff', password='pass')
        resp = self.client.get(reverse('dashboard:home'))
        self.assertEqual(resp.status_code, 200)

    def test_post_signin_redirect(self):
        resp = self.client.post(reverse('dashboard:page', kwargs={'page_name':'auth-signin'}), {'username': 'staff', 'password': 'pass'})
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('dashboard:home'), resp['Location'])

    def test_post_signin_invalid_shows_error(self):
        resp = self.client.post(reverse('dashboard:page', kwargs={'page_name':'auth-signin'}), {'username': 'staff', 'password': 'wrong'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Invalid username or password.')
