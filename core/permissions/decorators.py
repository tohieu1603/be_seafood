"""
Shield permission decorators for Django Ninja routes.

Usage:
    @orders_router.get("/", response=List[OrderSchema])
    @require_permission('order:read')
    def list_orders(request):
        ...

    @orders_router.post("/")
    @require_any_permission('order:create', 'order:manage')
    def create_order(request, payload):
        ...
"""
from functools import wraps
from typing import Callable, Union, List
from ninja.errors import HttpError
from core.permissions.shield import shield


def require_permission(permission_name: str, error_message: str = None):
    """
    Decorator to require a specific permission.

    Args:
        permission_name: Permission in format 'resource:action'
        error_message: Custom error message (optional)

    Example:
        @require_permission('order:create')
        def create_order(request, payload):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.user

            if not shield.can(user, permission_name):
                msg = error_message or f"Permission denied: {permission_name}"
                raise HttpError(403, msg)

            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(*permission_names: str, error_message: str = None):
    """
    Decorator to require ANY of the given permissions.

    Args:
        *permission_names: Variable number of permission names
        error_message: Custom error message (optional)

    Example:
        @require_any_permission('order:create', 'order:manage')
        def create_order(request, payload):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.user

            if not shield.has_any(user, *permission_names):
                msg = error_message or f"Permission denied: requires any of {permission_names}"
                raise HttpError(403, msg)

            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_all_permissions(*permission_names: str, error_message: str = None):
    """
    Decorator to require ALL of the given permissions.

    Args:
        *permission_names: Variable number of permission names
        error_message: Custom error message (optional)

    Example:
        @require_all_permissions('order:update', 'order:assign')
        def update_and_assign_order(request, order_id, payload):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.user

            if not shield.has_all(user, *permission_names):
                msg = error_message or f"Permission denied: requires all of {permission_names}"
                raise HttpError(403, msg)

            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_role(*roles: str, error_message: str = None):
    """
    Decorator to require specific role(s).

    Args:
        *roles: Variable number of role names
        error_message: Custom error message (optional)

    Example:
        @require_role('admin', 'manager')
        def admin_only_action(request):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.user

            if user.role not in roles:
                msg = error_message or f"Access denied: requires role in {roles}"
                raise HttpError(403, msg)

            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def check_permission(permission_name: str) -> Callable:
    """
    Function-based permission checker (not a decorator).
    Use this inside route functions for conditional logic.

    Args:
        permission_name: Permission to check

    Returns:
        Callable that takes request and returns bool

    Example:
        def my_route(request):
            if check_permission('order:delete')(request):
                # user can delete
                ...
    """
    def checker(request):
        return shield.can(request.user, permission_name)
    return checker
