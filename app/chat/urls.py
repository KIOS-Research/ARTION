from django.urls import path

from . import views

app_name = 'chat'

urlpatterns = [
    path('user/<str:room_name>/', views.RoomUserView.as_view(), name='room'),
    path('<int:mission_id>/', views.ChatView.as_view(), name='chat_index'),
]
