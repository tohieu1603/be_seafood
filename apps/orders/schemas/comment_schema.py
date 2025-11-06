"""
Schemas for Order Comments/Chat API.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ==================== Input Schemas ====================

class CreateCommentSchema(BaseModel):
    """Schema for creating a new comment."""
    message: Optional[str] = Field(None, min_length=1, max_length=5000)
    # Note: image will be handled via multipart/form-data, not in JSON

    class Config:
        from_attributes = True


class UpdateCommentSchema(BaseModel):
    """Schema for updating a comment."""
    message: str = Field(..., min_length=1, max_length=5000)

    class Config:
        from_attributes = True


# ==================== Output Schemas ====================

class CommentUserSchema(BaseModel):
    """User info in comment."""
    id: int
    first_name: str
    last_name: str
    email: str

    class Config:
        from_attributes = True

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class CommentSchema(BaseModel):
    """Schema for comment response."""
    id: int
    order_id: int
    user: Optional[CommentUserSchema]
    user_name: str
    message: Optional[str]
    image: Optional[str]  # Image URL
    has_image: bool
    created_at: datetime
    updated_at: datetime
    is_edited: bool
    is_system_message: bool

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, comment):
        """Convert ORM model to schema."""
        from django.conf import settings

        # Build full image URL if image exists
        image_url = None
        if comment.image:
            # Get base URL from settings or use default
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            image_url = f"{base_url}{comment.image.url}"

        return cls(
            id=comment.id,
            order_id=comment.order_id,
            user=CommentUserSchema.from_orm(comment.user) if comment.user else None,
            user_name=comment.user_name,
            message=comment.message,
            image=image_url,
            has_image=comment.has_image,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            is_edited=comment.is_edited,
            is_system_message=comment.is_system_message
        )


class CommentListResponse(BaseModel):
    """Response for list of comments."""
    comments: list[CommentSchema]
    total: int
    order_id: int

    class Config:
        from_attributes = True
