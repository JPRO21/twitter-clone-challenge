from django.conf import settings
from django.db import models


class Tweet(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tweets",
    )
    body = models.CharField(max_length=280)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["author", "created_at"],
                name="tweet_author_created_idx",
            )
        ]

    def __str__(self):
        return f"{self.author.username}: {self.body[:50]}"
