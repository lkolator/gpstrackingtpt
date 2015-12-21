from datetime import timedelta
from flask import Flask
from flask import request, safe_join, session, app, g
from flask import Response, render_template, send_from_directory
from flask_socketio import SocketIO, emit
from flask.views import MethodView
from model import TrackerDatabase, integlist, route_to_dict, distance_filter, zero_pos_filter
import json
import os
import time
import random
import sys

app = Flask(__name__)

CFG_PARAM = ('htr', 'str', 'tpr', 'pho', 'mod')
FLGS = ('power', 'casing', 'casing_h', 'strap', 'strap_h', 'hardware')

app = Flask(__name__)
socketio = SocketIO(app, async_mode='gevent')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = TrackerDatabase()

    return db

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

class Decoder(json.JSONDecoder):
    def _convert_coord(self, lat, lon):
        if lat[2] == '.' and lon[2] == '.':
            lat_coord, lon_coord = float(lat[:-1]), float(lon[:-1])
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

class Dump(MethodView):
    def get(self):
        return "<br>\n".join([str(record) for record in get_db().dump_all()])


class Index(MethodView):
    def get(self):
        return render_template('index.html', devices=get_db().get_sns())


class DeviceHandler(MethodView):
    def get(self, device_id):
        if 'UBLOX-HttpClient' not in request.headers.get('User-Agent'):
            lat = 0.0
            lon = 0.0
            lastrecord = get_db().get_last(device_id)
            if lastrecord is None:
                return "No such device"
            try:
                posrecord = [d for d in zero_pos_filter(get_db().dump(device_id, -1))][-1]
                lat = float(posrecord[4])
                lon = float(posrecord[5])
            except:
                pass

            dates = get_db().get_dates(device_id)
            dates.reverse()
            return render_template('maps.html',
                    dev=device_id,
                    lat=lat,
                    lon=lon,
                    integrity=integlist.l,
                    dates=dates)
        config = prepare_config(get_db().dump_config(device_id))
        return Response(json.dumps(config),  mimetype='application/json')

    def post(self, device_id):
        try:
            if 'UBLOX-HttpClient' not in request.headers.get('User-Agent'):
                rec = prepare_form(request.form.to_dict())
                get_db().update(device_id, rec['htr'], rec['str'], rec['tpr'], rec['pho'], rec['mod'])
                return "OK"
            data = json.loads(request.data, cls=Decoder)

            # insert data and change pos if not zero
            get_db().insert(device_id, data['utc'], data['flg'], data['lat'], data['lon'])
            if float(data['lat']) != 0.0 and float(data['lon']) != 0.0:
                socketio.emit('newpos', {'lat': float(data['lat']), 'lng': float(data['lon'])}, namespace='/' + str(device_id))

            # update integrity status
            socketio.emit('integrity', integlist.to_dict(int(data['flg'], 16)), namespace='/' + str(device_id))

            cfg = dict.fromkeys(['cfg'], get_db().is_config(device_id))
            return Response(json.dumps(cfg),  mimetype='application/json')
        except Exception as e:
            print e
            return "Failed"

def emit_route(dp, devid):
    data = get_db().geo_by_date(devid, dp)
    route = route_to_dict([r for r in distance_filter(data)])
    emit('route', {'positions': route}, namespace='/' + str(devid))

@socketio.on('new connection')
def io_newconn(args):
    devid = int(args['device'])

    data = get_db().get_last(devid)
    if data is None:
        return
    last_date = get_db().get_dates(devid)[-1]

    print "Refreshing state of... " + str(devid)
    i, addtime, rectime, flags, lat, lon,_ = data

    emit('integrity', integlist.to_dict(int(flags, 16)), namespace='/' + str(devid))
    emit_route(last_date, devid)

@socketio.on('datepick')
def io_datepick(args):
    devid = int(args['device'])
    dp = args['dp']
    emit_route(dp, devid)

app.add_url_rule('/', view_func=Index.as_view('index'))
app.add_url_rule('/dump', view_func=Dump.as_view('dump'))
app.add_url_rule('/<int:device_id>', view_func=DeviceHandler.as_view('devicehandler'))


if __name__ == '__main__':
    if len(sys.argv) == 2:
        port = int(sys.argv[1])
    else:
        port = int(os.environ.get("PORT", 8111))

    # app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    socketio.run(app, debug=True, host='0.0.0.0', port=port)
