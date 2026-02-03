from django.test import TestCase
from django.urls import reverse

class HomeTests(TestCase):
    def test_landing_page_status_code(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_landing_page_template(self):
        response = self.client.get(reverse('home'))
        self.assertTemplateUsed(response, 'home/index.html')

    def test_landing_page_content(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, "ELITE TOURNAMENTS")
        self.assertContains(response, "Dominate the Competitive Scene")
