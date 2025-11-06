"""
Socket.IO client for Django to broadcast events.
Replaces Django Channels with HTTP calls to Socket.IO server.
"""
import requests
import logging
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Socket.IO server URL
SOCKETIO_SERVER_URL = getattr(
    settings,
    'SOCKETIO_SERVER_URL',
    'http://localhost:4000'
)


def _post_to_socketio(endpoint: str, data: Dict[str, Any]) -> bool:
    """
    Send HTTP POST request to Socket.IO server.

    Args:
        endpoint: API endpoint (e.g., '/broadcast/order-created')
        data: Payload to send

    Returns:
        bool: True if successful, False otherwise
    """
    url = f"{SOCKETIO_SERVER_URL}{endpoint}"

    try:
        response = requests.post(
            url,
            json=data,
            timeout=2  # 2 second timeout
        )
        response.raise_for_status()

        result = response.json()
        logger.info(
            f"✅ Broadcasted to Socket.IO: {endpoint} "
            f"(Clients: {result.get('clients', 0)})"
        )
        return True

    except requests.exceptions.RequestException as e:
        logger.error(
            f"❌ Failed to broadcast to Socket.IO: {endpoint} - {e}"
        )
        return False
    except Exception as e:
        logger.error(
            f"❌ Unexpected error broadcasting to Socket.IO: {endpoint} - {e}"
        )
        return False


def broadcast_order_created(order_data: Dict[str, Any]) -> bool:
    """
    Broadcast order_created event to all connected clients.

    Args:
        order_data: Order data dictionary (must be JSON serializable)

    Returns:
        bool: True if successful
    """
    logger.info(
        f"🔔 Broadcasting order_created for order "
        f"#{order_data.get('order_number', 'unknown')}"
    )

    return _post_to_socketio('/broadcast/order-created', {
        'order': order_data
    })


def broadcast_order_updated(order_data: Dict[str, Any]) -> bool:
    """
    Broadcast order_updated event to all connected clients.

    Args:
        order_data: Order data dictionary

    Returns:
        bool: True if successful
    """
    logger.info(
        f"🔔 Broadcasting order_updated for order "
        f"#{order_data.get('order_number', 'unknown')}"
    )

    return _post_to_socketio('/broadcast/order-updated', {
        'order': order_data
    })


def broadcast_order_deleted(order_id: int) -> bool:
    """
    Broadcast order_deleted event to all connected clients.

    Args:
        order_id: Order ID

    Returns:
        bool: True if successful
    """
    logger.info(f"🔔 Broadcasting order_deleted for order ID {order_id}")

    return _post_to_socketio('/broadcast/order-deleted', {
        'order_id': str(order_id)
    })


def broadcast_order_status_changed(
    order_id: int,
    old_status: str,
    new_status: str,
    order_data: Dict[str, Any]
) -> bool:
    """
    Broadcast order_status_changed event to all connected clients.

    Args:
        order_id: Order ID
        old_status: Previous status
        new_status: New status
        order_data: Full order data

    Returns:
        bool: True if successful
    """
    logger.info(
        f"🔔 Broadcasting order_status_changed for order ID {order_id} "
        f"({old_status} → {new_status})"
    )

    return _post_to_socketio('/broadcast/order-status-changed', {
        'order_id': str(order_id),
        'old_status': old_status,
        'new_status': new_status,
        'order': order_data
    })


def broadcast_order_image_uploaded(
    order_id: int,
    image_data: Dict[str, Any],
    order_data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Broadcast order_image_uploaded event to all connected clients.

    Args:
        order_id: Order ID
        image_data: Image data dictionary
        order_data: Optional full order data for realtime update

    Returns:
        bool: True if successful
    """
    logger.info(f"🔔 Broadcasting order_image_uploaded for order ID {order_id}")

    payload = {
        'order_id': str(order_id),
        'image': image_data
    }

    if order_data:
        payload['order'] = order_data

    return _post_to_socketio('/broadcast/order-image-uploaded', payload)


def broadcast_order_image_deleted(
    order_id: int,
    image_id: int,
    order_data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Broadcast order_image_deleted event to all connected clients.

    Args:
        order_id: Order ID
        image_id: Image ID that was deleted
        order_data: Optional full order data for realtime update

    Returns:
        bool: True if successful
    """
    logger.info(f"🔔 Broadcasting order_image_deleted for order ID {order_id}")

    payload = {
        'order_id': str(order_id),
        'image_id': str(image_id)
    }

    if order_data:
        payload['order'] = order_data

    return _post_to_socketio('/broadcast/order-image-deleted', payload)


def broadcast_order_assigned(
    order_id: int,
    assigned_users: list,
    order_data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Broadcast order_assigned event to all connected clients.

    Args:
        order_id: Order ID
        assigned_users: List of assigned user data
        order_data: Optional full order data for realtime update

    Returns:
        bool: True if successful
    """
    logger.info(f"🔔 Broadcasting order_assigned for order ID {order_id}")

    payload = {
        'order_id': str(order_id),
        'assigned_users': assigned_users
    }

    if order_data:
        payload['order'] = order_data

    return _post_to_socketio('/broadcast/order-assigned', payload)


# ==================== Comment/Chat Broadcasting ====================

def broadcast_comment_created(order_id: int, comment_data: Dict[str, Any]) -> bool:
    """
    Broadcast comment_created event to all connected clients.

    Args:
        order_id: Order ID
        comment_data: Comment data dictionary

    Returns:
        bool: True if successful
    """
    logger.info(
        f"🔔 Broadcasting comment_created for order ID {order_id}"
    )

    return _post_to_socketio('/broadcast/comment-created', {
        'order_id': str(order_id),
        'comment': comment_data
    })


def broadcast_comment_updated(order_id: int, comment_data: Dict[str, Any]) -> bool:
    """
    Broadcast comment_updated event to all connected clients.

    Args:
        order_id: Order ID
        comment_data: Updated comment data

    Returns:
        bool: True if successful
    """
    logger.info(
        f"🔔 Broadcasting comment_updated for order ID {order_id}"
    )

    return _post_to_socketio('/broadcast/comment-updated', {
        'order_id': str(order_id),
        'comment': comment_data
    })


def broadcast_comment_deleted(order_id: int, comment_id: int) -> bool:
    """
    Broadcast comment_deleted event to all connected clients.

    Args:
        order_id: Order ID
        comment_id: Comment ID that was deleted

    Returns:
        bool: True if successful
    """
    logger.info(
        f"🔔 Broadcasting comment_deleted for order ID {order_id}, comment {comment_id}"
    )

    return _post_to_socketio('/broadcast/comment-deleted', {
        'order_id': str(order_id),
        'comment_id': str(comment_id)
    })
