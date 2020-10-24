import discord
import websockets
import re
import asyncio
from configparser import ConfigParser
from os.path import abspath
client = discord.Client()

cp = ConfigParser()
cp.read(abspath("./config.cfg"))
section = cp.sections()[0]
channelid = int(cp.get(section, 'dcchannel'))
bottoken = cp.get(section, 'dcbottoken')

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    print(message)
    print(message.channel.id)
    print(message.author)
    botfliter = re.match(r'^\[QQ: (.*?)\].*?#0000$', str(message.author))
    if not botfliter:
        if message.channel.id == channelid:
            async with websockets.connect('ws://127.0.0.1:'+cp.get(section, 'websocketport2')) as websocket:
                messages = message.content
                if messages[0:2] != '//':
                    print(messages[0:2])
                    emojis = re.findall(r'<:.*?:.*?>', messages)
                    print(emojis)
                    for emoji in emojis:
                        a = re.match(r'\<:.*?:(.*?)\>',emoji)
                        print(a.group(1))
                        if a:
                            b = 'https://cdn.discordapp.com/emojis/'+a.group(1)
                            messages = re.sub(emoji, f'[<ImageURL:{b}>]',messages)
                    print(messages)
                    for embed in message.embeds:
                        messages += embed
                    try:
                        messages += f'[<ImageURL:{message.attachments[0].proxy_url}>]'
                    except Exception:
                        pass
                    await websocket.send(f'{message.author}: {messages}')
asyncio.create_task(client.run(bottoken))