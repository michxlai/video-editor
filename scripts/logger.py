import logging
from pathlib import Path


def setup_logger(log_path: Path, name: str = "pause-remover") -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
    fh = logging.FileHandler(log_path)
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def log_step(
    logger: logging.Logger,
    step: str,
    status: str,
    message: str,
    correction: str = "",
) -> None:
    line = f"{step} | {status} | {message}"
    if correction:
        line += f" | correction: {correction}"
    if status == "FAIL":
        logger.error(line)
    else:
        logger.info(line)
