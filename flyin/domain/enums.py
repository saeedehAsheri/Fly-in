from enum import Enum


class ZoneType(Enum):
    """Types of zones in the map."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"
