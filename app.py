from datetime import timedelta
from flask import Flask
from flask import request, safe_join, session, app, g
from flask import Response, render_template, send_from_directory
from flask.views import MethodView
from pygeocoder import Geocoder
import json
import os
import time
import random
from model import TrackerDatabase

app = Flask(__name__)

db = TrackerDatabase()

CFG_PARAM = ('htr', 'str', 'tpr', 'pho')
FLGS = ('power', 'casing', 'casing_h', 'strap', 'strap_h', 'hardware')
# "{"srn":"00000000","lat":"00000.00000X","lon":"00000.00000X","utc":"000000.00","acc":"00000","flg":"0000"}";
# htr - HTTP tracking; 0 - off, 1 - on
# str - SMS tracking; 0 - off, 1 - on
# tpr - tracking period; 0 - 15s, 1 - 1min, 2 - 5min, 3 - 30min
# pho - SMS reporting phone number; variable field length (?), must be '\0'
# terminated
# www - HTTP reporting address; variable field length (?), must be '\0'
# terminated
# prt - HTTP reporting port number
# {"srn":"00000000","htr":"X","str":"X","tpr":""X","pho":"+000000000000","www":"0000000000000000000000000000000000000000","prt":"00000"}"

app = Flask(__name__)


def prepare_config(record):
    config = {}
    for name, val in zip(CFG_PARAM, record):
        if val:
            config[name] = val
    return config


def prepare_form(config):
    record = dict.fromkeys(CFG_PARAM)
    if 'htrAct' in config.keys() and 'htr' not in config.keys():
        config.update({'htr':'0'})
    if 'strAct' in config.keys() and 'str' not in config.keys():
        config.update({'str':'0'})
    for key in config.keys():
        if record.has_key(key):
            record[key] = config[key]
    return record


def parse_flags(flags):
    flgs = {}
    masks = (0x8000, 0x4000, 0x2000, 0x1000, 0x0800, 0x0400)
    for flg, msk in zip(FLGS, masks):
        flgs[flg] = flags & msk
    return flgs


class Decoder(json.JSONDecoder):
    def _convert_coord(self, lat, lon):
        if lat[2] == '.' and lon[2] == '.':
            lat, lon = float(lat), float(lon)
        else:
            lat_coord = int(lat[:3]) + float(lat[3:len(lat) - 1])/60
            lon_coord = int(lon[:3]) + float(lon[3:len(lon) - 1])/60
        if lat[-1] == 'S':
            lat_coord = -lat_coord
        if lon[-1] == 'W':
            lon_coord = -lon_coord
        return lat_coord, lon_coord

    def decode(self, obj):
        obj = obj.replace('\x27', '\x22')
        data = json.JSONDecoder.decode(self, obj)
        data['lat'], data['lon'] = self._convert_coord(data['lat'], data['lon'])
        return data


class Decoder2(json.JSONDecoder):
    def decode(self, obj):
        obj = obj.replace('\x27', '\x22')
        return json.JSONDecoder.decode(self, obj)


class Main(MethodView):
    def get(self):
        #return 'OK'
        #db.drop()
        return "\n".join([str(record) for record in db.dump_all()])


class DeviceHandler(MethodView):
    def get(self, device_id):
        if 'UBLOX-HttpClient' not in request.headers.get('User-Agent'):
            record = db.dump(device_id)
            if not record:
                return "Not available"
            flags = parse_flags(int(record[0][3], base=16))
            return render_template('maps.html', dev=device_id, lat=record[0][4],
                                    lon=record[0][5], flags=flags)
        config = prepare_config(db.dump_config(device_id))
        return Response(json.dumps(config),  mimetype='application/json')

    def post(self, device_id):
        try:
            if 'UBLOX-HttpClient' not in request.headers.get('User-Agent'):
                rec = prepare_form(request.form.to_dict())
                db.update(device_id, rec['htr'], rec['str'], rec['tpr'], rec['pho'])
                return "OK"
            data = json.loads(request.data, cls=Decoder)
            try:
                results = Geocoder.reverse_geocode(data['lat'], data['lon'])
            except:
                results = "Not available"
            print results
            db.insert(device_id, data['utc'], data['flg'], data['lat'], data['lon'])
            cfg = dict.fromkeys(['cfg'], db.is_config(device_id))
            return Response(json.dumps(cfg),  mimetype='application/json')
        except:
            return "Failed"


app.add_url_rule('/', view_func=Main.as_view('main'))
app.add_url_rule('/<string:device_id>', view_func=DeviceHandler.as_view('devicehandler'))

if __name__ == '__main__':
    # app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    app.run(debug=True, host='0.0.0.0', port=8111)
