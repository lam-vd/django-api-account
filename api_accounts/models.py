from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid
import random

User = get_user_model()

class PasswordResetCode(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_codes')
  code = models.CharField(max_length=6, unique=True)
  token = models.UUIDField(default=uuid.uuid4, editable=False)
  created_at = models.DateTimeField(auto_now_add=True)
  attempts = models.IntegerField(default=0)

  # limit 15 minutes for password reset
  def is_expired(self):
    expiration_minutes = 15
    return (timezone.now() - self.created_at) > timedelta(minutes=expiration_minutes)

  def is_max_attempts_reached(self):
    max_attempts = 5
    return self.attempts >= max_attempts

  def increment_attempts(self):
    self.attempts += 1
    self.save()

  def __str__(self):
    return f'Password reset token for {self.user.email} - {self.code}'

  @classmethod

  def create_for_user(cls, user):
    cls.objects.filter(user=user).delete()
    code = str(random.randint(100000, 999999))
    return cls.objects.create(user=user, code=code)
