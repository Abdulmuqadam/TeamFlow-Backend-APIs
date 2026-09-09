from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User


class UserManagerTests(APITestCase):
	def test_create_user_requires_email(self):
		with self.assertRaisesMessage(ValueError, "Email is required"):
			User.objects.create_user("", "Missing Email", "password123")

	def test_create_superuser_sets_staff_and_superuser_flags(self):
		user = User.objects.create_superuser(
			"admin@example.com", "Admin User", "password123"
		)

		self.assertTrue(user.is_staff)
		self.assertTrue(user.is_superuser)
		self.assertTrue(user.check_password("password123"))


class UserApiTests(APITestCase):
	register_url = reverse("register")
	login_url = reverse("token_obtain_pair")
	refresh_url = reverse("token_refresh")
	me_url = reverse("user-detail")

	def test_register_creates_user_with_hashed_password(self):
		response = self.client.post(
			self.register_url,
			{
				"email": "user@example.com",
				"full_name": "Test User",
				"password": "password123",
			},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		user = User.objects.get(email="user@example.com")
		self.assertTrue(user.check_password("password123"))
		self.assertNotEqual(user.password, "password123")
		self.assertNotIn("password", response.data)

	def test_register_rejects_short_password_and_invalid_email(self):
		short_password_response = self.client.post(
			self.register_url,
			{
				"email": "user@example.com",
				"full_name": "Test User",
				"password": "short",
			},
			format="json",
		)
		invalid_email_response = self.client.post(
			self.register_url,
			{
				"email": "not-an-email",
				"full_name": "Test User",
				"password": "password123",
			},
			format="json",
		)

		self.assertEqual(
			short_password_response.status_code, status.HTTP_400_BAD_REQUEST
		)
		self.assertEqual(
			invalid_email_response.status_code, status.HTTP_400_BAD_REQUEST
		)

	def test_register_rejects_duplicate_email(self):
		User.objects.create_user("user@example.com", "Existing User", "password123")

		response = self.client.post(
			self.register_url,
			{
				"email": "user@example.com",
				"full_name": "Duplicate User",
				"password": "password123",
			},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_login_returns_access_and_refresh_tokens(self):
		User.objects.create_user("user@example.com", "Test User", "password123")

		response = self.client.post(
			self.login_url,
			{"email": "user@example.com", "password": "password123"},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("access", response.data)
		self.assertIn("refresh", response.data)

	def test_refresh_returns_new_access_token(self):
		User.objects.create_user("user@example.com", "Test User", "password123")
		login_response = self.client.post(
			self.login_url,
			{"email": "user@example.com", "password": "password123"},
			format="json",
		)

		response = self.client.post(
			self.refresh_url,
			{"refresh": login_response.data["refresh"]},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("access", response.data)

	def test_invalid_credentials_are_rejected(self):
		User.objects.create_user("user@example.com", "Test User", "password123")

		response = self.client.post(
			self.login_url,
			{"email": "user@example.com", "password": "wrong-password"},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_me_requires_authentication_and_returns_current_user(self):
		unauthenticated_response = self.client.get(self.me_url)
		user = User.objects.create_user("user@example.com", "Test User", "password123")
		self.client.force_authenticate(user=user)

		authenticated_response = self.client.get(self.me_url)

		self.assertEqual(
			unauthenticated_response.status_code, status.HTTP_401_UNAUTHORIZED
		)
		self.assertEqual(authenticated_response.status_code, status.HTTP_200_OK)
		self.assertEqual(authenticated_response.data["email"], user.email)
		self.assertNotIn("password", authenticated_response.data)
