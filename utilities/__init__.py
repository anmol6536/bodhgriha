from .logger import configure_logging
import os

LOGGER = configure_logging(debug=os.environ.get("LOG_DEBUG", False))