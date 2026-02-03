from django.urls import path
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from . import views
from .sitemaps import StaticViewSitemap, GameModeSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'gamemodes': GameModeSitemap,
}

urlpatterns = [
    path('', views.landing_page_view, name='home'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('sitemap.xml', views.sitemap_view, name='django.contrib.sitemaps.views.sitemap'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('cohort/<int:cohort_id>/join/', views.join_cohort_view, name='join_cohort'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('player/<str:gamer_tag>/analytics/', views.player_analytics_view, name='player_analytics'),
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('fixture-solo/<int:fixture_id>/record-stats/', views.record_solo_stats_view, name='record_solo_stats'),
    path('fixture-team/<int:fixture_id>/record-stats/', views.record_team_stats_view, name='record_team_stats'),
    
    # Squad Management
    path('squad/create/', views.create_squad_view, name='create_squad'),
    path('squad/<int:team_id>/manage/', views.manage_squad_view, name='manage_squad'),
    path('invite/<int:invite_id>/respond/', views.respond_invite_view, name='respond_invite'),
    
    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),
    path('notification/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # Brackets
    path('cohort/<int:cohort_id>/brackets/', views.bracket_view, name='brackets'),
    
    # Game Modes & M-Pesa
    path('gamemode/<int:mode_id>/', views.gamemode_detail_view, name='gamemode_detail'),
    path('gamemode/<int:mode_id>/pay/<int:cohort_id>/', views.initiate_payment_view, name='initiate_payment'),
    path('mpesa/callback/', views.mpesa_callback_view, name='mpesa_callback'),
    # Recruitment
    path('recruitment/', views.recruitment_center_view, name='recruitment_center'),
    path('recruitment/post-agent/', views.post_free_agent_view, name='post_free_agent'),
    path('recruitment/post-squad/', views.post_squad_recruitment_view, name='post_squad_recruitment'),
    path('recruitment/apply/<int:recruitment_id>/', views.apply_to_squad_view, name='apply_to_squad'),
    path('recruitment/manage-request/<int:request_id>/<str:action>/', views.manage_join_request_view, name='manage_join_request'),
    path('recruitment/deactivate-squad/<int:recruitment_id>/', views.deactivate_recruitment_view, name='deactivate_recruitment'),
    path('recruitment/deactivate-agent/', views.deactivate_free_agent_view, name='deactivate_free_agent'),
    path('ai-chat/', views.ai_chat_view, name='ai_chat'),
]
