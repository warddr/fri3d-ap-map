from flask import Flask, request, jsonify, render_template, g
import geopy.distance
from geojson import Feature, Point, FeatureCollection, LineString, MultiLineString
import requests
from requests.structures import CaseInsensitiveDict

import sqlite3


app = Flask(__name__, template_folder='templates', static_url_path='/static')

DATABASE = 'telegrambot.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route("/")
def hello():
  return "Hello World!"

@app.route("/api/geojson/AP")
def api_geojson_hotspots():
  number = request.args.get('number', default = "%", type = str)
  cur = get_db().cursor()
  features = []
  cur.execute("SELECT id, number, lon, lat FROM AP WHERE number LIKE ?", (number,))
  for points in cur.fetchall():
    mypoint = Point((float(points[2]), float(points[3])))
    features.append(Feature(geometry=mypoint, properties={"name": points[1]}))
  return FeatureCollection(features)


@app.route("/map")
def map():
  return render_template('map.html.j2', hotspots="api/geojson/AP")

@app.route("/apdetail")
def apdetail():
  number = request.args.get('number', type = str)
  return render_template('apdetail.html.j2', number=number, hotspots="api/geojson/AP?number="+number)


if __name__ == "__main__":
  app.run(host='0.0.0.0', debug=True, port=4242)
