import traceback
from datetime import datetime

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.utils.crypto import get_random_string
from rest_framework import status

from .forms import AddMissionForm, AddTeamPredefinedForm, MissionTeamForm, CarForm, AssignCarForm, \
    FeatureForm
from .models import Mission, TeamPredefined, TeamPredefinedMembers, Team, UserTeam, Car, TeamCar, MapFeature


def mission_unique_code():
    uid = get_random_string(4, allowed_chars='0123456789') + '-' + \
        get_random_string(4, allowed_chars='0123456789') + '-' + \
        get_random_string(4, allowed_chars='0123456789')

    while Mission.objects.filter(unique_code=uid).first() is not None:
        uid = get_random_string(4, allowed_chars='0123456789') + '-' + \
              get_random_string(4, allowed_chars='0123456789') + '-' + \
              get_random_string(4, allowed_chars='0123456789')

    return uid


class MapIdView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, pk):
        mission_obj = get_object_or_404(Mission, mission_id=pk)
        people_list = []
        for user in User.objects.filter(is_active=True).exclude(pk=request.user.pk):
            people_list.append({'full_name': user.first_name + ' ' + user.last_name, 'username': user.username})

        feature_list = []
        for feature in MapFeature.objects.filter(user=request.user, mission_id=pk, valid_to=None):

            feat_type = feature.geom.geom_type
            if str(feat_type) == 'Point':
                feature_list.append({'type': str(feat_type), 'id': feature.pk, 'lat': feature.geom[0],
                                     'lng': feature.geom[1], 'timestamp': feature.timestamp, 'name': feature.name})
            else:
                list_geom = []
                for coord in feature.geom:
                    list_geom.append([coord[0], coord[1]])
                feature_list.append({'type': str(feat_type), 'id': feature.pk, 'geom': list_geom,
                                     'timestamp': feature.timestamp, 'name': feature.name})

        context = {
            'mission_id': pk,
            'mission_ended': mission_obj.is_closed,
            'mission_code': mission_obj.unique_code,
            'username': request.user,
            'server_mode': settings.USE_X_FORWARDED_HOST,
            'people_list': people_list,
            'feature_list': feature_list,
        }
        return render(request, 'web/map.html', context)


class NewMissionView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request):
        return render(request, 'web/newMission.html', {'form': AddMissionForm(request.POST or None),
                                                       'username': request.user})

    def post(self, request):
        form = AddMissionForm(request.POST or None)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.date = datetime.now()
            obj.create_user_id = request.user.pk
            uid = mission_unique_code()
            obj.unique_code = uid
            obj.is_closed = False
            obj.save()
            request.session['code'] = uid
            return redirect(reverse('web:mission_predefined_view', args=[obj.pk]))
        else:
            return render(request, 'web/newMission.html', {'form': form, 'username': request.user})


class EndMissionView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, mission_id):
        obj = get_object_or_404(Mission, pk=mission_id)
        try:
            obj.is_closed = True
            obj.save()
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return HttpResponse(status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return HttpResponseRedirect(reverse('web:find_mission'))


class FindMissionView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request):
        obj = Mission.objects.filter(~Q(is_hidden=True)).values('name', 'date', 'unique_code', 'mission_id', 'is_closed')

        return render(request, 'web/findMission.html', {'data': obj, 'username': request.user})


class AddMapFeatureView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def post(self, request):
        form = FeatureForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user_id = request.user.pk
            obj.mission_id = form.cleaned_data.get("mission_id")
            obj.save()
            return JsonResponse(data={'pk': obj.pk})
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)


class DeleteMapFeatureView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def post(self, request):

        obj = get_object_or_404(MapFeature, pk=request.POST['pk'])
        try:
            obj.valid_to = datetime.now()
            obj.save()
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return HttpResponse(status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return HttpResponse(status=status.HTTP_204_NO_CONTENT)


class ImageView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, name):
        if default_storage.exists(name):
            data = open(default_storage.path(name), 'rb')
            return FileResponse(data, )
        return HttpResponse(status=status.HTTP_404_NOT_FOUND)


# #### Predefined Teams - Start ####
class ViewPredefinedTeamsView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request):
        obj = TeamPredefined.objects.all()

        return render(request, 'web/predefined_view.html', {'data': obj, 'username': request.user})


class AddPredefinedTeamsView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request):
        form = AddTeamPredefinedForm()
        context = {
            'form': form,
            'title': 'Predefined Teams',
            'type': 'add',
            'view_url': reverse('web:predefined_view'),
            'username': request.user
        }
        return render(request, 'web/predefined_form.html', context)

    def post(self, request):
        form = AddTeamPredefinedForm(request.POST)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('web:predefined_view'))
        else:
            context = {
                'form': form,
                'title': 'Predefined Teams',
                'type': 'add',
                'view_url': reverse('web:predefined_view'),
                'username': request.user
            }
            return render(request, 'web/predefined_form.html', context)


