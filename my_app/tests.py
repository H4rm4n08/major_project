from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User


class HomeViewTests(TestCase):
    def test_redirects_to_login_when_unauthenticated(self):
        response = self.client.get(reverse("my_app:home"))
        self.assertRedirects(response, "/users/login/?next=/")

    def test_accessible_when_authenticated(self):
        User.objects.create_user(username="testuser", password="testpass")
        self.client.login(username="testuser", password="testpass")
        response = self.client.get(reverse("my_app:home"))
        self.assertEqual(response.status_code, 200)
