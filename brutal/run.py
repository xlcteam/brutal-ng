import logging

from twisted.python import log

from brutal.core.bot import BotManager


def main(config):
    """
    this is the primary run loop, should probably catch quits here?
    """
    # TODO: move logging to BotManager, make configurable
    filename = config.LOG_FILE
    level = config.LOG_LEVEL
    fmt = config.LOG_FORMAT

    # reset formatters
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    logging.basicConfig(level=level, format=fmt,
                        filename=filename)

    observer = log.PythonLoggingObserver()
    observer.start()

    bot_manager = BotManager(config)
    bot_manager.start()
