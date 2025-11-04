"""Input schemas for orders."""
from typing import List, Optional, Union
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from ninja import Schema


class ProductItemInput(BaseModel):
    """Product item input schema."""

    product_id: Optional[int] = None
    product_name: str
    quantity: Decimal = Field(gt=0)
    unit: str
    price: Decimal = Field(ge=0)
    note: Optional[str] = Field(default='', max_length=500)


class CreateOrderSchema(BaseModel):
    """Schema for creating an order - nhân viên nội bộ tạo đơn."""

    # Thông tin khách đặt hàng (nhập trực tiếp)
    customer_name: str = Field(min_length=1, max_length=255)
    customer_phone: str = Field(min_length=10, max_length=15)
    customer_address: str = Field(min_length=1)

    # Sản phẩm
    items: List[ProductItemInput] = Field(min_items=1)

    # Phí
    shipping_fee: Decimal = Field(default=0, ge=0)
    chip_fee: Decimal = Field(default=0, ge=0)

    # Thời gian giao hàng
    delivery_time: Optional[datetime] = None

    # Phân công nhân viên
    assigned_to_ids: List[int] = Field(default_factory=list)

    # Ghi chú
    notes: str = Field(default='', max_length=1000)

    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError('Đơn hàng phải có ít nhất 1 sản phẩm')
        return v

    @validator('customer_phone')
    def validate_phone(cls, v):
        import re
        if not re.match(r'^(0|\+84)[1-9][0-9]{8,9}$', v):
            raise ValueError('Số điện thoại không hợp lệ')
        return v


class UpdateOrderStatusSchema(BaseModel):
    """Schema for updating order status."""

    new_status: str
    failure_reason: Optional[str] = None

    @validator('failure_reason')
    def validate_failure_reason(cls, v, values):
        if values.get('new_status') == 'failed' and not v:
            raise ValueError('Phải nhập lý do khi đánh dấu thất bại')
        return v


class UpdateAssignedUsersSchema(BaseModel):
    """Schema for updating assigned users."""

    assigned_to_ids: List[int] = Field(..., min_items=1)


class UploadOrderImageSchema(BaseModel):
    """Schema for uploading order images."""

    image_type: str = Field(..., pattern='^(weighing|invoice|other)$')


class OrderFilterSchema(Schema):
    """Schema for filtering orders."""

    status: Optional[str] = Field(None, description="Filter by order status")
    customer_id: Optional[int] = Field(None, description="Filter by customer ID")
    assigned_to_me: bool = Field(False, description="Show only orders assigned to me")
    search: Optional[str] = Field(None, description="Search by order_number, customer name, phone")
    date_from: Optional[datetime] = Field(None, description="Filter orders from this date")
    date_to: Optional[datetime] = Field(None, description="Filter orders to this date")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")

    class Config:
        """Pydantic config."""
        # Allow None for all optional fields
        validate_assignment = True
        arbitrary_types_allowed = True
