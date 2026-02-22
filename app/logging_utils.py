import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger() -> logging.Logger:
    """
    Configure application logger with console + rotating file output.
    """
    logger = logging.getLogger("data_mapping_app")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    logs_dir = Path("app/logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        logs_dir / "app.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False
    return logger

