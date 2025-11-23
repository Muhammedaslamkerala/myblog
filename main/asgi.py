"""
ASGI config for main project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import users.routing
import blog.routing 

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings') # Replace 'myproject'

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            blog.routing.websocket_urlpatterns +  # Blog chat: /ws/post/<slug>/chat/
            users.routing.websocket_urlpatterns
            
        )
    ),
})