class NotFoundError(LookupError):
    pass


class ConflictError(RuntimeError):
    pass


class RuleValidationError(ValueError):
    pass
