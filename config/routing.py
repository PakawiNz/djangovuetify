import datetime
import json
from enum import Enum

import channels
from asgiref.sync import async_to_sync
from channels.auth import AuthMiddlewareStack
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf.urls import url


class UserConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user_id = self.scope['user'].id
        if not user_id:
            await self.close()

        self.group_name = 'user_{}'.format(user_id)
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def notification(self, event):
        await self.send(text_data=json.dumps(event))

    async def push_data(self, event):
        await self.send(text_data=json.dumps(event))


application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter([
            url(r'^ws/socket/$', UserConsumer),
        ])
    ),
})


class NOTI_COLOR(Enum):
    BLACK = 'black'
    RED = 'red'
    YELLOW = 'yellow'
    GREEN = 'green'


def _group_send(group_name, data):
    channel_layer = channels.layers.get_channel_layer()
    group_send = async_to_sync(channel_layer.group_send)
    group_send(group_name, data)


def notify_user(user, message, color: NOTI_COLOR = NOTI_COLOR.BLACK):
    _group_send(
        'user_{}'.format(user.id),
        {
            'type': 'notification',
            'message': message,
            'color': color.value,
            'timestamp': datetime.datetime.now().timestamp()
        }
    )


def push_data(user, data: dict):
    data['type'] = 'push_data'
    _group_send('user_{}'.format(user.id), data)
