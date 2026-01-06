import sqlite3

con = sqlite3.connect("database.db")
cur = con.cursor()

# ---------------- ADMIN TABLE ----------------
cur.execute("""
CREATE TABLE IF NOT EXISTS admin (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL
)
""")

# ---------------- ELECTION TABLE ----------------
cur.execute("""
CREATE TABLE IF NOT EXISTS election (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    is_open INTEGER DEFAULT 0
)
""")

# ---------------- VOTERS TABLE ----------------
cur.execute("""
CREATE TABLE IF NOT EXISTS voters (
    voter_id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    has_voted INTEGER DEFAULT 0
)
""")

# ---------------- CANDIDATES TABLE ----------------
cur.execute("""
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
)
""")

# ---------------- VOTES TABLE ----------------
cur.execute("""
CREATE TABLE IF NOT EXISTS votes (
    voter_id TEXT,
    candidate_id INTEGER,
    FOREIGN KEY (voter_id) REFERENCES voters(voter_id),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
)
""")

# ---------------- DEFAULT ADMIN ----------------
cur.execute("DELETE FROM admin")
cur.execute(
    "INSERT INTO admin (username, password) VALUES (?, ?)",
    ("admin", "admin123")
)

# ---------------- DEFAULT ELECTION ----------------
cur.execute("DELETE FROM election")
cur.execute("""
INSERT INTO election (name, description, is_open)
VALUES (?, ?, ?)
""", (
    "Organization Election",
    "Internal voting for members",
    0   # 0 = CLOSED, 1 = OPEN
))

con.commit()
con.close()

print("✅ Database initialized successfully")