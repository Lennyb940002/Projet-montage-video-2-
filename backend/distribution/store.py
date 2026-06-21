"""Persistance des posts de distribution (SQLite). Statuts :
pending | posted | auto_posted | skipped | failed.
Sert aussi de DATABASE de production : montres (asset_ids), concept (mechanic),
musique -> base de l'anti-répétition (recent_models / recent_music)."""
import os, json, sqlite3, datetime

_SCHEMA = """
CREATE TABLE IF NOT EXISTS distribution_posts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL,
    video_path    TEXT NOT NULL,
    mechanic      TEXT NOT NULL,
    content_angle TEXT NOT NULL,
    layout        TEXT NOT NULL,
    asset_ids     TEXT NOT NULL,
    music         TEXT,
    caption       TEXT NOT NULL,
    status        TEXT NOT NULL,
    tg_message_id TEXT,
    decided_at    TEXT
);
"""


def _model_of(path):
    return os.path.basename(os.path.dirname(path))


class DistStore:
    def __init__(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.path = path
        with self._c() as c:
            c.executescript(_SCHEMA)

    def _c(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c

    def insert(self, video_path, mechanic, content_angle, layout, asset_ids,
               caption, music=None):
        with self._c() as c:
            cur = c.execute(
                "INSERT INTO distribution_posts(created_at, video_path, mechanic, "
                "content_angle, layout, asset_ids, music, caption, status) "
                "VALUES (?,?,?,?,?,?,?,?, 'pending')",
                (datetime.datetime.now().isoformat(timespec="seconds"), video_path,
                 mechanic, content_angle, layout, json.dumps(asset_ids), music, caption))
            return cur.lastrowid

    def recent_models(self, n):
        """Modèles (montres) utilisés dans les n derniers posts -> à éviter."""
        with self._c() as c:
            rows = c.execute("SELECT asset_ids FROM distribution_posts "
                             "ORDER BY id DESC LIMIT ?", (n,)).fetchall()
        out = set()
        for r in rows:
            for p in json.loads(r["asset_ids"]):
                out.add(_model_of(p))
        return out

    def recent_music(self, n):
        """Musiques utilisées dans les n derniers posts -> à éviter."""
        with self._c() as c:
            rows = c.execute("SELECT music FROM distribution_posts "
                             "WHERE music IS NOT NULL ORDER BY id DESC LIMIT ?",
                             (n,)).fetchall()
        return {r["music"] for r in rows}

    def update_status(self, pid, status, tg_message_id=None):
        with self._c() as c:
            c.execute("UPDATE distribution_posts SET status=?, decided_at=?, "
                      "tg_message_id=COALESCE(?, tg_message_id) WHERE id=?",
                      (status, datetime.datetime.now().isoformat(timespec="seconds"),
                       tg_message_id, pid))

    def get(self, pid):
        with self._c() as c:
            r = c.execute("SELECT * FROM distribution_posts WHERE id=?", (pid,)).fetchone()
            return dict(r) if r else None

    def query_pending(self):
        with self._c() as c:
            rows = c.execute(
                "SELECT * FROM distribution_posts WHERE status='pending' ORDER BY id").fetchall()
            return [dict(r) for r in rows]
