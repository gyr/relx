import logging


def logger_setup(name: str, verbose: bool = False) -> logging.Logger:
    """
    Retrieves a logger with the specified name.  This function
    ensures that the basic configuration is done.

    :param name: module name
    :param verbose: set local debug log level
    :return: log
    """
    # Use the name directly, don't re-create a new logger.
    logger = logging.getLogger(name)

    if verbose:
        logger.setLevel(logging.DEBUG)

    return logger


def global_logger_config(verbose: bool = False, log_file: bool = False) -> None:
    """
    Set logging level and log to file for the root logger.
    This affacts all loggers.

    :param verbose: enable debug mode.
    :param log_file: log to file.
    """
    logger = logging.getLogger()

    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)

    # create console handler with a higher log level
    stream_handler = logging.StreamHandler()
    # stream_handler.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    # formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    stream_handler.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(stream_handler)

    if log_file:
        # create file handler which logs even debug messages
        file_handler = logging.FileHandler("/tmp/relx.log")
        # file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
