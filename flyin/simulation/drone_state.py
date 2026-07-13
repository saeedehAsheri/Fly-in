from dataclasses import dataclass

from flyin.pathfinding.path import Path


@dataclass
class DroneState:
    """Runtime state of one drone during the simulation."""

    drone_id: int
    path: Path
    path_index: int = 0
    transit_from: str | None = None
    transit_to: str | None = None
    transit_remaining: int = 0
    arrived: bool = False

    def current_zone(self) -> str:
        """Return the current zone name of the drone."""
        return self.path.zones[self.path_index]

    def next_zone(self) -> str | None:
        """Return the next zone name, or None if the drone is at the end."""
        next_index = self.path_index + 1

        if next_index >= len(self.path.zones):
            return None

        return self.path.zones[next_index]

    def is_in_transit(self) -> bool:
        """Return True if the drone is flying to a restricted zone."""
        return self.transit_to is not None and self.transit_remaining > 0

    def start_transit(self, from_zone: str, to_zone: str) -> None:
        """Put the drone on a connection toward a restricted zone."""
        self.transit_from = from_zone
        self.transit_to = to_zone
        self.transit_remaining = 1

    def finish_transit(self) -> str:
        """Finish a restricted-zone transit and return the destination zone."""
        if self.transit_to is None:
            raise ValueError("Drone is not in transit.")

        destination = self.transit_to
        self.transit_from = None
        self.transit_to = None
        self.transit_remaining = 0
        self.path_index += 1
        return destination
