"""Permission models for Shield-style RBAC."""
from django.db import models
from core.database.base_model import BaseModel


class Permission(BaseModel):
    """
    Permission model - represents a specific action that can be performed.
    Shield-style permissions use resource:action format.

    Examples:
        - order:create
        - order:read
        - order:update
        - order:delete
        - order:change_status
        - order:assign_users
        - user:manage
    """

    # Resource and action
    resource = models.CharField(
        max_length=50,
        verbose_name='Resource',
        help_text='Resource name (e.g., order, user, product)'
    )
    action = models.CharField(
        max_length=50,
        verbose_name='Action',
        help_text='Action name (e.g., create, read, update, delete)'
    )

    # Human-readable info
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Permission Name',
        help_text='Unique permission name in format resource:action'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description'
    )

    class Meta:
        db_table = 'permissions'
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
        unique_together = [['resource', 'action']]
        ordering = ['resource', 'action']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate name from resource:action if not provided."""
        if not self.name:
            self.name = f"{self.resource}:{self.action}"
        super().save(*args, **kwargs)


class RolePermission(BaseModel):
    """
    Role-Permission mapping table.
    Links roles (from UserRole enum) to permissions.
    """

    role = models.CharField(
        max_length=20,
        verbose_name='Role',
        help_text='Role name from UserRole enum (admin, manager, sale, etc.)'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='role_permissions',
        verbose_name='Permission'
    )

    class Meta:
        db_table = 'role_permissions'
        verbose_name = 'Role Permission'
        verbose_name_plural = 'Role Permissions'
        unique_together = [['role', 'permission']]
        ordering = ['role', 'permission']

    def __str__(self):
        return f"{self.role} - {self.permission.name}"


class UserPermission(BaseModel):
    """
    User-specific permissions (overrides).
    Allows granting or revoking specific permissions to individual users.
    """

    from apps.users.models.user import User

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='custom_permissions',
        verbose_name='User'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='user_permission_overrides',
        verbose_name='Permission'
    )
    granted = models.BooleanField(
        default=True,
        verbose_name='Granted',
        help_text='True = grant permission, False = revoke permission'
    )

    class Meta:
        db_table = 'user_permissions'
        verbose_name = 'User Permission'
        verbose_name_plural = 'User Permissions'
        unique_together = [['user', 'permission']]
        ordering = ['user', 'permission']

    def __str__(self):
        action = 'granted' if self.granted else 'revoked'
        return f"{self.user.username} - {self.permission.name} ({action})"
