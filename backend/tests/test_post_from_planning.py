import datetime
import importlib.util
import os

_P = os.path.join(os.path.dirname(__file__), "..", "..", "deploy", "post_from_planning.py")
_spec = importlib.util.spec_from_file_location("poster", _P)
poster = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(poster)

NOW = datetime.datetime(2026, 7, 8, 12, 0, tzinfo=poster.TZ)


def _item(date, heure, posted=False):
    return {"date": date, "heure": heure, "posted": posted}


def test_due_selection():
    assert poster._due(_item("2026-07-08", "07:00"), NOW) is True          # passé
    assert poster._due(_item("2026-07-08", "15:00"), NOW) is False         # futur
    assert poster._due(_item("2026-07-07", "21:00"), NOW) is True          # hier
    assert poster._due(_item("2026-07-08", "07:00", posted=True), NOW) is False  # déjà posté


def test_short_title_tiktok():
    long = "Un titre vraiment très long qui dépasse largement les quatre-vingt-dix caractères autorisés par TikTok pour rien"
    assert len(poster._short_title(long)) <= poster.TIKTOK_TITLE_MAX
    assert poster._short_title("court") == "court"
