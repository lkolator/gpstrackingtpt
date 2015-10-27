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


FILE_FORMAT = '%Y_%m_%d_%H_%M_%S'


app = Flask(__name__)


last_time = 0
counter = 0


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


class Main(MethodView):
    def get(self):
        return "OK"
        #return render_template('index.html', devices=devices)


class Hello(MethodView):
    def get(self):
        di = {'aaaa':'0ff0'}
        return Response(json.dumps(di),  mimetype='application/json')

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

if __name__ == '__main__':
    #app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    app.run(debug=True, host='0.0.0.0', port=8111)
