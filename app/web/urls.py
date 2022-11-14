from django.conf import settings
from django.urls import path
from django.contrib.auth import views as auth_views

from . import views
from .forms import CustomAuthenticationForm

app_name = 'web'

urlpatterns = [
    # map urls
    path('map/<int:pk>/', views.MapIdView.as_view(), name='map_id'),
    # mission urls
    path('new-mission/', views.NewMissionView.as_view(), name='new_mission'),
    path('end-mission/<int:mission_id>/', views.EndMissionView.as_view(), name='end_mission'),
    path('', views.FindMissionView.as_view(), name='find_mission'),
    # predefined teams urls
    path('predefined_team/view/', views.ViewPredefinedTeamsView.as_view(), name='predefined_view'),
    path('predefined_team/add/', views.AddPredefinedTeamsView.as_view(), name='predefined_add'),
    path('predefined_team/edit/<int:pk>/', views.EditPredefinedTeamsView.as_view(), name='predefined_edit'),
    path('predefined_team/delete/<int:pk>/', views.DeletePredefinedTeamsView.as_view(), name='predefined_delete'),
    # mission teams urls
    path('team/view/<int:mission_id>/', views.ViewMissionTeamsView.as_view(), name='team_view'),
    path('team/predefined/view/<int:mission_id>/', views.ViewPredefinedTeamsMissionView.as_view(), name='mission_predefined_view'),
    path('team/add/<int:mission_id>/', views.AddMissionTeamsView.as_view(), name='team_add'),
    path('team/add/predefined/<int:mission_id>/<int:team_id>/', views.AssignPredefinedTeamsMissionView.as_view(), name='mission_predefined_add'),
    path('team/edit/<int:mission_id>/<int:pk>/', views.EditMissionTeamsView.as_view(), name='team_edit'),
    path('team/delete/<int:mission_id>/<int:pk>/', views.DeleteMissionTeamsView.as_view(), name='team_delete'),
    # car urls
    path('car/view/', views.ViewCarView.as_view(), name='car_view'),
    path('car/add/', views.AddCarView.as_view(), name='car_add'),
    path('car/edit/<int:pk>/', views.EditCarView.as_view(), name='car_edit'),
    path('car/delete/<int:pk>/', views.DeleteCarView.as_view(), name='car_delete'),
    # mission cars
    path('car/view/<int:mission_id>/', views.ViewMissionCarView.as_view(), name='mission_car_view'),
    path('car/release/<int:mission_id>/<int:pk>/', views.ReleaseMissionCarView.as_view(), name='mission_car_release'),
    # map feature urls
    path('feature/add/', views.AddMapFeatureView.as_view(), name='add_feature'),
    path('feature/delete/', views.DeleteMapFeatureView.as_view(), name='delete_feature'),
    # auth urls
    path('login/', auth_views.LoginView.as_view(
        extra_context={'next': settings.HOME_URL},authentication_form=CustomAuthenticationForm), name='user_login'),
    path('logout/', auth_views.LogoutView.as_view(next_page=settings.LOGIN_URL), name='user_logout'),
    # media url
    path('media/<str:name>/', views.ImageView.as_view())
]
