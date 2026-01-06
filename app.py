import os
import sqlite3
import random
import csv
from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "secure-org-voting"

# ================= EMAIL CONFIG =================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'sp8424468@gmail.com'
app.config['MAIL_PASSWORD'] = 'mpyxwpwyyzqtddyu'
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= DATABASE =================
def db():
    return sqlite3.connect("database.db")

# ================= HOME =================
@app.route("/")
def index():
    return render_template("index.html")

# ================= VOTER VERIFY =================
@app.route("/verify", methods=["POST"])
def verify():
    voter_id = request.form["voter"]

    with db() as con:
        voter = con.execute(
            "SELECT email, has_voted FROM voters WHERE voter_id=?",
            (voter_id,)
        ).fetchone()

    if not voter:
        return render_template("message.html", msg="Voter ID not found")

    if voter[1] == 1:
        return redirect("/results")

    otp = random.randint(1000, 9999)
    session["otp"] = str(otp)
    session["voter_id"] = voter_id

    # 🔐 TRY EMAIL OTP
    try:
        msg = Message(
            "Voting OTP",
            recipients=[voter[0]],
            body=f"Your OTP is {otp}"
        )
        mail.send(msg)
        print("OTP sent via EMAIL")
    except Exception as e:
        # 🔁 FALLBACK (SAFE MODE)
        print("EMAIL FAILED, OTP (TEST MODE):", otp)

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
        election = con.execute(
            "SELECT is_open FROM election"
        ).fetchone()

        if not election or election[0] == 0:
            return render_template("message.html", msg="Election is closed")

        voted = con.execute(
            "SELECT has_voted FROM voters WHERE voter_id=?",
            (session["voter_id"],)
        ).fetchone()

        if voted and voted[0] == 1:
            return redirect("/results")

        candidates = con.execute(
            "SELECT id, name FROM candidates"
        ).fetchall()

        if not candidates:
            return render_template("message.html", msg="No candidates available")

        if request.method == "POST":
            cid = request.form["candidate"]

            con.execute(
                "INSERT INTO votes (candidate_id) VALUES (?)",
                (cid,)
            )

            con.execute(
                "UPDATE voters SET has_voted=1 WHERE voter_id=?",
                (session["voter_id"],)
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

        total = con.execute(
            "SELECT COUNT(*) FROM voters"
        ).fetchone()[0]

        voted = con.execute(
            "SELECT COUNT(*) FROM voters WHERE has_voted=1"
        ).fetchone()[0]

    return render_template(
        "results.html",
        data=data,
        voted=voted,
        total=total
    )

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
        election = con.execute("SELECT * FROM election").fetchone()
        candidates = con.execute("SELECT * FROM candidates").fetchall()

    return render_template(
        "admin_dashboard.html",
        election=election,
        candidates=candidates
    )

# ================= OPEN / CLOSE ELECTION =================
@app.route("/admin/set_status/<int:state>", methods=["POST"])
def set_status(state):
    if not session.get("admin"):
        return redirect("/admin")

    with db() as con:
        con.execute(
            "UPDATE election SET is_open=?",
            (state,)
        )
        con.commit()

    return redirect("/admin/dashboard")

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

# ================= UPLOAD VOTERS CSV =================
@app.route("/admin/upload_voters", methods=["GET", "POST"])
def upload_voters():
    if not session.get("admin"):
        return redirect("/admin")

    if request.method == "POST":
        file = request.files["file"]
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)

        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            with db() as con:
                for row in reader:
                    con.execute(
                        "INSERT OR IGNORE INTO voters (voter_id,email,has_voted) VALUES (?,?,0)",
                        (row["voter_id"], row["email"])
                    )
                con.commit()

        return redirect("/admin/dashboard")

    return render_template("upload_voters.html")

# ================= LOGOUT =================
@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)