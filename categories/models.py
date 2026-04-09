from django.db import models

from django.conf import settings


class Category(models.Model):
    name = models.CharField(
        max_length=100
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='categories'
    )

    is_default = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['user']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'user'],
                name='unique_category_per_user'
            )
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if not self.name:
            raise ValueError("Category name cannot be empty")

        if self.is_default and self.user is not None:
            raise ValueError("Default category cannot belong to a user")

    def save(self, *args, **kwargs):
        self.name = self.name.strip().lower()
        super().save(*args, **kwargs)
