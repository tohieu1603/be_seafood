"""Order API router."""
from typing import Optional

from ninja import Router, File, UploadedFile, Form, Query

from apps.orders.schemas.input_schema import (
    CreateOrderSchema,
    UpdateOrderStatusSchema,
    UpdateAssignedUsersSchema,
    UploadOrderImageSchema,
    OrderFilterSchema
)
from apps.orders.schemas.output_schema import (
    OrderOutSchema,
    OrderDetailSchema
)
from apps.orders.schemas.activity_schema import OrderActivitySchema
from apps.orders.services.service_a import OrderService
from core.responses.api_response import ApiResponse, ErrorResponse
from core.utils.pagination import PaginatedResponse
from core.authentication import JWTAuth

orders_router = Router(auth=JWTAuth())
order_service = OrderService()


@orders_router.get("/permissions", response={200: dict})
def get_user_permissions(request):
    """Get current user's permissions."""
    try:
        from core.enums.base_enum import UserRole

        user = request.auth

        allowed_statuses = UserRole.get_allowed_statuses(user.role)

        return 200, {
            "role": user.role,
            "role_label": UserRole.get_label(UserRole(user.role)),
            "allowed_statuses": [status.value for status in allowed_statuses],
            "can_create_order": user.role in [UserRole.ADMIN.value, UserRole.MANAGER.value, UserRole.SALE.value],
        }
    except Exception as e:
        return 200, {
            "role": "unknown",
            "role_label": "Unknown",
            "allowed_statuses": [],
            "can_create_order": False,
        }


@orders_router.post("/", response={201: OrderDetailSchema, 400: ErrorResponse})
def create_order(request, payload: CreateOrderSchema):
    """Create a new order."""
    try:
        user = request.auth

        order = order_service.create_order(payload, user)
        return 201, order
    except ValueError as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": f"Error creating order: {str(e)}"}


@orders_router.get("/", response=PaginatedResponse[OrderOutSchema])
def list_orders(
    request,
    filters: OrderFilterSchema = Query(...)
):
    """List all orders with filters."""
    try:
        user = request.auth

        orders, total = order_service.get_orders(
            filters,
            user_id=user.id if user and filters.assigned_to_me else None
        )

        return PaginatedResponse.create(
            items=orders,
            total=total,
            page=filters.page,
            page_size=filters.page_size
        )
    except Exception as e:
        print(f"Error in list_orders: {e}")
        import traceback
        traceback.print_exc()
        return PaginatedResponse.create(
            items=[],
            total=0,
            page=1,
            page_size=20
        )


@orders_router.get("/{order_id}", response={200: OrderDetailSchema, 404: ErrorResponse})
def get_order(request, order_id: int):
    """Get order by ID."""
    order = order_service.get_order_by_id(order_id)
    if not order:
        return 404, {"detail": f"Order with ID {order_id} not found"}
    return 200, order


@orders_router.patch("/{order_id}/status", response={200: OrderDetailSchema, 400: ErrorResponse, 403: ErrorResponse})
def update_order_status(request, order_id: int, payload: UpdateOrderStatusSchema):
    """Update order status."""
    try:
        from core.enums.base_enum import UserRole

        user = request.auth

        # Check permission before updating status
        order = order_service.get_order_by_id(order_id)
        if not order:
            return 400, {"detail": "Order not found"}

        # Check if user can transition from current status to new status
        if not UserRole.can_transition(user.role, order.status, payload.new_status):
            return 403, {"detail": f"Bạn không có quyền chuyển đơn từ '{order.status}' sang '{payload.new_status}'. Vai trò của bạn chỉ được phép làm các giai đoạn: {', '.join(UserRole.get_allowed_statuses(user.role))}"}

        order = order_service.update_order_status(order_id, payload, user)
        return 200, order
    except ValueError as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": f"Error updating status: {str(e)}"}


@orders_router.post("/{order_id}/images", response={201: dict, 400: ErrorResponse})
def upload_order_image(
    request,
    order_id: int,
    image: UploadedFile = File(...),
    payload: Form[UploadOrderImageSchema] = None
):
    """Upload image for order."""
    try:
        user = request.auth

        image_type = payload.image_type if payload else "other"

        order_image = order_service.upload_order_image(
            order_id=order_id,
            image_file=image,
            image_type=image_type,
            user=user
        )

        return 201, {
            "message": "Image uploaded successfully",
            "image_id": order_image.id,
            "image_url": order_image.image.url
        }
    except ValueError as e:
        return 400, {"detail": str(e)}


@orders_router.patch("/{order_id}/assigned-users", response={200: OrderDetailSchema, 400: ErrorResponse, 403: ErrorResponse})
def update_assigned_users(request, order_id: int, payload: UpdateAssignedUsersSchema):
    """Update assigned users for an order."""
    try:
        from core.enums.base_enum import UserRole

        user = request.auth

        # Only admin and manager can reassign
        if user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
            return 403, {"detail": "Chỉ Admin và Manager mới có quyền phân công lại nhân viên"}

        order = order_service.update_assigned_users(order_id, payload.assigned_to_ids, user)
        return 200, order
    except ValueError as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": f"Error updating assigned users: {str(e)}"}


@orders_router.get("/statistics/summary", response=dict)
def get_order_statistics(request):
    """Get order statistics."""
    try:
        stats = order_service.get_order_statistics()
        return stats
    except Exception as e:
        return {"error": str(e)}


@orders_router.delete("/{order_id}/images/{image_id}", response={204: None, 404: ErrorResponse})
def delete_order_image(request, order_id: int, image_id: int):
    """Delete an order image."""
    try:
        from apps.orders.models import OrderImage
        from apps.orders.websocket_utils import broadcast_order_image_deleted

        image = OrderImage.objects.filter(id=image_id, order_id=order_id).first()
        if not image:
            return 404, {"detail": f"Image with ID {image_id} not found in order {order_id}"}

        # Delete the file from disk
        if image.image:
            image.image.delete(save=False)

        # Delete the database record
        image.delete()

        # Broadcast image deleted event
        broadcast_order_image_deleted(order_id, image_id)

        return 204, None
    except Exception as e:
        return 400, {"detail": str(e)}


@orders_router.get("/{order_id}/activities", response={200: list[OrderActivitySchema], 404: ErrorResponse})
def get_order_activities(request, order_id: int):
    """Get activity log for an order."""
    try:
        from apps.orders.models import OrderActivity

        order = order_service.get_order_by_id(order_id)
        if not order:
            return 404, {"detail": f"Order with ID {order_id} not found"}

        activities = OrderActivity.objects.filter(order=order).select_related('user').order_by('-created_at')
        return 200, list(activities)
    except Exception as e:
        return 400, {"detail": str(e)}


@orders_router.delete("/{order_id}", response={204: None, 404: ErrorResponse})
def delete_order(request, order_id: int):
    """Delete an order."""
    try:
        from apps.orders.websocket_utils import broadcast_order_deleted

        order = order_service.get_order_by_id(order_id)
        if not order:
            return 404, {"detail": f"Order with ID {order_id} not found"}

        order.delete()

        # Broadcast order deleted event
        broadcast_order_deleted(order_id)

        return 204, None
    except Exception as e:
        return 400, {"detail": str(e)}
