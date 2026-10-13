from __future__ import annotations

import logging

import pytest

from bids_inventory.logger import add_log_files, bi_logger, set_current_dataset


@pytest.fixture
def logger():
    log = bi_logger()
    handlers = list(log.handlers)
    yield log
    set_current_dataset(None)
    for handler in log.handlers:
        if handler not in handlers:
            handler.close()
            log.removeHandler(handler)


def test_warnings_and_errors_mention_the_dataset(logger, caplog):
    caplog.set_level("INFO", logger="bids_inventory")
    set_current_dataset("ds000001 1/10")
    logger.info("info")
    logger.warning("warning")
    set_current_dataset(None)
    logger.error("error")

    messages = [r.getMessage() for r in caplog.records]
    assert messages == ["info", "[ds000001 1/10] warning", "error"]


def test_add_log_files(logger, tmp_path):
    warnings_log, errors_log = add_log_files(tmp_path / "logs")

    set_current_dataset("ds000002 2/10")
    logger.info("some info")
    logger.warning("some warning")
    logger.error("some error")
    try:
        raise ValueError("boom")
    except ValueError:
        logger.exception("some exception")
    for handler in logger.handlers:
        handler.flush()

    warnings_content = warnings_log.read_text()
    errors_content = errors_log.read_text()
    assert "[ds000002 2/10] some warning" in warnings_content
    assert "error" not in warnings_content
    assert "info" not in warnings_content
    assert "[ds000002 2/10] some error" in errors_content
    assert "ValueError: boom" in errors_content  # traceback is kept
    assert "warning" not in errors_content


def test_log_files_only_created_if_needed(logger, tmp_path):
    warnings_log, errors_log = add_log_files(tmp_path / "logs")
    logging.getLogger("bids_inventory").info("only info")
    assert not warnings_log.exists()
    assert not errors_log.exists()
