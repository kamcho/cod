from django.contrib import sitemaps
from django.urls import reverse
from .models import GameMode

class StaticViewSitemap(sitemaps.Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return ['home', 'leaderboard', 'recruitment_center', 'login', 'register']

    def location(self, item):
        return reverse(item)

class GameModeSitemap(sitemaps.Sitemap):
    priority = 0.9
    changefreq = 'monthly'

    def items(self):
        return GameMode.objects.all()

    def location(self, item):
        return reverse('gamemode_detail', args=[item.id])
