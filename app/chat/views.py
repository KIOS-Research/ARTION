import datetime
import hashlib

import pytz
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from web.models import ChatPrivateRoom, ChatMessage, ChatRoomMembers, Team, Mission


def index(request):
    return render(request, 'chat/index.html')


class RoomUserView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Initialize room view
    """
    login_rl = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def test_func(self):
        return True

    def get(self, request, room_name):
        sorted_names = sorted([request.user.username, room_name])
        str_names = 'chat_{user1}_{user2}'.format(user1=sorted_names[0], user2=sorted_names[1])
        hash_code = hashlib.md5(str_names.encode()).hexdigest()
        room_obj = ChatPrivateRoom.objects.filter(hash_code=hash_code).first()
        msg_list = []
        if room_obj is not None:
            msgs = ChatMessage.objects.filter(room=room_obj)
            for msg in msgs:
                is_sender = True if msg.sender.username == request.user.username else False
                if msg.content.type == 'text':
                    msg_list.append({'msg': msg.content.chattext.text, 'is_sender': is_sender})
                elif msg.content.type == 'poi':
                    msg_list.append({'msg': str(msg.content.poi), 'is_sender': is_sender})

        return render(request, 'chat/room.html', {
            'room_name': room_name,
            'msg_list': msg_list
        })


class ChatView(LoginRequiredMixin, View):
    """
    Initialize chat view. User chats and latest conversation
    """
    login_rl = settings.LOGIN_URL
    redirect_field_name = 'redirect_to'

    def get(self, request, mission_id):
        unread_num = ChatRoomMembers.objects.filter(user=request.user, unread=True,
                                                    room__mission_id=mission_id).count()
        rooms = ChatPrivateRoom.objects.filter(
            mission_id=mission_id, room_member__user=request.user
        ).exclude(type='team')

        chat_list = []
        open_chat = request.GET.get('chat-name', None)
        open_display_name = open_chat
        open_chat_type = request.GET.get('chat-type', None)
        has_open_chat = True if open_chat is not None else False
        if has_open_chat and open_chat == 'ccc':
            open_chat = Mission.objects.get(pk=mission_id).create_user.username
        people_list = []
        for user in User.objects.filter(is_active=True).exclude(pk=request.user.pk):
            people_list.append(user.username)

        teams = Team.objects.filter(mission__pk=mission_id)

        for room in rooms:
            room_name_obj = ChatRoomMembers.objects.filter(room=room, ).exclude(user=request.user).first()
            unread = ChatRoomMembers.objects.filter(room=room, user=request.user).first().unread
            if room_name_obj is not None:
                room_name = room_name_obj.user.username
            else:
                continue

            last_msg = ChatMessage.objects.filter(room=room, mission_id=mission_id).order_by('-date_created')
            if len(last_msg) > 0:
                last_msg_date = last_msg[0].date_created
            else:
                last_msg_date = datetime.datetime.min.replace(tzinfo=pytz.UTC)

            if has_open_chat and room_name == open_chat:
                unread = False
            chat_list.append({
                'name': room_name,
                'display_name': room_name,
                'is_active': True,
                'last_msg_date': last_msg_date,
                'type': 'user',
                'unread': unread
            })

        rooms = ChatPrivateRoom.objects.filter(mission_id=mission_id).exclude(type='user')
        for room in rooms:
            room_name = str(room.team_id)
            display_name = room.team.name
            members = ChatRoomMembers.objects.filter(room=room, user=request.user).first()
            if members is not None:
                unread = ChatRoomMembers.objects.filter(room=room, user=request.user).first().unread
            last_msg = ChatMessage.objects.filter(room=room, mission_id=mission_id).order_by('-date_created')
            if len(last_msg) > 0:
                last_msg_date = last_msg[0].date_created
            else:
                last_msg_date = datetime.datetime.min.replace(tzinfo=pytz.UTC)

            if has_open_chat and room_name == open_chat:
                open_display_name = display_name
                unread = False
            chat_list.append({
                'name': room_name,
                'display_name': display_name,
                'is_active': True,
                'last_msg_date': last_msg_date,
                'type': room.type,
                'unread': unread
            })

        if len(chat_list) < 1:
            if has_open_chat:
                if open_chat_type == 'team':
                    str_names = 'chat_team_{team}_{mission_id}'.format(team=open_chat, mission_id=mission_id)
                    hash_code = hashlib.md5(str_names.encode()).hexdigest()
                    room_obj = ChatPrivateRoom.objects.filter(hash_code=hash_code).first()
                    if room_obj is not None:
                        open_display_name = room_obj.team.name

                return render(request, 'chat/modal_room.html', {
                    'room_name': open_chat,
                    'room_display_name': open_display_name,
                    'room_type': open_chat_type,
                    'msg_list': [],
                    'chat_list': [],
                    'has_chat': True,
                    'people_list': people_list,
                    'teams': teams,
                    'mission_id': mission_id,
                    'server_mode': settings.USE_X_FORWARDED_HOST,
                    'unread_num': unread_num
                })
            else:
                return render(request, 'chat/modal_room.html', {
                    'room_name': '',
                    'room_display_name': '',
                    'room_type': '',
                    'msg_list': [],
                    'chat_list': [],
                    'has_chat': False,
                    'people_list': people_list,
                    'teams': teams,
                    'mission_id': mission_id,
                    'server_mode': settings.USE_X_FORWARDED_HOST,
                    'unread_num': unread_num
                })

        chat_list_ordered = sorted(chat_list, key=lambda d: d['last_msg_date'], reverse=True)
        if not has_open_chat:
            return render(request, 'chat/modal_room.html', {
                'room_name': '',
                'room_display_name': '',
                'room_type': '',
                'msg_list': [],
                'chat_list': chat_list_ordered,
                'has_chat': False,
                'people_list': people_list,
                'teams': teams,
                'mission_id': mission_id,
                'server_mode': settings.USE_X_FORWARDED_HOST,
                'unread_num': unread_num
            })

        if has_open_chat:
            room_name = open_chat
            room_type = open_chat_type
        else:
            room_name = chat_list_ordered[0]['name']
            room_type = chat_list_ordered[0]['type']
            open_display_name = chat_list_ordered[0]['display_name']
            chat_list_ordered[0]['unread'] = False

        if room_type == 'team':
            str_names = 'chat_team_{team}_{mission_id}'.format(team=room_name, mission_id=mission_id)
        else:
            sorted_names = sorted([request.user.username, room_name])
            str_names = 'chat_{user1}_{user2}_{mission_id}'.format(
                user1=sorted_names[0],
                user2=sorted_names[1],
                mission_id=mission_id
            )

        hash_code = hashlib.md5(str_names.encode()).hexdigest()
        room_obj = ChatPrivateRoom.objects.filter(hash_code=hash_code).first()
        msg_list = []
        if room_obj is not None:
            room_member = ChatRoomMembers.objects.filter(room=room_obj, user=request.user).first()
            if room_member is not None:
                room_member.unread = False
                room_member.save()
            unread_num = ChatRoomMembers.objects.filter(user=request.user, unread=True,
                                                        room__mission_id=mission_id).count()
            msgs = ChatMessage.objects.filter(room=room_obj, mission_id=mission_id).order_by('-date_created')[:40:-1]
            for msg in msgs:
                is_sender = True if msg.sender.username == request.user.username else False
                if msg.content.type == 'text':
                    msg_list.append({'msg': msg.content.chattext.text, 'is_sender': is_sender,
                                     'time': timezone.localtime(msg.date_created), 'sender': msg.sender.username})
                elif msg.content.type == 'poi':
                    msg_list.append({'msg': str(msg.content.poi), 'is_sender': is_sender,
                                     'time': timezone.localtime(msg.date_created), 'sender': msg.sender.username})
                elif msg.content.type == 'route':
                    msg_list.append({'msg': str(msg.content.route), 'is_sender': is_sender,
                                     'time': timezone.localtime(msg.date_created), 'sender': msg.sender.username})
                elif msg.content.type == 'photo':
                    msg_list.append({'msg': str(msg.content.photo), 'is_sender': is_sender,
                                     'time': timezone.localtime(msg.date_created), 'sender': msg.sender.username})

        # return render(request, 'chat/room.html', {
        return render(request, 'chat/modal_room.html', {
            'room_name': room_name,
            'room_display_name': open_display_name,
            'room_type': room_type,
            'msg_list': msg_list,
            'chat_list': chat_list_ordered,
            'has_chat': True,
            'people_list': people_list,
            'teams': teams,
            'mission_id': mission_id,
            'server_mode': settings.USE_X_FORWARDED_HOST,
            'unread_num': unread_num
        })
