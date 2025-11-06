"""
API endpoints for Order Comments/Chat.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime

from apps.orders.models import Order, OrderComment
from apps.orders.schemas.comment_schema import (
    CreateCommentSchema,
    UpdateCommentSchema,
    CommentSchema,
    CommentListResponse
)
from apps.orders.socketio_client import broadcast_comment_created, broadcast_comment_updated, broadcast_comment_deleted
from apps.users.models import User
from core.dependencies import get_current_user

router = APIRouter(prefix="/orders", tags=["Order Comments"])


@router.get("/{order_id}/comments", response_model=CommentListResponse)
def get_order_comments(
    order_id: int,
    user: User = Depends(get_current_user)
):
    """
    Get all comments for an order.
    Returns comments in chronological order.
    """
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        raise HTTPException(status_code=404, detail="Order not found")

    comments = OrderComment.objects.filter(order=order).select_related('user').order_by('created_at')

    comment_schemas = [CommentSchema.from_orm(comment) for comment in comments]

    return CommentListResponse(
        comments=comment_schemas,
        total=len(comment_schemas),
        order_id=order_id
    )


@router.post("/{order_id}/comments", response_model=CommentSchema)
async def create_comment(
    order_id: int,
    message: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    user: User = Depends(get_current_user)
):
    """
    Create a new comment in an order.
    Supports text message and/or image attachment.
    """
    # Validate: Must have either message or image
    if not message and not image:
        raise HTTPException(
            status_code=400,
            detail="Must provide either message or image"
        )

    # Get order
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        raise HTTPException(status_code=404, detail="Order not found")

    # Create comment
    comment = OrderComment.objects.create(
        order=order,
        user=user,
        message=message or ""
    )

    # Handle image upload if provided
    if image:
        # Save image
        from django.core.files.base import ContentFile
        import os
        from django.utils import timezone

        # Generate filename
        ext = os.path.splitext(image.filename)[1]
        filename = f"comment_{comment.id}_{int(timezone.now().timestamp())}{ext}"

        # Read and save file
        content = await image.read()
        comment.image.save(filename, ContentFile(content), save=True)

    comment.refresh_from_db()

    # Broadcast to Socket.IO
    comment_data = CommentSchema.from_orm(comment).model_dump(mode='json')
    broadcast_comment_created(order_id, comment_data)

    return CommentSchema.from_orm(comment)


@router.put("/comments/{comment_id}", response_model=CommentSchema)
def update_comment(
    comment_id: int,
    data: UpdateCommentSchema,
    user: User = Depends(get_current_user)
):
    """
    Update a comment (text only).
    Only the comment author can update.
    """
    try:
        comment = OrderComment.objects.select_related('user', 'order').get(id=comment_id)
    except OrderComment.DoesNotExist:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check permission
    if comment.user != user:
        raise HTTPException(status_code=403, detail="You can only edit your own comments")

    # Can't edit system messages
    if comment.is_system_message:
        raise HTTPException(status_code=403, detail="Cannot edit system messages")

    # Update
    comment.message = data.message
    comment.is_edited = True
    comment.save(update_fields=['message', 'is_edited', 'updated_at'])

    # Broadcast update
    comment_data = CommentSchema.from_orm(comment).model_dump(mode='json')
    broadcast_comment_updated(comment.order_id, comment_data)

    return CommentSchema.from_orm(comment)


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    user: User = Depends(get_current_user)
):
    """
    Delete a comment.
    Only the comment author can delete (or admin).
    """
    try:
        comment = OrderComment.objects.select_related('user', 'order').get(id=comment_id)
    except OrderComment.DoesNotExist:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check permission
    if comment.user != user and not user.is_staff:
        raise HTTPException(status_code=403, detail="You can only delete your own comments")

    # Can't delete system messages
    if comment.is_system_message:
        raise HTTPException(status_code=403, detail="Cannot delete system messages")

    order_id = comment.order_id
    comment_id = comment.id

    # Delete
    comment.delete()

    # Broadcast deletion
    broadcast_comment_deleted(order_id, comment_id)

    return JSONResponse(
        status_code=200,
        content={"message": "Comment deleted successfully"}
    )


@router.post("/{order_id}/comments/system")
def create_system_comment(
    order_id: int,
    message: str,
    user: User = Depends(get_current_user)
):
    """
    Create a system-generated comment.
    Used for activity logs (e.g., "Status changed to Weighing").
    Internal use only.
    """
    # Only staff can create system messages
    if not user.is_staff:
        raise HTTPException(status_code=403, detail="Only staff can create system messages")

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        raise HTTPException(status_code=404, detail="Order not found")

    comment = OrderComment.objects.create(
        order=order,
        message=message,
        is_system_message=True
    )

    # Broadcast
    comment_data = CommentSchema.from_orm(comment).model_dump(mode='json')
    broadcast_comment_created(order_id, comment_data)

    return CommentSchema.from_orm(comment)
