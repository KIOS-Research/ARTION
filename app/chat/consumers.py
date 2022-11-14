import hashlib
import json
import traceback
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.gis.geos import Point, LineString
from django.db import transaction
from django.utils import timezone

from web.models import ChatMessageContent, ChatText, ChatPrivateRoom, ChatRoomMembers, ChatMessage, Poi, ChatTicket, Route, Mission, Team


class AsyncChatConsumer(AsyncWebsocketConsumer):
    """
    One to one chat consumer
    """
    # Called on connection.
    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            # check for ticket in url
            if parse_qs(self.scope["query_string"].decode("utf8")):
                self.user = await self.get_user(parse_qs(self.scope["query_string"].decode("utf8"))["ticket"][0], self.scope['client'][0])

        if not self.user.is_authenticated:
            await self.close()
            return

        self.type = self.scope['url_route']['kwargs']['room_type']
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.mission_id = self.scope['url_route']['kwargs']['mission_id']
        self.room_users = []
        if self.type == 'user':
            if self.room_name == 'ccc':
                self.room_name = await self.get_ccc_user(self.mission_id)
            if self.room_name is None:
                await self.close()
                return
            # close if self-chat
            if self.user.username == self.room_name:
                await self.close()
                return
            sorted_names = sorted([self.user.username, self.room_name])
            str_names = 'chat_{user1}_{user2}_{mission_id}'.format(user1=sorted_names[0], user2=sorted_names[1], mission_id=self.mission_id)
            self.room_group_name = hashlib.md5(str_names.encode()).hexdigest()
            await self.create_private_room(self.room_group_name, self.user.username, self.room_name, self.mission_id)
        elif self.type == 'team':
            self.room_name = await self.get_team()
            if self.room_name is None:
                # print('Team not found')
                await self.close()
                return

            str_names = 'chat_team_{team}_{mission_id}'.format(team=self.room_name, mission_id=self.mission_id)
            self.room_group_name = hashlib.md5(str_names.encode()).hexdigest()
            # print('team-channel name', str_names, self.room_group_name)
            await self.create_team_room(self.room_group_name, self.room_name, self.mission_id)
        else:
            print('wrong chat type')
            await self.close()
            return
        await self.get_chat_members()

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    # Called when the socket closes
    async def disconnect(self, close_code):
        # print(close_code)
        if close_code != 1006:
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Receive message from WebSocket
    # Called with either text_data or bytes_data for each frame
    async def receive(self, text_data=None, bytes_data=None):
        mission_id = None
        msg_type = None
        text_data_json = None
        data = None
        print('msg', text_data)
        if text_data is not None:
            text_data_json = json.loads(text_data)
            msg_type = text_data_json['msg_type']
            mission_id = text_data_json['mission_id']

        if mission_id and msg_type:
            if msg_type == 'text':
                await self.save_text_msg(text_data_json['message'], mission_id)

                data = {
                    'type': 'chat_message',
                    'message': text_data_json['message'],
                    'mission_id': mission_id,
                    'msg_type': msg_type,
                    'lat': None,
                    'long': None,
                    'info': None,
                    'name': None,
                    'user': self.user.username,
                    'time': text_data_json['time'],
                }

            elif msg_type == 'poi':
                info = text_data_json['info'] if 'info' in text_data_json else None
                await self.save_poi_msg(mission_id, text_data_json['lat'], text_data_json['long'],
                                        info, text_data_json['name'],)
                data={
                    'type': 'chat_message',
                    'message': text_data_json['message'],
                    'mission_id': mission_id,
                    'msg_type': msg_type,
                    'lat': text_data_json['lat'],
                    'long': text_data_json['long'],
                    'info': info,
                    'name': text_data_json['name'],
                    'user': self.user.username,
                    'time': text_data_json['time'],
                }

            elif msg_type == 'route':
                info = text_data_json['info'] if 'info' in text_data_json else None
                await self.save_route_msg(mission_id, text_data_json['geom'],
                                          info, text_data_json['name'],)
                list_geom = []
                for obj in text_data_json['geom']:
                    list_geom.append([obj['lat'], obj['lng']])

                data = {
                    'type': 'route_message',
                    'mission_id': mission_id,
                    'msg_type': msg_type,
                    'geom': list_geom,
                    'info': info,
                    'name': text_data_json['name'],
                    'user': self.user.username,
                    'time': text_data_json['time'],
                }

            if data is not None:
                await self.channel_layer.group_send(
                    self.room_group_name, data)

                alert={
                    'type': 'alert_message',
                    'user': data['user'],
                    'time': data['time'],
                    'msg_type': data['msg_type'],
                    'chat': self.room_name
                }
                await self.set_unread()
                for user in self.room_users:
                    name = 'alert_{user}_{mission_id}'.format(user=user, mission_id=self.mission_id)
                    await self.channel_layer.group_send(
                        name, alert)

    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'mission_id': event['mission_id'],
            'msg_type': event['msg_type'],
            'lat': event['lat'],
            'long': event['long'],
            'info': event['info'],
            'name': event['name'],
            'user': event['user'],
            'time': event['time'],
        }))
        await self.set_read()

    # receive route from room group
    async def route_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'mission_id': event['mission_id'],
            'msg_type': event['msg_type'],
            'geom': event['geom'],
            'info': event['info'],
            'name': event['name'],
            'user': event['user'],
            'time': event['time'],
        }))
        await self.set_read()

    # receive img from room group
    async def image_message(self, event):
        await self.save_img_msg(event['mission_id'], event['obj_id'], event['user'])
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'mission_id': event['mission_id'],
            'msg_type': event['msg_type'],
            'geom': event['geom'],
            'user': event['user'],
            'url': event['url'],
            'detect_url': event['detect_url'],
            'time': event['time'],
            'time_taken': event['time_taken'],
        }))
        await self.set_read()

    @database_sync_to_async
    def get_ccc_user(self, mission_id):
        try:
            return Mission.objects.get(pk=mission_id).create_user.username
        except Exception:
            return None

    @database_sync_to_async
    def get_user(self, ticket, ip):
        try:
            print('ticket', ticket)
            print('ip', ip)
            return ChatTicket.objects.get(ticket=ticket, ip_address=ip).user
        except Exception:
            return AnonymousUser()

    @database_sync_to_async
    def get_team(self,):
        try:
            print(self.user.create_user.all().filter(mission_id=self.mission_id).first())
            if self.user.create_user.all().filter(mission_id=self.mission_id).first() is None:
                return str(Team.objects.get(team_user=self.user, mission__pk=self.mission_id).pk)
            else:
                return self.room_name
        except Exception:
            traceback.print_exc()
            return None

    @database_sync_to_async
    def get_chat_members(self):
        try:
            self.chat_member = ChatRoomMembers.objects.get(room=self.chat_room, user=self.user)
        except Exception:
            traceback.print_exc()
            self.chat_member = None

        try:
            chat_members = ChatRoomMembers.objects.filter(room=self.chat_room).exclude(user=self.user)
            for member in chat_members:
                self.room_users.append(member.user.username)
        except Exception:
            traceback.print_exc()
            self.room_users = []

    @database_sync_to_async
    def create_private_room(self, room_name, user1, user2, mission_id):
        try:
            with transaction.atomic():
                obj, created = ChatPrivateRoom.objects.get_or_create(
                    hash_code=room_name,
                    mission_id=mission_id,
                    type='user'
                )
                self.chat_room=obj
                if created:
                    ChatRoomMembers.objects.create(
                        room=obj,
                        user=User.objects.get(username=user1)
                    )
                    ChatRoomMembers.objects.create(
                        room=obj,
                        user=User.objects.get(username=user2)
                    )
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return False
        return True

    @database_sync_to_async
    def create_team_room(self, room_name, _id, mission_id):
        try:
            with transaction.atomic():
                obj, created = ChatPrivateRoom.objects.get_or_create(
                    hash_code=room_name,
                    type='team',
                    team_id=_id,
                    mission_id=mission_id,
                )
                self.chat_room = obj
                if created:
                    print(_id, mission_id)
                    chat = Team.objects.get(pk=_id, mission_id=mission_id)
                    chat_members = chat.team_user.all()

                    for member in chat_members:
                        ChatRoomMembers.objects.create(
                            room=obj,
                            user=member
                        )
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return False
        return True

    @database_sync_to_async
    def set_unread(self):
        try:
            ChatRoomMembers.objects.filter(room=self.chat_room).exclude(user=self.user).update(unread=True)
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return False
        return True

    @database_sync_to_async
    def set_read(self):
        try:
            if self.chat_member:
                self.chat_member.unread = False
                self.chat_member.save()
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return False
        return True

    @database_sync_to_async
    def save_text_msg(self, msg, mission_id):
        try:
            with transaction.atomic():
                if ChatText.objects.all().count() < 1:
                    id_number = 1
                    id_txt = 'text.1'
                else:
                    id_number = ChatText.objects.latest('number_id').number_id + 1
                    id_txt = 'text.' + str(id_number)
                obj = ChatMessageContent.objects.create(id=id_txt, type='text')
                ChatText.objects.create(id=obj, text=msg, number_id=id_number)
                ChatMessage.objects.create(
                    date_created=timezone.now(),
                    room=ChatPrivateRoom.objects.get(hash_code=self.room_group_name),
                    sender=self.user,
                    content=obj,
                    mission_id=mission_id
                )
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return False
        return True

    @database_sync_to_async
    def save_poi_msg(self, mission_id, lat, long, info, name):
        try:
            with transaction.atomic():
                if Poi.objects.all().count() < 1:
                    id_number = 1
                    id_txt = 'poi.1'
                else:
                    id_number = Poi.objects.latest('number_id').number_id + 1
                    id_txt = 'poi.' + str(id_number)
                obj = ChatMessageContent.objects.create(id=id_txt, type='poi')
                Poi.objects.create(
                    id=obj,
                    geom=Point(lat, long),
                    timestamp=timezone.localtime(timezone.now()),
                    mission_id=mission_id,
                    info=info,
                    name=name,
                    user=self.user,
                    number_id=id_number,
                )
                ChatMessage.objects.create(
                    date_created=timezone.now(),
                    room=ChatPrivateRoom.objects.get(hash_code=self.room_group_name),
                    sender=self.user,
                    content=obj,
                    mission_id=mission_id
                )
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return False
        return True

    @database_sync_to_async
    def save_route_msg(self, mission_id, geom, info, name):
        try:
            with transaction.atomic():
                if Route.objects.all().count() < 1:
                    id_number = 1
                    id_txt = 'route.1'
                else:
                    id_number = Route.objects.latest('number_id').number_id + 1
                    id_txt = 'route.' + str(id_number)

                points = []
                for obj in geom:
                    points.append(Point(obj['lat'], obj['lng']))
                linestring = LineString(points)
                obj = ChatMessageContent.objects.create(id=id_txt, type='route')
                Route.objects.create(
                    id=obj,
                    geom=linestring,
                    timestamp=timezone.now(),
                    mission_id=mission_id,
                    info=info,
                    name=name,
                    user=self.user,
                    number_id=id_number,
                )
                ChatMessage.objects.create(
                    date_created=timezone.now(),
                    room=ChatPrivateRoom.objects.get(hash_code=self.room_group_name),
                    sender=self.user,
                    content=obj,
                    mission_id=mission_id
                )
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return False
        return True

    @database_sync_to_async
    def save_img_msg(self, mission_id, obj_id, username):
        try:
            with transaction.atomic():
                ChatMessage.objects.create(
                    date_created=timezone.now(),
                    room=ChatPrivateRoom.objects.get(hash_code=self.room_group_name),
                    sender=User.objects.get(username=username),
                    content_id=obj_id,
                    mission_id=mission_id
                )
        except Exception as e:
            print(e)
            if settings.DEBUG:
                traceback.print_exc()
            return False
        return True


