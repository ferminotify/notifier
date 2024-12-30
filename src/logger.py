import logging
import os
from dotenv import load_dotenv

class Logger:
    def __init__(self):
        load_dotenv()
        level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.logger = logging.getLogger("notifier")
        self.logger.setLevel(level)
        
        self.file_handler = None
        self.stream_handler = None

        if not self.logger.handlers:
            # File handler
            self.file_handler = logging.FileHandler("notifier.log")
            self.file_handler.setLevel(level)
            self.formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(filename)s: %(levelname)s - %(message)s"
            )
            self.file_handler.setFormatter(self.formatter)
            self.logger.addHandler(self.file_handler)

            # Stream handler (for terminal output)
            self.stream_handler = logging.StreamHandler()
            self.stream_handler.setLevel(level)
            self.stream_handler.setFormatter(self.formatter)
            self.logger.addHandler(self.stream_handler)

            self.logger.info("==========================================================================")
            self.logger.info("START")

            self.logger.info("Logger initialized")
            self.logger.debug("Debugging enabled")
            self.logger.info("Info enabled")
            self.logger.warning("Warning enabled")
            self.logger.error("Error enabled")
            self.logger.critical("Critical enabled")

    def info(self, message):
        self.logger.info(message)
        if self.file_handler:
            self.file_handler.flush()

    def debug(self, message):
        self.logger.debug(message)
        if self.file_handler:
            self.file_handler.flush()

    def warning(self, message):
        self.logger.warning(message)
        if self.file_handler:
            self.file_handler.flush()

    def error(self, message):
        self.logger.error(message)
        if self.file_handler:
            self.file_handler.flush()

    def critical(self, message):
        self.logger.critical(message)
        if self.file_handler:
            self.file_handler.flush()

    def close(self):
        if self.file_handler:
            self.file_handler.close()
        logging.shutdown()
        self.logger.info("Logger closed")
        self.logger.debug("Debugging disabled")
        self.logger.info("Info disabled")
        self.logger.warning("Warning disabled")
        self.logger.error("Error disabled")
        self.logger.critical("Critical disabled")
        self.logger.info("END")
        self.logger.info("==========================================================================")