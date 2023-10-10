from django.urls import path

from apps.chat import consumers

from . import views

chatsocket_urlpatterns = [
    path("api/v2/ws/chat/<uuid:id>/", consumers.ChatConsumer.as_asgi())
]
