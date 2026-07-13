from flyin.domain.graph import Graph
from flyin.simulation.simulation_result import SimulationResult
from flyin.visualization.color import AnsiColor


class TerminalVisualizer:
    """Colored terminal visualizer for the graph and simulation output."""

    def __init__(self, graph: Graph, use_color: bool = True) -> None:
        """Initialize the visualizer."""
        self.graph = graph
        self.use_color = use_color

    def graph_summary(self) -> str:
        """Return a visual summary of zones and connections."""
        lines = ["Map overview:"]
        lines.append(f"  Start: {self._zone_label(self.graph.start_name)}")
        lines.append(f"  End: {self._zone_label(self.graph.end_name)}")
        lines.append(f"  Zones: {self.graph.zone_count}")
        lines.append(f"  Connections: {self.graph.connection_count}")
        lines.append("")
        lines.append("Zones:")

        for zone_name in sorted(self.graph.zones):
            zone = self.graph.get_zone(zone_name)
            label = self._zone_label(zone_name)
            zone_type = zone.zone_type.value
            if zone_name in {self.graph.start_name, self.graph.end_name}:
                capacity = "∞"
            else:
                capacity = str(zone.max_drones)
            lines.append(
                f"  {label} ({zone.x}, {zone.y}) "
                f"type={zone_type} capacity={capacity}",
            )

        lines.append("")
        lines.append("Connections:")
        for key in sorted(self.graph.connections):
            connection = self.graph.connections[key]
            left = self._zone_label(connection.zone_a)
            right = self._zone_label(connection.zone_b)
            lines.append(
                f"  {left} <-> {right} "
                f"capacity={connection.max_link_capacity}",
            )

        return "\n".join(lines)

    def render_result(
        self,
        result: SimulationResult,
        capacity_info: bool = False,
        verbose: bool = True,
    ) -> str:
        """Return colored simulation output."""
        lines: list[str] = []

        for turn in result.turns:
            if verbose:
                prefix = AnsiColor.paint(
                    f"Turn {turn.turn_number}:",
                    "yellow",
                    self.use_color,
                )
                colored_moves = self._color_move_line(turn.to_subject_line())
                line = f"{prefix} {colored_moves}"
            else:
                line = self._color_move_line(turn.to_subject_line())
            lines.append(line)

            if capacity_info:
                lines.extend(f"  {item}" for item in turn.capacity_info)

        if verbose:
            status_color = "green" if result.success else "red"
            lines.append(
                AnsiColor.paint(
                    f"Success: {result.success}",
                    status_color,
                    self.use_color,
                ),
            )
            lines.append(f"Total turns: {result.total_turns}")

        return "\n".join(lines)

    def _zone_label(self, zone_name: str) -> str:
        """Return a colored zone label."""
        zone = self.graph.get_zone(zone_name)
        return AnsiColor.paint_zone(zone, self.use_color)

    def _color_move_line(self, line: str) -> str:
        """Color the zone or connection part of each move token."""
        colored_tokens: list[str] = []

        for token in line.split():
            if "-" not in token:
                colored_tokens.append(token)
                continue

            drone_id, target = token.split("-", 1)
            if self.graph.has_zone(target):
                colored_tokens.append(f"{drone_id}-{self._zone_label(target)}")
            else:
                colored_tokens.append(
                    AnsiColor.paint(token, "cyan", self.use_color)
                )

        return " ".join(colored_tokens)
