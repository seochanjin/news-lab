"""Safe error formatting shared by isolated pipeline failures."""


def safe_error(error: Exception) -> str:
    message = " ".join(str(error).split())
    if len(message) > 200:
        message = message[:197] + "..."
    return f"{type(error).__name__}: {message}" if message else type(error).__name__
