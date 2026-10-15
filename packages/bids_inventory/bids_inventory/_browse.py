"""Launch the marimo app to browse the listing of known datasets."""

import subprocess
import sys
from pathlib import Path

# imported to fail early (with an explanation) if the 'browse' extra is not installed
import marimo  # noqa: F401

NOTEBOOK = Path(__file__).parent / "browse_app.py"


def browse(edit: bool = False) -> None:
    """Open the dashboard (a marimo notebook) in the browser.

    Parameters
    ----------
    edit : bool
        Open the notebook in edit mode (``marimo edit``) instead of as an app (``marimo run``).
    """
    command = [sys.executable, "-m", "marimo", "edit" if edit else "run", str(NOTEBOOK)]
    try:
        subprocess.run(command, check=True)
    except KeyboardInterrupt:
        pass
