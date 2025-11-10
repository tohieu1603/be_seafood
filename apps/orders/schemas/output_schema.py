"""Output schemas for orders."""
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from ninja import Schema
from urllib.parse import quote


class UserBasicSchema(Schema):
    """Basic user info."""

    id: int
    username: str
    first_name: str
    last_name: str

    @staticmethod
    def from_orm(user):
        return UserBasicSchema(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )


class CustomerBasicSchema(Schema):
    """Basic customer info."""

    id: int
    name: str
    phone: str
    address: str
    is_vip: bool


class OrderItemSchema(Schema):
    """Order item schema."""

    id: int
    product_name: str
    quantity: Decimal
    unit: str
    price: Decimal
    total: Decimal
    note: str


class OrderImageSchema(Schema):
    """Order image schema."""

    id: int
    image: str
    image_type: str
    uploaded_by: Optional[UserBasicSchema] = None
    created_at: datetime


class OrderStatusHistorySchema(Schema):
    """Order status history schema."""

    id: int
    from_status: str
    to_status: str
    changed_by: Optional[UserBasicSchema] = None
    notes: Optional[str] = None
    created_at: datetime


class OrderOutSchema(Schema):
    """Basic order output schema for list view."""

    id: int
    order_number: str
    customer_name: str
    customer_phone: str
    customer_address: str
    status: str
    status_changed_at: datetime
    deadline: Optional[datetime]
    delivery_time: Optional[datetime]
    received_time: Optional[datetime]
    kitchen_time: Optional[datetime]
    total: Decimal
    assigned_to: List[UserBasicSchema]
    created_at: datetime
    created_by: Optional[UserBasicSchema] = None

    # Order details
    items_count: int = 0
    images_count: int = 0

    # Calculated fields
    is_overdue: bool = False
    remaining_minutes: Optional[int] = None

    @staticmethod
    def resolve_is_overdue(obj):
        """Check if order is overdue."""
        if obj.deadline and obj.status not in ['completed', 'failed']:
            from django.utils import timezone
            return timezone.now() > obj.deadline
        return False

    @staticmethod
    def resolve_remaining_minutes(obj):
        """Calculate remaining minutes."""
        if obj.deadline and obj.status not in ['completed', 'failed']:
            from django.utils import timezone
            delta = obj.deadline - timezone.now()
            return int(delta.total_seconds() / 60)
        return None


class OrderDetailSchema(Schema):
    """Detailed order output schema."""

    id: int
    order_number: str
    customer_name: str
    customer_phone: str
    customer_address: str
    status: str
    status_changed_at: datetime
    deadline: Optional[datetime]
    delivery_time: Optional[datetime]
    received_time: Optional[datetime]
    kitchen_time: Optional[datetime]

    # Items
    items: List[OrderItemSchema]

    # Financial
    subtotal: Decimal
    shipping_fee: Decimal
    chip_fee: Decimal
    total: Decimal

    # Assignment
    assigned_to: List[UserBasicSchema]
    created_by: Optional[UserBasicSchema] = None

    # Images
    images: List[OrderImageSchema] = []

    # History
    status_history: List[OrderStatusHistorySchema] = []

    # Notes
    notes: Optional[str] = None
    failure_reason: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Calculated
    is_overdue: bool = False
    remaining_minutes: Optional[int] = None

    @staticmethod
    def resolve_is_overdue(obj):
        """Check if order is overdue."""
        if obj.deadline and obj.status not in ['completed', 'failed']:
            from django.utils import timezone
            return timezone.now() > obj.deadline
        return False

    @staticmethod
    def resolve_remaining_minutes(obj):
        """Calculate remaining minutes."""
        if obj.deadline and obj.status not in ['completed', 'failed']:
            from django.utils import timezone
            delta = obj.deadline - timezone.now()
            return int(delta.total_seconds() / 60)
        return None
