import logging
import os

progress_bars = os.getenv("PROGRESS_BARS", False)
logger = logging.getLogger("rent-finder")


def configure_logging(level=logging.INFO, fmt=None):
    if fmt is None:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    stream_handler = logging.StreamHandler()
    file_handler = logging.FileHandler("rent_finder.log", encoding="utf-8")
    stream_handler.setFormatter(logging.Formatter(fmt))
    file_handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(os.getenv("LOG_LEVEL", level))
    root.addHandler(stream_handler)
    root.addHandler(file_handler)

    return logger
