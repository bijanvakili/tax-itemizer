from collections import namedtuple
import logging
import re


MockLogRecord = namedtuple("MockLogRecord", ["level", "msg", "args", "kwargs"])


class MockLogger(logging.Logger):
    def __init__(self):
        super().__init__("test")
        self.messages = []

    def isEnabledFor(self, level):
        return True

    def _log(self, level, message, args, **kwargs):  # pylint: disable=arguments-differ
        self.messages.append(MockLogRecord(level, message, args, kwargs))


def log_contains_message(logger, message, level=None, expected_args=None):
    def _is_match(entry):
        if level and entry.level != level:
            return False
        if expected_args and entry.args != expected_args:
            return False
        return re.search(message, entry.msg)

    return any(map(_is_match, logger.messages))
