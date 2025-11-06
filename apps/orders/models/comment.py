"""
Order Chat/Discussion models.
Allows users to comment and discuss within order context.
"""
from django.db import models
from django.utils import timezone
from apps.orders.models import Order
from apps.users.models import User


class OrderComment(models.Model):
    """
    Comment/chat message in an order.
    Supports text messages and image attachments.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_comments'
    )
    message = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to='order_comments/%Y/%m/%d/',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)

    # Metadata
    is_system_message = models.BooleanField(
        default=False,
        help_text="System-generated message (e.g., 'Order status changed')"
    )

    class Meta:
        db_table = 'order_comments'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['order', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"Comment on Order #{self.order.order_number} by {self.user.get_full_name() if self.user else 'System'}"

    @property
    def has_image(self):
        return bool(self.image)

    @property
    def user_name(self):
        if self.user:
            return self.user.get_full_name()
        return "System"


class OrderCommentReaction(models.Model):
    """
    Reactions to comments (like, thumbs up, etc.)
    Optional feature for future enhancement.
    """
    REACTION_CHOICES = [
        ('like', '👍 Like'),
        ('heart', '❤️ Heart'),
        ('check', '✅ Check'),
    ]

    comment = models.ForeignKey(
        OrderComment,
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comment_reactions'
    )
    reaction_type = models.CharField(
        max_length=10,
        choices=REACTION_CHOICES,
        default='like'
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'order_comment_reactions'
        unique_together = ['comment', 'user', 'reaction_type']
        indexes = [
            models.Index(fields=['comment', 'reaction_type']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} {self.reaction_type} on comment {self.comment.id}"
