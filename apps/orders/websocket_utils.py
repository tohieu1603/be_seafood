"""
WebSocket utility functions for broadcasting order events.
"""
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


def broadcast_order_created(order_data):
    """Broadcast order_created event to all connected clients."""
    logger.info(f"🔔 Broadcasting order_created for order #{order_data.get('order_number', 'unknown')}")

    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.error("❌ Channel layer is None! WebSocket will not work.")
        return

    try:
        async_to_sync(channel_layer.group_send)(
            'order_updates',
            {
                'type': 'order_created',
                'order': order_data
            }
        )
        logger.info(f"✅ Broadcasted order_created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to broadcast order_created: {e}")


def broadcast_order_updated(order_data):
    """Broadcast order_updated event to all connected clients."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'order_updates',
        {
            'type': 'order_updated',
            'order': order_data
        }
    )


def broadcast_order_deleted(order_id):
    """Broadcast order_deleted event to all connected clients."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'order_updates',
        {
            'type': 'order_deleted',
            'order_id': str(order_id)
        }
    )


def broadcast_order_status_changed(order_id, old_status, new_status, order_data):
    """Broadcast order_status_changed event to all connected clients."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'order_updates',
        {
            'type': 'order_status_changed',
            'order_id': str(order_id),
            'old_status': old_status,
            'new_status': new_status,
            'order': order_data
        }
    )


def broadcast_order_image_uploaded(order_id, image_data):
    """Broadcast order_image_uploaded event to all connected clients."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'order_updates',
        {
            'type': 'order_image_uploaded',
            'order_id': str(order_id),
            'image': image_data
        }
    )


def broadcast_order_image_deleted(order_id, image_id):
    """Broadcast order_image_deleted event to all connected clients."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'order_updates',
        {
            'type': 'order_image_deleted',
            'order_id': str(order_id),
            'image_id': str(image_id)
        }
    )


def broadcast_order_assigned(order_id, assigned_users):
    """Broadcast order_assigned event to all connected clients."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'order_updates',
        {
            'type': 'order_assigned',
            'order_id': str(order_id),
            'assigned_users': assigned_users
        }
    )
