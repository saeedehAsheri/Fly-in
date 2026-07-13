from dataclasses import dataclass

from flyin.simulation.turn_result import TurnResult


@dataclass(frozen=True)
class SimulationResult:
    """Final result of a complete simulation."""

    turns: list[TurnResult]
    success: bool

    @property
    def total_turns(self) -> int:
        """Return the number of simulated turns."""
        return len(self.turns)

    def to_subject_output(self) -> str:
        """Return only the required movement lines."""
        lines = [
            turn.to_subject_line()
            for turn in self.turns
            if not turn.is_empty()
        ]
        return "\n".join(lines)

    def to_verbose_output(self, capacity_info: bool = False) -> str:
        """Return readable output with optional capacity diagnostics."""
        lines: list[str] = []
        for turn in self.turns:
            lines.append(turn.to_verbose_line())
            if capacity_info:
                lines.extend(f"  {item}" for item in turn.capacity_info)
        lines.append(f"Success: {self.success}")
        lines.append(f"Total turns: {self.total_turns}")
        return "\n".join(lines)

    def __str__(self) -> str:
        """Return the required subject output by default."""
        return self.to_subject_output()
