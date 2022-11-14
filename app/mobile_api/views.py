import base64
import datetime
import hashlib
import traceback
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.gis.geos import Point
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from rest_framework.views import APIView

from .api_serializers import MissionValidationSerializer, UploadPhotoSerializer, ImageMsgSerializer, \
    ChatHistorySerializer
from web.models import Mission, ChatTicket, Photo, ChatMessage, ChatPrivateRoom, Team

from .detection.detector import detect


class MobileLogin(ObtainAuthToken):

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        existing_obj = ChatTicket.objects.filter(
            user=user,
            ip_address=ip
        ).first()
        if existing_obj is None:
            obj = ChatTicket.objects.create(
                user=user,
                ticket=uuid.uuid4(),
                ip_address=ip
            )

            return Response(status=status.HTTP_201_CREATED, data={"ticket": obj.ticket, 'token': token.key, })
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)


class MobileLogout(ObtainAuthToken):
    """
    Logout a user
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        token = request.auth

        if token:
            token.delete()
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            existing_obj = ChatTicket.objects.filter(
                user=request.user,
                ip_address=ip
            ).first()
            if existing_obj:
                existing_obj.delete()
        return Response(status=204)


class MissionValidationView(APIView):
    """
    Validate mission code
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MissionValidationSerializer

    def post(self, request):
        serializer = MissionValidationSerializer(
            data=request.data
        )

        # Return a 400 response if the data was invalid.
        serializer.is_valid(raise_exception=True)
        try:
            obj = Mission.objects.get(
                unique_code=serializer.validated_data["unique_code"],
                is_closed=False,
            )
            return Response(status=200, data={"mission_id": obj.mission_id})
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return Response(status=404)


class UploadPhotoView(APIView):
    """
    Upload photo
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def put(self, request):
        try:
            data = request.data.copy()
            fixed_date = data['timestamp'].replace(' (Eastern European Standard Time)', '')
            fixed_date = fixed_date.replace(' (Eastern European Summer Time)', '')
            data['timestamp'] = datetime.datetime.strptime(fixed_date, '%a %b %d %Y %H:%M:%S %Z%z')
            data['geom'] = Point(float(data['lat']), float(data['long']))
            data['user_id'] = request.user.pk
            serializer = UploadPhotoSerializer(
                data=data
            )
        except Exception as e:
            if settings.DEBUG:
                print(e)
            return Response(status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # Return a 400 response if the data was invalid.
        if not serializer.is_valid():
            if settings.DEBUG:
                print(serializer.errors)
            return Response(status=400)

        try:
            receiver = None
            str_names = None
            if serializer.validated_data['receiver'] == 'ccc':
                receiver = Mission.objects.get(mission_id=serializer.validated_data['mission_id']).create_user.username
                # send file in chat
                sorted_names = sorted([request.user.username, receiver])
                str_names = 'chat_{user1}_{user2}_{mission_id}'.format(user1=sorted_names[0], user2=sorted_names[1],
                                                                       mission_id=serializer.validated_data['mission_id'])
            elif serializer.validated_data['receiver'] == 'team':
                receiver = str(Team.objects.get(mission_id=serializer.validated_data['mission_id'], team_user=request.user).pk)
                # send file in chat
                str_names = 'chat_team_{team}_{mission_id}'.format(team=receiver, mission_id=serializer.validated_data['mission_id'])
                print('team send image', str_names)

            if receiver is None or str_names is None:
                return Response(status=400)
            obj = serializer.save()
            obj.path_detect = detect(obj.path.path)
            obj.save()

            room_name = hashlib.md5(str_names.encode()).hexdigest()
            msg_data = ImageMsgSerializer(data={
                    'type': 'image_message',
                    'msg_type': 'image',
                    'user': request.user.username,
                    'geom': [obj.geom[0], obj.geom[1]],
                    'url': settings.SERVER_URL + obj.path.url,
                    'detect_url': settings.SERVER_URL + obj.path_detect.url,
                    'mission_id': obj.mission.pk,
                    'time': datetime.datetime.now(),
                    'time_taken': obj.timestamp,
                    'obj_id': obj.pk,
                })
            msg_data.is_valid(raise_exception=True)
            print(room_name, msg_data.data)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(room_name, msg_data.data)

            return Response(status=200, data={"path": settings.SERVER_URL + obj.path.url, "id": obj.pk})
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return Response(status=404)


class GetPhotoView(APIView):
    """
    Retrieve photo
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, path):
        obj = Photo.objects.get(path=path)
        with open(obj.path.path, "rb") as image_file:
            encoded_string = 'data:image/png;base64,' + base64.b64encode(image_file.read()).decode('ascii')

        return Response(encoded_string,)


class GetChatHistory(APIView):
    """
    Retrieve history messages of a chat
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, chat_type, mission_id):
        current_room = None
        if chat_type == 'ccc':
            ccc_user = Mission.objects.get(mission_id=mission_id).create_user
            rooms = ChatPrivateRoom.objects.filter(type='user', mission_id=mission_id, room_member__user=request.user)
            for room in rooms:
                if room.room_member.filter(user=ccc_user):
                    current_room = room
                    break
        elif chat_type == 'team':
            team_obj = Team.objects.get(mission_id=mission_id, team_user=request.user)
            current_room = ChatPrivateRoom.objects.get(type='team', mission_id=mission_id, team=team_obj)

        if not current_room:
            return Response(status=status.HTTP_404_NOT_FOUND)

        msg_list = []
        msgs = ChatMessage.objects.filter(room=current_room, mission_id=mission_id).order_by('-date_created')[:40:-1]
        for msg in msgs:
            is_sender = True if msg.sender.username == request.user.username else False
            if msg.content.type == 'text':
                msg_list.append({'type': msg.content.type, 'msg': msg.content.chattext.text, 'is_sender': is_sender,
                                 'time': timezone.localtime(msg.date_created), 'sender': msg.sender.username})
            elif msg.content.type == 'poi':
                msg_list.append(
                    {'type': msg.content.type, 'name': msg.content.poi.name, 'lat': msg.content.poi.geom[0],
                     'long': msg.content.poi.geom[1], 'is_sender': is_sender, 'time': timezone.localtime(msg.date_created),
                     'sender': msg.sender.username})
            elif msg.content.type == 'route':
                list_geom = []
                for coord in msg.content.route.geom:
                    list_geom.append([coord[0], coord[1]])
                msg_list.append({'type': msg.content.type, 'name': msg.content.route.name, 'geom': list_geom,
                                 'is_sender': is_sender, 'time': timezone.localtime(msg.date_created),
                                 'sender': msg.sender.username})
            elif msg.content.type == 'photo':
                path = settings.SERVER_URL + msg.content.photo.path.url
                print(msg.content.photo.timestamp)
                tm_photo = timezone.localtime(msg.content.photo.timestamp).strftime('%a %b %d %Y %H:%M:%S')
                tm_sent = timezone.localtime(msg.date_created).strftime('%a %b %d %Y %H:%M:%S')
                msg_list.append({'type': msg.content.type, 'is_sender': is_sender,
                                 'time': tm_sent, 'time_taken': tm_photo, 'sender': msg.sender.username,
                                 'lat': msg.content.photo.geom[0], 'long': msg.content.photo.geom[1],
                                 'path': path, 'id': msg.content.photo.pk})
        data = ChatHistorySerializer(msg_list, many=True)
        return Response(data.data)
