from flask import Flask, render_template, request, redirect, session
import sqlite3, requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

API_KEY = "c9ede8d9d7af183be3cfd46baede175d"

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, email TEXT, password TEXT, city TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, city TEXT, temp REAL, humidity REAL, aqi INT, weather TEXT, time TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY, city TEXT, status TEXT, reason TEXT, time TEXT)")

    conn.commit()
    conn.close()

init_db()

# ---------- DATA FETCH ----------
def get_env(city):
    w = requests.get(f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric").json()
    lat, lon = w['coord']['lat'], w['coord']['lon']
    temp = w['main']['temp']
    humidity = w['main']['humidity']
    weather = w['weather'][0]['main']

    air = requests.get(f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}").json()
    aqi = air['list'][0]['main']['aqi']

    return temp, humidity, weather, aqi

# ---------- RISK ENGINE ----------
def risk(temp, aqi):
    if aqi >= 4 or temp > 42:
        return "DANGER", "High AQI or Extreme Heat"
    elif aqi == 3 or temp > 35:
        return "WARNING", "Moderate Risk"
    else:
        return "SAFE", "Normal"

# ---------- ROUTES ----------
@app.route("/", methods=["GET","POST"])
def index():
    if "user" not in session:
        return redirect("/login")

    data = None
    if request.method == "POST":
        city = request.form["city"]

        temp, humidity, weather, aqi = get_env(city)
        status, reason = risk(temp, aqi)

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute("INSERT INTO logs(city,temp,humidity,aqi,weather,time) VALUES(?,?,?,?,?,?)",
                    (city,temp,humidity,aqi,weather,str(datetime.now())))

        if status != "SAFE":
            cur.execute("INSERT INTO alerts(city,status,reason,time) VALUES(?,?,?,?)",
                        (city,status,reason,str(datetime.now())))

        conn.commit()
        conn.close()

        data = {"city":city,"temp":temp,"humidity":humidity,"weather":weather,"aqi":aqi,"status":status,"reason":reason}

    return render_template("index.html", data=data)

# ---------- LOGIN ----------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        user = cur.execute("SELECT * FROM users WHERE email=? AND password=?", (email,password)).fetchone()

        if user:
            session["user"] = user[1]
            return redirect("/")
    return render_template("login.html")

# ---------- REGISTER ----------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        city = request.form["city"]

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO users(name,email,password,city) VALUES(?,?,?,?)",(name,email,password,city))
        conn.commit()
        conn.close()

        return redirect("/login")
    return render_template("register.html")

# ---------- HISTORY ----------
@app.route("/history")
def history():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    logs = cur.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 10").fetchall()
    alerts = cur.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 10").fetchall()

    conn.close()
    return render_template("history.html", logs=logs, alerts=alerts)

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)