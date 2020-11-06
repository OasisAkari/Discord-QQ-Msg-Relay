import asyncio
import json
import os
import re
import sqlite3
import traceback
from configparser import ConfigParser
from os.path import abspath

import aiohttp
import discord
import websockets
from discord import Webhook, AsyncWebhookAdapter

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

def connect_db(path):
    dbpath = os.path.abspath(path)
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    return c

async def dc_debug_webhook(message, username, avatar_url=None):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(5)) as session:
        webhook = Webhook.from_url(debug_webhook_link
                                   ,
                                   adapter=AsyncWebhookAdapter(session))
        await webhook.send(message, username=username,
                           avatar_url=avatar_url)


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    if debug == True:
        await dc_debug_webhook(f'互联DC侧机器人已启动。', f'[INFO] DCBOT')


@client.event
async def on_message(message):
    botfliter = re.match(r'^\[QQ: (.*?)\].*?#0000$', str(message.author))
    if not botfliter:
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
                                emsglst.append(field_value['name'] + field_value['value'])
                        if 'description' in ele:
                            emsglst.append(ele['description'])
                        if 'footer' in ele:
                            emsglst.append(ele['footer']['text'])
                        if 'image' in ele:
                            emsglst.append(f'[<ImageURL:{ele["image"]["proxy_url"]}>]')
                    messages += "\n".join(emsglst)
                    try:
                        messages += f'[<ImageURL:{message.attachments[0].proxy_url}>]'
                    except Exception:
                        pass
                    dst = {}
                    dst['Type'] = 'QQ'
                    dst['UID'] = str(message.author.id)
                    dst['Name'] = str(message.author)
                    if message.author.nick is not None:
                        dst['Nick'] = message.author.nick
                    dst['MID'] = str(message.id)
                    dst['Text'] = messages
                    print(dst)
                    j = json.dumps(dst)
                    await websocket.send(j)
import websockets
@client.event
async def on_connect():
    await connectws()

async def connectws():
    while True:
        try:
            async with websockets.connect('ws://127.0.0.1:' + websocket_port) as websocket:
                while True:
                    try:
                        recv_text = await websocket.recv()
                        j = json.loads(recv_text)
                        if j['Type'] == 'QQrecall':
                            channel = client.get_channel(channelid)
                            c = connect_db('./msgdb.db')
                            cc = c.execute("SELECT * FROM ID WHERE QQID=?", (j['MID'],))
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
        async with websockets.connect('ws://127.0.0.1:' + websocket_port) as websocket:
            dst = {}
            dst['Type'] = 'DCdelete'
            dst['MID'] = message.id
            j = json.dumps(dst)
            await websocket.send(j)
            await websocket.close()

asyncio.create_task(client.run(bottoken))
