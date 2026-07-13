import heapq

from flyin.domain.graph import Graph
from flyin.pathfinding.path import Path
from flyin.pathfinding.path_utils import (
    count_priority_zones,
    get_zone_cost,
    is_blocked_zone,
    reconstruct_path,
)


class Dijkstra:
    """Dijkstra shortest path algorithm for the Fly-in graph."""

    def __init__(self, graph: Graph) -> None:
        """Initialize Dijkstra with a graph."""
        self.graph = graph

    def find_shortest_path(self, start_name: str, end_name: str) -> Path:
        """Find the lowest-cost path from start_name to end_name."""
        if not self.graph.has_zone(start_name):
            raise ValueError(f"Unknown start zone: {start_name}")

        if not self.graph.has_zone(end_name):
            raise ValueError(f"Unknown end zone: {end_name}")

        start_zone = self.graph.get_zone(start_name)
        end_zone = self.graph.get_zone(end_name)

        if is_blocked_zone(start_zone):
            raise ValueError("Start zone cannot be blocked.")

        if is_blocked_zone(end_zone):
            raise ValueError("End zone cannot be blocked.")

        distances: dict[str, float] = {}
        priority_score: dict[str, int] = {}
        previous: dict[str, str | None] = {}

        for zone_name in self.graph.zones:
            distances[zone_name] = float("inf")
            priority_score[zone_name] = 0
            previous[zone_name] = None

        distances[start_name] = 0
        priority_queue: list[tuple[float, int, str]] = [(0, 0, start_name)]

        while priority_queue:
            current_cost, current_priority, current_name = heapq.heappop(
                priority_queue,
            )

            if current_cost > distances[current_name]:
                continue

            if current_cost == distances[current_name]:
                if current_priority > priority_score[current_name]:
                    continue

            if current_name == end_name:
                break

            for neighbor_name, _conn in self.graph.neighbors(current_name):
                neighbor_zone = self.graph.get_zone(neighbor_name)

                if is_blocked_zone(neighbor_zone):
                    continue

                move_cost = get_zone_cost(neighbor_zone)
                new_cost = current_cost + move_cost
                bonus = 1 if neighbor_zone.zone_type.value == "priority" else 0
                new_priority = current_priority - bonus

                should_update = new_cost < distances[neighbor_name]
                same_cost_better_priority = (
                    new_cost == distances[neighbor_name]
                    and new_priority < priority_score[neighbor_name]
                )

                if should_update or same_cost_better_priority:
                    distances[neighbor_name] = new_cost
                    priority_score[neighbor_name] = new_priority
                    previous[neighbor_name] = current_name
                    heapq.heappush(
                        priority_queue,
                        (new_cost, new_priority, neighbor_name),
                    )

        if distances[end_name] == float("inf"):
            return Path(zones=[], cost=0)

        path_zones = reconstruct_path(previous, start_name, end_name)
        priority_count = count_priority_zones(path_zones, self.graph)
        _ = priority_count
        return Path(zones=path_zones, cost=int(distances[end_name]))
