from django.urls import path

from apps.profiles import consumers

notification_socket_urlpatterns = [
    path("api/v2/ws/notifications/", consumers.NotificationConsumer.as_asgi())
]
