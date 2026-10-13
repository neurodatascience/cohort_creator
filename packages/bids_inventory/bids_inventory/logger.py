"""General logger for the bids_inventory package."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from rich.logging import RichHandler

# dataset being processed, added to warnings and errors to know where they come from
_context: dict[str, str | None] = {"dataset": None}


def bi_logger(log_level: str = "INFO") -> logging.Logger:
    FORMAT = "%(message)s"

    logging.basicConfig(
        level=log_level,
        format=FORMAT,
        datefmt="[%X]",
        handlers=[RichHandler()],
    )

    logger = logging.getLogger("bids_inventory")
    if not any(isinstance(f, _DatasetContext) for f in logger.filters):
        logger.addFilter(_DatasetContext())
    return logger


def set_current_dataset(label: str | None) -> None:
    """Set the dataset being processed (``None`` when done).

    Warnings and errors logged meanwhile are prefixed with it,
    for example ``[ds000001 1/1380]``.
    """
    _context["dataset"] = label


class _DatasetContext(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        dataset = _context["dataset"]
        if dataset and record.levelno >= logging.WARNING and not hasattr(record, "dataset"):
            record.dataset = dataset
            record.msg = f"[{dataset}] {record.msg}"
        return True


def add_log_files(log_dir: Path) -> tuple[Path, Path]:
    """Also save warnings and errors in 2 separate files in ``log_dir``.

    Returns
    -------
    The paths to the warnings and errors log files.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s (%(filename)s:%(lineno)d)",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger("bids_inventory")
    files = []
    for name, keep in [
        ("warnings", lambda record: record.levelno == logging.WARNING),
        ("errors", lambda record: record.levelno >= logging.ERROR),
    ]:
        log_file = log_dir / f"{timestamp}_{name}.log"
        handler = logging.FileHandler(log_file, delay=True)
        handler.setLevel(logging.WARNING)
        handler.addFilter(keep)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        files.append(log_file)
    return files[0], files[1]
