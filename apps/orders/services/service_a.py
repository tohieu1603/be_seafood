"""Order service with business logic."""
from typing import List, Optional, Tuple
from datetime import timedelta
from django.utils import timezone
from django.db import transaction

from apps.orders.models import Order, OrderItem, OrderActivity
from apps.orders.repositories.repository_a import OrderRepository
from apps.orders.schemas.input_schema import CreateOrderSchema, UpdateOrderStatusSchema, OrderFilterSchema
from apps.products.models import Product
from apps.users.models import User
from core.enums.base_enum import OrderStatus
from apps.orders.websocket_utils import (
    broadcast_order_created,
    broadcast_order_updated,
    broadcast_order_deleted,
    broadcast_order_status_changed,
    broadcast_order_image_uploaded,
    broadcast_order_assigned
)


class OrderService:
    """Service for order business logic."""

    def __init__(self):
        self.repository = OrderRepository()

    def _log_activity(
        self,
        order: Order,
        user: User,
        activity_type: str,
        description: str,
        old_value: str = None,
        new_value: str = None,
        metadata: dict = None
    ):
        """Log activity for order."""
        OrderActivity.objects.create(
            order=order,
            user=user,
            activity_type=activity_type,
            description=description,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata
        )

    def get_orders(
        self,
        filters: OrderFilterSchema,
        user_id: Optional[int] = None
    ) -> Tuple[List[Order], int]:
        """Get orders with pagination."""
        queryset = self.repository.get_all_orders(filters, user_id)
        total = queryset.count()

        # Pagination
        offset = (filters.page - 1) * filters.page_size
        limit = filters.page_size
        orders = list(queryset[offset:offset + limit])

        return orders, total

    def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Get order by ID."""
        return self.repository.get_order_by_id(order_id)

    @transaction.atomic
    def create_order(
        self,
        order_data: CreateOrderSchema,
        user: User
    ) -> Order:
        """Create a new order - nhân viên nội bộ tạo đơn."""
        # Calculate totals
        subtotal = sum(item.quantity * item.price for item in order_data.items)
        total = subtotal + order_data.shipping_fee + order_data.chip_fee

        # Calculate deadline
        duration = OrderStatus.get_duration_minutes(OrderStatus.CREATED)
        deadline = timezone.now() + timedelta(minutes=duration)

        # Create order với thông tin khách hàng nhập trực tiếp
        order = Order.objects.create(
            order_name='',  # Temporary placeholder, will be set below
            customer_name=order_data.customer_name,
            customer_phone=order_data.customer_phone,
            customer_address=order_data.customer_address,
            status=OrderStatus.CREATED.value,
            status_changed_at=timezone.now(),
            deadline=deadline,
            delivery_time=order_data.delivery_time,  # Now required
            subtotal=subtotal,
            shipping_fee=order_data.shipping_fee,
            chip_fee=order_data.chip_fee,
            total=total,
            created_by=user,
            notes=order_data.notes
        )

        # Auto-generate order_name if not provided (use order_number)
        if not order_data.order_name:
            order.order_name = order.order_number
            order.save(update_fields=['order_name'])
        else:
            order.order_name = order_data.order_name
            order.save(update_fields=['order_name'])

        # Add items
        for item_data in order_data.items:
            # If product_id is provided, fetch the product
            product = None
            if item_data.product_id:
                try:
                    product = Product.objects.get(id=item_data.product_id)
                except Product.DoesNotExist:
                    raise ValueError(f"Product with ID {item_data.product_id} not found")

            OrderItem.objects.create(
                order=order,
                product=product,  # Can be None if manually entered
                product_name=item_data.product_name,
                quantity=item_data.quantity,
                unit=item_data.unit,
                price=item_data.price,
                note=item_data.note or ''
            )

        # Assign users
        if order_data.assigned_to_ids:
            assigned_users = User.objects.filter(id__in=order_data.assigned_to_ids)
            order.assigned_to.set(assigned_users)

        # Log activity
        self._log_activity(
            order=order,
            user=user,
            activity_type='created',
            description=f"Tạo đơn hàng #{order.order_number} cho khách hàng {order.customer_name}",
            metadata={
                'customer_name': order.customer_name,
                'customer_phone': order.customer_phone,
                'total': float(order.total)
            }
        )

        # Broadcast order created event
        from apps.orders.schemas.output_schema import OrderDetailSchema
        order_data = OrderDetailSchema.from_orm(order).model_dump(mode='json')
        broadcast_order_created(order_data)

        return order

    @transaction.atomic
    def update_order(
        self,
        order_id: int,
        order_data,
        user: User
    ) -> Order:
        """Update order details (items, customer info, fees, etc.)."""
        from apps.orders.schemas.input_schema import UpdateOrderSchema

        order = self.get_order_by_id(order_id)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")

        # Update basic fields if provided
        if order_data.order_name is not None:
            order.order_name = order_data.order_name
        if order_data.customer_name is not None:
            order.customer_name = order_data.customer_name
        if order_data.customer_phone is not None:
            order.customer_phone = order_data.customer_phone
        if order_data.customer_address is not None:
            order.customer_address = order_data.customer_address
        if order_data.shipping_fee is not None:
            order.shipping_fee = order_data.shipping_fee
        if order_data.chip_fee is not None:
            order.chip_fee = order_data.chip_fee
        if order_data.delivery_time is not None:
            order.delivery_time = order_data.delivery_time
        if order_data.notes is not None:
            order.notes = order_data.notes

        # Update items if provided
        if order_data.items is not None:
            # Delete existing items
            order.items.all().delete()

            # Create new items
            for item_data in order_data.items:
                product = None
                if item_data.product_id:
                    try:
                        product = Product.objects.get(id=item_data.product_id)
                    except Product.DoesNotExist:
                        raise ValueError(f"Product with ID {item_data.product_id} not found")

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=item_data.product_name,
                    quantity=item_data.quantity,
                    unit=item_data.unit,
                    price=item_data.price,
                    note=item_data.note or ''
                )

        # Recalculate totals
        subtotal = sum(item.total for item in order.items.all())
        order.subtotal = subtotal
        order.total = subtotal + order.shipping_fee + order.chip_fee
        order.save()

        # Update assigned users if provided
        if order_data.assigned_to_ids is not None:
            assigned_users = User.objects.filter(id__in=order_data.assigned_to_ids)
            order.assigned_to.set(assigned_users)

        # Log activity
        self._log_activity(
            order=order,
            user=user,
            activity_type='updated',
            description=f"Cập nhật đơn hàng #{order.order_number}",
            metadata={
                'updated_by': user.get_full_name()
            }
        )

        # Broadcast order updated event
        from apps.orders.schemas.output_schema import OrderDetailSchema
        order_data_dict = OrderDetailSchema.from_orm(order).model_dump(mode='json')
        broadcast_order_updated(order_data_dict)

        return order

    @transaction.atomic
    def update_order_status(
        self,
        order_id: int,
        status_data: UpdateOrderStatusSchema,
        user: User
    ) -> Order:
        """Update order status."""
        order = self.get_order_by_id(order_id)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")

        # Validate status transition
        self._validate_status_transition(order, status_data.new_status)

        # Validate transition requirements
        self._validate_transition_requirements(order, status_data.new_status)

        # Get old status for logging
        old_status = order.status
        old_status_label = OrderStatus.get_label(OrderStatus(old_status))
        new_status_label = OrderStatus.get_label(OrderStatus(status_data.new_status))

        # Update status
        order.update_status(
            new_status=status_data.new_status,
            user=user,
            reason=status_data.failure_reason
        )

        # Log activity
        self._log_activity(
            order=order,
            user=user,
            activity_type='status_change',
            description=f"Chuyển trạng thái từ '{old_status_label}' sang '{new_status_label}'",
            old_value=old_status,
            new_value=status_data.new_status,
            metadata={
                'reason': status_data.failure_reason if status_data.failure_reason else None
            }
        )

        # Broadcast order status changed event
        from apps.orders.schemas.output_schema import OrderDetailSchema
        order_data = OrderDetailSchema.from_orm(order).model_dump(mode='json')
        broadcast_order_status_changed(order.id, old_status, status_data.new_status, order_data)

        return order

    def _validate_status_transition(self, order: Order, new_status: str):
        """Validate if status transition is allowed."""
        current_status = order.status

        # Can't change from completed or failed
        if current_status in [OrderStatus.COMPLETED.value, OrderStatus.FAILED.value]:
            raise ValueError(
                f"Không thể thay đổi trạng thái từ '{OrderStatus.get_label(OrderStatus(current_status))}'"
            )

        # Can always mark as failed
        if new_status == OrderStatus.FAILED.value:
            return

        # Define the workflow order
        workflow_order = [
            OrderStatus.CREATED.value,
            OrderStatus.WEIGHING.value,
            OrderStatus.CREATE_INVOICE.value,
            OrderStatus.SEND_PHOTO.value,
            OrderStatus.PAYMENT.value,
            OrderStatus.IN_KITCHEN.value,
            OrderStatus.PROCESSING.value,
            OrderStatus.DELIVERY.value,
            OrderStatus.COMPLETED.value,
        ]

        # Validate new status is in workflow
        if new_status not in workflow_order:
            raise ValueError(
                f"Trạng thái '{new_status}' không hợp lệ"
            )

        # Get current and new status indices
        try:
            current_index = workflow_order.index(current_status)
            new_index = workflow_order.index(new_status)
        except ValueError:
            raise ValueError("Trạng thái không hợp lệ")

        # Special case: Can jump from PAYMENT to DELIVERY
        if current_status == OrderStatus.PAYMENT.value and new_status == OrderStatus.DELIVERY.value:
            return

        # Can only move to adjacent status (forward or backward by 1 step)
        if abs(new_index - current_index) != 1:
            raise ValueError(
                "Không thể nhảy cóc trạng thái. Vui lòng chuyển tuần tự theo quy trình."
            )

        # Additional check: Can only move TO completed from delivery status
        if new_status == OrderStatus.COMPLETED.value and current_status != OrderStatus.DELIVERY.value:
            raise ValueError(
                "Chỉ có thể chuyển sang 'Hoàn thành' từ trạng thái 'Giao hàng'"
            )

    def _validate_transition_requirements(self, order: Order, new_status: str):
        """Validate business requirements for each status transition."""
        current_status = order.status

        # CREATED -> WEIGHING: Must confirm weighing is done
        if current_status == OrderStatus.CREATED.value and new_status == OrderStatus.WEIGHING.value:
            # No special requirements, just confirmation in frontend
            pass

        # WEIGHING -> CREATE_INVOICE: Should have weighing images (but not strictly required)
        if current_status == OrderStatus.WEIGHING.value and new_status == OrderStatus.CREATE_INVOICE.value:
            # Optional: Check for weighing images
            pass

        # CREATE_INVOICE -> SEND_PHOTO: Must confirm sending photos to customer
        if current_status == OrderStatus.CREATE_INVOICE.value and new_status == OrderStatus.SEND_PHOTO.value:
            # No special requirements, just confirmation in frontend
            pass

        # SEND_PHOTO -> PAYMENT: Must confirm sending invoice to customer
        if current_status == OrderStatus.SEND_PHOTO.value and new_status == OrderStatus.PAYMENT.value:
            # No special requirements, just confirmation in frontend
            pass

        # PAYMENT -> IN_KITCHEN: Must confirm payment received
        if current_status == OrderStatus.PAYMENT.value and new_status == OrderStatus.IN_KITCHEN.value:
            # Payment confirmation required (handled in frontend)
            # Optional: bill image upload
            pass

        # IN_KITCHEN -> PROCESSING: Can set deadline
        if current_status == OrderStatus.IN_KITCHEN.value and new_status == OrderStatus.PROCESSING.value:
            # Optional: update deadline
            pass

        # PROCESSING -> DELIVERY: Must have shipping info
        if current_status == OrderStatus.PROCESSING.value and new_status == OrderStatus.DELIVERY.value:
            # Shipping info required (handled in frontend)
            pass

        # DELIVERY -> COMPLETED: Must confirm delivery success
        if current_status == OrderStatus.DELIVERY.value and new_status == OrderStatus.COMPLETED.value:
            # Confirmation required (handled in frontend)
            pass

    @transaction.atomic
    def update_assigned_users(
        self,
        order_id: int,
        user_ids: list[int],
        user: User
    ) -> Order:
        """Update assigned users for an order."""
        order = self.get_order_by_id(order_id)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")

        # Get users
        from apps.users.models import User as UserModel
        users = UserModel.objects.filter(id__in=user_ids)

        if len(users) != len(user_ids):
            raise ValueError("One or more user IDs are invalid")

        # Update assigned users
        order.assigned_to.set(users)
        order.save()

        # Create activity log
        self.repository.create_activity(
            order=order,
            action="assigned_users_updated",
            description=f"Phân công lại cho: {', '.join([u.get_full_name() for u in users])}",
            user=user
        )

        # Broadcast assignment change
        assigned_users_data = [{'id': u.id, 'name': u.get_full_name()} for u in users]
        broadcast_order_assigned(order.id, assigned_users_data)

        return order

    @transaction.atomic
    def upload_order_image(
        self,
        order_id: int,
        image_file,
        image_type: str,
        user: User
    ):
        """Upload image for order."""
        order = self.get_order_by_id(order_id)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")

        image = self.repository.add_order_image(
            order=order,
            image_data={
                'image': image_file,
                'image_type': image_type,
                'uploaded_by': user
            }
        )

        # Log activity
        image_type_labels = {
            'weighing': 'ảnh cân hàng',
            'invoice': 'ảnh phiếu đặt hàng',
            'other': 'ảnh khác'
        }
        self._log_activity(
            order=order,
            user=user,
            activity_type='image_uploaded',
            description=f"Upload {image_type_labels.get(image_type, 'ảnh')}",
            metadata={
                'image_type': image_type,
                'image_id': image.id
            }
        )

        # Broadcast image uploaded event
        image_data = {
            'id': image.id,
            'image_url': image.image.url if image.image else None,
            'image_type': image.image_type,
            'uploaded_by': user.get_full_name()
        }
        broadcast_order_image_uploaded(order.id, image_data)

        return image

    def get_order_statistics(self):
        """Get order statistics."""
        counts = self.repository.count_orders_by_status()
        stats = {item['status']: item['count'] for item in counts}

        return {
            'total': sum(stats.values()),
            'by_status': stats,
            'completed': stats.get(OrderStatus.COMPLETED.value, 0),
            'failed': stats.get(OrderStatus.FAILED.value, 0),
            'in_progress': sum(
                count for status, count in stats.items()
                if status not in [OrderStatus.COMPLETED.value, OrderStatus.FAILED.value]
            )
        }
