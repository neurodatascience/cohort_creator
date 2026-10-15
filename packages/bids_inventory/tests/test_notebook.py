from pathlib import Path

import pytest

# needs the 'notebook' extra
pytest.importorskip("marimo")
pytest.importorskip("dash")


def test_browse_notebook_runs(monkeypatch):
    """The marimo notebook runs and shows the same datasets as the dash app by default."""
    notebooks = Path(__file__).parents[1] / "notebooks"
    monkeypatch.syspath_prepend(str(notebooks))
    import browse

    _, defs = browse.app.run()

    assert len(defs["filtered_df"]) > 0
    assert set(defs["filtered_df"]["name"]) <= set(defs["df"]["name"])
