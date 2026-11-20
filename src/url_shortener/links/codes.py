ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
RESERVED_CODES = frozenset(
    {"health", "shorten", "stats", "docs", "redoc", "openapi.json"}
)
MAX_CODE_ATTEMPTS = 5


def encode_code(value: int) -> str:
    if value <= 0:
        raise ValueError("Sequence values must be positive")
    parts = []
    while value:
        value, remainder = divmod(value, len(ALPHABET))
        parts.append(ALPHABET[remainder])
    return "".join(reversed(parts))
