import sqlite3
import json
from geopy.distance import great_circle

DBNAME="tracker.db"
TNAME="trackdata"
CNAME="configdata"

def date_filter(data, d):
    for el in data:
        if el[1].startswith(d): yield el

def distance_filter(data, distance=5.0):
    yield data[0]
    last = data[0]
    for i in range(1, len(data) - 1):
        if great_circle(data[i], last).meters > distance:
            last = data[i]
            yield last

def route_to_dict(route):
    return [{'lat': lat, 'lng': lng} for lat, lng in route]

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
                        new TEXT, \
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

    def geo_by_date(self, device, date):
        return [(d[4], d[5]) for d in date_filter(self.dump(device, -1), date)]

    def drop(self):
        cur = self.conn.cursor()
        cur.execute('drop table if exists ' + self.tname + ';')

    def update(self, device, htr, str, tpr, pho):
        cur = self.conn.cursor()
        cur.execute('insert or replace into ' + self.cname +
                    '(addtime, device, httptracking, smstracking, period, phone, new) \
                    values(DateTime(\'now\'), ?, ?, ?, ?, ?, "1");', (device, htr, str, tpr, pho))
        self.conn.commit()

    def dump_config(self, device):
        cur = self.conn.cursor()
        cur.execute('select httptracking, smstracking, period, phone from ' +
                    self.cname + ' where device=?;', (device,))
        cfg = cur.fetchone()
        cur.execute('insert or replace into ' + self.cname +
                    '(addtime, device, httptracking, smstracking, period, phone, new) \
                    values(DateTime(\'now\'), ?, "", "", "", "", "0");', (device,))
        self.conn.commit()
        return cfg

    def get_last(self, device):
        cur = self.conn.cursor()
        cur.execute('select * from trackdata where id=(select max(id) from trackdata where device is ' + str(device) + ')')
        return cur.fetchone()

    def get_dates(self, device):
        cur = self.conn.cursor()
        cur.execute('select addtime from trackdata where device is ' + str(device))
        return sorted(set([dt[0].split()[0] for dt in cur.fetchall()]))

    def get_sns(self):
        cur = self.conn.cursor()
        cur.execute('select distinct device from trackdata')
        return [d[0] for d in cur.fetchall()]

    def is_config(self, device):
        cur = self.conn.cursor()
        cur.execute('select new from ' + self.cname + ' where device=?;', (device,))
        try:
            retval = cur.fetchone()[0]
        except:
            retval = '0'
        return retval

    def __str__(self):
        return "Tracker db: " + self.dbname + "(" + self.tname + ")"

class Integrity(object):
    def __init__(self, name, mask_current=0x0000, mask_historical=0x0000):
        self.name = name
        self.h = mask_historical
        self.c = mask_current

    def has_current(self):
        return self.c != 0

    def has_historical(self):
        return self.h != 0

    def test_current(self, flags):
        if self.has_current() is False:
            return None
        return (self.c & flags) != 0

    def test_historical(self, flags):
        if self.has_historical() is False:
            return None
        return (self.h & flags) != 0

class IntegrityList(object):
    def __init__(self, l):
        self.l = l

    def test(self, flags):
        return [(i.name, i.test_current(flags), i.test_historical(flags)) for i in self.l]

    def to_dict(self, flags):
        d = {}
        for integ, c, h in self.test(flags):
            if c is not None:
                d[integ + "-CURRENT"] = c
            if h is not None:
                d[integ + "-HISTORICAL"] = h

        return d 

integlist = IntegrityList([
    Integrity('Power', 0x8000),
    Integrity('Casing', 0x4000, 0x2000),        
    Integrity('Strap', 0x1000, 0x0800),
    Integrity('Hardware', 0x0000, 0x0400)
])
