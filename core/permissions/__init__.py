"""Permission utilities."""
from .shield import shield, Shield
from .decorators import (
    require_permission,
    require_any_permission,
    require_all_permissions,
    require_role,
    check_permission
)

__all__ = [
    'shield',
    'Shield',
    'require_permission',
    'require_any_permission',
    'require_all_permissions',
    'require_role',
    'check_permission'
]
