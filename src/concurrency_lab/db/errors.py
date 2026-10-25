"""Driver classification without parsing or exposing private SQL/error text."""

from sqlalchemy.exc import DBAPIError


def mysql_error_code(error: DBAPIError) -> int | None:
    arguments = getattr(error.orig, "args", ())
    return arguments[0] if arguments and isinstance(arguments[0], int) else None
