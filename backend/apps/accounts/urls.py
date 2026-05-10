"""
Accounts URL configuration.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='auth-register'),
    path('login/', views.LoginView.as_view(), name='auth-login'),
    path('logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('me/', views.UserProfileView.as_view(), name='auth-me'),
    path('me/info/', views.TokenRefreshInfoView.as_view(), name='auth-me-info'),
    path('me/password/', views.PasswordChangeView.as_view(), name='auth-password-change'),
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('company/', views.CompanyView.as_view(), name='company-detail'),
    path('company/create/', views.CompanyCreateView.as_view(), name='company-create'),
    path('company/members/', views.UserCompanyView.as_view(), name='company-members'),
]
