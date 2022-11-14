from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import ModelForm

from .models import Mission, Photo, TeamPredefined, TeamCar, Team, UserTeam, Car, MapFeature


class CustomAuthenticationForm(AuthenticationForm):

    def confirm_login_allowed(self, user):
        # execute default behavior
        super(CustomAuthenticationForm, self).confirm_login_allowed(user)
        self.error_messages['wrong_group'] = "This account is inactive."
        if not user.groups.filter(name='ccc').exists():
            raise ValidationError(
                self.error_messages['wrong_group'],
                code='wrong_group',
            )


class AddMissionForm(ModelForm):
    class Meta:
        model = Mission
        fields = [
            'name',
        ]

    def __init__(self, *args, **kwargs):
        super(AddMissionForm, self).__init__(*args, **kwargs)

        self.fields['name'].required = True
        self.fields['name'].label = 'Mision name'
        self.fields['name'].widget.attrs.update({'class': 'form-control'})


class UploadImageForm(ModelForm):
    lat = forms.DecimalField(required=True)
    long = forms.DecimalField(required=True)
    mission_id = forms.ModelChoiceField(queryset=Mission.objects.all())

    class Meta:
        model = Photo
        fields = [
            'timestamp',
            'path',
            'info',
            'lat',
            'long',
            'mission_id',
        ]


class AddTeamPredefinedForm(ModelForm):
    team_member = forms.ModelMultipleChoiceField(queryset=User.objects.filter(is_active=True).order_by('last_name'), widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = TeamPredefined
        fields = [
            'team_name',
            'info',
            'team_member',
        ]

    def __init__(self, *args, **kwargs):
        super(AddTeamPredefinedForm, self).__init__(*args, **kwargs)

        self.fields['team_name'].required = True
        self.fields['team_name'].label = 'Predefined Team Name'
        self.fields['team_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['info'].label = 'Additional Information'
        self.fields['info'].widget.attrs.update({'class': 'form-control'})
        self.fields['team_member'].label = 'Users in Team'
        self.fields['team_member'].label_from_instance = lambda obj: "{last} {first}".format(
            last=obj.last_name,
            first=obj.first_name)


class MissionTeamForm(ModelForm):
    team_user = forms.ModelMultipleChoiceField(queryset=User.objects.filter(is_active=True), widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = Team
        fields = [
            'name',
            'info',
            'leader',
            'team_user',
            'mission',
        ]

    def __init__(self, mission_id, is_add, team, *args, **kwargs):
        super(MissionTeamForm, self).__init__(*args, **kwargs)

        self.fields['name'].required = True
        self.fields['name'].label = 'Team Name'
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['info'].label = 'Additional Information'
        self.fields['info'].widget.attrs.update({'class': 'form-control'})
        if is_add:
            teams = UserTeam.objects.filter(team__mission__is_closed=False)
            self.fields['team_user'].queryset = User.objects.filter(~Q(team_member__in=teams), is_active=True).order_by('last_name')
        else:
            teams = UserTeam.objects.filter(team__mission__is_closed=False).exclude(team=team)
            self.fields['team_user'].queryset = User.objects.filter(~Q(team_member__in=teams), is_active=True).order_by('last_name')
        self.fields['team_user'].label = 'Users in Team'
        self.fields['team_user'].label_from_instance = lambda obj: "{last} {first}".format(last=obj.last_name, first=obj.first_name)
        self.fields['leader'].label = 'Team Leader'
        self.fields['leader'].widget.attrs.update({'class': 'form-control'})
        self.fields['leader'].queryset = User.objects.filter(is_active=True)
        self.fields['leader'].label_from_instance = lambda obj: "%s" % obj
        self.fields['mission'].widget = forms.HiddenInput()


class CarForm(ModelForm):

    class Meta:
        model = Car
        fields = [
            'license_plates',
            'registration_number',
        ]

    def __init__(self, *args, **kwargs):
        super(CarForm, self).__init__(*args, **kwargs)

        self.fields['license_plates'].required = True
        self.fields['license_plates'].label = 'License Plates'
        self.fields['license_plates'].widget.attrs.update({'class': 'form-control'})
        self.fields['registration_number'].label = 'Registration Number'
        self.fields['registration_number'].widget.attrs.update({'class': 'form-control'})


class AssignCarForm(ModelForm):
    team = forms.ModelChoiceField(widget=forms.Select, queryset=None)

    class Meta:
        model = TeamCar
        fields = ['car', 'team', 'mission']

    def __init__(self, mission_id, *args, **kwargs):
        super(AssignCarForm, self).__init__(*args, **kwargs)

        self.fields['mission'].widget = forms.HiddenInput()
        self.fields['car'].label = 'License Plates'
        self.fields['car'].widget.attrs.update({'class': 'form-control'})
        self.fields['car'].queryset = Car.objects.all()
        self.fields['car'].label_from_instance = lambda obj: "%s" % obj.license_plates
        self.fields['car'].required = False
        self.fields['team'].label = "Assign to Team"
        self.fields['team'].queryset = Team.objects.filter(mission_id=mission_id)
        self.fields['team'].widget.attrs.update({'class': 'form-control'})
        self.fields['team'].label_from_instance = lambda obj: "%s" % obj.name


class FeatureForm(ModelForm):
    mission_id = forms.IntegerField()

    class Meta:
        model = MapFeature
        fields = [
            'name',
            'info',
            'geom',
            'mission_id',
        ]

    def __init__(self, *args, **kwargs):
        super(FeatureForm, self).__init__(*args, **kwargs)