class EditPredefinedTeamsView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, pk):
        obj = get_object_or_404(TeamPredefined, pk=pk)
        form = AddTeamPredefinedForm(request.POST or None, instance=obj,)
        context = {
            'form': form,
            'title': 'Predefined Teams',
            'type': 'edit',
            'view_url': reverse('web:predefined_view'),
            'username': request.user
        }
        return render(request, 'web/predefined_form.html', context)

    def post(self, request, pk):
        obj = get_object_or_404(TeamPredefined, pk=pk)
        form = AddTeamPredefinedForm(request.POST or None, instance=obj)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('web:predefined_view'))
        else:
            context = {
                'form': form,
                'title': 'Predefined Teams',
                'type': 'edit',
                'view_url': reverse('web:predefined_view'),
                'username': request.user
            }
            return render(request, 'web/predefined_form.html', context)


class DeletePredefinedTeamsView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, pk):
        obj = get_object_or_404(TeamPredefined, pk=pk)
        try:
            with transaction.atomic():
                for member in TeamPredefinedMembers.objects.filter(team=obj):
                    member.delete()
                obj.delete()
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return HttpResponse(status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return HttpResponseRedirect(reverse('web:predefined_view'))
# #### Predefined Teams - End ####


# #### Predefined Teams Mission - Start ####
class ViewPredefinedTeamsMissionView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, mission_id):
        mission_obj = Mission.objects.get(mission_id=mission_id)
        if mission_obj.is_closed:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)
        obj = (team for team in TeamPredefined.objects.all() if team.available_team)
        context = {
            'data': obj,
            'mission_id': mission_id,
            'mission_ended': mission_obj.is_closed,
            'mission_code': mission_obj.unique_code,
            'username': request.user,
            'server_mode': settings.USE_X_FORWARDED_HOST,
        }
        return render(request, 'web/mission_predefined_view.html', context)


class AssignPredefinedTeamsMissionView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, mission_id, team_id):
        if Mission.objects.get(mission_id=mission_id).is_closed:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)

        obj = get_object_or_404(TeamPredefined, pk=team_id)
        if obj.available_team:
            team = Team.objects.create(
                name=obj.team_name,
                info=obj.info,
                mission_id=mission_id,
            )
            # assign users in team
            for member in obj.team_member.all():
                UserTeam.objects.create(
                    user=member,
                    team=team
                )
        return HttpResponseRedirect(reverse('web:mission_predefined_view', args=[mission_id]))
# #### Predefined Teams Missions - End ####


# #### Mission Teams - Start ####
class ViewMissionTeamsView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, mission_id):
        obj = Team.objects.filter(mission_id=mission_id)
        mission_obj = Mission.objects.get(mission_id=mission_id)
        context = {
            'data': obj,
            'mission_id': mission_id,
            'mission_ended': mission_obj.is_closed,
            'mission_code': mission_obj.unique_code,
            'username': request.user,
            'server_mode': settings.USE_X_FORWARDED_HOST,
        }
        return render(request, 'web/team_view.html', context)


class AddMissionTeamsView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, mission_id):
        if Mission.objects.get(mission_id=mission_id).is_closed:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)

        form = MissionTeamForm(mission_id=mission_id, is_add=True, team=None)
        code = Mission.objects.get(mission_id=mission_id).unique_code

        context = {
            'form': form,
            'mission_id': mission_id,
            'title': 'Mission Team',
            'mission_code': code,
            'mission_ended': False,
            'server_mode': settings.USE_X_FORWARDED_HOST,
            'view_url': reverse('web:team_view', args=[mission_id]),
        }
        return render(request, 'web/team_form.html', context=context)

    def post(self, request, mission_id):
        if Mission.objects.get(mission_id=mission_id).is_closed:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)

        data = request.POST.copy()
        data['mission'] = Mission.objects.get(pk=mission_id)
        code = data['mission'].unique_code
        form = MissionTeamForm(data=data, mission_id=mission_id, is_add=True, team=None)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('web:team_view', args=[mission_id]))
        else:
            # code = Mission.objects.get(mission_id=mission_id).unique_code
            context = {
                'form': form,
                'username': request.user,
                'mission_id': mission_id,
                'mission_code': code,
                'mission_ended': False,
                'title': 'Mission Team',
                'server_mode': settings.USE_X_FORWARDED_HOST,
                'view_url': reverse('web:team_view', args=[mission_id])
            }
            return render(request, 'web/team_form.html', context)


