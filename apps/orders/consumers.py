"""
WebSocket consumers for real-time order updates.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class OrderConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time order updates.
    Handles:
    - Order creation
    - Order status updates
    - Order deletion
    - Order image uploads/deletes
    - Order assignments
    """

    async def connect(self):
        """Accept WebSocket connection and join order updates group."""
        self.room_group_name = 'order_updates'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to order updates'
        }))

    async def disconnect(self, close_code):
        """Leave room group on disconnect."""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Receive message from WebSocket (currently not used for client->server).
        This consumer is primarily for server->client broadcasts.
        """
        pass

    # Handler for order_created event
    async def order_created(self, event):
        """Send order_created event to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'order_created',
            'order': event['order']
        }))

    # Handler for order_updated event
    async def order_updated(self, event):
        """Send order_updated event to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'order_updated',
            'order': event['order']
        }))

    # Handler for order_deleted event
    async def order_deleted(self, event):
        """Send order_deleted event to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'order_deleted',
            'order_id': event['order_id']
        }))

    # Handler for order_status_changed event
    async def order_status_changed(self, event):
        """Send order_status_changed event to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'order_status_changed',
            'order_id': event['order_id'],
            'old_status': event['old_status'],
            'new_status': event['new_status'],
            'order': event['order']
        }))

    # Handler for order_image_uploaded event
    async def order_image_uploaded(self, event):
        """Send order_image_uploaded event to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'order_image_uploaded',
            'order_id': event['order_id'],
            'image': event['image']
        }))

    # Handler for order_image_deleted event
    async def order_image_deleted(self, event):
        """Send order_image_deleted event to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'order_image_deleted',
            'order_id': event['order_id'],
            'image_id': event['image_id']
        }))

    # Handler for order_assigned event
    async def order_assigned(self, event):
        """Send order_assigned event to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'order_assigned',
            'order_id': event['order_id'],
            'assigned_users': event['assigned_users']
        }))
