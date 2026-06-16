"""
@module: app.logging_config
@context: FastAPI backend — cross-cutting concern.
@role: Configure process-wide logging from Settings. Logs to stdout by default
       (12-factor / HA: the platform aggregates them); writes to a per-node file
       under LOG_DIR only when LOG_TO_STDOUT=false. Every record carries
       NODE_NAME so logs from multiple instances stay distinguishable
       (project_rules.md §18).
"""

import logging
import sys

from app.config import Settings


def configure_logging(settings: Settings) -> logging.Logger:
    """Configure the root logger from settings and return the app logger."""
    level = logging.getLevelNamesMapping().get(settings.log_level.upper(), logging.INFO)
    formatter = logging.Formatter(
        f"%(asctime)s %(levelname)s [{settings.node_name}] %(name)s: %(message)s"
    )

    if settings.log_to_stdout:
        handler: logging.Handler = logging.StreamHandler(sys.stdout)
    else:
        settings.log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(settings.log_dir / "app.log", encoding="utf-8")
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(handler)

    return logging.getLogger("app")
