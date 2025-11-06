"""
Order Comments API router (Django Ninja).
"""
from ninja import Router, File, UploadedFile, Form
from typing import Optional

from apps.orders.models import Order, OrderComment
from apps.orders.schemas.comment_schema import (
    UpdateCommentSchema,
    CommentSchema,
    CommentListResponse
)
from apps.orders.socketio_client import broadcast_comment_created, broadcast_comment_updated, broadcast_comment_deleted
from apps.users.models import User
from core.authentication import JWTAuth
from core.responses.api_response import ErrorResponse

comments_router = Router(auth=JWTAuth())


@comments_router.get("/{order_id}/comments", response={200: CommentListResponse, 404: ErrorResponse})
def get_order_comments(request, order_id: int):
    """
    Get all comments for an order.
    Returns comments in chronological order.
    """
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return 404, {"detail": "Order not found"}

    comments = OrderComment.objects.filter(order=order).select_related('user').order_by('created_at')

    comment_schemas = [CommentSchema.from_orm(comment) for comment in comments]

    return 200, CommentListResponse(
        comments=comment_schemas,
        total=len(comment_schemas),
        order_id=order_id
    )


@comments_router.post("/{order_id}/comments", response={201: CommentSchema, 400: ErrorResponse, 404: ErrorResponse})
def create_comment(
    request,
    order_id: int,
    message: Optional[str] = Form(None),
    image: Optional[UploadedFile] = File(None)
):
    """
    Create a new comment in an order.
    Supports text message and/or image attachment.
    """
    user = request.auth

    # Validate: Must have either message or image
    if not message and not image:
        return 400, {"detail": "Must provide either message or image"}

    # Get order
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return 404, {"detail": "Order not found"}

    # Create comment
    comment = OrderComment.objects.create(
        order=order,
        user=user,
        message=message or ""
    )

    # Handle image upload if provided
    if image:
        from django.core.files.base import ContentFile
        import os
        from django.utils import timezone

        # Generate filename
        ext = os.path.splitext(image.name)[1]
        filename = f"comment_{comment.id}_{int(timezone.now().timestamp())}{ext}"

        # Read and save file
        content = image.read()
        comment.image.save(filename, ContentFile(content), save=True)

    comment.refresh_from_db()

    # Broadcast to Socket.IO
    comment_data = CommentSchema.from_orm(comment).model_dump(mode='json')
    broadcast_comment_created(order_id, comment_data)

    return 201, CommentSchema.from_orm(comment)


@comments_router.put("/comments/{comment_id}", response={200: CommentSchema, 400: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def update_comment(request, comment_id: int, payload: UpdateCommentSchema):
    """
    Update a comment (text only).
    Only the comment author can update.
    """
    user = request.auth

    try:
        comment = OrderComment.objects.select_related('user', 'order').get(id=comment_id)
    except OrderComment.DoesNotExist:
        return 404, {"detail": "Comment not found"}

    # Check permission
    if comment.user != user:
        return 403, {"detail": "You can only edit your own comments"}

    # Can't edit system messages
    if comment.is_system_message:
        return 403, {"detail": "Cannot edit system messages"}

    # Update
    comment.message = payload.message
    comment.is_edited = True
    comment.save(update_fields=['message', 'is_edited', 'updated_at'])

    # Broadcast update
    comment_data = CommentSchema.from_orm(comment).model_dump(mode='json')
    broadcast_comment_updated(comment.order_id, comment_data)

    return 200, CommentSchema.from_orm(comment)


@comments_router.delete("/comments/{comment_id}", response={204: None, 403: ErrorResponse, 404: ErrorResponse})
def delete_comment(request, comment_id: int):
    """
    Delete a comment.
    Only the comment author can delete (or admin).
    """
    user = request.auth

    try:
        comment = OrderComment.objects.select_related('user', 'order').get(id=comment_id)
    except OrderComment.DoesNotExist:
        return 404, {"detail": "Comment not found"}

    # Check permission
    if comment.user != user and not user.is_staff:
        return 403, {"detail": "You can only delete your own comments"}

    # Can't delete system messages
    if comment.is_system_message:
        return 403, {"detail": "Cannot delete system messages"}

    order_id = comment.order_id
    comment_id_to_delete = comment.id

    # Delete
    comment.delete()

    # Broadcast deletion
    broadcast_comment_deleted(order_id, comment_id_to_delete)

    return 204, None


@comments_router.post("/{order_id}/comments/system", response={201: CommentSchema, 403: ErrorResponse, 404: ErrorResponse})
def create_system_comment(request, order_id: int, message: str):
    """
    Create a system-generated comment.
    Used for activity logs (e.g., "Status changed to Weighing").
    Internal use only.
    """
    user = request.auth

    # Only staff can create system messages
    if not user.is_staff:
        return 403, {"detail": "Only staff can create system messages"}

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return 404, {"detail": "Order not found"}

    comment = OrderComment.objects.create(
        order=order,
        message=message,
        is_system_message=True
    )

    # Broadcast
    comment_data = CommentSchema.from_orm(comment).model_dump(mode='json')
    broadcast_comment_created(order_id, comment_data)

    return 201, CommentSchema.from_orm(comment)
