"""Persistance SQLite des vidéos générées. Source de l'historique (snapshot
read-only) lu par le Policy — T1/T2. Aucune décision ici."""
import os, json, sqlite3, datetime

_SCHEMA = """
CREATE TABLE IF NOT EXISTS generated_videos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL,
    mechanic_type TEXT NOT NULL,
    content_angle TEXT NOT NULL,
    layout_type   TEXT NOT NULL,
    asset_ids     TEXT NOT NULL,
    duration      REAL NOT NULL,
    status        TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.path = path
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def _conn(self):
        return sqlite3.connect(self.path)

    def insert(self, recipe, status):
        with self._conn() as c:
            c.execute(
                "INSERT INTO generated_videos(created_at, mechanic_type, "
                "content_angle, layout_type, asset_ids, duration, status) "
                "VALUES (?,?,?,?,?,?,?)",
                (datetime.datetime.now().isoformat(timespec="seconds"),
                 recipe.mechanic, recipe.content_angle, recipe.layout,
                 json.dumps(list(recipe.assets)), recipe.duration, status))

    def query_recent(self, n):
        """Les n dernières entrées (plus récent d'abord), projetées sur les 3
        dimensions de diversité {mechanic, content_angle, layout}."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT mechanic_type, content_angle, layout_type "
                "FROM generated_videos ORDER BY id DESC LIMIT ?", (n,)).fetchall()
        return [{"mechanic": r[0], "content_angle": r[1], "layout": r[2]}
                for r in rows]
