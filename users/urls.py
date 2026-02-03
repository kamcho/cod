from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('register/step2/', views.register_step2_view, name='register_step2'),
    path('register/check-gamer-tag/', views.check_gamer_tag, name='check_gamer_tag'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
]
