import sqlite3

DBNAME="tracker.db"
TNAME="trackdata"

class TrackerDatabase(object):
    def __init__(self, dbname = DBNAME, tname = TNAME):
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

    def insert(self, device, rectime, flags, lat, lon):
        cur = self.conn.cursor()
        cur.execute('insert into ' + self.tname +
                    '(addtime, device, recordtime, flags, latitude, longitude) \
                    values(DateTime(\'now\'), ' +
                    str(device) + ', ' + str(rectime) + ', ' + str(flags) +
                    ', ' + str(lat) + ', ' + str(lon) + ');')
        self.conn.commit()

    def dump(self, device, records=1):
        cur = self.conn.cursor()
        return [row for row in cur.execute('select * from ' + self.tname +
                ' where device like ' + str(device) + ' order by id desc' +
                ' limit ' + str(records) + ';')]

    def dump_all(self):
        cur = self.conn.cursor()
        return [row for row in cur.execute('select * from ' + self.tname + ';')]

    def __str__(self):
        return "Tracker db: " + self.dbname + "(" + self.tname + ")"
