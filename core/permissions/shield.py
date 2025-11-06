"""
Shield-style Permission Checker.

Provides a clean API for checking permissions:
    - shield.can(user, 'order:create')
    - shield.can(user, 'order:update', order_id)
    - @shield.require('order:delete')
"""
from typing import Optional, Any
from django.contrib.auth import get_user_model
from apps.users.models import Permission, RolePermission, UserPermission
from core.enums import UserRole

User = get_user_model()


class Shield:
    """
    Shield permission checker - centralized permission management.
    """

    def __init__(self):
        """Initialize Shield with permission cache."""
        self._permission_cache = {}
        self._role_permission_cache = {}

    def can(
        self,
        user: User,
        permission_name: str,
        resource_id: Optional[Any] = None
    ) -> bool:
        """
        Check if user has permission.

        Args:
            user: User object
            permission_name: Permission in format 'resource:action'
            resource_id: Optional resource ID for object-level permissions

        Returns:
            bool: True if user has permission, False otherwise

        Examples:
            shield.can(user, 'order:create')
            shield.can(user, 'order:update', order_id=123)
        """
        # Admin and Manager have all permissions
        if user.role in [UserRole.ADMIN.value, UserRole.MANAGER.value]:
            return True

        # Check user-specific permission overrides first
        user_perm = self._check_user_permission(user, permission_name)
        if user_perm is not None:
            return user_perm

        # Check role-based permissions
        return self._check_role_permission(user.role, permission_name)

    def cannot(
        self,
        user: User,
        permission_name: str,
        resource_id: Optional[Any] = None
    ) -> bool:
        """Inverse of can() - returns True if user does NOT have permission."""
        return not self.can(user, permission_name, resource_id)

    def has_any(self, user: User, *permission_names: str) -> bool:
        """
        Check if user has ANY of the given permissions.

        Args:
            user: User object
            *permission_names: Variable number of permission names

        Returns:
            bool: True if user has at least one permission

        Example:
            shield.has_any(user, 'order:create', 'order:update')
        """
        return any(self.can(user, perm) for perm in permission_names)

    def has_all(self, user: User, *permission_names: str) -> bool:
        """
        Check if user has ALL of the given permissions.

        Args:
            user: User object
            *permission_names: Variable number of permission names

        Returns:
            bool: True if user has all permissions

        Example:
            shield.has_all(user, 'order:create', 'order:update')
        """
        return all(self.can(user, perm) for perm in permission_names)

    def get_user_permissions(self, user: User) -> list[str]:
        """
        Get all permissions for a user.

        Returns:
            list: List of permission names user has access to
        """
        # Admin and Manager have all permissions
        if user.role in [UserRole.ADMIN.value, UserRole.MANAGER.value]:
            return list(Permission.objects.values_list('name', flat=True))

        # Get role permissions
        role_perms = set(
            RolePermission.objects
            .filter(role=user.role)
            .select_related('permission')
            .values_list('permission__name', flat=True)
        )

        # Apply user-specific overrides
        user_perms = UserPermission.objects.filter(user=user).select_related('permission')
        for up in user_perms:
            if up.granted:
                role_perms.add(up.permission.name)
            else:
                role_perms.discard(up.permission.name)

        return list(role_perms)

    def _check_user_permission(self, user: User, permission_name: str) -> Optional[bool]:
        """
        Check user-specific permission override.

        Returns:
            bool: True/False if override exists, None if no override
        """
        try:
            permission = Permission.objects.get(name=permission_name)
            user_perm = UserPermission.objects.filter(
                user=user,
                permission=permission
            ).first()

            if user_perm:
                return user_perm.granted
        except Permission.DoesNotExist:
            pass

        return None

    def _check_role_permission(self, role: str, permission_name: str) -> bool:
        """
        Check if role has permission.

        Args:
            role: Role name (from UserRole enum)
            permission_name: Permission name

        Returns:
            bool: True if role has permission
        """
        # Use cache key
        cache_key = f"{role}:{permission_name}"
        if cache_key in self._role_permission_cache:
            return self._role_permission_cache[cache_key]

        # Query database
        try:
            permission = Permission.objects.get(name=permission_name)
            has_permission = RolePermission.objects.filter(
                role=role,
                permission=permission
            ).exists()

            # Cache result
            self._role_permission_cache[cache_key] = has_permission
            return has_permission
        except Permission.DoesNotExist:
            return False

    def grant(self, user: User, permission_name: str) -> bool:
        """
        Grant a permission to a user (override).

        Args:
            user: User object
            permission_name: Permission name

        Returns:
            bool: True if granted successfully
        """
        try:
            permission = Permission.objects.get(name=permission_name)
            UserPermission.objects.update_or_create(
                user=user,
                permission=permission,
                defaults={'granted': True}
            )
            return True
        except Permission.DoesNotExist:
            return False

    def revoke(self, user: User, permission_name: str) -> bool:
        """
        Revoke a permission from a user (override).

        Args:
            user: User object
            permission_name: Permission name

        Returns:
            bool: True if revoked successfully
        """
        try:
            permission = Permission.objects.get(name=permission_name)
            UserPermission.objects.update_or_create(
                user=user,
                permission=permission,
                defaults={'granted': False}
            )
            return True
        except Permission.DoesNotExist:
            return False

    def clear_cache(self):
        """Clear permission cache."""
        self._permission_cache.clear()
        self._role_permission_cache.clear()


# Global Shield instance
shield = Shield()
