import sqlite3

DBNAME="tracker.db"
TNAME="trackdata"
CNAME="configdata"

class TrackerDatabase(object):
    def __init__(self, dbname = DBNAME, tname = TNAME, cname = CNAME):
        self.cname = cname
        self.tname = tname
        self.dbname = dbname
        self.conn = sqlite3.connect(self.dbname)
        cur = self.conn.cursor()
        cur.execute('create table if not exists ' + self.tname +
                '(id INTEGER PRIMARY KEY AUTOINCREMENT, \
                        addtime DATETIME, \
                        recordtime INTEGER, \
                        flags TEXT, \
                        latitude REAL, \
                        longitude REAL, \
                        device INTEGER \
                        );')
        cur.execute('create table if not exists ' + self.cname +
                   '(   addtime DATETIME, \
                        httptracking TEXT, \
                        smstracking TEXT, \
                        period TEXT, \
                        phone TEXT, \
                        new INTEGER, \
                        device INTEGER PRIMARY KEY \
                        );')

    def insert(self, device, rectime, flags, lat, lon):
        cur = self.conn.cursor()
        cur.execute('insert into ' + self.tname +
                    '(addtime, device, recordtime, flags, latitude, longitude) \
                    values(DateTime(\'now\'), ?, ?, ?, ?, ?);', (device, rectime, flags, lat, lon))
        self.conn.commit()

    def dump(self, device, records=1):
        cur = self.conn.cursor()
        return [row for row in cur.execute('select * from ' + self.tname +
                ' where device like ? order by id desc limit ? ;', (device, records))]

    def dump_all(self):
        cur = self.conn.cursor()
        return [row for row in cur.execute('select * from ' + self.tname + ';')]

    def drop(self):
        cur = self.conn.cursor()
        cur.execute('drop table if exists ' + self.tname + ';')

    def update(self, device, htr, str, tpr, pho):
        cur = self.conn.cursor()
        cur.execute('insert or replace into ' + self.cname +
                    '(addtime, device, httptracking, smstracking, period, phone, new) \
                    values(DateTime(\'now\'), ?, ?, ?, ?, ?, 1);', (device, htr, str, tpr, pho))
        self.conn.commit()

    def dump_config(self, device):
        cur = self.conn.cursor()
        cur.execute('select httptracking, smstracking, period, phone from ' +
                    self.cname + ' where device=?;', (device,))
        cfg = cur.fetchone()
        cur.execute('insert or replace into ' + self.cname +
                    '(addtime, device, httptracking, smstracking, period, phone, new) \
                    values(DateTime(\'now\'), ?, "", "", "", "", 0);', (device,))
        self.conn.commit()
        return cfg

    def is_config(self, device):
        cur = self.conn.cursor()
        cur.execute('select new from ' + self.cname + ' where device=?;', (device,))
        return bool(cur.fetchone()[0])

    def __str__(self):
        return "Tracker db: " + self.dbname + "(" + self.tname + ")"
