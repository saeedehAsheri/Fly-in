from collections import defaultdict

from flyin.domain.graph import Graph
from flyin.pathfinding.path import Path
from flyin.pathfinding.path_finder import PathFinder
from flyin.simulation.drone_state import DroneState
from flyin.simulation.move import Move
from flyin.simulation.simulation_result import SimulationResult
from flyin.simulation.turn_result import TurnResult


class Simulator:
    """Turn-based simulator for moving drones from start to end."""

    def __init__(self, graph: Graph, nb_drones: int) -> None:
        """Initialize the simulator with a graph and number of drones."""
        if nb_drones <= 0:
            raise ValueError("Number of drones must be greater than zero.")

        self.graph = graph
        self.nb_drones = nb_drones

    def run(
        self,
        paths: list[Path] | None = None,
        path: Path | None = None,
        max_turns: int = 1000,
    ) -> SimulationResult:
        """Run the simulation until all drones reach the end hub."""
        if max_turns <= 0:
            raise ValueError("max_turns must be greater than zero.")

        if paths is None:
            if path is not None:
                paths = [path]
            else:
                paths = PathFinder(self.graph).find_multiple_paths()

        valid_paths = [
            candidate for candidate in paths if not candidate.is_empty()
        ]
        if not valid_paths:
            raise ValueError(
                "Cannot simulate without at least one valid path."
            )

        for candidate in valid_paths:
            self._validate_path(candidate)

        drones = self._create_drones(valid_paths)
        occupancy = self._initial_occupancy()
        reserved_arrivals: dict[str, int] = defaultdict(int)
        turns: list[TurnResult] = []

        for turn_number in range(1, max_turns + 1):
            if self._all_drones_arrived(drones):
                return SimulationResult(turns=turns, success=True)

            turn = self._simulate_one_turn(
                turn_number=turn_number,
                drones=drones,
                occupancy=occupancy,
                reserved_arrivals=reserved_arrivals,
            )

            # Store every simulated turn, including wait-only turns.
            # now reflects the real number of discrete simulation turns.
            turns.append(turn)

        success = self._all_drones_arrived(drones)
        return SimulationResult(turns=turns, success=success)

    def _validate_path(self, path: Path) -> None:
        """Validate that a path can be simulated."""
        if path.is_empty():
            raise ValueError("Cannot simulate an empty path.")

        if len(path.zones) < 2:
            raise ValueError("Path must contain at least start and end zones.")

        if path.zones[0] != self.graph.start_name:
            raise ValueError("Path must start at the graph start zone.")

        if path.zones[-1] != self.graph.end_name:
            raise ValueError("Path must end at the graph end zone.")

        for zone_name in path.zones:
            if not self.graph.has_zone(zone_name):
                raise ValueError(f"Path contains unknown zone: {zone_name}")
            if self.graph.get_zone(zone_name).is_blocked():
                raise ValueError(f"Path contains blocked zone: {zone_name}")

        for index in range(len(path.zones) - 1):
            zone_a = path.zones[index]
            zone_b = path.zones[index + 1]

            if not self.graph.has_connection(zone_a, zone_b):
                raise ValueError(
                    f"Path contains missing connection: {zone_a}-{zone_b}"
                )

    def _create_drones(self, paths: list[Path]) -> list[DroneState]:
        """Create drone states and assign paths with load balancing."""
        loads = [0 for _path in paths]
        drones: list[DroneState] = []

        for drone_id in range(1, self.nb_drones + 1):
            best_index = min(
                range(len(paths)),
                key=lambda index: (
                    loads[index] + paths[index].cost,
                    loads[index],
                ),
            )
            loads[best_index] += 1
            drones.append(
                DroneState(drone_id=drone_id, path=paths[best_index])
            )

        return drones

    def _initial_occupancy(self) -> dict[str, int]:
        """Create initial occupancy for all finite-capacity zones."""
        occupancy: dict[str, int] = {}

        for zone_name in self.graph.zones:
            if not self._is_unlimited_hub(zone_name):
                occupancy[zone_name] = 0

        return occupancy

    def _simulate_one_turn(
        self,
        turn_number: int,
        drones: list[DroneState],
        occupancy: dict[str, int],
        reserved_arrivals: dict[str, int],
    ) -> TurnResult:
        """Simulate one turn and return its executed moves."""
        moves: list[Move] = []
        link_usage: dict[tuple[str, str], int] = defaultdict(int)
        planned_departures: dict[str, int] = defaultdict(int)
        planned_arrivals: dict[str, int] = defaultdict(int)

        self._reserve_links_for_arrivals(drones, link_usage)
        already_moved = self._process_transit_arrivals(
            drones=drones,
            occupancy=occupancy,
            reserved_arrivals=reserved_arrivals,
            moves=moves,
        )

        ordered_drones = sorted(
            [
                drone
                for drone in drones
                if (
                    not drone.arrived
                    and not drone.is_in_transit()
                    and drone.drone_id not in already_moved
                )
            ],
            key=lambda drone: (
                self._is_restricted_destination(drone),
                -drone.path_index,
                drone.drone_id,
            ),
        )

        for drone in ordered_drones:
            current_zone = drone.current_zone()
            next_zone = drone.next_zone()

            if next_zone is None:
                drone.arrived = True
                continue

            if not self._can_use_connection(
                current_zone,
                next_zone,
                link_usage,
            ):
                continue

            destination_zone = self.graph.get_zone(next_zone)
            is_restricted_move = destination_zone.movement_cost() == 2

            if not self._has_destination_capacity(
                zone_name=next_zone,
                occupancy=occupancy,
                planned_departures=planned_departures,
                planned_arrivals=planned_arrivals,
                reserved_arrivals=reserved_arrivals,
                reserve_for_next_turn=is_restricted_move,
            ):
                continue

            connection = self.graph.get_connection(current_zone, next_zone)
            link_usage[connection.key()] += 1

            if not self._is_unlimited_hub(current_zone):
                planned_departures[current_zone] += 1

            if is_restricted_move:
                drone.start_transit(current_zone, next_zone)
                if not self._is_unlimited_hub(next_zone):
                    reserved_arrivals[next_zone] += 1
                moves.append(
                    Move(
                        drone_id=drone.drone_id,
                        target=self._connection_label(current_zone, next_zone),
                    ),
                )
            else:
                if not self._is_unlimited_hub(next_zone):
                    planned_arrivals[next_zone] += 1
                self._move_drone_to_zone(drone, next_zone)
                moves.append(Move(drone_id=drone.drone_id, target=next_zone))

        self._apply_occupancy_changes(
            occupancy=occupancy,
            departures=planned_departures,
            arrivals=planned_arrivals,
        )

        capacity_lines = self._build_capacity_info(occupancy, link_usage)
        return TurnResult(
            turn_number=turn_number,
            moves=moves,
            capacity_info=capacity_lines,
        )

    def _reserve_links_for_arrivals(
        self,
        drones: list[DroneState],
        link_usage: dict[tuple[str, str], int],
    ) -> None:
        """Count restricted-zone arrival flights as connection usage."""
        for drone in drones:
            if (
                drone.is_in_transit()
                and drone.transit_from
                and drone.transit_to
            ):
                connection = self.graph.get_connection(
                    drone.transit_from,
                    drone.transit_to,
                )
                link_usage[connection.key()] += 1

    def _process_transit_arrivals(
        self,
        drones: list[DroneState],
        occupancy: dict[str, int],
        reserved_arrivals: dict[str, int],
        moves: list[Move],
    ) -> set[int]:
        """Move drones that were already flying into restricted zones."""
        moved_ids: set[int] = set()

        for drone in sorted(drones, key=lambda item: item.drone_id):
            if not drone.is_in_transit():
                continue

            if drone.transit_to is None:
                continue

            destination = drone.finish_transit()

            if not self._is_unlimited_hub(destination):
                reserved_arrivals[destination] -= 1
                occupancy[destination] = occupancy.get(destination, 0) + 1

            if destination == self.graph.end_name:
                drone.arrived = True

            moves.append(Move(drone_id=drone.drone_id, target=destination))
            moved_ids.add(drone.drone_id)

        return moved_ids

    def _move_drone_to_zone(self, drone: DroneState, next_zone: str) -> None:
        """Move a drone immediately to a normal or priority zone."""
        drone.path_index += 1
        if next_zone == self.graph.end_name:
            drone.arrived = True

    def _apply_occupancy_changes(
        self,
        occupancy: dict[str, int],
        departures: dict[str, int],
        arrivals: dict[str, int],
    ) -> None:
        """Apply planned zone departures and arrivals."""
        for zone_name, count in departures.items():
            occupancy[zone_name] = occupancy.get(zone_name, 0) - count

        for zone_name, count in arrivals.items():
            occupancy[zone_name] = occupancy.get(zone_name, 0) + count

    def _can_use_connection(
        self,
        zone_a: str,
        zone_b: str,
        link_usage: dict[tuple[str, str], int],
    ) -> bool:
        """Return True if the connection still has capacity this turn."""
        connection = self.graph.get_connection(zone_a, zone_b)
        return link_usage[connection.key()] < connection.max_link_capacity

    def _has_destination_capacity(
        self,
        zone_name: str,
        occupancy: dict[str, int],
        planned_departures: dict[str, int],
        planned_arrivals: dict[str, int],
        reserved_arrivals: dict[str, int],
        reserve_for_next_turn: bool,
    ) -> bool:
        """Return True if the destination zone can receive another drone."""
        if self._is_unlimited_hub(zone_name):
            return True

        zone = self.graph.get_zone(zone_name)
        current = occupancy.get(zone_name, 0)
        leaving = planned_departures.get(zone_name, 0)
        arriving = planned_arrivals.get(zone_name, 0)
        reserved = reserved_arrivals.get(zone_name, 0)
        extra_reserved = 1 if reserve_for_next_turn else 0
        expected = current - leaving + arriving + reserved + extra_reserved

        return expected <= zone.max_drones

    def _build_capacity_info(
        self,
        occupancy: dict[str, int],
        link_usage: dict[tuple[str, str], int],
    ) -> list[str]:
        """Build human-readable zone and connection capacity lines."""
        lines: list[str] = []

        for zone_name in sorted(occupancy):
            zone = self.graph.get_zone(zone_name)
            used = occupancy[zone_name]
            lines.append(
                f"Zone {zone_name}: {used}/{zone.max_drones} drones"
            )

        for key in sorted(self.graph.connections):
            connection = self.graph.connections[key]
            used = link_usage.get(key, 0)
            label = self._connection_label(
                connection.zone_a,
                connection.zone_b,
            )
            lines.append(
                f"Connection {label}: "
                f"{used}/{connection.max_link_capacity} capacity used",
            )

        return lines

    def _connection_label(self, zone_a: str, zone_b: str) -> str:
        """Return a stable label for a connection."""
        return f"{zone_a}-{zone_b}"

    def _is_restricted_destination(self, drone: DroneState) -> bool:
        """Return True if the drone's next move targets a restricted zone."""
        next_zone = drone.next_zone()
        if next_zone is None:
            return False
        return self.graph.get_zone(next_zone).movement_cost() == 2

    def _is_unlimited_hub(self, zone_name: str) -> bool:
        """Return True for start and end hubs."""
        return zone_name in {self.graph.start_name, self.graph.end_name}

    def _all_drones_arrived(self, drones: list[DroneState]) -> bool:
        """Return True if every drone reached the end zone."""
        return all(drone.arrived for drone in drones)
