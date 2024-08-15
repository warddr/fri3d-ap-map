import sqlite3

from flask import Flask, g, render_template, request
from geojson import Feature, FeatureCollection, LineString, Point

app = Flask(__name__, template_folder="templates", static_url_path="/", static_folder="static")

DATABASE = "telegrambot.db"


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


def get_ap_info(number):
    cur = get_db().cursor()
    cur.execute("SELECT id, number, lon, lat, switch, switchport FROM AP WHERE number = ?", (number,))
    result = cur.fetchone()
    if result is not None:
        ap_info = {
            "id": result[0],
            "number": result[1],
            "lon": result[2],
            "lat": result[3],
            "switch": result[4],
            "switchport": result[5],
        }
        return ap_info
    else:
        return None


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/api/geojson/switch")
def api_geojson_switch():
    features = []
    cur = get_db().cursor()
    cur.execute("SELECT id, locatie, naam, lon, lat FROM switch ")
    for points in cur.fetchall():
        mypoint = Point((float(points[3]), float(points[4])))
        features.append(
            Feature(
                geometry=mypoint,
                properties={"name": points[2], "id": points[0], "location": points[1]},
            )
        )
    return FeatureCollection(features)


@app.route("/api/geojson/AP")
def api_geojson_AP():
    number = request.args.get("number", default="%", type=str)
    cur = get_db().cursor()
    features = []
    cur.execute("SELECT id, number, lon, lat, switch, switchport FROM AP WHERE number LIKE ?", (number,))
    for points in cur.fetchall():
        mypoint = Point((float(points[2]), float(points[3])))
        features.append(
            Feature(geometry=mypoint, properties={"name": points[1], "switch": points[4], "switchport": points[5]})
        )
    return FeatureCollection(features)


@app.route("/api/geojson/lines")
def api_geojson_lines():
    features = []
    cur = get_db().cursor()
    cur.execute("SELECT AP.lon, AP.lat, switch.lon, switch.lat FROM AP INNER JOIN switch ON AP.switch = switch.id")
    for points in cur.fetchall():
        myline = LineString([(float(points[0]), float(points[1])), (float(points[2]), float(points[3]))])
        features.append(Feature(geometry=myline, properties={}))
    return FeatureCollection(features)


@app.route("/map")
def map():
    return render_template(
        "map.html.j2",
        APs="api/geojson/AP",
        switches="api/geojson/switch",
        lines="api/geojson/lines",
    )


@app.route("/apdetail")
def apdetail():
    number = request.args.get("number", type=str)
    apinfo = get_ap_info(number)
    return render_template("apdetail.html.j2", apinfo=apinfo, hotspots="api/geojson/AP?number=" + number)


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=4242)
