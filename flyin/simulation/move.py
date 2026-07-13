from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    """Represents one drone output token during one simulation turn."""

    drone_id: int
    target: str

    def __str__(self) -> str:
        """Return the subject-style movement format."""
        return f"D{self.drone_id}-{self.target}"
