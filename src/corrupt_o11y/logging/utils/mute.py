import logging


def repropagate_uvicorn() -> None:
    # We are muting uvicorn.access because you should make your own access logger
    logging.getLogger("uvicorn.access").disabled = True

    for _log in ("uvicorn", "uvicorn.errors"):
        logging.getLogger(_log).handlers.clear()
        logging.getLogger(_log).propagate = True


def mute_taskiq() -> None:
    logging.getLogger("taskiq.process-manager").disabled = True
    logging.getLogger("taskiq.receiver.receiver").disabled = True
    logging.getLogger("taskiq.cli.scheduler.run").disabled = True


def repropagate_faststream() -> None:
    logging.getLogger("faststream").handlers.clear()
    logging.getLogger("faststream").propagate = True
