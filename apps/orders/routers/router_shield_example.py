"""
Example router showing Shield permission usage.

This demonstrates how to use Shield-style RBAC in your routes.
You can copy these patterns to update existing routes.
"""
from ninja import Router
from apps.orders.schemas.output_schema import OrderOutSchema, OrderDetailSchema
from apps.orders.schemas.input_schema import CreateOrderSchema, UpdateOrderSchema
from apps.orders.services.service_a import OrderService
from core.authentication import JWTAuth
from core.permissions import (
    require_permission,
    require_any_permission,
    require_all_permissions,
    shield
)

# Create router with JWT authentication
orders_shield_router = Router(auth=JWTAuth(), tags=['Orders (Shield)'])
order_service = OrderService()


# Example 1: Simple permission check
@orders_shield_router.post("/")
@require_permission('order:create')
def create_order(request, payload: CreateOrderSchema):
    """
    Create a new order.
    Requires: order:create permission
    """
    user = request.auth
    order = order_service.create_order(payload, user)
    return {"success": True, "order": order}


# Example 2: Require ANY of multiple permissions
@orders_shield_router.patch("/{order_id}")
@require_any_permission('order:update', 'order:manage')
def update_order(request, order_id: int, payload: UpdateOrderSchema):
    """
    Update an order.
    Requires: order:update OR order:manage permission
    """
    order = order_service.update_order(order_id, payload)
    return {"success": True, "order": order}


# Example 3: Require ALL permissions
@orders_shield_router.patch("/{order_id}/assign-and-notify")
@require_all_permissions('order:assign_users', 'order:update')
def assign_and_notify(request, order_id: int, user_ids: list[int]):
    """
    Assign users to order AND send notification.
    Requires: BOTH order:assign_users AND order:update permissions
    """
    # Your logic here
    return {"success": True, "message": "Users assigned and notified"}


# Example 4: Manual permission check inside function
@orders_shield_router.delete("/{order_id}")
@require_permission('order:delete')
def delete_order(request, order_id: int):
    """
    Delete an order.

    Uses manual permission check for additional logic.
    """
    user = request.auth

    # Manual check for soft vs hard delete
    can_hard_delete = shield.can(user, 'order:hard_delete')

    if can_hard_delete:
        # Permanently delete
        order_service.hard_delete_order(order_id)
        return {"success": True, "message": "Order permanently deleted"}
    else:
        # Soft delete
        order_service.soft_delete_order(order_id)
        return {"success": True, "message": "Order moved to trash"}


# Example 5: Get user permissions (for frontend)
@orders_shield_router.get("/my-permissions")
def get_my_permissions(request):
    """
    Get current user's permissions.
    Frontend can use this to show/hide UI elements.
    """
    user = request.auth
    permissions = shield.get_user_permissions(user)

    return {
        "username": user.username,
        "role": user.role,
        "permissions": permissions,
        "can": {
            "create_order": shield.can(user, 'order:create'),
            "update_order": shield.can(user, 'order:update'),
            "delete_order": shield.can(user, 'order:delete'),
            "change_status": shield.can(user, 'order:change_status'),
            "view_all_orders": shield.can(user, 'order:view_all'),
        }
    }


# Example 6: Conditional logic based on permissions
@orders_shield_router.get("/")
def list_orders(request, assigned_to_me: bool = False):
    """
    List orders.

    If user has 'order:view_all', shows all orders.
    Otherwise, only shows orders assigned to them.
    """
    user = request.auth

    # Check if user can view all orders
    if shield.can(user, 'order:view_all'):
        # Return all orders
        orders = order_service.get_all_orders()
    else:
        # Return only assigned orders
        orders = order_service.get_orders_assigned_to(user.id)

    return {"success": True, "orders": orders}


# Example 7: Custom error message
@orders_shield_router.post("/{order_id}/approve")
@require_permission(
    'order:approve',
    error_message="Chỉ Manager và Admin mới có quyền duyệt đơn hàng"
)
def approve_order(request, order_id: int):
    """
    Approve an order.
    Custom Vietnamese error message.
    """
    order_service.approve_order(order_id)
    return {"success": True, "message": "Đơn hàng đã được duyệt"}
