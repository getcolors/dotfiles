"""Expected, user-facing failures."""


class DotfilesError(Exception):
    def __init__(self, message, code='operation_failed', stage=None):
        super().__init__(message)
        self.code = code
        self.stage = stage
