import asyncio
import re
import traceback
from configparser import ConfigParser
from os.path import abspath

import aiohttp
import discord
import websockets
from discord import Webhook, AsyncWebhookAdapter
from graia.application import GraiaMiraiApplication, Session
from graia.application.group import Group, Member
from graia.application.message.chain import MessageChain
from graia.application.message.elements.internal import Plain, Image, FlashImage, At, App, AtAll, Xml, Json, \
    Poke, Voice, Quote, Face
from graia.application.message.elements.internal import UploadMethods
from graia.broadcast import Broadcast

cp = ConfigParser()
cp.read(abspath("./config.cfg"))
section = cp.sections()[0]

loop = asyncio.get_event_loop()

qq = int(cp.get(section, 'qq'))
bcc = Broadcast(loop=loop, debug_flag=False)
app = GraiaMiraiApplication(
    broadcast=bcc,
    connect_info=Session(
        host=cp.get(section, 'mah_link'),
        authKey=cp.get(section, 'mah_auth'),
        account=qq,
        websocket=True
    )
)

target_qqgroup = int(cp.get(section, 'qqgroup'))
webhook_link = cp.get(section, 'webhook_link')
websocket_port = cp.get(section, 'websocket_port')
debug = cp.get(section, 'debug')
print(debug)
if debug == 'True':
    debug = True
if debug == True:
    debug_webhook_link = cp.get(section, 'debug_webhook_link')
else:
    debug_webhook_link = None

CLIENTS = set()


async def msgbroadcast(msg):
    await asyncio.gather(
        *[ws.send(msg) for ws in CLIENTS],
        return_exceptions=False,
    )
    await asyncio.sleep(0.1)


async def msgbroadcast_handler(websocket, path):
    CLIENTS.add(websocket)
    try:
        async for msg in websocket:
            await msgbroadcast(msg)
    except websockets.exceptions.ConnectionClosedOK:
        pass
    finally:
        CLIENTS.remove(websocket)


@bcc.receiver("ApplicationLaunched")
async def start_websocket():
    await websockets.serve(msgbroadcast_handler, '127.0.0.1', websocket_port)


async def dc_debug_webhook(message, username, avatar_url=None):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(5)) as session:
        webhook = Webhook.from_url(debug_webhook_link
                                   ,
                                   adapter=AsyncWebhookAdapter(session))
        await webhook.send(message, username=username,
                           avatar_url=avatar_url)


@bcc.receiver("ApplicationLaunched")
async def runprompt():
    if debug == True:
        await dc_debug_webhook(f'互联QQ侧机器人已启动。', f'[INFO] QQBOT',
                           'https://cdn.discordapp.com/avatars/700205918918541333/c039f234d1796106fb989bcb0e3fe735.png')

@bcc.receiver("ApplicationLaunched")
async def recv_msg():
    async with websockets.connect('ws://127.0.0.1:' + websocket_port) as websocket:
        while True:
            recv_text = await websocket.recv()
            mch = re.match(r'\[(.*?)\](.*)',recv_text)
            try:
                if mch:
                    if mch.group(1) == 'QQ':
                        msgchain = MessageChain.create([])
                        text = mch.group(2)
                        text = re.sub('\[\<.*:.*\>\]', '', text)
                        text = re.split(r'(@\[QQ: .*?\].*#0000|@\[QQ: .*?\])', text)
                        for ele in text:
                            matele = re.match(r'@\[QQ: (.*?)]', ele)
                            if matele:
                                msgchain = msgchain.plusWith([At(int(matele.group(1)))])
                            else:
                                msgchain = msgchain.plusWith([Plain(ele)])
                        await app.sendGroupMessage(target_qqgroup, msgchain)
                        textre = re.findall(r'\[\<.*?:.*?\>\]', mch.group(2))
                        for elements in textre:
                            a = re.match(r'\[\<ImageURL:(.*)\>\]', elements)
                            if a:
                                msgchain2 = msgchain.create([Image.fromNetworkAddress(url=a.group(1), method=UploadMethods.Group)])
                                await app.sendGroupMessage(target_qqgroup, msgchain2)
                    elif mch.group(1) == 'Discord':
                        recv_text = mch.group(2).split('!:!:!:wqwqw!qwqwq')
                        async with aiohttp.ClientSession() as session:
                            webhook = Webhook.from_url(webhook_link
                                                       ,
                                                       adapter=AsyncWebhookAdapter(session))
                            qqavatarbase = 'https://ptlogin2.qq.com/getface?appid=1006102&imgtype=3&uin=' + recv_text[0]
                            async with session.get(qqavatarbase) as qlink:
                                try:
                                    qqavatarlink = re.match(r'pt.setHeader\({".*?":"(https://thirdqq.qlogo.cn/.*)"}\)',
                                                            await qlink.text())
                                    qqavatarlink = qqavatarlink.group(1)
                                except Exception:
                                    qqavatarlink = None
                            await webhook.send(recv_text[2], username=f'[QQ: {recv_text[0]}] {recv_text[1]}',
                                                   avatar_url=qqavatarlink,
                                                   allowed_mentions=discord.AllowedMentions(everyone=True))
            except websockets.exceptions.ConnectionClosedOK:
                pass

