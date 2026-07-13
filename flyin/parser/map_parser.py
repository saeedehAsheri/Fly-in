import re
from dataclasses import dataclass
from pathlib import Path

from flyin.domain.connection import Connection
from flyin.domain.enums import ZoneType
from flyin.domain.graph import Graph
from flyin.domain.zone import Zone
from flyin.parser.exceptions import ParserError


@dataclass(frozen=True)
class ParsedMap:
    """Result of parsing a Fly-in map file."""

    nb_drones: int
    graph: Graph


class MapParser:
    """Parser for Fly-in map files."""

    def parse_file(self, file_path: str) -> ParsedMap:
        """Parse a map file.

        Args:
            file_path: Path to the map file.

        Returns:
            Parsed map data containing drone count and graph.

        Raises:
            ValueError: If the file cannot be read.
            ParserError: If the file content is invalid.
        """
        path = Path(file_path)

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise ValueError(f"Could not read file: {file_path}") from error

        return self.parse_lines(lines)

    def parse_lines(self, lines: list[str]) -> ParsedMap:
        """Parse map file lines.

        Args:
            lines: Lines from the map file.

        Returns:
            Parsed map data.

        Raises:
            ParserError: If the map content is invalid.
        """
        graph = Graph()
        nb_drones: int | None = None
        first_meaningful_line_found = False

        for index, raw_line in enumerate(lines, start=1):
            line = self._clean_line(raw_line)

            if line == "":
                continue

            if not first_meaningful_line_found:
                first_meaningful_line_found = True
                if not line.startswith("nb_drones:"):
                    raise ParserError(
                        index,
                        "First valid line must define nb_drones.",
                    )

            if line.startswith("nb_drones:"):
                if nb_drones is not None:
                    raise ParserError(
                        index,
                        "Duplicate nb_drones definition.",
                    )
                nb_drones = self._parse_nb_drones(line, index)

            elif line.startswith("start_hub:"):
                zone = self._parse_zone_line(
                    line,
                    "start_hub:",
                    index,
                )
                self._add_zone(graph, zone, index, is_start=True)

            elif line.startswith("end_hub:"):
                zone = self._parse_zone_line(
                    line,
                    "end_hub:",
                    index,
                )
                self._add_zone(graph, zone, index, is_end=True)

            elif line.startswith("hub:"):
                zone = self._parse_zone_line(line, "hub:", index)
                self._add_zone(graph, zone, index)

            elif line.startswith("connection:"):
                connection = self._parse_connection_line(line, index)
                self._add_connection(graph, connection, index)

            else:
                raise ParserError(index, f"Unknown line format: {line}")

        if nb_drones is None:
            raise ParserError(1, "Missing nb_drones definition.")

        self._validate_graph(graph, len(lines))

        return ParsedMap(nb_drones=nb_drones, graph=graph)

    def _clean_line(self, line: str) -> str:
        """Remove comments and surrounding spaces from a line."""
        without_comment = line.split("#", 1)[0]
        return without_comment.strip()

    def _add_zone(
        self,
        graph: Graph,
        zone: Zone,
        line_number: int,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        """Add a zone to the graph and convert graph errors."""
        try:
            graph.add_zone(zone, is_start=is_start, is_end=is_end)
        except ValueError as error:
            raise ParserError(line_number, str(error)) from error

    def _add_connection(
        self,
        graph: Graph,
        connection: Connection,
        line_number: int,
    ) -> None:
        """Add a connection to the graph and convert graph errors."""
        try:
            graph.add_connection(connection)
        except ValueError as error:
            raise ParserError(line_number, str(error)) from error

    def _validate_graph(self, graph: Graph, line_count: int) -> None:
        """Validate the final graph and convert graph errors."""
        error_line = max(line_count, 1)

        try:
            graph.validate()
        except ValueError as error:
            raise ParserError(error_line, str(error)) from error

    def _parse_nb_drones(self, line: str, line_number: int) -> int:
        """Parse the number of drones."""
        parts = line.split(":", 1)

        if len(parts) != 2:
            raise ParserError(line_number, "Invalid nb_drones format.")

        value = parts[1].strip()

        if not value.isdigit():
            raise ParserError(
                line_number,
                "nb_drones must be a positive integer.",
            )

        nb_drones = int(value)

        if nb_drones <= 0:
            raise ParserError(
                line_number,
                "nb_drones must be greater than zero.",
            )

        return nb_drones

    def _parse_zone_line(
        self,
        line: str,
        prefix: str,
        line_number: int,
    ) -> Zone:
        """Parse a start_hub, end_hub, or hub line."""
        content = line.removeprefix(prefix).strip()
        main_part, metadata = self._split_metadata(content, line_number)

        self._validate_metadata_keys(
            metadata,
            {"zone", "color", "max_drones"},
            line_number,
            "zone",
        )

        parts = main_part.split()

        if len(parts) != 3:
            raise ParserError(
                line_number,
                "Zone format must be: <name> <x> <y> [metadata].",
            )

        name = parts[0]
        self._validate_zone_name(name, line_number)

        try:
            x = int(parts[1])
            y = int(parts[2])
        except ValueError as error:
            raise ParserError(
                line_number,
                "Zone coordinates must be integers.",
            ) from error

        zone_type = ZoneType.NORMAL
        color: str | None = None
        max_drones = 1

        if "zone" in metadata:
            zone_type = self._parse_zone_type(
                metadata["zone"],
                line_number,
            )

        if "color" in metadata:
            color = self._parse_color(metadata["color"], line_number)

        if "max_drones" in metadata:
            max_drones = self._parse_positive_int(
                metadata["max_drones"],
                "max_drones",
                line_number,
            )

        return Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=color,
            max_drones=max_drones,
        )

    def _parse_connection_line(
        self,
        line: str,
        line_number: int,
    ) -> Connection:
        """Parse a connection line."""
        content = line.removeprefix("connection:").strip()
        main_part, metadata = self._split_metadata(content, line_number)

        self._validate_metadata_keys(
            metadata,
            {"max_link_capacity"},
            line_number,
            "connection",
        )

        if "-" not in main_part:
            raise ParserError(
                line_number,
                "Connection format must be: <zone1>-<zone2> [metadata].",
            )

        zone_names = main_part.split("-")

        if len(zone_names) != 2:
            raise ParserError(
                line_number,
                "Connection must contain exactly two zone names.",
            )

        zone_a = zone_names[0].strip()
        zone_b = zone_names[1].strip()

        if zone_a == "" or zone_b == "":
            raise ParserError(
                line_number,
                "Connection zone names cannot be empty.",
            )

        if zone_a == zone_b:
            raise ParserError(
                line_number,
                "A zone cannot be connected to itself.",
            )

        max_link_capacity = 1

        if "max_link_capacity" in metadata:
            max_link_capacity = self._parse_positive_int(
                metadata["max_link_capacity"],
                "max_link_capacity",
                line_number,
            )

        return Connection(
            zone_a=zone_a,
            zone_b=zone_b,
            max_link_capacity=max_link_capacity,
        )

    def _split_metadata(
        self,
        content: str,
        line_number: int,
    ) -> tuple[str, dict[str, str]]:
        """Split main content and metadata block."""
        metadata: dict[str, str] = {}

        has_open_bracket = "[" in content
        has_close_bracket = "]" in content

        if not has_open_bracket and not has_close_bracket:
            return content.strip(), metadata

        if has_open_bracket != has_close_bracket:
            raise ParserError(
                line_number,
                "Invalid metadata block syntax.",
            )

        match = re.fullmatch(r"(.+?)\s*\[(.*?)\]\s*", content)

        if match is None:
            raise ParserError(
                line_number,
                "Invalid metadata block syntax.",
            )

        main_part = match.group(1).strip()
        metadata_part = match.group(2).strip()

        if metadata_part == "":
            return main_part, metadata

        tokens = metadata_part.split()

        for token in tokens:
            if "=" not in token:
                raise ParserError(
                    line_number,
                    f"Invalid metadata token: {token}",
                )

            key, value = token.split("=", 1)

            if key == "" or value == "":
                raise ParserError(
                    line_number,
                    f"Invalid metadata token: {token}",
                )

            if key in metadata:
                raise ParserError(
                    line_number,
                    f"Duplicate metadata key: {key}",
                )

            metadata[key] = value

        return main_part, metadata

    def _validate_metadata_keys(
        self,
        metadata: dict[str, str],
        allowed_keys: set[str],
        line_number: int,
        context: str,
    ) -> None:
        """Validate metadata keys."""
        for key in metadata:
            if key not in allowed_keys:
                raise ParserError(
                    line_number,
                    f"Unknown {context} metadata: {key}",
                )

    def _validate_zone_name(
        self,
        name: str,
        line_number: int,
    ) -> None:
        """Validate a zone name."""
        if name == "":
            raise ParserError(line_number, "Zone name cannot be empty.")

        if "-" in name:
            raise ParserError(
                line_number,
                "Zone name cannot contain dashes.",
            )

        if " " in name:
            raise ParserError(
                line_number,
                "Zone name cannot contain spaces.",
            )

    def _parse_zone_type(
        self,
        value: str,
        line_number: int,
    ) -> ZoneType:
        """Parse and validate a zone type."""
        try:
            return ZoneType(value)
        except ValueError as error:
            raise ParserError(
                line_number,
                f"Invalid zone type: {value}",
            ) from error

    def _parse_color(
        self,
        value: str,
        line_number: int,
    ) -> str:
        """Parse and validate a color value."""
        if value == "":
            raise ParserError(line_number, "Color cannot be empty.")

        if " " in value:
            raise ParserError(
                line_number,
                "Color must be a single-word string.",
            )

        return value

    def _parse_positive_int(
        self,
        value: str,
        field_name: str,
        line_number: int,
    ) -> int:
        """Parse a positive integer value."""
        if not value.isdigit():
            raise ParserError(
                line_number,
                f"{field_name} must be a positive integer.",
            )

        number = int(value)

        if number <= 0:
            raise ParserError(
                line_number,
                f"{field_name} must be greater than zero.",
            )

        return number
