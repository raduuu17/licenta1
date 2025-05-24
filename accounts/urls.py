from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.user_profile, name='profile'),
    path('profile/edit/', views.UpdateProfileView.as_view(), name='edit_profile'),
    path('preferences/', views.set_preferences, name='set_preferences'),
    path('preferences/edit/', views.UpdatePreferencesView.as_view(), name='edit_preferences'),
]