async def sendmsg(message):
    async with websockets.connect('ws://127.0.0.1:' + websocket_port) as websocket:
        message = '!:!:!:wqwqw!qwqwq'.join(message)
        await websocket.send('[Discord]' + message)


@bcc.receiver("GroupMessage", priority=3)
async def group_message_handler(app: GraiaMiraiApplication, message: MessageChain, group: Group, member: Member):
    if group.id == target_qqgroup:
        if message.asDisplay()[0:2] != '//':
            if debug == True:
                await dc_debug_webhook(f'收到消息链`{str(message)}`，开始转换消息链。', f'[INFO] {group.id}',
                                       avatar_url='https://cdn.discordapp.com/avatars/700205918918541333/c039f234d1796106fb989bcb0e3fe735.png')
            msglist = []
            newquotetarget = None
            quotes = message.get(Quote)
            for quote in quotes:
                senderId = quote.senderId
                orginquote = quote.origin.asDisplay()
                if senderId == qq:
                    msglist.append(f'> {orginquote}')
                else:
                    msglist.append(f'> {senderId}: {orginquote}')
                newquotetargetre = re.match(r'(.*?):.*',orginquote)
                if newquotetargetre:
                    newquotetarget = newquotetargetre.group(1)
            ats = message.get(At)
            for at in ats:
                atId = at.target
                atdis = f'@[QQ: {atId}]'
                print(atdis, f'@[QQ: {qq}]')
                if atdis == f'@[QQ: {qq}]':
                    print(newquotetarget)
                    if newquotetarget != None:
                        atdis = f'@{newquotetarget} '
                if atdis not in msglist:
                    msglist.append(atdis)
            atalls = message.get(AtAll)
            for atall in atalls:
                msglist.append('@全体成员')
            msgs = message.get(Plain)
            for msg in msgs:
                if msg.text != ' ':
                    msglist.append(msg.text)
            imgs = message.get(Image)
            for img in imgs:
                msglist.append(img.url)
            faces = message.get(Face)
            for face in faces:
                msglist.append(f'[表情{face.faceId}]')
            xmls = message.get(Xml)
            for xml in xmls:
                msglist.append('[Xml消息]')
            jsons = message.get(Json)
            for jsonn in jsons:
                msglist.append('[Json消息]')
            apps = message.get(App)
            for appp in apps:
                msglist.append('[App消息]')
            pokes = message.get(Poke)
            for poke in pokes:
                msglist.append('[戳一戳]')
            voices = message.get(Voice)
            for voice in voices:
                msglist.append('[语音]')
            flashimages = message.get(FlashImage)
            for flashimage in flashimages:
                msglist.append('[闪照]')
            allmsg = '\n'.join(msglist)
            msglist = str(member.id), member.name, allmsg
            async with websockets.connect('ws://127.0.0.1:' + websocket_port) as websocket:
                message = '!:!:!:wqwqw!qwqwq'.join(msglist)
                await websocket.send('[Discord]' + message)

loop2 = asyncio.new_event_loop()
loop2.create_task(app.launch_blocking())