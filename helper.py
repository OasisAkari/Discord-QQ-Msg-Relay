import os
import sqlite3
import traceback

import aiohttp
from discord import Webhook, AsyncWebhookAdapter
import websockets
import eventlet

def writeid(dcmsgid, qqmsgid):
    dbpath = os.path.abspath('./msgid.db')
    if not os.path.exists(dbpath):
        createdb = open(dbpath, 'w')
        createdb.close()
        conn = sqlite3.connect(dbpath)
        c = conn.cursor()
        c.execute('''CREATE TABLE ID
               (DCID TEXT PRIMARY KEY     NOT NULL,
               QQID           TEXT    NOT NULL);''')
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO ID (DCID, QQID) VALUES (?, ?)", (dcmsgid, qqmsgid))
    except Exception:
        c.execute("DElETE FROM ID WHERE DCID=?", (dcmsgid,))
        c.execute("DElETE FROM ID WHERE QQID=?", (qqmsgid,))
        c.execute("INSERT INTO ID (DCID, QQID) VALUES (?, ?)", (dcmsgid, qqmsgid))
    conn.commit()


def delid(qqmsgid):
    dbpath = os.path.abspath('./msgid.db')
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    c.execute("DElETE FROM ID WHERE QQID=?", (qqmsgid,))
    conn.commit()

def writeqqmsg(msgid, msg):
    dbpath = os.path.abspath('./qqmsg.db')
    if not os.path.exists(dbpath):
        createdb = open(dbpath, 'w')
        createdb.close()
        conn = sqlite3.connect(dbpath)
        c = conn.cursor()
        c.execute('''CREATE TABLE MSG
               (ID TEXT PRIMARY KEY     NOT NULL,
               MSG           TEXT    NOT NULL);''')
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    c.execute("INSERT INTO MSG (ID, MSG) VALUES (?, ?)", (msgid, msg))
    conn.commit()


def writedcuser(dcname, id):
    dbpath = os.path.abspath('./dcname.db')
    if not os.path.exists(dbpath):
        createdb = open(dbpath, 'w')
        createdb.close()
        conn = sqlite3.connect(dbpath)
        c = conn.cursor()
        c.execute('''CREATE TABLE DCNAME
               (NAME TEXT PRIMARY KEY     NOT NULL,
               ID           TEXT    NOT NULL);''')
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO DCNAME (NAME, ID) VALUES (?, ?)", (dcname, id))
    except Exception:
        c.execute("DElETE FROM DCNAME WHERE NAME =?", (dcname,))
        c.execute("INSERT INTO DCNAME (NAME, ID) VALUES (?, ?)", (dcname, id))
    conn.commit()


def connect_db(path):
    dbpath = os.path.abspath(path)
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    return c


async def dc_debug_webhook(debug_webhook_link, message, username, avatar_url=None):
    eventlet.monkey_patch()
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(15)) as session:
            webhook = Webhook.from_url(debug_webhook_link
                                       ,
                                       adapter=AsyncWebhookAdapter(session))
            await webhook.send(message, username=username,
                               avatar_url=avatar_url)
        await session.close()
    except eventlet.TimeoutError:
        traceback.print_exc()


async def sendtoWebsocket(websocket_port, text):
    eventlet.monkey_patch()
    try:
        with eventlet.Timeout(15):
            async with websockets.connect('ws://127.0.0.1:' + websocket_port) as websocket:
                await websocket.send(text)
                await websocket.close()
    except eventlet.TimeoutError:
        traceback.print_exc()