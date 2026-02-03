from django.test import TestCase
from django.urls import reverse
from .models import User

class UserAuthTests(TestCase):
    def test_registration_flow(self):
        # Step 1
        response = self.client.post(reverse('register'), {
            'email': 'newplayer@example.com',
            'phone_number': '0722000000',
            'password1': '1234'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('register_step2'))
        
        # Step 2
        response = self.client.post(reverse('register_step2'), {
            'gamer_tag': 'UniqueGamer123',
            'full_name': 'New Player',
            'county': 'Nairobi'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('profile'))
        
        user = User.objects.get(email='newplayer@example.com')
        self.assertEqual(user.gamer_tag, 'UniqueGamer123')
        self.assertEqual(user.full_name, 'New Player')

    def test_login(self):
        user = User.objects.create_user(
            username='player1',
            email='player1@example.com',
            phone_number='0711111111',
            password='password123',
            full_name='Player One',
            county='Mombasa'
        )
        response = self.client.post(reverse('login'), {
            'username': 'player1@example.com', # We use email as USERNAME_FIELD
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('profile'))

    def test_profile_view_protected(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
