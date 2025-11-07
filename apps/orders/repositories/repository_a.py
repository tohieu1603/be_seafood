"""Order repository."""
from typing import List, Optional
from django.db.models import Q, Prefetch, Count
from apps.orders.models import Order, OrderItem, OrderImage
from apps.orders.schemas.input_schema import OrderFilterSchema


class OrderRepository:
    """Repository for Order model."""

    @staticmethod
    def get_all_orders(filters: OrderFilterSchema, user_id: Optional[int] = None):
        """Get all orders with filters."""
        queryset = Order.objects.select_related(
            'created_by'
        ).prefetch_related(
            'assigned_to',
            'items',
            'images'
        ).annotate(
            items_count=Count('items', distinct=True),
            images_count=Count('images', distinct=True)
        )

        # Apply filters
        if filters.status:
            queryset = queryset.filter(status=filters.status)

        if filters.assigned_to_me and user_id:
            queryset = queryset.filter(assigned_to__id=user_id)

        if filters.search:
            queryset = queryset.filter(
                Q(order_name__icontains=filters.search) |
                Q(order_number__icontains=filters.search) |
                Q(customer_name__icontains=filters.search) |
                Q(customer_phone__icontains=filters.search)
            )

        if filters.date_from:
            # Convert to timezone-aware datetime at start of day
            from django.utils import timezone as tz
            from datetime import datetime, time

            # If date_from is a string, parse it
            if isinstance(filters.date_from, str):
                date_obj = datetime.fromisoformat(filters.date_from.replace('Z', '+00:00'))
                if date_obj.tzinfo is None:
                    # Make it timezone-aware at start of day
                    date_obj = tz.make_aware(datetime.combine(date_obj.date(), time.min))
                start_date = date_obj
            else:
                # Already a datetime object
                if filters.date_from.tzinfo is None:
                    start_date = tz.make_aware(datetime.combine(filters.date_from.date(), time.min))
                else:
                    start_date = filters.date_from

            queryset = queryset.filter(created_at__gte=start_date)

        if filters.date_to:
            # Include entire day by using end of day (23:59:59)
            from django.utils import timezone as tz
            from datetime import datetime, time, timedelta

            # If date_to is a string, parse it
            if isinstance(filters.date_to, str):
                date_obj = datetime.fromisoformat(filters.date_to.replace('Z', '+00:00'))
                if date_obj.tzinfo is None:
                    # Make it timezone-aware at end of day
                    date_obj = tz.make_aware(datetime.combine(date_obj.date(), time.max))
                end_date = date_obj
            else:
                # Already a datetime object
                if filters.date_to.tzinfo is None:
                    end_date = tz.make_aware(datetime.combine(filters.date_to.date(), time.max))
                else:
                    # Add full day
                    end_date = filters.date_to.replace(hour=23, minute=59, second=59, microsecond=999999)

            queryset = queryset.filter(created_at__lte=end_date)

        return queryset

    @staticmethod
    def get_order_by_id(order_id: int) -> Optional[Order]:
        """Get order by ID with all relations."""
        try:
            return Order.objects.select_related(
                'created_by'
            ).prefetch_related(
                'assigned_to',
                'items__product',
                'images',
                'status_history'
            ).get(id=order_id)
        except Order.DoesNotExist:
            return None

    @staticmethod
    def get_order_by_number(order_number: str) -> Optional[Order]:
        """Get order by order number."""
        try:
            return Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return None

    @staticmethod
    def create_order(order_data: dict) -> Order:
        """Create a new order."""
        return Order.objects.create(**order_data)

    @staticmethod
    def update_order(order: Order, update_data: dict) -> Order:
        """Update an order."""
        for key, value in update_data.items():
            setattr(order, key, value)
        order.save()
        return order

    @staticmethod
    def delete_order(order: Order):
        """Delete an order (soft delete if needed)."""
        order.delete()

    @staticmethod
    def get_order_images(order: Order, image_type: Optional[str] = None) -> List[OrderImage]:
        """Get order images by type."""
        queryset = order.images.all()
        if image_type:
            queryset = queryset.filter(image_type=image_type)
        return list(queryset)

    @staticmethod
    def add_order_image(order: Order, image_data: dict) -> OrderImage:
        """Add image to order."""
        return OrderImage.objects.create(order=order, **image_data)

    @staticmethod
    def count_orders_by_status():
        """Count orders by status."""
        from django.db.models import Count
        return Order.objects.values('status').annotate(count=Count('id'))
