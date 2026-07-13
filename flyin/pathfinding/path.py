from dataclasses import dataclass


@dataclass(frozen=True)
class Path:
    """Represents a path from the start hub to the end hub."""

    zones: list[str]
    cost: int

    def is_empty(self) -> bool:
        """Return True if the path has no zones."""
        return len(self.zones) == 0

    def length(self) -> int:
        """Return the number of zones in the path."""
        return len(self.zones)

    def internal_zones(self) -> set[str]:
        """Return path zones excluding the first and last zone."""
        if len(self.zones) <= 2:
            return set()
        return set(self.zones[1:-1])

    def __str__(self) -> str:
        """Return a readable path representation."""
        if self.is_empty():
            return "No path found"
        return " -> ".join(self.zones) + f" | cost={self.cost}"
