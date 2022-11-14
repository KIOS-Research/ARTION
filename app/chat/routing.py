from django.urls import re_path

from . import consumers, location_consumer, location_global_consumer

websocket_urlpatterns = [
    re_path(r'wss/chat/(?P<room_type>\w+)/(?P<room_name>\w+)/(?P<mission_id>\w+)/$', consumers.AsyncChatConsumer.as_asgi()),
    re_path(r'wss/location/(?P<mission_id>\w+)/$', location_consumer.AsyncLocationConsumer.as_asgi()),
    re_path(r'wss/locationGlobal/(?P<mission_id>\w+)/$', location_global_consumer.AsyncLocationConsumer.as_asgi()),
    re_path(r'wss/alert/(?P<mission_id>\w+)/$', consumers.AsyncAlertConsumer.as_asgi()),
]
