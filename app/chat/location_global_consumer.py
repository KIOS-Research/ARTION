import json
import traceback

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from web.models import ChatTicket, UserTeam, Mission, UserLocation


class AsyncLocationConsumer(AsyncWebsocketConsumer):
    """
    Location consumer
    """
    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            print('authentication failed')
            await self.close()
            return

        try:
            mission_id = self.scope['url_route']['kwargs']['mission_id']
            mission_obj = await self.find_mission(mission_id)
            # if mission is not active reject the connection
            if mission_obj.is_closed:
                await self.close()
                return

            self.global_team = "global_"+str(mission_id)

        except Exception:
            if settings.DEBUG:
                traceback.print_exc()
            await self.close()
            return

        await self.channel_layer.group_add(
            self.global_team,
            self.channel_name
        )

        await self.accept()

    # Called when the socket closes
    async def disconnect(self, close_code):
        print(close_code)
        if close_code != 1006:
            # Leave room group
            await self.channel_layer.group_discard(
                self.global_team,
                self.channel_name
            )

    # Called with either text_data or bytes_data for each frame
    async def receive(self, text_data=None, bytes_data=None):
        if text_data is not None:
            text_data_json = json.loads(text_data)
            lat = text_data_json["lat"]
            long = text_data_json["long"]
            timestamp = text_data_json["timestamp"]
            user = text_data_json['user']
            team = text_data_json['team']

            if lat and long and timestamp and user and team:
                # Send message to group
                await self.channel_layer.group_send(
                    self.global_team,
                    {
                        'type': 'location_global',
                        'user': user,
                        'lat': lat,
                        'long': long,
                        'timestamp': timestamp,
                        'team': team
                    }
                )

    # Receive message from room group
    async def location_global(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'lat': event['lat'],
            'long': event['long'],
            'user': event['user'],
            'timestamp': event['timestamp'],
            'team': event['team'],
        }))

    @database_sync_to_async
    def find_mission(self, mission_id):
        return Mission.objects.get(mission_id=mission_id)
