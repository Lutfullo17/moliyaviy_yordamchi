from django.db import models
from django.conf import settings


class Transaction(models.Model):
    TYPE_CHOICES = (
        ('income', 'Income'),
        ('expense', 'Expense'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions'
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES
    )

    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )

    note = models.TextField(
        blank=True
    )

    date = models.DateField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.user} - {self.amount} ({self.type})"

    def clean(self):
        if self.amount <= 0:
            raise ValueError("Amount must be greater than 0")

        if self.type not in ['income', 'expense']:
            raise ValueError("Invalid transaction type")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)