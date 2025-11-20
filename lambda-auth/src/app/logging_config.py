import logging
import sys

_logging_configured = False


def configure_logging(log_level: str = "INFO"):
    global _logging_configured

    if _logging_configured:
        return

    root_logger = logging.getLogger()

    if root_logger.handlers:
        _logging_configured = True
        return

    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    formatter = logging.Formatter("[%(levelname)s] %(asctime)s %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)

    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
