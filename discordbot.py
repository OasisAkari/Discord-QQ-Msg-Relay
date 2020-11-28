import asyncio
import json
import re
import traceback
from configparser import ConfigParser
from os.path import abspath
import discord
import helper
import websockets

client = discord.Client()

cp = ConfigParser()
cp.read(abspath("./config.cfg"))
section = cp.sections()[0]
channelid = int(cp.get(section, 'dc_channel'))
bottoken = cp.get(section, 'dc_bottoken')
websocket_port = cp.get(section, 'websocket_port')
debug = cp.get(section, 'debug')
if debug == 'True':
    debug = True
if debug == True:
    debug_webhook_link = cp.get(section, 'debug_webhook_link')
else:
    debug_webhook_link = None


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    if debug == True:
        await helper.dc_debug_webhook(debug_webhook_link, f'互联DC侧机器人已启动。', f'[INFO] DCBOT')


@client.event
async def on_message(message):
    botfliter = re.match(r'^\[QQ: (.*?)\].*?#0000$', str(message.author))
    if not botfliter:
        print(message)
        if message.channel.id == channelid:
            async with websockets.connect('ws://127.0.0.1:' + websocket_port) as websocket:
                messages = message.content
                if messages[0:2] != '//':
                    emojis = re.findall(r'<:.*?:.*?>', messages)
                    for emoji in emojis:
                        a = re.match(r'\<:.*?:(.*?)\>', emoji)
                        if a:
                            b = 'https://cdn.discordapp.com/emojis/' + a.group(1)
                            messages = re.sub(emoji, f'[<ImageURL:{b}>]', messages)
                    emsglst = []
                    for embed in message.embeds:
                        ele = embed.to_dict()
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
                    dst['Text'] = messages
                    print(dst)
                    j = json.dumps(dst)
                    await websocket.send(j)


@client.event
async def on_connect():
    while True:
        try:
            async with websockets.connect('ws://127.0.0.1:' + websocket_port) as websocket:
                while True:
                    try:
                        recv_text = await websocket.recv()
                        j = json.loads(recv_text)
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
                                continue
                    except websockets.exceptions.ConnectionClosedError:
                        traceback.print_exc()
                        await websocket.close()
                        break
                    except Exception:
                        traceback.print_exc()
                await asyncio.sleep(5)
        except Exception:
            traceback.print_exc()
            await asyncio.sleep(5)


@client.event
async def on_message_delete(message):
    if message.id != -1:
        dst = {}
        dst['Type'] = 'DCdelete'
        dst['MID'] = message.id
        j = json.dumps(dst)
        await helper.sendtoWebsocket(websocket_port, j)


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
                dst = {}
                dst['Type'] = 'QQrecallD'
                dst['UID'] = str(before.author.id)
                dst['Name'] = str(before.author)
                try:
                    if before.author.nick is not None:
                        dst['Nick'] = before.author.nick
                except AttributeError:
                    pass
                dst['MID'] = before.id
                dst['Text'] = messages + '\n（已编辑）'
                j = json.dumps(dst)
                await helper.sendtoWebsocket(websocket_port, j)
                dst['Type'] = 'QQ'
                j = json.dumps(dst)
                await helper.sendtoWebsocket(websocket_port, j)



client.run(bottoken)
