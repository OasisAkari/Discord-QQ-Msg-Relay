import asyncio
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
                    messages = f'{message.author}: {messages}'
                    await websocket.send(f'[QQ][{message.id}]' + messages)
import websockets
@client.event
async def on_connect():
    async with websockets.connect('ws://127.0.0.1:' + websocket_port) as websocket:
        while True:
            recv_text = await websocket.recv()
            try:
                channel = client.get_channel(channelid)
                mch = re.match(r'\[(.*?)\](.*)', recv_text, re.S)
                if mch:
                    if mch.group(1) == 'QQrecall':
                        dbpath = os.path.abspath('./msgdb.db')
                        conn = sqlite3.connect(dbpath)
                        c = conn.cursor()
                        cc = c.execute("SELECT * FROM ID WHERE QQID=?", (mch.group(2),))
                        for x in cc:
                            msgid = x[0]
                        try:
                            aa = await channel.fetch_message(msgid)
                            print(aa)
                            await aa.delete()
                        except:
                            continue
            except Exception:
                traceback.print_exc()

@client.event
async def on_message_delete(message):
    async with websockets.connect('ws://127.0.0.1:' + websocket_port) as websocket:
        await websocket.send(f'[DCdelete]{message.id}')

asyncio.create_task(client.run(bottoken))
