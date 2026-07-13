from flyin.domain.graph import Graph
from flyin.pathfinding.dijkstra import Dijkstra
from flyin.pathfinding.path import Path
from flyin.pathfinding.path_utils import (
    count_priority_zones,
    get_path_cost,
    is_blocked_zone,
)


class PathFinder:
    """High-level pathfinding interface."""

    def __init__(self, graph: Graph) -> None:
        """Initialize the path finder with a graph."""
        self.graph = graph
        self._dijkstra = Dijkstra(graph)

    def find_shortest_path(self, start_name: str, end_name: str) -> Path:
        """Find the shortest path between two zones."""
        return self._dijkstra.find_shortest_path(start_name, end_name)

    def find_start_to_end_path(self) -> Path:
        """Find the shortest path from graph start zone to graph end zone."""
        return self.find_shortest_path(
            self.graph.start_name,
            self.graph.end_name,
        )

    def find_multiple_paths(self, max_paths: int = 8) -> list[Path]:
        """Find several useful simple paths from start to end.

        The method enumerates simple paths with a bounded DFS, sorts them by
        weighted cost, priority-zone preference, and length. Then it keeps
        a diverse subset. This gives the simulator several routes instead
        of forcing every drone through the same bottleneck.
        """
        if max_paths <= 0:
            raise ValueError("max_paths must be greater than zero.")

        raw_paths = self._enumerate_paths(
            start_name=self.graph.start_name,
            end_name=self.graph.end_name,
            max_candidates=max(max_paths * 8, 32),
        )

        if not raw_paths:
            best_path = self.find_start_to_end_path()
            return [] if best_path.is_empty() else [best_path]

        sorted_paths = sorted(
            raw_paths,
            key=lambda path: (
                path.cost,
                -count_priority_zones(path.zones, self.graph),
                len(path.zones),
            ),
        )
        return self._select_diverse_paths(sorted_paths, max_paths)

    def _enumerate_paths(
        self,
        start_name: str,
        end_name: str,
        max_candidates: int,
    ) -> list[Path]:
        """Enumerate bounded simple paths from start to end."""
        paths: list[Path] = []
        max_depth = max(2, min(len(self.graph.zones), 40))

        def dfs(current: str, visited: set[str], route: list[str]) -> None:
            if len(paths) >= max_candidates:
                return

            if len(route) > max_depth:
                return

            if current == end_name:
                path = Path(
                    zones=route.copy(),
                    cost=get_path_cost(route, self.graph),
                )
                paths.append(path)
                return

            neighbors = []
            for neighbor_name, _connection in self.graph.neighbors(current):
                if neighbor_name in visited:
                    continue
                zone = self.graph.get_zone(neighbor_name)
                if is_blocked_zone(zone):
                    continue
                neighbors.append(neighbor_name)

            neighbors.sort(
                key=lambda name: (
                    self.graph.get_zone(name).movement_cost(),
                    self._priority_sort_value(name),
                    name,
                ),
            )

            for neighbor_name in neighbors:
                visited.add(neighbor_name)
                route.append(neighbor_name)
                dfs(neighbor_name, visited, route)
                route.pop()
                visited.remove(neighbor_name)

        dfs(start_name, {start_name}, [start_name])
        return paths

    def _priority_sort_value(self, zone_name: str) -> int:
        """Return 0 for priority zones, 1 for all other zones."""
        zone = self.graph.get_zone(zone_name)
        if zone.zone_type.value == "priority":
            return 0
        return 1

    def _select_diverse_paths(
        self,
        paths: list[Path],
        max_paths: int,
    ) -> list[Path]:
        """Select a useful subset of paths with limited internal overlap."""
        selected: list[Path] = []

        for path in paths:
            if len(selected) >= max_paths:
                break

            if not selected:
                selected.append(path)
                continue

            path_internal = path.internal_zones()
            too_similar = False
            for chosen in selected:
                chosen_internal = chosen.internal_zones()
                if not path_internal and not chosen_internal:
                    too_similar = True
                    break
                overlap = len(path_internal & chosen_internal)
                smaller = max(1, min(len(path_internal), len(chosen_internal)))
                if overlap / smaller > 0.80:
                    too_similar = True
                    break

            if not too_similar:
                selected.append(path)

        if len(selected) < max_paths:
            for path in paths:
                if len(selected) >= max_paths:
                    break
                if path not in selected:
                    selected.append(path)

        return selected
