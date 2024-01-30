from django.urls import path

from apps.chat import consumers

chatsocket_urlpatterns = [
    path("api/v2/ws/chats/<str:id>/", consumers.ChatConsumer.as_asgi())
]
