import os
import sqlite3

dbpath = os.path.abspath('./msgid.db')
createdb = open(dbpath, 'w')
createdb.close()
conn = sqlite3.connect(dbpath)
d = conn.cursor()
d.execute('''CREATE TABLE ID
       (DCID TEXT PRIMARY KEY     NOT NULL,
       QQID           TEXT    NOT NULL);''')
d.close()

dbpath = os.path.abspath('./qqmsg.db')
createdb = open(dbpath, 'w')
createdb.close()
conn = sqlite3.connect(dbpath)
c = conn.cursor()
c.execute('''CREATE TABLE MSG
       (ID TEXT PRIMARY KEY     NOT NULL,
       MSG           TEXT    NOT NULL);''')
c.close()

dbpath = os.path.abspath('./dcname.db')
createdb = open(dbpath, 'w')
createdb.close()
conn = sqlite3.connect(dbpath)
c = conn.cursor()
c.execute('''CREATE TABLE DCNAME
       (NAME TEXT PRIMARY KEY     NOT NULL,
       ID           TEXT    NOT NULL);''')
c.close()