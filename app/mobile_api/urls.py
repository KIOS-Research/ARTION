from django.urls import path

from . import views

app_name = 'mobile_api'

urlpatterns = [
    path('login/', views.MobileLogin.as_view()),
    path('logout/', views.MobileLogout.as_view()),
    path('authenticate_mission_code/', views.MissionValidationView.as_view()),
    path('image/', views.UploadPhotoView.as_view()),
    path('media/<str:path>/', views.GetPhotoView.as_view()),
    path('chat_history/<str:chat_type>/<int:mission_id>/', views.GetChatHistory.as_view()),
]
