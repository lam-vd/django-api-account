# accounts/urls.py
from django.urls import path
from .views import (
    LoginAPIView,
    LogoutAPIView,
    ForgotPasswordAPIView,
    VerifyCodeAPIView,
    ResetPasswordAPIView,
)

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot-password'),
    path('verify-code/', VerifyCodeAPIView.as_view(), name='verify-code'),
    path('reset-password/', ResetPasswordAPIView.as_view(), name='reset-password'),
]
