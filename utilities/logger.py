import logging
import structlog
import sys
import logging
import structlog


def configure_logging(debug: bool = False):
    # Configure the standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    processors = [
        # 1. Context first
        structlog.contextvars.merge_contextvars,   # optional: if you use contextvars for request_id etc.

        # 2. Core metadata
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.add_log_level,

        structlog.processors.CallsiteParameterAdder(
            parameters={
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            }
        ),

        # 3. Exception / stack handling
        structlog.processors.StackInfoRenderer(),   # adds stack info if exc_info=True
        structlog.processors.format_exc_info       # renders exception trace
    ]

    # 4. Output renderer (last step)
    if debug:
        processors.append(structlog.dev.ConsoleRenderer())       # human-friendly
    else:
        processors.append(structlog.processors.JSONRenderer())   # machine-readable

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG if debug else logging.INFO),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger()


if __name__ == "__main__":
    log = configure_logging(debug=True)  # or False in prod
    log.info("HELLO WORLD")
    log.warning("HELLO WORLD")
    log.error("HELLO WORLD")
    log.debug("HELLO WORLD")
    log.critical("HELLO WORLD")
