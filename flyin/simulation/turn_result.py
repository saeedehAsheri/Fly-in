from dataclasses import dataclass, field

from flyin.simulation.move import Move


@dataclass(frozen=True)
class TurnResult:
    """Stores all moves and optional diagnostics for one turn."""

    turn_number: int
    moves: list[Move]
    capacity_info: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Return True if no drone moved in this turn."""
        return len(self.moves) == 0

    def to_subject_line(self) -> str:
        """Return the required subject output for this turn."""
        return " ".join(str(move) for move in self.moves)

    def to_verbose_line(self) -> str:
        """Return a readable debug output for this turn."""
        if self.is_empty():
            return f"Turn {self.turn_number}: wait"
        return f"Turn {self.turn_number}: {self.to_subject_line()}"

    def __str__(self) -> str:
        """Return the required subject output for this turn."""
        return self.to_subject_line()
