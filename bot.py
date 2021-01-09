import asyncio
import json
import re
import traceback
from configparser import ConfigParser
from datetime import timedelta, timezone
from os.path import abspath

import aiohttp
import discord
import websockets
from discord import Webhook, AsyncWebhookAdapter
from graia.application import GraiaMiraiApplication, Session
from graia.application.event.mirai import GroupRecallEvent
from graia.application.group import Group, Member
from graia.application.message.chain import MessageChain
from graia.application.message.elements.internal import Plain, Image, FlashImage, At, App, AtAll, Xml, Json, \
    Poke, Voice, Quote, Face, Source
from graia.application.message.elements.internal import UploadMethods
from graia.broadcast import Broadcast

import helper

cp = ConfigParser()
cp.read(abspath("./config.cfg"))
section = cp.sections()[0]

target_qqgroup = int(cp.get(section, 'qqgroup'))
webhook_link = cp.get(section, 'webhook_link')
websocket_port = cp.get(section, 'websocket_port')
face_link = cp.get(section, 'face_link')
debug = cp.get(section, 'debug')
channelid = int(cp.get(section, 'dc_channel'))
serverid = int(cp.get(section, 'dc_server'))
if debug == 'True' or '1':
    debug = True
else:
    debug = False

if debug:
    debug_webhook_link = cp.get(section, 'debug_webhook_link')
else:
    debug_webhook_link = None

loop = asyncio.get_event_loop()

qq = int(cp.get(section, 'qq'))
bcc = Broadcast(loop=loop, debug_flag=debug)
app = GraiaMiraiApplication(
    broadcast=bcc,
    connect_info=Session(
        host=cp.get(section, 'mah_link'),
        authKey=cp.get(section, 'mah_auth'),
        account=qq,
        websocket=True
    )
)

CLIENTS = set()


async def msgbroadcast(msg):
    await asyncio.gather(
        *[ws.send(msg) for ws in CLIENTS],
        return_exceptions=False,
    )
    await asyncio.sleep(1)


async def msgbroadcast_handler(websocket, path):
    CLIENTS.add(websocket)
    try:
        async for msg in websocket:
            await msgbroadcast(msg)
    except websockets.exceptions.ConnectionClosedOK:
        pass
    finally:
        CLIENTS.remove(websocket)


@bcc.receiver("ApplicationLaunched", priority=1)
async def start_websocket():
    await websockets.serve(msgbroadcast_handler, '127.0.0.1', websocket_port)


@bcc.receiver("ApplicationLaunched")
async def ready():
    if debug:
        await helper.dc_debug_webhook(debug_webhook_link, f'互联QQ侧机器人已启动。', f'[INFO] QQBOT',
                                      'https://cdn.discordapp.com/avatars/700205918918541333/c039f234d1796106fb989bcb0e3fe735.png')


