import re
from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        if email and password:
            user = authenticate(username=email, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError("Tài khoản đã bị vô hiệu hóa.")
                data['user'] = user
            else:
                raise serializers.ValidationError("Thông tin đăng nhập không chính xác.")
        else:
            raise serializers.ValidationError("Cần nhập email và password.")
        return data

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Nếu email tồn tại, chúng tôi sẽ gửi hướng dẫn đặt lại mật khẩu.")
        return value

class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()
    token = serializers.UUIDField()

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()
    token = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        # Kiểm tra mật khẩu mạnh (ít nhất 8 ký tự, chứa chữ hoa, chữ thường, số và ký tự đặc biệt)
        if len(value) < 8:
            raise serializers.ValidationError("Mật khẩu phải có ít nhất 8 ký tự.")
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Mật khẩu phải có ít nhất 1 chữ hoa.")
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("Mật khẩu phải có ít nhất 1 chữ thường.")
        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError("Mật khẩu phải có ít nhất 1 chữ số.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError("Mật khẩu phải có ít nhất 1 ký tự đặc biệt.")
        return value