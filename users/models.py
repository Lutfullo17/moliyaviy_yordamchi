from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        blank=True,
        null=True
    )

    def __str__(self):
        return self.username

    telegram_id = models.BigIntegerField(null=True, blank=True)
    telegram_code = models.CharField(max_length=10, null=True, blank=True)