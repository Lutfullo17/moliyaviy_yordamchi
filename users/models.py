from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # Qo'shimcha fieldlar kerak bo'lsa shu yerga qo'shasiz
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return self.username