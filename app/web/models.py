import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.core.cache import cache
from django.core.validators import RegexValidator
from django.utils import timezone

managed_val = True


class Car(models.Model):
    license_plates = models.CharField(
        max_length=6, unique=True,
        validators=[RegexValidator(regex=r'^[A-Z]{3}\d{3}$', message='Invalid format')]
    )
    registration_number = models.CharField(max_length=50, blank=True, null=True)
    team_car = models.ManyToManyField(
        'Team',
        through='TeamCar',
        through_fields=('car', 'team'),
    )

    @property
    def available_car(self):
        teams = self.assigned_team.all()
        for team in teams:
            if not team.mission.is_closed:
                return False
        return True

    class Meta:
        managed = managed_val
        db_table = 'car'


class ChatMessage(models.Model):
    date_created = models.DateTimeField()
    room = models.ForeignKey('ChatPrivateRoom', models.DO_NOTHING)
    sender = models.ForeignKey(User, models.DO_NOTHING)
    content = models.ForeignKey('ChatMessageContent', models.DO_NOTHING)
    mission = models.ForeignKey('Mission', models.DO_NOTHING)

    class Meta:
        managed = managed_val
        db_table = 'chat_message'


class ChatMessageContent(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    type = models.CharField(max_length=50)

    class Meta:
        managed = managed_val
        db_table = 'chat_message_content'


class ChatMessageRecipients(models.Model):
    message = models.ForeignKey(ChatMessage, models.DO_NOTHING)
    user = models.ForeignKey(User, models.DO_NOTHING)

    class Meta:
        managed = managed_val
        db_table = 'chat_message_recipients'


class ChatPrivateRoom(models.Model):
    type_ch = [
        ('user', 'user'),
        ('team', 'team')
    ]
    hash_code = models.CharField(max_length=32)
    type = models.CharField(max_length=10, choices=type_ch)
    team = models.ForeignKey('Team', models.DO_NOTHING, null=True, blank=True)
    mission = models.ForeignKey('Mission', models.DO_NOTHING)

    class Meta:
        managed = managed_val
        db_table = 'chat_private_room'


class ChatRoomMembers(models.Model):
    room = models.ForeignKey(ChatPrivateRoom, models.DO_NOTHING, related_name='room_member')
    user = models.ForeignKey(User, models.DO_NOTHING)
    unread = models.BooleanField(default=False)

    class Meta:
        managed = managed_val
        db_table = 'chat_room_members'


class ChatText(models.Model):
    id = models.OneToOneField(ChatMessageContent, models.DO_NOTHING, db_column='id', primary_key=True)
    text = models.CharField(max_length=50)
    number_id = models.IntegerField()

    class Meta:
        managed = managed_val
        db_table = 'chat_text'


class ChatTicket(models.Model):
    user = models.ForeignKey(User, models.DO_NOTHING)
    ticket = models.UUIDField(primary_key=True)
    ip_address = models.CharField(max_length=15)

    class Meta:
        managed = managed_val
        db_table = 'chat_ticket'


class ChatUserProfile(models.Model):
    last_visit = models.DateTimeField()
    user = models.ForeignKey(User, models.DO_NOTHING)

    class Meta:
        managed = managed_val
        db_table = 'chat_user_profile'


class MapFeature(models.Model):
    geom = models.GeometryField(srid=4326)
    timestamp = models.DateTimeField(default=timezone.localtime)
    info = models.CharField(max_length=50, blank=True, null=True)
    mission = models.ForeignKey('Mission', models.DO_NOTHING)
    name = models.CharField(max_length=50)
    user = models.ForeignKey(User, models.DO_NOTHING, related_name='map_feature_user')
    valid_to = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = managed_val
        db_table = 'map_feature'


class Mission(models.Model):
    mission_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    date = models.DateTimeField()
    create_user = models.ForeignKey(User, models.DO_NOTHING, related_name='create_user')
    unique_code = models.CharField(max_length=50)
    is_closed = models.BooleanField()
    is_hidden = models.BooleanField(blank=True, null=True)
    assigned_user = models.ManyToManyField(
        User,
        through='UserMission',
        through_fields=('mission', 'user')
    )

    class Meta:
        managed = managed_val
        db_table = 'mission'


class Photo(models.Model):
    id = models.OneToOneField(ChatMessageContent, models.DO_NOTHING, db_column='id', primary_key=True)
    geom = models.GeometryField(srid=4326)
    timestamp = models.DateTimeField()
    path = models.ImageField()
    path_detect = models.ImageField(blank=True, null=True)
    mission = models.ForeignKey(Mission, models.DO_NOTHING)
    info = models.CharField(max_length=50, blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING)
    number_id = models.IntegerField()

    def __str__(self):
        return 'Photo message:<br> <img src={url} alt="chat image" width="175"><br><button id="photo-map-view" type="button" class="btn btn-orange" onclick="parent.addChatPhotoFeature(\'{url}\', \'{path_detect}\', \'{lat}\', \'{lng}\', \'{timestamp}\', \'{user}\');">View on map</button>'.format(url=self.path.url, path_detect=self.path_detect.url if self.path_detect else None, lat=self.geom[0], lng=self.geom[1], user=self.user.username, timestamp=self.timestamp)

    class Meta:
        managed = managed_val
        db_table = 'photo'


class Poi(models.Model):
    id = models.OneToOneField(ChatMessageContent, models.DO_NOTHING, db_column='id', primary_key=True)
    geom = models.GeometryField(srid=4326)
    timestamp = models.DateTimeField()
    info = models.CharField(max_length=50, blank=True, null=True)
    mission = models.ForeignKey(Mission, models.DO_NOTHING)
    name = models.CharField(max_length=50)
    user = models.ForeignKey(User, models.DO_NOTHING)
    number_id = models.IntegerField()

    class Meta:
        managed = managed_val
        db_table = 'poi'

    def __str__(self):
        return 'Point message:<br>{name}, {info}<br><button type="button" class="btn btn-orange" onclick="parent.addChatPointFeature(\'{name}\', \'{info}\', \'{lat}\', \'{lng}\', \'{timestamp}\', \'{user}\');">View on map</button>'.format(name=self.name, info=self.info, timestamp=self.timestamp, lat=self.geom[0], lng=self.geom[1], user=self.user.username)


class Route(models.Model):
    id = models.OneToOneField(ChatMessageContent, models.DO_NOTHING, db_column='id', primary_key=True)
    geom = models.GeometryField(srid=4326)
    timestamp = models.DateTimeField()
    info = models.CharField(max_length=50, blank=True, null=True)
    mission = models.ForeignKey(Mission, models.DO_NOTHING)
    name = models.CharField(max_length=50)
    user = models.ForeignKey(User, models.DO_NOTHING)
    number_id = models.IntegerField()

    class Meta:
        managed = managed_val
        db_table = 'route'

    def __str__(self):
        list_geom = []
        for coord in self.geom:
            list_geom.append([coord[1], coord[0]])
        return 'Route message:<br>{name}, {info}<br><button type="button" class="btn btn-orange" onclick="parent.addChatRouteFeature(\'{name}\', \'{info}\', {geom}, \'{timestamp}\', \'{user}\');">View on map</button>'.format(name=self.name, info=self.info, timestamp=self.timestamp, geom=list_geom, user=self.user.username)


class Team(models.Model):
    team_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    leader = models.ForeignKey(User, models.DO_NOTHING, related_name='leader', blank=True, null=True)
    info = models.CharField(max_length=50, blank=True, null=True)
    mission = models.ForeignKey(Mission, models.DO_NOTHING)
    team_user = models.ManyToManyField(
        User,
        through='UserTeam',
        through_fields=('team', 'user')
    )

    @property
    def number_of_members(self):
        return self.team_user.count()

    class Meta:
        managed = managed_val
        db_table = 'team'


class TeamCar(models.Model):
    team = models.ForeignKey(Team, models.DO_NOTHING)
    car = models.ForeignKey(Car, models.DO_NOTHING, related_name='assigned_team')
    mission = models.ForeignKey(Mission, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = managed_val
        db_table = 'team_car'
        unique_together = (('car', 'mission'), )


class TeamPredefined(models.Model):
    id = models.AutoField(primary_key=True)
    team_name = models.CharField(max_length=50)
    info = models.CharField(max_length=50, blank=True, null=True)
    team_member = models.ManyToManyField(
        User,
        through='TeamPredefinedMembers',
        through_fields=('team', 'user')
    )

    @property
    def available_team(self):
        members = self.team_member.all()
        for member in members:
            teams = member.team_member.all()
            for team in teams:
                if not team.team.mission.is_closed:
                    return False
        return True

    class Meta:
        managed = managed_val
        db_table = 'team_predefined'


class TeamPredefinedMembers(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, models.DO_NOTHING)
    team = models.ForeignKey(TeamPredefined, models.DO_NOTHING, related_name="predefined_team_members", )

    class Meta:
        managed = managed_val
        db_table = 'team_predefined_members'


class UserLatestLocation(models.Model):
    user = models.ForeignKey(User, models.DO_NOTHING)
    geom = models.GeometryField(srid=4326)
    timestamp = models.DateTimeField()

    class Meta:
        managed = managed_val
        db_table = 'user_latest_location'


class UserLocation(models.Model):
    user_team_mission = models.ForeignKey('UserTeam', models.CASCADE)
    geom = models.GeometryField(srid=4326)
    timestamp = models.DateTimeField()

    class Meta:
        managed = managed_val
        db_table = 'user_location'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    class Meta:
        managed = managed_val
        db_table = 'user_profile'

    def last_seen(self):
        return cache.get('seen_%s' % self.user.username)

    def online(self):
        if self.last_seen():
            now = datetime.datetime.now()
            if now > self.last_seen() + datetime.timedelta(
                         seconds=settings.USER_ONLINE_TIMEOUT):
                return False
            else:
                return True
        else:
            return False


class UserMission(models.Model):
    user = models.ForeignKey(User, models.DO_NOTHING)
    mission = models.ForeignKey(Mission, models.DO_NOTHING)

    class Meta:
        managed = managed_val
        db_table = 'user_mission'


class UserTeam(models.Model):
    user = models.ForeignKey(User, models.DO_NOTHING, related_name='team_member')
    team = models.ForeignKey(Team, models.DO_NOTHING)

    class Meta:
        managed = managed_val
        db_table = 'user_team'


class Video(models.Model):
    id = models.OneToOneField(ChatMessageContent, models.DO_NOTHING, db_column='id', primary_key=True)
    geom = models.GeometryField(srid=4326)
    timestamp = models.DateTimeField()
    path = models.CharField(max_length=50)
    mission = models.ForeignKey(Mission, models.DO_NOTHING)
    info = models.CharField(max_length=50, blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING)

    class Meta:
        managed = managed_val
        db_table = 'video'
