import sqlite3

con = sqlite3.connect("database.db")
cur = con.cursor()

# Add is_open column if not exists
try:
    cur.execute("ALTER TABLE election ADD COLUMN is_open INTEGER DEFAULT 0")
    print("✅ is_open column added")
except:
    print("ℹ️ is_open column already exists")

# Ensure election row exists
cur.execute("SELECT COUNT(*) FROM election")
count = cur.fetchone()[0]

if count == 0:
    cur.execute(
        "INSERT INTO election (id, name, description, is_open) VALUES (1, 'Demo Election', 'Test Election', 1)"
    )
    print("✅ Election created & opened")
else:
    cur.execute("UPDATE election SET is_open = 1 WHERE id = 1")
    print("✅ Election opened")

con.commit()
con.close()

print("🎉 Database fixed successfully")