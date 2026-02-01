import logging
import os

logger = logging.getLogger("rent-finder")


def configure_logging(level=logging.INFO, fmt=None):
    if fmt is None:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(os.getenv("LOG_LEVEL", level))
    root.addHandler(handler)

    return logger
