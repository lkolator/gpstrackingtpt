from datetime import timedelta
from flask import Flask
from flask import request, safe_join, session, app, g
from flask import Response, render_template, send_from_directory
from flask.views import MethodView
from pygeocoder import Geocoder
import json
import logging
import geojson
from geojson import LineString, Feature, FeatureCollection
import os
import time
import glob
import pickle
import time


LOG_FILE = '/var/log/geoserv.log'
MAIN_DIR = '/root/geoserver/'
FILE_FORMAT = '%Y_%m_%d_%H_%M_%S'

file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
))
logging.captureWarnings(True)

app = Flask(__name__)

app.logger.addHandler(file_handler)

last_time = 0
counter = 0


def session_create(device_id):
    #import pdb;pdb.set_trace()
    directory = 'devices/' + device_id + '/'
    if not os.path.exists(directory):
        os.makedirs(directory)
    try:
        session_end(device_id)
        with open(directory + time.strftime(FILE_FORMAT) + '.coord', 'w') as f:
            pickle.dump([], f)
    except IOError:
        app.logger.error('Can\'t create file or directory!')


def session_update(device_id, lat, lng):
    directory = 'devices/' + device_id + '/'
    print directory
    filename = glob.glob(directory + '*.coord')[0]
    with open(filename, 'r') as f:
        coords = pickle.load(f)
    with open(filename, 'w') as f:
        coords.append((lng, lat))
        pickle.dump(coords, f)
    filename = os.path.splitext(filename)[0] + '.json'
    with open(filename, 'w+') as f:
        resp = FeatureCollection([Feature(geometry=LineString(coords))])
        geojson.dump(resp, f)


def session_end(device_id):
    directory = 'devices/' + device_id + '/'
    filelist = glob.glob(directory + '*.coord')
    for file in filelist:
        os.remove(file)


class Decoder(json.JSONDecoder):
    def _convert_coord(self, lat, lon):
        if lat[2] == '.' and lon[2] == '.':
            lat, lon = float(lat), float(lon)
        else:
            lat = int(lat[:2]) + float(lat[2:len(lat) - 1])/60
            lon = int(lon[:3]) + float(lon[3:len(lon) - 1])/60
        return lat, lon

    def decode(self, obj):
        obj = obj.replace('\x27', '\x22')
        gps = json.JSONDecoder.decode(self, obj)
        gps['lat'], gps['lon'] = self._convert_coord(gps['lat'], gps['lon'])
        return gps


class Decoder2(json.JSONDecoder):
    def decode(self, obj):
        obj = obj.replace('\x27', '\x22')
        return json.JSONDecoder.decode(self, obj)


class API(MethodView):
    """REST API"""
    def get(self, device_id):
        entries = []
        entries_l = []
        directory = safe_join('devices', device_id)
        print directory
        os.chdir(MAIN_DIR + directory)
        filelist = glob.glob('*.json')
        os.chdir(MAIN_DIR)
        for file in filelist:
            link = os.path.splitext(file)[0]
            title = link.split('_')
            title = title[0]+'-'+title[1]+'-'+title[2]+ ' ' +title[3]+':'+title[4]+':'+title[5]
            entries.append(dict(link=link, title=title))

        entries.sort(reverse=True)
        return render_template('show_entries.html', id=device_id, entries=entries)

    def post(self, device_id):
        global last_time
        print request.data
        gps, volt = json.loads(request.data, cls=Decoder)
        if 'session' in gps:
            if gps['session'] == 'true':
                last_time = time.time()
                session_create(device_id)
            else:
                session_end(device_id)
            return 'OK'
        session_update(device_id, gps['lat'], gps['lon'])
        results = Geocoder.reverse_geocode(gps['lat'], gps['lon'])
        app.logger.debug("Addres: %s Latitude: %f, Longitude: %f, Altitude %.1f, Vbat: %d, Vgsm: %d, time_diff: %.1f", \
                          results[0], gps['lat'], gps['lon'], gps['alt'], volt['vbat'], volt['vgsm'], time.time() - last_time)
        last_time = time.time()
        return 'OK'


class GeoJSON(MethodView):
    def get(self, filename):
        filename = safe_join('devices/', filename)
        return send_from_directory(MAIN_DIR, filename)


class Trace(MethodView):
    """docstring for Trace"""
    def get(self, trace):
        directory = 'devices/' + str(trace) + '.json'
        with open(directory, 'r') as f:
            geojs = geojson.load(f)
            points = list(geojson.utils.coords(geojs['features']))
            first = points[0]
            last = points.pop()
        return render_template('temp.html', start=first, end=last, plik=trace)


class Main(MethodView):
    def get(self):
        return "OK"
        #return render_template('index.html', devices=devices)


class Hello(MethodView):
    def get(self):
        return 'OK'

    def post(self):
        try:
            global counter
            print request.data
            gps = json.loads(request.data, cls=Decoder)
            results = Geocoder.reverse_geocode(gps['lat'], gps['lon'])
            print results
            return unicode(results[0])
        except:
            return "OK"


class HelloPost(MethodView):
    def post(self):
        pass


app.add_url_rule('/', view_func=Main.as_view('main'))
app.add_url_rule('/hello', view_func=Hello.as_view('hello'))
app.add_url_rule('/hello/<string:device_id>', view_func=HelloPost.as_view('hellopost'))
app.add_url_rule('/<string:device_id>', view_func=API.as_view('device'))
app.add_url_rule('/files/<path:filename>', view_func=GeoJSON.as_view('geojson'))
app.add_url_rule('/<path:trace>', view_func=Trace.as_view('show_trace'))

if __name__ == '__main__':
    #app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    app.run(debug=True, host='0.0.0.0', port=8111)
