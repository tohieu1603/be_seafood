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
            queryset = queryset.filter(created_at__gte=filters.date_from)

        if filters.date_to:
            # Include entire day by adding 1 day and using __lt
            from datetime import timedelta
            end_date = filters.date_to + timedelta(days=1)
            queryset = queryset.filter(created_at__lt=end_date)

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
