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

qq = cp.get(section, 'qq')
bcc = Broadcast(loop=loop)
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
debug = cp.get(section, 'debug')
print(debug)
if debug == 'True':
    debug = True
if debug == True:
    debug_webhook_link = cp.get(section, 'debug_webhook_link')
else:
    debug_webhook_link = None


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


async def qq_recv_msg(websocket, path):
    while True:
        try:
            recv_text = await websocket.recv()
            if debug == True:
                await dc_debug_webhook(f'收到一条消息：`{recv_text}`，开始重建消息链。', f'[INFO] Websocket_QQ',
                                       avatar_url='https://cdn.discordapp.com/avatars/700205918918541333/c039f234d1796106fb989bcb0e3fe735.png')
            msgchain = MessageChain.create([])
            text = recv_text
            text = re.sub('\[\<.*:.*\>\]', '', text)
            text = re.split(r'(@\[QQ: .*?\].*#0000|@\[QQ: .*?\])', text)
            for ele in text:
                matele = re.match(r'@\[QQ: (.*?)]', ele)
                if matele:
                    msgchain = msgchain.plusWith([At(int(matele.group(1)))])
                else:
                    msgchain = msgchain.plusWith([Plain(ele)])
            try:
                await app.sendGroupMessage(target_qqgroup, msgchain)
                if debug == True:
                    await dc_debug_webhook(f'成功将`{str(msgchain)}`发送至{int(target_qqgroup)}！', f'[OK] {target_qqgroup}',
                                           avatar_url='https://cdn.discordapp.com/avatars/700205918918541333/c039f234d1796106fb989bcb0e3fe735.png')
            except Exception as e:
                if debug == True:
                    await dc_debug_webhook(f'`{str(msgchain)}`发送至{int(target_qqgroup)}时抛出了错误：\n{str(e)}',
                                           f'[ERROR] {target_qqgroup}',
                                           avatar_url='https://discordapp.com/assets/8becd37ab9d13cdfe37c08c496a9def3.svg')
            textre = re.findall(r'\[\<.*?:.*?\>\]', recv_text)
            for elements in textre:
                a = re.match(r'\[\<ImageURL:(.*)\>\]', elements)
                if a:
                    msgchain2 = msgchain.create([Image.fromNetworkAddress(url=a.group(1), method=UploadMethods.Group)])
                    try:
                        await app.sendGroupMessage(target_qqgroup, msgchain2)
                        if debug == True:
                            await dc_debug_webhook(f'成功将`{str(msgchain2)}`发送至{int(target_qqgroup)}！',
                                                   f'[OK] {target_qqgroup}',
                                                   avatar_url='https://cdn.discordapp.com/avatars/700205918918541333/c039f234d1796106fb989bcb0e3fe735.png')
                    except Exception as e:
                        if debug == True:
                            await dc_debug_webhook(f'`{str(msgchain)}`发送至{int(target_qqgroup)}时抛出了错误：\n{str(e)}',
                                                   f'[ERROR] {target_qqgroup}',
                                                   avatar_url='https://discordapp.com/assets/8becd37ab9d13cdfe37c08c496a9def3.svg')
        except websockets.exceptions.ConnectionClosedOK:
            pass


async def dc_recv_msg(websocket, path):
    while True:
        try:
            recv_text = await websocket.recv()
            if debug == True:
                await dc_debug_webhook(f'收到一条消息：`{recv_text}`，开始重建消息链。', f'[INFO] Websocket_DC')
            recv_text = recv_text.split('!:!:!:wqwqw!qwqwq')
            try:
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
                    if debug == True:
                        await dc_debug_webhook(f'成功将一条消息发送至Discord：`{recv_text[2]}`', f'[OK] Discord Webhook')
            except Exception as e:
                if debug == True:
                    await dc_debug_webhook(f'`{str(recv_text)}`发送时抛出了错误：\n{str(e)}',
                                           f'[ERROR] Discord Webhook',
                                           'https://discordapp.com/assets/8becd37ab9d13cdfe37c08c496a9def3.svg')
        except websockets.exceptions.ConnectionClosedOK:
            pass


@bcc.receiver("ApplicationLaunched", priority=1)
async def start_websocket():
    await websockets.serve(dc_recv_msg, '127.0.0.1', int(cp.get(section, 'websocket_dc_port')))


@bcc.receiver("ApplicationLaunched", priority=2)
async def start_websocket():
    await websockets.serve(qq_recv_msg, '127.0.0.1', int(cp.get(section, 'websocket_qq_port')))


async def sendmsg(message):
    async with websockets.connect('ws://127.0.0.1:' + cp.get(section, 'websocket_dc_port')) as websocket:
        try:
            message = '!:!:!:wqwqw!qwqwq'.join(message)
            await websocket.send(message)
            if debug == True:
                await dc_debug_webhook(f'成功发送一条消息到Websocket_DC：`{message}`', f'[OK] QQGroup -> Websocket_DC')
        except Exception as e:
            if debug == True:
                await dc_debug_webhook(f'`{str(message)}`发送时抛出了错误：\n{str(e)}',
                                       f'[ERROR] QQGroup -x Websocket_DC',
                                       'https://discordapp.com/assets/8becd37ab9d13cdfe37c08c496a9def3.svg')


@bcc.receiver("GroupMessage", priority=3)
async def group_message_handler(app: GraiaMiraiApplication, message: MessageChain, group: Group, member: Member):
    if group.id == target_qqgroup:
        try:
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
                if debug == True:
                    await dc_debug_webhook(f'消息链转换完毕：\n`{str(message)}` -> {str(allmsg)}。', f'[INFO] {group.id}',
                                           avatar_url='https://cdn.discordapp.com/avatars/700205918918541333/c039f234d1796106fb989bcb0e3fe735.png')
                msglist = str(member.id), member.name, allmsg
                await sendmsg(msglist)
            else:
                if debug == True:
                    await dc_debug_webhook('有一条消息触发转发过滤，此消息已过滤', f'[INFO] {group.id}',
                                           avatar_url='https://cdn.discordapp.com/avatars/700205918918541333/c039f234d1796106fb989bcb0e3fe735.png')
        except Exception as e:
            traceback.print_exc()
            if debug == True:
                await dc_debug_webhook(f'执行操作时发生了错误：\n`{str(e)}`', f'[ERROR] {group.id}',
                                       avatar_url='https://discordapp.com/assets/8becd37ab9d13cdfe37c08c496a9def3.svg')

app.launch_blocking()
