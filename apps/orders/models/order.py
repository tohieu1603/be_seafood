"""Order models."""
from django.db import models
from django.utils import timezone
from core.database.base_model import BaseModel
from core.enums.base_enum import OrderStatus
from apps.products.models import Product
from apps.users.models import User


def generate_order_number():
    """
    Generate sequential order number for the day.
    Format: Đơn X (where X resets daily)
    Example: Ngày 19: Đơn 1, Đơn 2, Đơn 3
             Ngày 20: Đơn 1, Đơn 2, Đơn 3 (reset)
    """
    from datetime import datetime
    from django.db.models import Max
    import re

    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    # Get all orders created today
    today_orders = Order.objects.filter(
        created_at__gte=today_start,
        created_at__lte=today_end
    )

    # Extract numbers from order_number (e.g., "Đơn 1" -> 1)
    max_num = 0
    for order in today_orders:
        match = re.search(r'Đơn\s*(\d+)', order.order_number)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num

    next_num = max_num + 1
    return f"Đơn {next_num}"


class Order(BaseModel):
    """Order model - chỉ có nhân viên nội bộ tạo và xử lý."""

    # Order numbering (auto-generated, resets daily)
    order_number = models.CharField(
        max_length=50,
        default=generate_order_number,
        verbose_name='Số đơn hàng (tự động theo ngày)',
        help_text='VD: Đơn 1, Đơn 2, Đơn 3 (reset mỗi ngày)'
    )

    # Order name (user input, can be duplicate)
    order_name = models.CharField(
        max_length=255,
        verbose_name='Tên đơn hàng',
        help_text='Tên đơn hàng tự đặt (có thể trùng)'
    )

    # Customer info (thông tin khách đặt hàng - nhập trực tiếp)
    customer_name = models.CharField(
        max_length=255,
        verbose_name='Tên khách hàng'
    )
    customer_phone = models.CharField(
        max_length=15,
        verbose_name='Số điện thoại'
    )
    customer_address = models.TextField(
        verbose_name='Địa chỉ giao hàng'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=[(s.value, OrderStatus.get_label(s)) for s in OrderStatus],
        default=OrderStatus.CREATED.value,
        verbose_name='Trạng thái'
    )

    # Timeline
    status_changed_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Thời gian chuyển trạng thái'
    )
    deadline = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Deadline'
    )
    delivery_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Thời gian giao hàng'
    )

    # Financial
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name='Tổng tiền sản phẩm'
    )
    shipping_fee = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name='Phí ship'
    )
    chip_fee = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name='Phí chip/đóng gói'
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name='Tổng tiền'
    )

    # Assignment
    assigned_to = models.ManyToManyField(
        User,
        related_name='assigned_orders',
        blank=True,
        verbose_name='Người phụ trách'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_orders',
        verbose_name='Người tạo'
    )

    # Notes
    notes = models.TextField(blank=True, verbose_name='Ghi chú')
    failure_reason = models.TextField(blank=True, verbose_name='Lý do thất bại')

    class Meta:
        db_table = 'orders'
        verbose_name = 'Đơn hàng'
        verbose_name_plural = 'Đơn hàng'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['order_name']),  # For search
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['delivery_time']),  # For display
        ]

    def __str__(self):
        """Display: OrderName - DeliveryTime (e.g., Đơn1 - 17:00)"""
        if self.delivery_time:
            time_str = self.delivery_time.strftime('%H:%M')
            return f"{self.order_name} - {time_str}"
        return f"{self.order_name} - Chưa có giờ giao"

    def get_display_name(self):
        """Get display name for order: OrderName - DeliveryTime"""
        return str(self)

    def calculate_total(self):
        """Calculate total amount."""
        self.subtotal = sum(item.total for item in self.items.all())
        self.total = self.subtotal + self.shipping_fee + self.chip_fee
        self.save()

    def update_status(self, new_status: str, user: User, reason: str = None):
        """Update order status."""
        old_status = self.status
        self.status = new_status
        self.status_changed_at = timezone.now()

        # Calculate new deadline
        duration = OrderStatus.get_duration_minutes(OrderStatus(new_status))
        if duration > 0:
            from datetime import timedelta
            self.deadline = self.status_changed_at + timedelta(minutes=duration)

        # Handle failure
        if new_status == OrderStatus.FAILED.value:
            self.failure_reason = reason or ''

        self.save()

        # Create status history
        OrderStatusHistory.objects.create(
            order=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=user,
            notes=reason or ''
        )


class OrderItem(BaseModel):
    """Order item model."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Đơn hàng'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Sản phẩm'
    )
    product_name = models.CharField(
        max_length=255,
        verbose_name='Tên sản phẩm'
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Số lượng'
    )
    unit = models.CharField(
        max_length=50,
        verbose_name='Đơn vị'
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name='Giá'
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name='Thành tiền'
    )
    note = models.TextField(
        blank=True,
        default='',
        verbose_name='Ghi chú món'
    )

    class Meta:
        db_table = 'order_items'
        verbose_name = 'Sản phẩm đơn hàng'
        verbose_name_plural = 'Sản phẩm đơn hàng'

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    def save(self, *args, **kwargs):
        """Calculate total on save."""
        self.total = self.quantity * self.price
        super().save(*args, **kwargs)


class OrderImage(BaseModel):
    """Order image model for weighing and invoice photos."""

    IMAGE_TYPE_CHOICES = [
        ('weighing', 'Ảnh cân hàng'),
        ('invoice', 'Ảnh phiếu đặt hàng'),
        ('other', 'Khác'),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Đơn hàng'
    )
    image = models.ImageField(
        upload_to='orders/%Y/%m/%d/',
        verbose_name='Hình ảnh'
    )
    image_type = models.CharField(
        max_length=20,
        choices=IMAGE_TYPE_CHOICES,
        verbose_name='Loại ảnh'
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name='Người upload'
    )

    class Meta:
        db_table = 'order_images'
        verbose_name = 'Hình ảnh đơn hàng'
        verbose_name_plural = 'Hình ảnh đơn hàng'

    def __str__(self):
        return f"{self.order.order_number} - {self.get_image_type_display()}"


class OrderStatusHistory(BaseModel):
    """Order status change history."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name='Đơn hàng'
    )
    from_status = models.CharField(
        max_length=20,
        verbose_name='Trạng thái cũ'
    )
    to_status = models.CharField(
        max_length=20,
        verbose_name='Trạng thái mới'
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name='Người thay đổi'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Ghi chú'
    )

    class Meta:
        db_table = 'order_status_history'
        verbose_name = 'Lịch sử trạng thái'
        verbose_name_plural = 'Lịch sử trạng thái'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order.order_number}: {self.from_status} -> {self.to_status}"
