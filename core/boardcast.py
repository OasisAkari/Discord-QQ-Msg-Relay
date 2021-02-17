import asyncio
from os.path import abspath

from graia.application import GraiaMiraiApplication, Session
from graia.broadcast import Broadcast

from config import config

loop = asyncio.get_event_loop()
config_filename = 'config.cfg'
config_path = abspath('./config/' + config_filename)


def c(q):
    return config(config_path, q)


bcc = Broadcast(loop=loop, debug_flag=c('debug'))
app = GraiaMiraiApplication(
    broadcast=bcc,
    enable_chat_log=c('enable_chat_log'),
    connect_info=Session(
        host=c('mah_link'),  # 填入 httpapi 服务运行的地址
        authKey=c('mah_auth'),  # 填入 authKey
        account=c('qq'),  # 你的机器人的 qq 号
        websocket=c('websocket')  # Graia 已经可以根据所配置的消息接收的方式来保证消息接收部分的正常运作.
    )
)
