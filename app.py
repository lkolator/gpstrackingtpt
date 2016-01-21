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

reg_b = re.compile(r"(android|bb\\d+|meego).+mobile|avantgo|bada\\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|mobile.+firefox|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\\.(browser|link)|vodafone|wap|windows ce|xda|xiino", re.I|re.M)
reg_v = re.compile(r"1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\\-(n|u)|c55\\/|capi|ccwa|cdm\\-|cell|chtm|cldc|cmd\\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\\-s|devi|dica|dmob|do(c|p)o|ds(12|\\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\\-|_)|g1 u|g560|gene|gf\\-5|g\\-mo|go(\\.w|od)|gr(ad|un)|haie|hcit|hd\\-(m|p|t)|hei\\-|hi(pt|ta)|hp( i|ip)|hs\\-c|ht(c(\\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\\-(20|go|ma)|i230|iac( |\\-|\\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\\/)|klon|kpt |kwc\\-|kyo(c|k)|le(no|xi)|lg( g|\\/(k|l|u)|50|54|\\-[a-w])|libw|lynx|m1\\-w|m3ga|m50\\/|ma(te|ui|xo)|mc(01|21|ca)|m\\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\\-2|po(ck|rt|se)|prox|psio|pt\\-g|qa\\-a|qc(07|12|21|32|60|\\-[2-7]|i\\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\\-|oo|p\\-)|sdk\\/|se(c(\\-|0|1)|47|mc|nd|ri)|sgh\\-|shar|sie(\\-|m)|sk\\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\\-|v\\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\\-|tdg\\-|tel(i|m)|tim\\-|t\\-mo|to(pl|sh)|ts(70|m\\-|m3|m5)|tx\\-9|up(\\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\\-|your|zeto|zte\\-", re.I|re.M)

CFG_PARAM = ('htr', 'str', 'tpr', 'pho', 'mod')
FLGS = ('power', 'casing', 'casing_h', 'strap', 'strap_h', 'hardware')

app = Flask(__name__)
socketio = SocketIO(app, async_mode='gevent')

# Examples:
# $GPGSV,12,05,50,07,,13,48,15,48,17,27,18,40,19,28,20,51,21,43,27,33,28,34,30,
# $GPGSA,A,3,05,13,15,20,30,28,,,,,,,3.62,1.62,3.23

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
            print request.headers.get('User-Agent')
            user_agent = request.headers.get('User-Agent')
            b = reg_b.search(user_agent)
            v = reg_v.search(user_agent[0:4])
            if b or v:
                print "Mobile"
            gpgsv = {}
            data = get_db().dump_sat(device_id)
            print data
            data = data[0].split(',')
            for key, val in zip(data[::2], data[1::2]):
                gpgsv[key] = val
            return render_template('satel.html', gpgsv=json.dumps(gpgsv))
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
            if 'text/plain' in request.headers.get('Content-type'):
                print request.data
                if 'GPGSV' in request.data:
                    get_db().update_sat(device_id, gpgsv=request.data)
                if 'GPGSA' in request.data:
                    get_db().update_sat(device_id, gpgsa=request.data)
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
