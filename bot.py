import asyncio
import json
import os
import re
import traceback
from datetime import timezone, timedelta
from os.path import abspath

import aiohttp
import eventlet
from discord import AsyncWebhookAdapter
from graia.application import GraiaMiraiApplication, MessageChain, Group, Member
from graia.application.event.mirai import GroupRecallEvent
from graia.application.message.elements.internal import Quote, Source, At, AtAll, Plain, Image, Face, Xml, Json, App, \
    Poke, Voice, FlashImage

import helper
from core.boardcast import bcc, app, c
import discord

config_path = abspath("config/config.cfg")

qq = int(c('qq'))
target_qqgroup = int(c('qqgroup'))
channelid = int(c('dc_channel'))
bottoken = c('dc_bottoken')
font_effect = c('font_effect')
face_link = c('face_link')
webhook_link = c('webhook_link')
serverid = int(c('dc_server'))
debug = c('debug')
if debug == 'True':
    debug = True
if debug == True:
    debug_webhook_link = c('debug_webhook_link')
else:
    debug_webhook_link = None

if font_effect == 'True':
    font_effect = True
else:
    font_effect = False

client = discord.Client()


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    if debug == True:
        await helper.dc_debug_webhook(debug_webhook_link, f'互联机器人已启动。', f'[INFO]')

@client.event
async def on_message(message):
    botfliter = re.match(r'^\[QQ: (.*?)\].*?#0000$', str(message.author))
    if not botfliter:
        print(message)
        if message.channel.id == channelid:
            messages = message.content
            if messages[0:2] != '//':
                await DCsendtoQQ(message, messages)

@client.event
async def on_message_edit(before, after):
    if before.channel.id == channelid:
        if before.id != -1:
            print(before)
            print(after)
            if before.content != after.content:
                messages = after.content
                emojis = re.findall(r'<:.*?:.*?>', messages)
                for emoji in emojis:
                    a = re.match(r'\<:.*?:(.*?)\>', emoji)
                    if a:
                        b = 'https://cdn.discordapp.com/emojis/' + a.group(1)
                        messages = re.sub(emoji, f'[<ImageURL:{b}>]', messages)
                findstrike = re.findall(r'~~.*?~~', messages, re.S)
                for strike in findstrike:
                    matchstrike = re.match(r'~~(.*)~~', strike, re.S).group(1)
                    q = ['']
                    for x in matchstrike:
                        q.append(x)
                    q.append('')
                    strikemsg = '̶'.join(q)
                    messages = re.sub(strike, strikemsg, messages)
                c = helper.connect_db('./msgid.db')
                cc = c.execute(f"SELECT * FROM ID WHERE DCID LIKE '%{str(before.id)}%'")
                for x in cc:
                    msgids = x[1]
                    print(msgids)
                    msgids = msgids.split('|')
                    for y in msgids:
                        if y != str(before.id):
                            try:
                                await app.revokeMessage(y)
                            except Exception:
                                traceback.print_exc()
                c.close()
                await DCsendtoQQ(after, messages, edited=True)

@client.event
async def on_message_delete(message):
    if message.id != -1:
        c = helper.connect_db('./msgid.db')
        cc = c.execute("SELECT * FROM ID WHERE DCID=?", (message.id,))
        for x in cc:
            msgids = x[1]
            msgids = msgids.split('|')
            for msgid in msgids:
                try:
                    await app.revokeMessage(msgid)
                except Exception:
                    continue
        c.close()

@bcc.receiver("GroupRecallEvent")
async def revokeevent(event: GroupRecallEvent):
    print(event)
    try:
        if event.group.id == target_qqgroup:
            dst = {}
            if event.authorId != qq:
                dst['Type'] = 'QQrecall'
            else:
                dst['Type'] = 'QQrecallI'
            dst['MID'] = event.messageId
            dst['UID'] = event.authorId
            j = dst
            if debug:
                print(event.authorId)
                try:
                    c = helper.connect_db('./qqmsg.db')
                    cc = c.execute("SELECT * FROM MSG WHERE ID=?", (event.messageId,))
                    for x in cc:
                        msg = x[1]
                    msg = re.sub('@', '\@', msg)
                    await helper.dc_debug_webhook(debug_webhook_link, f'{event.authorId} 撤回了一条消息： {msg}',
                                                  '[QQ]')
                except Exception:
                    traceback.print_exc()
            if j['Type'] == 'QQrecall':
                channel = client.get_channel(channelid)
                c = helper.connect_db('./msgid.db')
                cc = c.execute(f"SELECT * FROM ID WHERE QQID LIKE '%{j['MID']}%'")
                for x in cc:
                    msgid = x[0]
                try:
                    aa = await channel.fetch_message(msgid)
                    await aa.delete()
                except:
                    traceback.print_exc()
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
    except Exception:
        traceback.print_exc()


