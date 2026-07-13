from dataclasses import dataclass

from flyin.domain.enums import ZoneType


@dataclass(frozen=True)
class Zone:
    """Represents a zone/node in the drone map."""

    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = 1

    def movement_cost(self) -> int:
        """Return the movement cost to enter this zone."""
        if self.zone_type is ZoneType.RESTRICTED:
            return 2
        if self.zone_type is ZoneType.BLOCKED:
            raise ValueError("Blocked zones cannot be entered.")
        return 1

    def is_blocked(self) -> bool:
        """Return True if the zone is blocked."""
        return self.zone_type is ZoneType.BLOCKED
