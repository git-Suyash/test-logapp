import logging
import logging.handlers
from pathlib import Path


LOG_DIR = Path("runtime_logs")

LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger():

    logger = logging.getLogger("logApp")

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "logapp.log",
        maxBytes=10_000_000,
        backupCount=5,
        encoding="utf-8"
    )

    file_handler.setFormatter(formatter)

    # console_handler = logging.StreamHandler()

    # console_handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(file_handler)

    # logger.addHandler(console_handler)

    return logger