import json
import traceback
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.gis.geos import Point

from web.models import ChatTicket, UserTeam, Mission, UserLocation


class AsyncLocationConsumer(AsyncWebsocketConsumer):
    """
    Location consumer
    """
    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            # check for ticket in url
            if parse_qs(self.scope["query_string"].decode("utf8")):
                self.user = await self.get_user(parse_qs(self.scope["query_string"].decode("utf8"))["ticket"][0],
                                                self.scope['client'][0])

        if not self.user.is_authenticated:
            print('authentication failed')
            await self.close()
            return

        try:
            mission_id = self.scope['url_route']['kwargs']['mission_id']
            mission_obj = await self.find_mission(mission_id)
            # if mission is not active reject the connection
            if mission_obj.is_closed:
                print('mission closed')
                await self.close()
                return
            # get team of the user based on the mission
            self.user_team = await self.find_user_team_mission(mission_obj)
            self.global_team = "global_" + str(mission_id)

        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            await self.close()
            return

        await self.channel_layer.group_add(
            self.user_team,
            self.channel_name
        )

        await self.accept()

    # Called when the socket closes
    async def disconnect(self, close_code):
        # print(close_code)
        if close_code != 1006:
            # Leave room group
            await self.channel_layer.group_discard(
                self.user_team,
                self.channel_name
            )

    # Called with either text_data or bytes_data for each frame
    async def receive(self, text_data=None, bytes_data=None):
        if text_data is not None:
            text_data_json = json.loads(text_data)
            lat = text_data_json["lat"]
            long = text_data_json["long"]
            timestamp = text_data_json["timestamp"]

            if lat and long and timestamp:
                await self.save_location(lat, long, timestamp)
                # Send message to group
                await self.channel_layer.group_send(
                    self.user_team,
                    {
                        'type': 'location',
                        'user': self.user.username,
                        'lat': lat,
                        'long': long,
                        'timestamp': timestamp
                    }
                )

                # send location to global channel
                await self.channel_layer.group_send(
                    self.global_team,
                    {
                        'type': 'location_global',
                        'user': self.user.username,
                        'lat': lat,
                        'long': long,
                        'timestamp': timestamp,
                        'team': self.user_team_obj.team.name
                    }
                )

    # Receive message from room group
    async def location(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'lat': event['lat'],
            'long': event['long'],
            'user': event['user'],
            'timestamp': event['timestamp'],
        }))

    @database_sync_to_async
    def get_user(self, ticket, ip):
        try:
            print('ticket', ticket)
            print('ip', ip)
            return ChatTicket.objects.get(ticket=ticket, ip_address=ip).user
        except Exception:
            return AnonymousUser()

    @database_sync_to_async
    def find_mission(self, mission_id):
        return Mission.objects.get(mission_id=mission_id)

    @database_sync_to_async
    def find_user_team_mission(self, mission_obj):
        self.user_team_obj = UserTeam.objects.get(team__mission=mission_obj, user=self.user)
        return 'team_' + str(self.user_team_obj.team.pk)

    @database_sync_to_async
    def save_location(self, lat, long, timestamp):
        try:
            UserLocation.objects.create(
                user_team_mission=self.user_team_obj,
                timestamp=timestamp,
                geom=Point(lat, long)
            )
        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            return False
        return True

