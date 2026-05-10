"""
Accounts views: Login, Logout, Profile, Company, Register
"""
import logging

from django.contrib.auth import logout
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import CustomUser, Company, UserCompany
from .serializers import (
    UserSerializer, UserCreateSerializer, LoginSerializer,
    TokenSerializer, CompanySerializer, UserCompanySerializer,
    PasswordChangeSerializer,
)

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    """Register a new user account."""
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token_data = TokenSerializer.get_token_for_user(user, request)
        logger.info(f"New user registered: {user.email}")
        return Response(
            {
                'message': 'Registration successful.',
                **token_data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Authenticate and receive JWT tokens."""
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token_data = TokenSerializer.get_token_for_user(user, request)
        logger.info(f"User logged in: {user.email}")
        return Response(
            {
                'message': 'Login successful.',
                **token_data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """Invalidate the refresh token (blacklist it)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info(f"User logged out: {request.user.email}")
            return Response({'message': 'Logout successful.'}, status=status.HTTP_200_OK)
        except TokenError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get or update the current user's profile."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


class PasswordChangeView(APIView):
    """Change the current user's password."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        logger.info(f"Password changed for: {request.user.email}")
        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)


class UserListView(generics.ListAPIView):
    """List all users (admin only)."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['email', 'first_name', 'last_name']

    def get_queryset(self):
        if self.request.user.role in [CustomUser.Role.ADMIN]:
            return CustomUser.objects.all().order_by('last_name', 'first_name')
        # Non-admins can only see managers
        return CustomUser.objects.filter(
            role=CustomUser.Role.MANAGER, is_active=True
        ).order_by('last_name', 'first_name')


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or deactivate a specific user (admin only)."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CustomUser.objects.all()

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response(
                {'error': 'You cannot deactivate your own account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = False
        user.save()
        return Response({'message': 'User deactivated.'}, status=status.HTTP_200_OK)


class CompanyView(generics.RetrieveUpdateAPIView):
    """Get or update company information."""
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Return the first (and typically only) company
        company, _ = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Property Management Company'}
        )
        return company

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


class CompanyCreateView(generics.CreateAPIView):
    """Create a new company."""
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        company = serializer.save()
        UserCompany.objects.create(
            user=self.request.user,
            company=company,
            role=UserCompany.CompanyRole.OWNER,
        )


class UserCompanyView(generics.ListCreateAPIView):
    """List or add company members."""
    serializer_class = UserCompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserCompany.objects.select_related('user', 'company').filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save()


class TokenRefreshInfoView(APIView):
    """Return current user info (useful after token refresh)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)