class AsyncAlertConsumer(AsyncWebsocketConsumer):
    """
    One to one chat consumer
    """
    # Called on connection.
    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            # check for ticket in url
            if parse_qs(self.scope["query_string"].decode("utf8")):
                self.user = await self.get_user(parse_qs(self.scope["query_string"].decode("utf8"))["ticket"][0], self.scope['client'][0])

        if not self.user.is_authenticated:
            await self.close()
            return

        self.room_name =str(self.user.username)
        self.mission_id = self.scope['url_route']['kwargs']['mission_id']

        self.room_group_name= 'alert_{user}_{mission_id}'.format(user=self.room_name, mission_id=self.mission_id)
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    # Called when the socket closes
    async def disconnect(self, close_code):
        print(close_code)
        if close_code != 1006:
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Receive message from room group
    async def alert_message(self, event):
        # Send message to WebSocket
        print('alert event', event)
        await self.send(text_data=json.dumps({
            'msg_type': event['msg_type'],
            'user': event['user'],
            'time': event['time'],
            'chat': event['chat'],
        }))

    @database_sync_to_async
    def get_unread_num(self):
        try:
            unread=ChatRoomMembers.objects.filter(user=self.user, unread=True, room__mission_id=self.mission_id).count()
            return unread
        except Exception:
            return None

    @database_sync_to_async
    def get_user(self, ticket, ip):
        try:
            print('ticket', ticket)
            print('ip', ip)
            return ChatTicket.objects.get(ticket=ticket, ip_address=ip).user
        except Exception:
            return AnonymousUser()