@bcc.receiver("ApplicationLaunched", priority=10)
async def recv_msg():
    async with websockets.connect('ws://127.0.0.1:' + websocket_port) as websocket:
        while True:
            recv_text = await websocket.recv()
            j = json.loads(recv_text)
            print(j)
            try:
                if j['Type'] == 'QQ':
                    msgchain = MessageChain.create([])
                    text = j['Text']
                    helper.writedcuser(j['Name'], j['UID'])
                    if 'Nick' in j:
                        displayname = f'{j["Nick"]}({j["Name"]})'
                    else:
                        displayname = j["Name"]
                    text = f'{displayname}:\n{text}'
                    text = re.sub('\[<.*:.*>]', '', text)
                    text = re.sub(r'\r$|\n$', '', text)
                    text = re.split(r'(@\[QQ: .*?].*#0000|@\[QQ: .*?])', text)
                    for ele in text:
                        matele = re.match(r'@\[QQ: (.*?)]', ele)
                        if matele:
                            msgchain = msgchain.plusWith(MessageChain.create([At(int(matele.group(1)))]))
                        else:
                            msgchain = msgchain.plusWith(MessageChain.create([Plain(ele)]))
                    sendmsg = await app.sendGroupMessage(target_qqgroup, msgchain,
                    quote=j['Quote'] if 'Quote' in j else None)
                    if debug == True:
                        helper.writeqqmsg(sendmsg.messageId, '\n'.join(text))
                    msgid = str(sendmsg.messageId)
                    textre = re.findall(r'\[<.*?:.*?>]', j['Text'])
                    try:
                        for elements in textre:
                            a = re.match(r'\[\<ImageURL:(.*)\>\]', elements)
                            if a:
                                msgchain2 = msgchain.create(
                                    [Image.fromNetworkAddress(url=a.group(1), method=UploadMethods.Group)])
                                sendimg = await app.sendGroupMessage(target_qqgroup, msgchain2,
                                quote=j['Quote'] if 'Quote' in j else None)
                                msgid += f'|{sendimg.messageId}'
                                if debug == True:
                                    helper.writeqqmsg(sendimg.messageId, a.group(1))
                    except Exception:
                        traceback.print_exc()
                    helper.writeid(j['MID'], msgid)
                if j['Type'] == 'Discord':
                    async with aiohttp.ClientSession() as session:
                        webhook = Webhook.from_url(webhook_link
                                                   ,
                                                   adapter=AsyncWebhookAdapter(session))
                        qqavatarbase = 'https://ptlogin2.qq.com/getface?appid=1006102&imgtype=3&uin=' + j['UID']
                        async with session.get(qqavatarbase) as qlink:
                            try:
                                qqavatarlink = re.match(r'pt.setHeader\({".*?":"(https://thirdqq.qlogo.cn/.*)"}\)',
                                                        await qlink.text())
                                qqavatarlink = qqavatarlink.group(1)
                            except Exception:
                                qqavatarlink = None
                        if 'Quote' in j:
                            c = helper.connect_db('./msgid.db')
                            cc = c.execute("SELECT * FROM ID WHERE QQID=?", (j['Quote']['MID'],))
                            for x in cc:
                                msgids = x[0]
                                msgids = msgids.split('|')
                                msgid = msgids[0]
                            embed = discord.Embed.from_dict({
                                "description": f"{j['Quote']['Name']} | {j['Quote']['Time']}  [[ ↑ ]](https://discord.com/channels/{serverid}/{channelid}/{msgid})",
                                "footer": {"text": f"{j['Quote']['Text']}"},
                            })
                            embed.color = 0x4F545C
                            await webhook.send(username=f'[QQ: {j["UID"]}] {j["Name"]}',
                                               avatar_url=qqavatarlink,
                                               allowed_mentions=discord.AllowedMentions(everyone=True, users=True),
                                               embed=embed
                                               )
                        send = await webhook.send(j["Text"], username=f'[QQ: {j["UID"]}] {j["Name"]}',
                                                  avatar_url=qqavatarlink,
                                                  allowed_mentions=discord.AllowedMentions(everyone=True, users=True),
                                                  wait=True)
                        helper.writeid(send.id, j["MID"])
                if j['Type'] == 'DCdelete':
                    c = helper.connect_db('./msgid.db')
                    cc = c.execute("SELECT * FROM ID WHERE DCID=?", (j['MID'],))
                    for x in cc:
                        msgids = x[1]
                        msgids = msgids.split('|')
                        for msgid in msgids:
                            try:
                                await app.revokeMessage(msgid)
                            except Exception:
                                continue
                    c.close()
                if j['Type'] == 'QQrecallI':
                    c = helper.connect_db('./msgid.db')
                    cc = c.execute(f"SELECT * FROM ID WHERE QQID LIKE '%{j['MID']}%'")
                    for x in cc:
                        msgids = x[1]
                        print(msgids)
                        msgids = msgids.split('|')
                        for y in msgids:
                            if y != j['MID']:
                                try:
                                    await app.revokeMessage(y)
                                except Exception:
                                    traceback.print_exc()
                    c.close()
                if j['Type'] == 'QQrecallD':
                    c = helper.connect_db('./msgid.db')
                    cc = c.execute(f"SELECT * FROM ID WHERE DCID LIKE '%{j['MID']}%'")
                    for x in cc:
                        msgids = x[1]
                        print(msgids)
                        msgids = msgids.split('|')
                        for y in msgids:
                            if y != j['MID']:
                                try:
                                    await app.revokeMessage(y)
                                except Exception:
                                    traceback.print_exc()
                    c.close()
            except websockets.exceptions.ConnectionClosedOK:
                pass
            except Exception:
                traceback.print_exc()
                continue


