import os
import sqlite3
import random
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
from ai.microsoft_ai import login_risk_score, vote_anomaly_score

app = Flask(__name__)
app.secret_key = "secure-org-voting"

# ================= EMAIL CONFIG =================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'ranganath4113@gmail.com'
app.config['MAIL_PASSWORD'] = 'YOUR_APP_PASSWORD'
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= DATABASE =================
def db():
    return sqlite3.connect("database.db")


# ================= INIT AI TABLES =================
def init_ai_tables():
    with db() as con:
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
        con.commit()


# ✅ CALL AFTER FUNCTION DEFINITION
init_ai_tables()

# ================= HOME =================
@app.route("/")
def index():
    return render_template("index.html")

# ================= VOTER VERIFY (MICROSOFT AI LOGIN) =================
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

        # ===== Microsoft AI Login Risk =====
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
                ("Microsoft Azure AI: High-risk login blocked", now)
            )
            con.commit()
            return render_template(
                "message.html",
                msg="Microsoft AI Alert: Suspicious login detected"
            )

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

# ================= VOTE (MICROSOFT AI + BIOMETRIC) =================
@app.route("/vote", methods=["GET", "POST"])
def vote():
    if "voter_id" not in session:
        return redirect("/")

    with db() as con:
        candidates = con.execute(
            "SELECT id, name FROM candidates"
        ).fetchall()

        if request.method == "POST":
            # ===== Microsoft Face AI (Simulated) =====
            biometric_verified = True
            if not biometric_verified:
                return render_template(
                    "message.html",
                    msg="Microsoft Azure Face AI: Biometric failed"
                )

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

            # ===== Microsoft AI Vote Anomaly =====
            recent_votes = con.execute("""
                SELECT COUNT(*) FROM votes
                WHERE voted_at >= datetime('now','-1 minute')
            """).fetchone()[0]

            anomaly = vote_anomaly_score(recent_votes)
            if anomaly >= 70:
                con.execute(
                    "INSERT INTO ai_alerts (message, time) VALUES (?,?)",
                    ("Microsoft Azure AI: Voting anomaly detected", now)
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

        return render_template("message.html", msg="Invalid admin login")

    return render_template("admin_login.html")

# ================= ADMIN DASHBOARD =================
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect("/admin")

    with db() as con:
        alerts = con.execute("SELECT * FROM ai_alerts").fetchall()
        votes = con.execute("""
            SELECT c.name, COUNT(v.candidate_id)
            FROM candidates c
            LEFT JOIN votes v ON c.id = v.candidate_id
            GROUP BY c.id
        """).fetchall()

    return render_template(
        "admin_dashboard.html",
        alerts=alerts,
        votes=votes
    )

# ================= ADMIN LOGOUT =================
@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
import sqlite3
import random
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
from ai.microsoft_ai import login_risk_score, vote_anomaly_score

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

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= DATABASE =================
def db():
    return sqlite3.connect("database.db")


# ================= INIT AI TABLES =================
def init_ai_tables():
    with db() as con:
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
        con.commit()


# ✅ CALL AFTER FUNCTION DEFINITION
init_ai_tables()

# ================= HOME =================
@app.route("/")
def index():
    return render_template("index.html")

# ================= VOTER VERIFY (MICROSOFT AI LOGIN) =================
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

        # ===== Microsoft AI Login Risk =====
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
                ("Microsoft Azure AI: High-risk login blocked", now)
            )
            con.commit()
            return render_template(
                "message.html",
                msg="Microsoft AI Alert: Suspicious login detected"
            )

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

# ================= VOTE (MICROSOFT AI + BIOMETRIC) =================
@app.route("/vote", methods=["GET", "POST"])
def vote():
    if "voter_id" not in session:
        return redirect("/")

    with db() as con:
        candidates = con.execute(
            "SELECT id, name FROM candidates"
        ).fetchall()

        if request.method == "POST":
            # ===== Microsoft Face AI (Simulated) =====
            biometric_verified = True
            if not biometric_verified:
                return render_template(
                    "message.html",
                    msg="Microsoft Azure Face AI: Biometric failed"
                )

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

            # ===== Microsoft AI Vote Anomaly =====
            recent_votes = con.execute("""
                SELECT COUNT(*) FROM votes
                WHERE voted_at >= datetime('now','-1 minute')
            """).fetchone()[0]

            anomaly = vote_anomaly_score(recent_votes)
            if anomaly >= 70:
                con.execute(
                    "INSERT INTO ai_alerts (message, time) VALUES (?,?)",
                    ("Microsoft Azure AI: Voting anomaly detected", now)
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

        return render_template("message.html", msg="Invalid admin login")

    return render_template("admin_login.html")

# ================= ADMIN DASHBOARD =================
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect("/admin")

    with db() as con:
        alerts = con.execute("SELECT * FROM ai_alerts").fetchall()
        votes = con.execute("""
            SELECT c.name, COUNT(v.candidate_id)
            FROM candidates c
            LEFT JOIN votes v ON c.id = v.candidate_id
            GROUP BY c.id
        """).fetchall()

    return render_template(
        "admin_dashboard.html",
        alerts=alerts,
        votes=votes
    )

# ================= ADMIN LOGOUT =================
@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)