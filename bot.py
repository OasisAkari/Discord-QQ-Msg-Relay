import asyncio
import re

import aiohttp
import discord
import websockets
from discord import Webhook, AsyncWebhookAdapter
from graia.application import GraiaMiraiApplication, Session
from graia.application.group import Group, Member
from graia.application.message.chain import MessageChain
from graia.application.message.elements.internal import Plain, Image, FlashImage, Source, At, App, AtAll, Xml, Json, \
    Poke, Voice, Quote, Face
from graia.application.message.elements.internal import UploadMethods
from graia.broadcast import Broadcast
from configparser import ConfigParser
from os.path import abspath

cp = ConfigParser()
cp.read(abspath("./config.cfg"))
section = cp.sections()[0]

loop = asyncio.get_event_loop()

bcc = Broadcast(loop=loop)
app = GraiaMiraiApplication(
    broadcast=bcc,
    connect_info=Session(
        host=cp.get(section, 'mahlink'),
        authKey=cp.get(section, 'mahauth'),
        account=cp.get(section, 'qq'),
        websocket=True
    )
)

targetqqgroup = int(cp.get(section, 'qqgroup'))
webhooklink = cp.get(section, 'webhooklink')

async def qq_recv_msg(websocket, path):
    while True:
        try:
            recv_text = await websocket.recv()
            msgchain = MessageChain.create([])
            text = recv_text
            text = re.sub('\[\<.*:.*\>\]', '', text)
            text = re.split(r'(@\[QQ: .*?\].*#0000)',text)
            for ele in text:
                matele = re.match(r'@\[QQ: (.*?)]',ele)
                if matele:
                    print('t')
                    msgchain = msgchain.plusWith([At(int(matele.group(1)))])
                else:
                    msgchain = msgchain.plusWith([Plain(ele)])
            textre = re.findall(r'\[\<.*?:.*?\>\]', recv_text)
            for elements in textre:
                a = re.match(r'\[\<ImageURL:(.*)\>\]', elements)
                if a:
                    msgchain2 = msgchain.create([Image.fromNetworkAddress(url=a.group(1), method=UploadMethods.Group)])
                    await app.sendGroupMessage(targetqqgroup, msgchain2)
            print(msgchain)
            await app.sendGroupMessage(targetqqgroup, msgchain)
        except websockets.exceptions.ConnectionClosedOK:
            pass


async def dc_recv_msg(websocket, path):
    while True:
        try:
            recv_text = await websocket.recv()
            recv_text = recv_text.split('!:!:!:wqwqw!qwqwq')
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(5)) as session:
                webhook = Webhook.from_url(webhooklink
                                           ,
                                           adapter=AsyncWebhookAdapter(session))
                qqavatarbase = 'https://ptlogin2.qq.com/getface?appid=1006102&imgtype=3&uin=' + recv_text[0]
                async with session.get(qqavatarbase) as qlink:
                    try:
                        qqavatarlink = re.match(r'pt.setHeader\({".*?":"(https://thirdqq.qlogo.cn/.*)"}\)',
                                                await qlink.text())
                    except Exception:
                        qqavatarlink = 'https://im.qq.com/assets/images/logo.png'
                print(qqavatarlink)
                await webhook.send(recv_text[2], username=f'[QQ: {recv_text[0]}] {recv_text[1]}',
                                   avatar_url=qqavatarlink.group(1),
                                   allowed_mentions=discord.AllowedMentions(everyone=True))
        except websockets.exceptions.ConnectionClosedOK:
            pass


@bcc.receiver("ApplicationLaunched", priority=1)
async def start_websocket():
    await websockets.serve(dc_recv_msg, '127.0.0.1', int(cp.get(section, 'websocketport1')))


@bcc.receiver("ApplicationLaunched", priority=2)
async def start_websocket():
    await websockets.serve(qq_recv_msg, '127.0.0.1', int(cp.get(section, 'websocketport2')))


async def sendmsg(message):
    async with websockets.connect('ws://127.0.0.1:'+cp.get(section, 'websocketport1')) as websocket:
        a = await websocket.send('!:!:!:wqwqw!qwqwq'.join(message))
        print(a)


@bcc.receiver("GroupMessage", priority=3)
async def group_message_handler(app: GraiaMiraiApplication, message: MessageChain, group: Group, member: Member):
    if group.id == targetqqgroup:
        if message.asDisplay()[0:2] != '//':
            msglist = []
            quotes = message.get(Quote)
            for quote in quotes:
                senderId = quote.senderId
                msglist.append(f'> {senderId}: {quote.origin.asDisplay()}')
            ats = message.get(At)
            for at in ats:
                atId = at.target
                atdis = f'@[QQ: {atId}]'
                if atdis not in msglist:
                    msglist.append(f'@[QQ: {atId}]')
            atalls = message.get(AtAll)
            for atall in atalls:
                msglist.append('@全体成员')
            msgs = message.get(Plain)
            for msg in msgs:
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
            msglist = str(member.id), member.name, '\n'.join(msglist)

            print(msglist)
            await sendmsg(msglist)


app.launch_blocking()