@bcc.receiver("GroupMessage")
async def group_message_handler(app: GraiaMiraiApplication, message: MessageChain, group: Group, member: Member):
    if group.id == target_qqgroup:
        if message.asDisplay()[0:2] != '//':
            dst = {}
            print(message)
            msglist = []
            newquotetarget = None
            quotes = message.get(Quote)
            for quote in quotes:
                Quotet = {}
                senderId = quote.senderId
                orginquote = quote.origin.asDisplay()
                if senderId != qq:
                    try:
                        getnickname = await app.getMember(target_qqgroup, senderId)
                        getnickname = re.sub(r'(\*|_|`|~~)', r'\\\1', getnickname.name)
                        Quotet['Name'] = getnickname
                    except Exception:
                        Quotet['Name'] = senderId
                else:
                    newquotetargetre = re.match(r'(.*?):.*', orginquote)
                    if newquotetargetre:
                        newquotetarget = newquotetargetre.group(1)
                        Quotet['Name'] = newquotetarget
                        orginquote = re.sub(r'.*?:', '', orginquote)
                orginquote = re.sub('\r', '\n', orginquote)
                Quotet['MID'] = quote.id
                Quotet['Text'] = orginquote
                time = quote.origin[Source][0].time.astimezone(timezone(timedelta(hours=8)))
                time = re.sub(r'\+.*', '', str(time))
                Quotet['Time'] = time
                dst['Quote'] = Quotet
            ats = message.get(At)
            for at in ats:
                atId = at.target
                atdis = f'@[QQ: {atId}]'
                if atId == qq:
                    if newquotetarget != None:
                        mat = re.match(r'.*\((.*)\)', newquotetarget)
                        if mat:
                            newquotetarget = mat.group(1)
                        try:
                            c = helper.connect_db('./dcname.db')
                            cc = c.execute("SELECT * FROM DCNAME WHERE NAME=?", (newquotetarget,))
                            for x in cc:
                                print(x)
                                newquotetarge = f'<@!{x[1]}>'
                        except:
                            newquotetarge = f'@{newquotetarget}'
                        atdis = newquotetarge
                else:
                    try:
                        getnickname = await app.getMember(target_qqgroup, atId)
                        getnickname = re.sub(r'(\*|_|`|~~)', r'\\\1', getnickname.name)
                        atdis = f'{atdis} {getnickname}'
                    except Exception:
                        pass
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
                if face_link != 'None':
                    msglist.append(f'{face_link}s{face.faceId}.gif')
                else:
                    msglist.append(f'[表情{face.faceId}]')
            xmls = message.get(Xml)
            for xml in xmls:
                msglist.append(f'[Xml消息]\n```\n{xml}\n```')
            jsons = message.get(Json)
            for jsonn in jsons:
                msglist.append(f'[Json消息]\n```\n{jsonn}\n```')
            apps = message.get(App)
            for appp in apps:
                msglist.append(f'[App消息]\n```\n{appp}\n```')
            pokes = message.get(Poke)
            for poke in pokes:
                msglist.append('[戳一戳]')
            voices = message.get(Voice)
            for voice in voices:
                msglist.append('[语音]')
            flashimages = message.get(FlashImage)
            for flashimage in flashimages:
                if debug == True:
                    await helper.dc_debug_webhook(debug_webhook_link, f'{member.id} 发送了一条闪照 {flashimage.url}', '[QQ]')
            allmsg = '\n'.join(msglist)
            if debug == True:
                helper.writeqqmsg(message[Source][0].id, allmsg)
            dst['Type'] = 'Discord'
            dst['UID'] = str(member.id)
            dst['Name'] = member.name
            dst['MID'] = str(message[Source][0].id)
            dst['Text'] = allmsg
            j = json.dumps(dst)
            await helper.sendtoWebsocket(websocket_port, j)


@bcc.receiver("GroupRecallEvent")
async def revokeevent(event: GroupRecallEvent):
    print(event)
    if event.group.id == target_qqgroup:
        dst = {}
        if event.authorId != qq:
            dst['Type'] = 'QQrecall'
        else:
            dst['Type'] = 'QQrecallI'
        dst['MID'] = event.messageId
        dst['UID'] = event.authorId
        j = json.dumps(dst)
        await helper.sendtoWebsocket(websocket_port, j)
        if debug:
            print(event.authorId)
            try:
                c = helper.connect_db('./qqmsg.db')
                cc = c.execute("SELECT * FROM MSG WHERE ID=?", (event.messageId,))
                for x in cc:
                    msg = x[1]
                msg = re.sub('@', '\@', msg)
                await helper.dc_debug_webhook(debug_webhook_link, f'{event.authorId} 撤回了一条消息： {msg}', '[QQ]')
            except Exception:
                traceback.print_exc()


@bcc.receiver("GroupMessage")
async def group_message_handler(app: GraiaMiraiApplication, message: MessageChain, group: Group, member: Member):
    if group.id == target_qqgroup:
        if message.asDisplay() == '$count':
            a = helper.connect_db('./msgid.db').execute('SELECT COUNT(*) as cnt FROM ID').fetchone()
            b = helper.connect_db('./qqmsg.db').execute('SELECT COUNT(*) as cnt FROM MSG').fetchone()
            c = helper.connect_db('./dcname.db').execute('SELECT COUNT(*) as cnt FROM DCNAME').fetchone()
            d = f'''msgid.db:
- ID: {a[0]}
qqmsg.db:
- MSG: {b[0]}
dcname.db:
- DCNAME: {c[0]}'''
            await app.sendGroupMessage(group, MessageChain.create([Plain(d)]))


app.launch_blocking()
