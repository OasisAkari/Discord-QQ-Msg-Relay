import os
import sqlite3

def writeid(dcmsgid, qqmsgid):
    dbpath = os.path.abspath('./msgdb.db')
    if not os.path.exists(dbpath):
        createdb = open(dbpath,'w')
        createdb.close()
        conn = sqlite3.connect(dbpath)
        c = conn.cursor()
        c.execute('''CREATE TABLE ID
               (DCID TEXT PRIMARY KEY     NOT NULL,
               QQID           TEXT    NOT NULL);''')
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    c.execute("INSERT INTO ID (DCID, QQID) VALUES (?, ?)", (dcmsgid, qqmsgid))
    conn.commit()

def writeqqmsg(msgid, msg):
    dbpath = os.path.abspath('./qqmsg.db')
    if not os.path.exists(dbpath):
        createdb = open(dbpath,'w')
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
        createdb = open(dbpath,'w')
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