class DuplicateIdempotencyKey(Exception):
    """Raised when a concurrent request already inserted this (user, key) pair.

    Internal control-flow signal only — the order service catches it, reads the
    winner's stored response and returns that. It never reaches the HTTP layer.
    """

    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Idempotency key already in flight: {key}")
