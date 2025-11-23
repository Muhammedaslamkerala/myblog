# users/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

logger = logging.getLogger(__name__)

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        # Only allow authenticated users to connect
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        # Create a user-specific group name
        self.group_name = f"notifications_{self.user.id}"
        logger.info(f"User {self.user.id} connecting to WebSocket group {self.group_name}")

        # Join the user-specific group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the user-specific group if it was set
        if hasattr(self, 'group_name'):
            logger.info(f"User {self.user.id} disconnecting from WebSocket group {self.group_name}")
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def send_notification_update(self, event):
        """
        Handler for messages sent from the backend (e.g., Celery task) to the user's group.
        It forwards the message directly to the connected client.
        """
        data = event.get('data', {})
        logger.info(f"Sending WebSocket update to user {self.user.id}: {data}")
        await self.send(text_data=json.dumps(data))