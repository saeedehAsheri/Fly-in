from dataclasses import dataclass


@dataclass(frozen=True)
class Connection:
    """Represents a bidirectional connection/edge between two zones."""

    zone_a: str
    zone_b: str
    max_link_capacity: int = 1

    def __post_init__(self) -> None:
        """Validate connection data."""
        if self.max_link_capacity <= 0:
            raise ValueError("Connection capacity must be greater than zero.")

    def other_side(self, zone_name: str) -> str:
        """Return the opposite zone name of this connection."""
        if zone_name == self.zone_a:
            return self.zone_b
        if zone_name == self.zone_b:
            return self.zone_a
        raise ValueError(f"Zone {zone_name} is not part of this connection.")

    def key(self) -> tuple[str, str]:
        """Return a normalized key for duplicate detection."""
        if self.zone_a <= self.zone_b:
            return (self.zone_a, self.zone_b)
        return (self.zone_b, self.zone_a)
