"""Journal SQLite des posts valeur (anti-répétition des sujets + rotation coloris)."""
import os
import sqlite3


class PostsStore:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self._init()

    def _conn(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c

    def _init(self):
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS posts_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT, colorway TEXT, status TEXT,
                caption TEXT, n_slides INTEGER,
                created_at TEXT DEFAULT (datetime('now')))""")

    def insert(self, topic, colorway, caption=None, n_slides=None, status="pending"):
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO posts_log(topic,colorway,status,caption,n_slides) "
                "VALUES(?,?,?,?,?)", (topic, colorway, status, caption, n_slides))
            return cur.lastrowid

    def update_status(self, pid, status):
        with self._conn() as c:
            c.execute("UPDATE posts_log SET status=? WHERE id=?", (status, pid))

    def get(self, pid):
        with self._conn() as c:
            r = c.execute("SELECT * FROM posts_log WHERE id=?", (pid,)).fetchone()
            return dict(r) if r else None

    def recent_topics(self, n):
        """Les `n` derniers sujets postés (du plus récent au plus ancien)."""
        with self._conn() as c:
            rows = c.execute("SELECT topic FROM posts_log ORDER BY id DESC LIMIT ?",
                             (n,)).fetchall()
            return [r["topic"] for r in rows]

    def count(self):
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) AS n FROM posts_log").fetchone()["n"]
