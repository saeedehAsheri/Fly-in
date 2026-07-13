from flyin.domain.enums import ZoneType
from flyin.domain.graph import Graph
from flyin.domain.zone import Zone


def is_blocked_zone(zone: Zone) -> bool:
    """Return True if the zone is blocked."""
    return zone.is_blocked()


def is_priority_zone(zone: Zone) -> bool:
    """Return True if the zone is a priority zone."""
    return zone.zone_type is ZoneType.PRIORITY


def get_zone_cost(zone: Zone) -> int:
    """Return the cost of entering a zone."""
    return zone.movement_cost()


def get_path_cost(zones: list[str], graph: Graph) -> int:
    """Return the weighted cost of a complete path."""
    if len(zones) <= 1:
        return 0

    total = 0
    for zone_name in zones[1:]:
        total += graph.get_zone(zone_name).movement_cost()
    return total


def count_priority_zones(zones: list[str], graph: Graph) -> int:
    """Return how many priority zones are used by a path."""
    total = 0
    for zone_name in zones[1:-1]:
        if is_priority_zone(graph.get_zone(zone_name)):
            total += 1
    return total


def reconstruct_path(
    previous: dict[str, str | None],
    start_name: str,
    end_name: str,
) -> list[str]:
    """Reconstruct a path from the previous-node dictionary."""
    path: list[str] = []
    current: str | None = end_name

    while current is not None:
        path.append(current)
        current = previous[current]

    path.reverse()

    if not path or path[0] != start_name:
        return []

    return path