async def login_dcbot():
    try:
        await client.login(bottoken)
        await client.connect(reconnect=True)
    finally:
        if not client.is_closed():
            await client.close()

bcc.loop.create_task(login_dcbot())


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
                    Quotet['From'] = 'QQ'
                    try:
                        getnickname = await app.getMember(target_qqgroup, senderId)
                        getnickname = re.sub(r'(\*|_|`|~~)', r'\\\1', getnickname.name)
                        Quotet['Name'] = getnickname
                    except Exception:
                        Quotet['Name'] = senderId
                else:
                    Quotet['From'] = 'Discord'
                    newquotetargetre = re.match(r'(.*?):.*', orginquote)
                    if newquotetargetre:
                        newquotetarget = newquotetargetre.group(1)
                        Quotet['Name'] = newquotetarget
                        orginquote = re.sub(r'.*?:', '', orginquote)
                    else:
                        Quotet['Name'] = ''
                orginquote = re.sub('\r', '\n', orginquote)
                Quotet['MID'] = quote.id
                Quotet['Text'] = orginquote
                try:
                    time = quote.origin[Source][0].time.astimezone(timezone(timedelta(hours=8)))
                except:
                    time = ''
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
                    await helper.dc_debug_webhook(debug_webhook_link,
                                                  f'{member.id} 发送了一条闪照 {flashimage.url}', '[QQ]')
            allmsg = '\n'.join(msglist)
            if debug == True:
                helper.writeqqmsg(message[Source][0].id, allmsg)
            dst['UID'] = str(member.id)
            dst['Name'] = member.name
            dst['MID'] = str(message[Source][0].id)
            dst['Text'] = allmsg
            j = dst
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(20)) as session:
                webhook = discord.Webhook.from_url(webhook_link
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
                    cc = c.execute(f"SELECT * FROM ID WHERE QQID LIKE '%{j['Quote']['MID']}%'")
                    for x in cc:
                        print(x)
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
            await session.close()


async def DCsendtoQQ(message, messages, edited=False):
    emojis = re.findall(r'<:.*?:.*?>', messages)
    for emoji in emojis:
        a = re.match(r'\<:.*?:(.*?)\>', emoji)
        if a:
            b = 'https://cdn.discordapp.com/emojis/' + a.group(1)
            messages = re.sub(emoji, f'[<ImageURL:{b}>]', messages)
    emsglst = []
    for embed in message.embeds:
        ele = embed.to_dict()
        print(ele)
        if 'title' in ele:
            emsglst.append(ele['title'])
        if 'url' in ele:
            emsglst.append(ele['url'])
        if 'fields' in ele:
            for field_value in ele['fields']:
                emsglst.append(field_value['name'] + '\n' + field_value['value'])
        if 'description' in ele:
            emsglst.append(ele['description'])
        if 'footer' in ele:
            emsglst.append(ele['footer']['text'])
        if 'image' in ele:
            emsglst.append(f'[<ImageURL:{ele["image"]["proxy_url"]}>]')
    messages += "\n" + "\n".join(emsglst)
    try:
        matchformat = re.match(r'https://.*?/(.*)', message.attachments[0].proxy_url)
        if matchformat:
            matchformatt = re.match(r'.*\.(.*)', matchformat.group(1))
            if matchformatt:
                imgfmt = ['png', 'gif', 'jpg', 'jpeg', 'webp', 'ico', 'svg']
                if matchformatt.group(1) in imgfmt:
                    messages += f'[<ImageURL:{message.attachments[0].proxy_url}>]'
                else:
                    messages += f'[文件: {message.attachments[0].proxy_url}]'
    except Exception:
        pass
    atfind = re.findall(r'<@!.*>', messages)
    for at in atfind:
        a = re.match(r'<@!(.*)>', at)
        fetch_user = await client.fetch_user(int(a.group(1)))
        messages = re.sub(at, f'@{str(fetch_user)}', messages)
    # strikethrough
    if font_effect:
        findstrike = re.findall(r'~~.*?~~', messages, re.S)
        for strike in findstrike:
            matchstrike = re.match(r'~~(.*)~~', strike, re.S).group(1)
            q = ['']
            for x in matchstrike:
                q.append(x)
            q.append('')
            strikemsg = '̶'.join(q)
            messages = re.sub(strike, strikemsg, messages)
    dst = {}
    dst['Type'] = 'QQ'
    dst['UID'] = str(message.author.id)
    dst['Name'] = str(message.author)
    try:
        if message.author.nick is not None:
            dst['Nick'] = message.author.nick
    except Exception:
        pass
    dst['MID'] = str(message.id)
    if message.reference != None:
        c = helper.connect_db('./msgid.db')
        cc = c.execute(f"SELECT * FROM ID WHERE DCID LIKE '%{message.reference.message_id}%'")
        for x in cc:
            msgids = x[1]
            msgids = msgids.split('|')
            dst['Quote'] = msgids[0]
    dst['Text'] = messages
    j = dst
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
        matat = re.match(r'@\[QQ: (.*?)]', ele)
        if matat:
            msgchain = msgchain.plusWith(MessageChain.create([At(int(matat.group(1)))]))
        else:
            msgchain = msgchain.plusWith(MessageChain.create([Plain(ele)]))
    if edited:
        msgchain = msgchain.plusWith(MessageChain.create([Plain('（已编辑）')]))
    try:
        async def sendmsg(j, msgchain):
            textre = re.findall(r'\[<.*?:.*?>]', j['Text'])
            for elements in textre:
                a = re.match(r'\[\<ImageURL:(.*)\>\]', elements)
                if a:
                    msgchain = msgchain.plusWith(msgchain.create(
                        [Image.fromNetworkAddress(url=a.group(1))]))
            sendmsg = await app.sendGroupMessage(target_qqgroup, msgchain,
                                                 quote=j['Quote'] if 'Quote' in j else None)
            msgid = str(sendmsg.messageId)
            if debug == True:
                helper.writeqqmsg(msgid, j['Text'])
            return msgid

        try:
            with eventlet.Timeout(15):
                msgid = await sendmsg(j, msgchain)
        except eventlet.timeout.Timeout:
            raise TimeoutError
    except (TimeoutError, Exception):
        traceback.print_exc()
        sendmsg = await app.sendGroupMessage(target_qqgroup, msgchain,
                                             quote=j['Quote'] if 'Quote' in j else None)
        msgid = str(sendmsg.messageId)
        textre = re.findall(r'\[<.*?:.*?>]', j['Text'])
        try:
            for elements in textre:
                a = re.match(r'\[\<ImageURL:(.*)\>\]', elements)
                if a:
                    msgchain2 = msgchain.create(
                        [Image.fromNetworkAddress(url=a.group(1))])
                    sendimg = await app.sendGroupMessage(target_qqgroup, msgchain2,
                                                         quote=j['Quote'] if 'Quote' in j else None)
                    msgid += f'|{sendimg.messageId}'
                    if debug == True:
                        helper.writeqqmsg(msgid, a.group(1))
        except Exception:
            traceback.print_exc()
    helper.writeid(j['MID'], msgid)


@bcc.receiver("GroupMessage")
async def group_message_handler(app: GraiaMiraiApplication, message: MessageChain, group: Group, member: Member):
    if group.id == target_qqgroup:
        if message.asDisplay() == '$count':
            a = helper.connect_db('../msgid.db').execute('SELECT COUNT(*) as cnt FROM ID').fetchone()
            a1 = round(os.path.getsize('../msgid.db') / float(1024 * 1024), 2)
            b = helper.connect_db('../qqmsg.db').execute('SELECT COUNT(*) as cnt FROM MSG').fetchone()
            b1 = round(os.path.getsize('../qqmsg.db') / float(1024 * 1024), 2)
            c = helper.connect_db('../dcname.db').execute('SELECT COUNT(*) as cnt FROM DCNAME').fetchone()
            c1 = round(os.path.getsize('../dcname.db') / float(1024 * 1024), 2)
            d = f'''msgid.db({a1}MB):
- ID: {a[0]}
qqmsg.db({b1}MB):
- MSG: {b[0]}
dcname.db({c1}MB):
- DCNAME: {c[0]}'''
            await app.sendGroupMessage(group, MessageChain.create([Plain(d)]))
        if message.asDisplay() == '谁At我':
            try:
                if debug == True:
                    a = helper.connect_db('../qqmsg.db').execute(f"SELECT ID, MSG FROM MSG WHERE MSG LIKE '%{'@[QQ: ' + str(member.id) + ']'}%'").fetchall()[-1]
                    print(a[0])
                    await app.sendGroupMessage(group, MessageChain.create([Plain('This.')]), quote=int(a[0]))
            except Exception:
                await app.sendGroupMessage(group, MessageChain.create([Plain('无法定位。')]))


app.launch_blocking()
