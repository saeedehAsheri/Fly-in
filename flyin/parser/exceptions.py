class ParserError(Exception):
    """Raised when the map file contains invalid syntax or invalid data."""

    def __init__(self, line_number: int, message: str) -> None:
        """Initialize a parser error with line number and message."""
        self.line_number = line_number
        self.message = message
        super().__init__(f"Line {line_number}: {message}")
