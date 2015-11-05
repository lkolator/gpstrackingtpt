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

config = {
        'htr': '1',
        'str': '1',
        'tpr': '1',
        'pho': '+48509386813'
        }

cfg = {'cfg': '0'}

app = Flask(__name__)


def random_config():
    config['tpr'] = str(random.randint(0, 1))


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
        return "\n".join([str(record) for record in db.dump_all()])


class DeviceHandler(MethodView):
    def get(self, device_id):
        if 'UBLOX-HttpClient' not in request.headers.get('User-Agent'):
            record = db.dump(device_id)
            print record
            if not record:
                return "Not available"
            return render_template('maps.html', dev=device_id, lat=record[0][4],
                                    lon=record[0][5], flg=record[0][3])
        if device_id == '6292497':
            config['pho'] = '+48509386813'
        else:
            config['pho'] = '+48692434624'
        return Response(json.dumps(config),  mimetype='application/json')

    def post(self, device_id):
        try:
            print request.data
            data = json.loads(request.data, cls=Decoder)
            try:
                results = Geocoder.reverse_geocode(data['lat'], data['lon'])
            except:
                results = "Not available"
            print results
            db.insert(device_id, data['utc'], data['flg'], data['lat'], data['lon'])
            return Response(json.dumps(cfg),  mimetype='application/json')
        except:
            return "Failed"


app.add_url_rule('/', view_func=Main.as_view('main'))
app.add_url_rule('/<string:device_id>', view_func=DeviceHandler.as_view('devicehandler'))

if __name__ == '__main__':
    # app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    app.run(debug=True, host='0.0.0.0', port=8111)
