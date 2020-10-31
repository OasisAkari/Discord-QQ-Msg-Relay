import asyncio
import re
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
            try:
                if debug == True:
                    await dc_debug_webhook(
                        f'从频道{message.channel.id}中接收到一条消息：`{message.author}: {message.content + str(message.embeds)}`，开始消息链转换。',
                        f'[INFO] {message.channel.id}')
                async with websockets.connect('ws://127.0.0.1:' + websocket_port) as websocket:
                    messages = message.content
                    if messages[0:2] != '//':
                        print(messages[0:2])
                        emojis = re.findall(r'<:.*?:.*?>', messages)
                        print(emojis)
                        for emoji in emojis:
                            a = re.match(r'\<:.*?:(.*?)\>', emoji)
                            print(a.group(1))
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
                        try:
                            messages = f'{message.author}: {messages}'
                            await websocket.send('[QQ]'+messages)
                            if debug == True:
                                await dc_debug_webhook(
                                    f'成功发送一条消息到Websocket_QQ：{messages}', f'[OK] DCChannel -> Websocket_QQ')
                        except Exception as e:
                            if debug == True:
                                await dc_debug_webhook(f'`{str(message)}`发送时抛出了错误：\n{str(e)}',
                                                       f'[ERROR] DCChannel -x Websocket_QQ',
                                                       avatar_url='https://discordapp.com/assets/8becd37ab9d13cdfe37c08c496a9def3.svg')
                    else:
                        await dc_debug_webhook(
                            '此消息触发转发过滤，已过滤',
                            f'[INFO] {message.channel.id}')
            except Exception as e:
                traceback.print_exc()
                if debug == True:
                    await dc_debug_webhook(f'`执行操作时抛出了错误：\n{str(e)}',
                                           f'[ERROR] DCChannel',
                                           avatar_url='https://discordapp.com/assets/8becd37ab9d13cdfe37c08c496a9def3.svg')


asyncio.create_task(client.run(bottoken))
