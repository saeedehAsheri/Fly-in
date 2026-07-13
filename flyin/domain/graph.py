from flyin.domain.connection import Connection
from flyin.domain.zone import Zone


class Graph:
    """Custom graph implementation.

    The graph stores zones as nodes and connections as bidirectional edges.
    """

    def __init__(self) -> None:
        """Initialize an empty graph."""
        self._zones: dict[str, Zone] = {}
        self._connections: dict[tuple[str, str], Connection] = {}
        self._adjacency: dict[str, list[Connection]] = {}
        self._start_name: str | None = None
        self._end_name: str | None = None

    def add_zone(
        self,
        zone: Zone,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        """Add a zone to the graph.

        Args:
            zone: The zone to add.
            is_start: True if this zone is the start zone.
            is_end: True if this zone is the end zone.

        Raises:
            ValueError: If the zone name already exists, or if multiple
                start/end zones are added.
        """
        if zone.name in self._zones:
            raise ValueError(f"Duplicate zone name: {zone.name}")

        self._zones[zone.name] = zone
        self._adjacency[zone.name] = []

        if is_start:
            if self._start_name is not None:
                raise ValueError("Multiple start zones are not allowed.")
            self._start_name = zone.name

        if is_end:
            if self._end_name is not None:
                raise ValueError("Multiple end zones are not allowed.")
            self._end_name = zone.name

    def add_connection(self, connection: Connection) -> None:
        """Add a bidirectional connection to the graph.

        Args:
            connection: The connection to add.

        Raises:
            ValueError: If one of the zones does not exist, or if the
                connection already exists.
        """
        if connection.zone_a not in self._zones:
            raise ValueError(
                f"Unknown zone in connection: {connection.zone_a}"
            )

        if connection.zone_b not in self._zones:
            raise ValueError(
                f"Unknown zone in connection: {connection.zone_b}"
            )

        key = connection.key()

        if key in self._connections:
            connection_name = f"{connection.zone_a}-{connection.zone_b}"
            raise ValueError(f"Duplicate connection: {connection_name}")

        self._connections[key] = connection
        self._adjacency[connection.zone_a].append(connection)
        self._adjacency[connection.zone_b].append(connection)

    def get_zone(self, name: str) -> Zone:
        """Return a zone by name.

        Args:
            name: The zone name.

        Returns:
            The requested Zone object.

        Raises:
            ValueError: If the zone does not exist.
        """
        if name not in self._zones:
            raise ValueError(f"Unknown zone: {name}")

        return self._zones[name]

    def has_zone(self, name: str) -> bool:
        """Return True if the graph contains a zone with this name."""
        return name in self._zones

    def get_connection(self, zone_a: str, zone_b: str) -> Connection:
        """Return a connection between two zones.

        Args:
            zone_a: First zone name.
            zone_b: Second zone name.

        Returns:
            The connection between zone_a and zone_b.

        Raises:
            ValueError: If the connection does not exist.
        """
        key = self._connection_key(zone_a, zone_b)

        if key not in self._connections:
            raise ValueError(f"Unknown connection: {zone_a}-{zone_b}")

        return self._connections[key]

    def has_connection(self, zone_a: str, zone_b: str) -> bool:
        """Return True if a connection exists between two zones."""
        key = self._connection_key(zone_a, zone_b)
        return key in self._connections

    def neighbors(self, zone_name: str) -> list[tuple[str, Connection]]:
        """Return all neighbors of a zone.

        Args:
            zone_name: The zone name.

        Returns:
            A list of tuples containing neighbor zone names and connections.

        Raises:
            ValueError: If the zone does not exist.
        """
        if zone_name not in self._adjacency:
            raise ValueError(f"Unknown zone: {zone_name}")

        result: list[tuple[str, Connection]] = []

        for connection in self._adjacency[zone_name]:
            neighbor_name = connection.other_side(zone_name)
            result.append((neighbor_name, connection))

        return result

    def _connection_key(self, zone_a: str, zone_b: str) -> tuple[str, str]:
        """Return a normalized connection key."""
        if zone_a <= zone_b:
            return (zone_a, zone_b)
        return (zone_b, zone_a)

    def validate(self) -> None:
        """Validate that the graph has the required start and end zones.

        Raises:
            ValueError: If the start zone or end zone is missing.
        """
        if self._start_name is None:
            raise ValueError("Start zone is not defined.")

        if self._end_name is None:
            raise ValueError("End zone is not defined.")

    @property
    def start_name(self) -> str:
        """Return the start zone name.

        Raises:
            ValueError: If the start zone is not defined.
        """
        if self._start_name is None:
            raise ValueError("Start zone is not defined.")

        return self._start_name

    @property
    def end_name(self) -> str:
        """Return the end zone name.

        Raises:
            ValueError: If the end zone is not defined.
        """
        if self._end_name is None:
            raise ValueError("End zone is not defined.")

        return self._end_name

    @property
    def zones(self) -> dict[str, Zone]:
        """Return all zones in the graph."""
        return self._zones

    @property
    def connections(self) -> dict[tuple[str, str], Connection]:
        """Return all connections in the graph."""
        return self._connections

    @property
    def zone_count(self) -> int:
        """Return the number of zones in the graph."""
        return len(self._zones)

    @property
    def connection_count(self) -> int:
        """Return the number of connections in the graph."""
        return len(self._connections)
