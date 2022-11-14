from django.contrib.auth.models import User
from django.db import transaction
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, Serializer

from web.models import Mission, Photo, ChatMessageContent


class MissionValidationSerializer(ModelSerializer):
    class Meta:
        model = Mission
        fields = ['unique_code', ]


class UploadPhotoSerializer(ModelSerializer):
    user_id = serializers.IntegerField()
    receiver = serializers.CharField(required=True)
    mission_id = serializers.IntegerField()
    path = Base64ImageField(required=True)

    class Meta:
        model = Photo
        fields = ['timestamp', 'path', 'mission_id', 'info', 'user_id', 'geom', 'path', 'receiver']

    def create(self, validated_data):
        with transaction.atomic():
            if Photo.objects.all().count() < 1:
                id_number = 1
                id_txt = 'photo.1'
            else:
                id_number = Photo.objects.latest('number_id').number_id + 1
                id_txt = 'photo.' + str(id_number)
            content_obj = ChatMessageContent.objects.create(
                id=id_txt,
                type='photo'
            )
            return Photo.objects.create(
                id=content_obj,
                geom=validated_data['geom'],
                timestamp=validated_data['timestamp'],
                user=User.objects.get(pk=validated_data['user_id']),
                path=validated_data['path'],
                mission=Mission.objects.get(pk=validated_data['mission_id']),
                info=validated_data['info'],
                number_id=id_number,
            )


class ImageMsgSerializer(Serializer):
    type = serializers.CharField()
    msg_type = serializers.CharField()
    user = serializers.CharField()
    url = serializers.CharField()
    detect_url = serializers.CharField()
    mission_id = serializers.IntegerField()
    time = serializers.DateTimeField()
    time_taken = serializers.DateTimeField(required=False)
    obj_id = serializers.CharField()
    geom = serializers.ListSerializer(child=serializers.DecimalField(max_digits=25, decimal_places=20))


class ChatHistorySerializer(Serializer):
    type = serializers.CharField()
    is_sender = serializers.BooleanField()
    time = serializers.DateTimeField()
    time_taken = serializers.DateTimeField(required=False)
    sender = serializers.CharField()
    msg = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    lat = serializers.DecimalField(required=False, max_digits=30, decimal_places=25)
    long = serializers.DecimalField(required=False, max_digits=30, decimal_places=25)
    geom = serializers.ListSerializer(child=serializers.ListSerializer(child=serializers.DecimalField(max_digits=30, decimal_places=25)), required=False,)
    path = serializers.CharField(required=False)
    id = serializers.CharField(required=False)

