import importlib
import sys


def test_importing_shared_db_does_not_eager_load_session_module():
    sys.modules.pop("shared.db", None)
    sys.modules.pop("shared.db.session", None)

    importlib.import_module("shared.db")

    assert "shared.db.session" not in sys.modules