class EditMissionTeamsView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, mission_id, pk):
        if Mission.objects.get(mission_id=mission_id).is_closed:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)

        obj = get_object_or_404(Team, pk=pk)
        form = MissionTeamForm(data=request.POST or None, instance=obj, mission_id=mission_id, is_add=False, team=obj)
        code = Mission.objects.get(mission_id=mission_id).unique_code
        context = {
            'form': form,
            'username': request.user,
            'mission_id': mission_id,
            'mission_code': code,
            'mission_ended': False,
            'title': 'Mission Team',
            'server_mode': settings.USE_X_FORWARDED_HOST,
            'view_url': reverse('web:team_view', args=[mission_id])
        }
        return render(request, 'web/team_form.html', context)

    def post(self, request, mission_id, pk):
        if Mission.objects.get(mission_id=mission_id).is_closed:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)

        obj = get_object_or_404(Team, pk=pk)
        data = request.POST.copy()
        data['mission'] = Mission.objects.get(pk=mission_id)
        form = MissionTeamForm(data=data or None, instance=obj, mission_id=mission_id, is_add=False, team=obj)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('web:team_view', args=[mission_id]))
        else:
            if settings.DEBUG:
                print(form.errors)
            context = {
                'form': form,
                'username': request.user,
                'mission_id': mission_id,
                'mision_code': data['mission'].unique_code,
                'mission_ended': False,
                'title': 'Mission Team',
                'server_mode': settings.USE_X_FORWARDED_HOST,
                'view_url': reverse('web:team_view', args=[mission_id])
            }
            return render(request, 'web/team_form.html', context)


class DeleteMissionTeamsView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, mission_id, pk):
        if Mission.objects.get(mission_id=mission_id).is_closed:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)

        obj = get_object_or_404(Team, pk=pk, mission_id=mission_id)
        try:
            with transaction.atomic():
                for car in TeamCar.objects.filter(team=obj):
                    print(car.mission.pk)
                    car.delete()

                for member in UserTeam.objects.filter(team=obj):
                    member.delete()
                obj.delete()
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return HttpResponse(status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return HttpResponseRedirect(reverse('web:team_view', args=[mission_id]))
# #### Mission Teams - End ####


# #### Cars - Start ####
class ViewCarView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request):
        obj = Car.objects.all()

        return render(request, 'web/car_view.html', {'data': obj, 'username': request.user})


class AddCarView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request):
        form = CarForm()
        context = {
            'form': form,
            'title': 'Cars',
            'type': 'add',
            'view_url': reverse('web:car_view'),
            'username': request.user
        }
        return render(request, 'web/car_form.html', context)

    def post(self, request):
        form = CarForm(request.POST)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('web:car_view'))
        else:
            context = {
                'form': form,
                'title': 'Cars',
                'type': 'add',
                'view_url': reverse('web:car_view'),
                'username': request.user
            }
            return render(request, 'web/car_form.html', context)


class EditCarView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, pk):
        obj = get_object_or_404(Car, pk=pk)
        form = CarForm(data=request.POST or None, instance=obj)
        context = {
            'form': form,
            'title': 'Cars',
            'type': 'edit',
            'view_url': reverse('web:car_view'),
            'username': request.user
        }
        return render(request, 'web/car_form.html', context)

    def post(self, request, pk):
        obj = get_object_or_404(Car, pk=pk)
        form = CarForm(data=request.POST or None, instance=obj)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('web:car_view'))
        else:
            if settings.DEBUG:
                print(form.errors)
            context = {
                'form': form,
                'title': 'Cars',
                'type': 'edit',
                'view_url': reverse('web:car_view'),
                'username': request.user
            }
            return render(request, 'web/car_form.html', context)


class DeleteCarView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, pk):
        obj = get_object_or_404(Car, pk=pk)
        try:
            obj.delete()
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return HttpResponse(status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return HttpResponseRedirect(reverse('web:car_view'))
# #### Cars - End ####


# #### Cars Mission - Start ####
class ViewMissionCarView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, mission_id):
        mission_obj = Mission.objects.get(mission_id=mission_id)
        if mission_obj.is_closed:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)

        assign_form = AssignCarForm(mission_id=mission_id)
        obj = Car.objects.all()
        context = {
            'data': obj,
            'username': request.user,
            'mission_id': mission_id,
            'mission_code': mission_obj.unique_code,
            'mission_ended': mission_obj.is_closed,
            'server_mode': settings.USE_X_FORWARDED_HOST,
            'assign_form': assign_form
        }
        return render(request, 'web/mission_car_view.html', context)

    def post(self, request, mission_id):
        if Mission.objects.get(mission_id=mission_id).is_closed:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)

        data = request.POST.copy()
        data['mission'] = Mission.objects.get(pk=mission_id)
        form = AssignCarForm(data=data, mission_id=mission_id)
        obj = Car.objects.all()

        if form.is_valid():
            form.save()

            return HttpResponseRedirect(reverse('web:mission_car_view', args=[mission_id]))
        if settings.DEBUG:
            print(form.errors)
        context = {
            'data': obj,
            'username': request.user,
            'mission_id': mission_id,
            'mission_code': data['mission'].unique_code,
            'mission_ended': False,
            'server_mode': settings.USE_X_FORWARDED_HOST,
            'assign_form': form
        }
        return render(request, 'web/mission_car_view.html', context)


class ReleaseMissionCarView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, mission_id, pk):
        try:
            if Mission.objects.get(mission_id=mission_id).is_closed:
                return HttpResponse(status=status.HTTP_403_FORBIDDEN)
            obj = get_object_or_404(TeamCar, mission_id=mission_id, car_id=pk)
            obj.delete()
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return HttpResponse(status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return HttpResponseRedirect(reverse('web:mission_car_view', args=[mission_id]))
# #### Cars Mission - End ####
