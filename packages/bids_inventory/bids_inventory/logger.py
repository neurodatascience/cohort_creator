"""General logger for the bids_inventory package."""

from __future__ import annotations

import logging

from rich.logging import RichHandler


def bi_logger(log_level: str = "INFO") -> logging.Logger:
    FORMAT = "%(message)s"

    logging.basicConfig(
        level=log_level,
        format=FORMAT,
        datefmt="[%X]",
        handlers=[RichHandler()],
    )

    return logging.getLogger("bids_inventory")
