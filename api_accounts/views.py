# accounts/views.py
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle
from rest_framework.permissions import IsAuthenticated
from .models import PasswordResetCode
import logging

from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    LoginSerializer,
    ForgotPasswordSerializer,
    VerifyCodeSerializer,
    ResetPasswordSerializer
)
from .models import PasswordResetCode

User = get_user_model()
logger = logging.getLogger(__name__)

# --- Login API với JWT ---
class LoginAPIView(APIView):
    throttle_classes = [AnonRateThrottle]  # Giới hạn tốc độ cho người dùng chưa đăng nhập
    permission_classes = []
    def post(self, request):
        print("Request data:", request.data)
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            logger.info(f"User {user.email} đăng nhập thành công")
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_200_OK)
        print("Serializer errors:", serializer.errors)
        logger.warning(f"Đăng nhập thất bại cho email: {request.data.get('email')}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- Logout API: Blacklist refresh token ---
class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Chỉ cho phép người đã đăng nhập
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()  # Đưa refresh token vào danh sách đen
            logger.info(f"User {request.user.email} đăng xuất thành công")
            return Response({"message": "Đăng xuất thành công."}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Lỗi khi đăng xuất", exc_info=e)
            return Response({"error": "Có lỗi xảy ra."}, status=status.HTTP_400_BAD_REQUEST)

# --- Forgot Password API: Tạo mã và gửi email ---
class ForgotPasswordAPIView(APIView):
    throttle_classes = [AnonRateThrottle]  # Giới hạn số lần gửi yêu cầu

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                # Tạo mã đặt lại mật khẩu và token mới cho người dùng
                reset_code = PasswordResetCode.create_for_user(user)
                # Gửi email có chứa mã và token (cần cấu hình EMAIL_BACKEND và các thông số email trong settings.py)
                send_mail(
                    'Mã xác thực đặt lại mật khẩu',
                    f'Mã xác thực của bạn là: {reset_code.code}\nToken: {reset_code.token}',
                    'noreply@example.com',  # Điền email gửi của bạn
                    [email],
                    fail_silently=False,
                )
                logger.info(f"Đã gửi mã đặt lại mật khẩu tới {email}")
            except User.DoesNotExist:
                logger.info(f"Yêu cầu reset password cho email không tồn tại: {email}")
            # Trả về thông báo chung bất kể email có tồn tại hay không
            return Response({"message": "Nếu email tồn tại, chúng tôi sẽ gửi hướng dẫn đặt lại mật khẩu."},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- Verify Code API: Kiểm tra mã và token ---
class VerifyCodeAPIView(APIView):
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            code = serializer.validated_data['code']
            token = serializer.validated_data['token']

            try:
                user = User.objects.get(email=email)
                reset_codes = PasswordResetCode.objects.filter(
                    user=user,
                    code=code,
                    token=token
                ).order_by('-created_at')
                if not reset_codes.exists():
                    logger.warning(f"Mã sai cho {email}")
                    return Response({"error": "Mã không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)
                reset_code = reset_codes.first()

                # Nếu số lần kiểm tra vượt quá giới hạn
                if reset_code.is_max_attempts_reached():
                    reset_code.delete()
                    logger.warning(f"Đã vượt quá số lần thử mã cho {email}")
                    return Response({"error": "Đã vượt quá số lần thử. Yêu cầu mã mới."},
                                    status=status.HTTP_400_BAD_REQUEST)

                reset_code.increment_attempts()

                if reset_code.is_expired():
                    logger.warning(f"Mã hết hạn cho {email}")
                    return Response({"error": "Mã đã hết hạn."}, status=status.HTTP_400_BAD_REQUEST)

                logger.info(f"Mã được xác thực cho {email}")
                return Response({"message": "Mã hợp lệ.", "token": str(token)}, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                logger.error("User không tồn tại khi xác thực mã", exc_info=True)
                return Response({"error": "Thông tin không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- Reset Password API: Đặt lại mật khẩu sau khi xác thực mã ---
class ResetPasswordAPIView(APIView):
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            code = serializer.validated_data['code']
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']

            try:
                user = User.objects.get(email=email)
                reset_codes = PasswordResetCode.objects.filter(
                    user=user,
                    code=code,
                    token=token
                ).order_by('-created_at')
                if not reset_codes.exists():
                    logger.warning(f"Reset password thất bại do mã không hợp lệ cho {email}")
                    return Response({"error": "Thông tin không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)
                reset_code = reset_codes.first()
                if reset_code.is_expired():
                    logger.warning(f"Mã hết hạn khi reset password cho {email}")
                    return Response({"error": "Mã đã hết hạn."}, status=status.HTTP_400_BAD_REQUEST)

                # Đặt lại mật khẩu (mã hóa mật khẩu mới)
                user.password = make_password(new_password)
                user.save()
                # Xoá toàn bộ mã đặt lại mật khẩu của người dùng sau khi đặt lại thành công
                PasswordResetCode.objects.filter(user=user).delete()
                logger.info(f"Đổi mật khẩu thành công cho {email}")
                return Response({"message": "Đặt lại mật khẩu thành công."}, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                logger.error(f"Reset password cho user không tồn tại: {email}", exc_info=True)
                return Response({"error": "Thông tin không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
