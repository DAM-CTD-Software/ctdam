import json
import logging
import logging.config
from pathlib import Path


def setup_logging(log_base_dir="./logs"):
    """Initialize logging from JSON config with per-package log files.

    Creates separate log files for each package directory in src/ctdam/.

    Args:
        log_base_dir: Base logs directory path
    """
    log_base = Path(log_base_dir)
    log_base.mkdir(exist_ok=True)

    # Load base config from JSON
    config_file = Path(__file__).parent / "logging_config.json"
    with open(config_file, "r") as f:
        config = json.load(f)

    # Discover module directories in src/ctdam/
    ctdam_src = Path(__file__).parent
    module_dirs = [
        d.name
        for d in ctdam_src.iterdir()
        if d.is_dir() and not d.name.startswith("_")
    ]

    # Create log subdirectories and build handlers/loggers dynamically
    for module_dir in module_dirs:
        (log_base / module_dir).mkdir(exist_ok=True)

        handler_name = f"{module_dir}_handler"
        log_file = log_base / module_dir / f"{module_dir}.log"

        config["handlers"][handler_name] = {
            "class": "logging.FileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": str(log_file),
        }

        config["loggers"][f"ctdam.{module_dir}"] = {
            "level": "DEBUG",
            "handlers": [handler_name, "console"],
            "propagate": False,
        }

    logging.config.dictConfig(config)


def get_logger(module_name):
    """Get a logger for a module.

    Args:
        module_name: Use __name__

    Returns:
        Configured logger instance
    """
    return logging.getLogger(module_name)
