import os
import sqlite3
import random
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
from ai.microsoft_ai import login_risk_score, vote_anomaly_score

# ================= APP CONFIG =================
app = Flask(__name__)
app.secret_key = "secure-org-voting"

# ================= EMAIL CONFIG =================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'ranganath4113@gmail.com'
app.config['MAIL_PASSWORD'] = 'rodubflnxhcpjzac'
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)

# ================= FOLDERS =================
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= DATABASE =================
def db():
    return sqlite3.connect("database.db")

# ================= INIT DATABASE =================
def init_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            voter_id TEXT PRIMARY KEY,
            email TEXT,
            has_voted INTEGER DEFAULT 0
        )
        """)

        con.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        )
        """)

        con.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            voted_at TEXT
        )
        """)

        con.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            username TEXT,
            password TEXT
        )
        """)

        con.execute("""
        CREATE TABLE IF NOT EXISTS ai_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            time TEXT
        )
        """)

        con.execute("""
        CREATE TABLE IF NOT EXISTS security_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id TEXT,
            ip TEXT,
            time TEXT
        )
        """)

        con.execute(
            "INSERT OR IGNORE INTO admin VALUES ('admin','admin123')"
        )
        con.commit()

init_db()

# ================= HOME =================
@app.route("/")
def index():
    return render_template("index.html")

# ================= VOTER VERIFY =================
@app.route("/verify", methods=["POST"])
def verify():
    voter_id = request.form["voter"]
    ip = request.remote_addr
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with db() as con:
        voter = con.execute(
            "SELECT email, has_voted FROM voters WHERE voter_id=?",
            (voter_id,)
        ).fetchone()

        if not voter:
            return render_template("message.html", msg="Voter ID not found")

        if voter[1] == 1:
            return render_template("message.html", msg="You already voted")

        attempts = con.execute(
            "SELECT COUNT(*) FROM security_logs WHERE ip=?",
            (ip,)
        ).fetchone()[0]

        risk = login_risk_score(attempts, True)

        con.execute(
            "INSERT INTO security_logs (voter_id, ip, time) VALUES (?,?,?)",
            (voter_id, ip, now)
        )

        if risk >= 80:
            con.execute(
                "INSERT INTO ai_alerts (message, time) VALUES (?,?)",
                ("Microsoft AI: High-risk login blocked", now)
            )
            con.commit()
            return render_template("message.html",
                msg="AI Alert: Suspicious login detected")

        con.commit()

    otp = random.randint(1000, 9999)
    session["otp"] = str(otp)
    session["voter_id"] = voter_id

    try:
        msg = Message(
            "Voting OTP",
            recipients=[voter[0]],
            body=f"Your OTP is {otp}"
        )
        mail.send(msg)
    except:
        print("OTP (TEST MODE):", otp)

    return redirect("/otp")

# ================= OTP =================
@app.route("/otp", methods=["GET", "POST"])
def otp():
    if request.method == "POST":
        if request.form["otp"] == session.get("otp"):
            return redirect("/vote")
        return render_template("message.html", msg="Invalid OTP")
    return render_template("otp.html")

# ================= VOTE =================
@app.route("/vote", methods=["GET", "POST"])
def vote():
    if "voter_id" not in session:
        return redirect("/")

    with db() as con:
        candidates = con.execute(
            "SELECT id, name FROM candidates"
        ).fetchall()

        if not candidates:
            return render_template("message.html",
                msg="No candidates available")

        if request.method == "POST":
            biometric_verified = True
            if not biometric_verified:
                return render_template("message.html",
                    msg="Biometric verification failed")

            cid = request.form["candidate"]
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            con.execute(
                "INSERT INTO votes (candidate_id, voted_at) VALUES (?,?)",
                (cid, now)
            )
            con.execute(
                "UPDATE voters SET has_voted=1 WHERE voter_id=?",
                (session["voter_id"],)
            )

            recent = con.execute("""
                SELECT COUNT(*) FROM votes
                WHERE voted_at >= datetime('now','-1 minute')
            """).fetchone()[0]

            anomaly = vote_anomaly_score(recent)
            if anomaly >= 70:
                con.execute(
                    "INSERT INTO ai_alerts (message, time) VALUES (?,?)",
                    ("AI: Voting anomaly detected", now)
                )

            con.commit()
            session.clear()
            return redirect("/results")

    return render_template("vote.html", candidates=candidates)

# ================= RESULTS =================
@app.route("/results")
def results():
    with db() as con:
        data = con.execute("""
        SELECT c.name, COUNT(v.candidate_id)
        FROM candidates c
        LEFT JOIN votes v ON c.id = v.candidate_id
        GROUP BY c.id
        """).fetchall()
    return render_template("results.html", data=data)

# ================= ADMIN LOGIN =================
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        with db() as con:
            admin = con.execute(
                "SELECT * FROM admin WHERE username=? AND password=?",
                (u, p)
            ).fetchone()

        if admin:
            session["admin"] = True
            return redirect("/admin/dashboard")

        return render_template("message.html", msg="Invalid login")

    return render_template("admin_login.html")

# ================= ADMIN DASHBOARD =================
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect("/admin")

    with db() as con:
        candidates = con.execute("SELECT * FROM candidates").fetchall()
        alerts = con.execute("SELECT * FROM ai_alerts").fetchall()

    return render_template(
        "admin_dashboard.html",
        candidates=candidates,
        alerts=alerts
    )

# ================= ADD CANDIDATE =================
@app.route("/admin/add_candidate", methods=["GET", "POST"])
def add_candidate():
    if not session.get("admin"):
        return redirect("/admin")

    if request.method == "POST":
        name = request.form["name"]
        with db() as con:
            con.execute(
                "INSERT INTO candidates (name) VALUES (?)",
                (name,)
            )
            con.commit()
        return redirect("/admin/dashboard")

    return render_template("add_candidate.html")

# ================= UPLOAD VOTERS =================
@app.route("/admin/upload_voters", methods=["POST"])
def upload_voters():
    if not session.get("admin"):
        return redirect("/admin")

    file = request.files.get("file")
    if not file or file.filename == "":
        return render_template("message.html",
            msg="No file selected")

    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        with db() as con:
            for row in reader:
                con.execute(
                    "INSERT OR IGNORE INTO voters (voter_id, email, has_voted) VALUES (?,?,0)",
                    (row["voter_id"], row["email"])
                )
            con.commit()

    return redirect("/admin/dashboard")

# ================= ADMIN LOGOUT =================
@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
