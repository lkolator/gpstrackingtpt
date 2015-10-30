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
                        flags INTEGER, \
                        position STRING \
                        )')

    def insert(self, rectime, flags, pos):
        cur = self.conn.cursor()
        cur.execute('insert into ' + self.tname +
                '(addtime, recordtime, flags, position) \
                        values(DateTime(\'now\'), ' +
                        str(rectime) + ', ' + str(flags) + ", \'" + pos + '\')')
        self.conn.commit()

    def dump(self):
        cur = self.conn.cursor()
        return [row for row in cur.execute('select * from ' + self.tname)]

    def __str__(self):
        return "Tracker db: " + self.dbname + "(" + self.tname + ")"
