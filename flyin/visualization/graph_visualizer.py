"""Graphical (matplotlib) animated visualizer for the Fly-in simulation.

matplotlib.pyplot is imported lazily inside show() so that the backend
can be selected before pyplot initialises — this is the only way to
guarantee the correct GUI backend on both macOS and Linux.
"""
import math
import os
import sys
from typing import TYPE_CHECKING, Any

from flyin.domain.enums import ZoneType
from flyin.domain.graph import Graph
from flyin.domain.zone import Zone
from flyin.simulation.simulation_result import SimulationResult

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

_MATPLOTLIB_COLORS: dict[str, str] = {
    "red": "#e74c3c",
    "green": "#2ecc71",
    "blue": "#3498db",
    "orange": "#e67e22",
    "yellow": "#f1c40f",
    "purple": "#9b59b6",
    "magenta": "#e91e63",
    "cyan": "#00bcd4",
    "gray": "#95a5a6",
    "grey": "#95a5a6",
    "white": "#ecf0f1",
    "black": "#2c3e50",
    "lime": "#a8e063",
    "gold": "#f9ca24",
    "brown": "#a0522d",
    # Extended colors used in some maps
    "maroon": "#800000",
    "darkred": "#8b0000",
    "crimson": "#dc143c",
    "violet": "#ee82ee",
    "rainbow": "#ff69b4",
}

_TYPE_DEFAULTS: dict[ZoneType, str] = {
    ZoneType.NORMAL: "#bdc3c7",
    ZoneType.RESTRICTED: "#e74c3c",
    ZoneType.PRIORITY: "#00bcd4",
    ZoneType.BLOCKED: "#7f8c8d",
}

_DRONE_COLORS = [
    "#e74c3c", "#3498db", "#2ecc71", "#f39c12",
    "#9b59b6", "#1abc9c", "#e67e22", "#34495e",
    "#e91e63", "#00bcd4", "#8bc34a", "#ff5722",
]


def _zone_fill(zone: Zone) -> str:
    """Return a matplotlib hex color for a zone."""
    if zone.color:
        color = _MATPLOTLIB_COLORS.get(zone.color.lower())
        if color:
            return color
    return _TYPE_DEFAULTS.get(zone.zone_type, "#bdc3c7")


def _drone_color(drone_id: int) -> str:
    """Return a consistent color for a drone."""
    return _DRONE_COLORS[(drone_id - 1) % len(_DRONE_COLORS)]


# ---------------------------------------------------------------------------
# GraphVisualizer
# ---------------------------------------------------------------------------

class GraphVisualizer:
    """Matplotlib-based animated visualizer for the Fly-in simulation."""

    _NODE_RADIUS = 0.30
    _DRONE_RADIUS = 0.12
    _FONT_ZONE = 7
    _FONT_DRONE = 6

    def __init__(
        self,
        graph: Graph,
        result: SimulationResult,
        nb_drones: int,
        interval: float = 1.0,
    ) -> None:
        """Initialize the visualizer.

        Args:
            graph: The parsed zone graph.
            result: Completed simulation result.
            nb_drones: Total number of drones.
            interval: Seconds to pause between turns.
        """
        self.graph = graph
        self.result = result
        self.nb_drones = nb_drones
        self._interval = interval
        self._positions = self._compute_layout()
        self._drone_history = self._build_drone_history()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @staticmethod
    def is_display_available() -> bool:
        """Return True if a GUI display is reachable."""
        if sys.platform in ("darwin", "win32"):
            return True
        return bool(
            os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
        )

    def show(self) -> None:
        """Render the animated simulation in a matplotlib window.

        The backend is chosen before matplotlib.pyplot is imported so that
        the correct GUI toolkit is selected on every platform.

        Raises:
            RuntimeError: If no GUI display is available.
            ImportError: If matplotlib is not installed.
        """
        if not self.is_display_available():
            raise RuntimeError(
                "No display found. The GUI requires a running desktop "
                "environment.\n"
                "On a remote server use:  ssh -X user@host\n"
                "Alternatively use --visual for colored terminal output."
            )

        import matplotlib
        current = matplotlib.get_backend().lower()
        non_interactive = {"agg", "pdf", "ps", "svg", "cairo", "template"}

        if current in non_interactive:
            # Prefer TkAgg (needs python3-tk on Debian/Ubuntu) then Qt5Agg.
            for backend in ("TkAgg", "Qt5Agg", "Qt4Agg", "GTK3Agg", "WXAgg"):
                try:
                    matplotlib.use(backend)
                    break
                except Exception:  # noqa: BLE001
                    continue

        import matplotlib.pyplot as plt  # noqa: PLC0415
        import matplotlib.patches as mpatches  # noqa: PLC0415

        plt.ion()
        try:
            self._animate(plt, mpatches)
        except KeyboardInterrupt:
            pass
        finally:
            plt.ioff()
            plt.show(block=True)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _compute_layout(self) -> dict[str, tuple[float, float]]:
        """Scale zone (x, y) coordinates to fit the canvas."""
        xs = [zone.x for zone in self.graph.zones.values()]
        ys = [zone.y for zone in self.graph.zones.values()]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1)
        span_y = max(max_y - min_y, 1)
        scale = min(10.0 / span_x, 7.0 / span_y)

        return {
            name: (
                (zone.x - min_x) * scale + 1.0,
                (zone.y - min_y) * scale + 1.0,
            )
            for name, zone in self.graph.zones.items()
        }

    # ------------------------------------------------------------------
    # Main animation loop
    # ------------------------------------------------------------------

    def _animate(self, plt: Any, mpatches: Any) -> None:
        """Build the figure and run the per-turn animation."""
        fig, ax = plt.subplots(figsize=(14, 9))
        fig.patch.set_facecolor("#1a1a2e")
        ax.set_facecolor("#16213e")
        ax.set_aspect("equal")
        ax.axis("off")

        self._set_axis_limits(ax)
        self._draw_legend(fig, mpatches)
        self._draw_connections(ax, plt)
        zone_circles = self._draw_zones(ax, plt)

        title = ax.set_title(
            "Fly-in Simulation  -  Initial state",
            color="white",
            fontsize=13,
            pad=10,
        )

        drone_artists = self._init_drone_artists(ax, plt)
        plt.tight_layout()
        plt.pause(self._interval)

        for turn_idx, state in enumerate(self._drone_history[1:], start=1):
            turn_obj = (
                self.result.turns[turn_idx - 1]
                if turn_idx <= len(self.result.turns)
                else None
            )

            label = f"Turn {turn_idx}"
            if turn_obj:
                moves = "  |  " + turn_obj.to_subject_line()
                if len(moves) > 80:
                    moves = moves[:77] + "..."
                label += moves
            title.set_text(label)

            self._update_drone_artists(drone_artists, state)
            self._flash_active_zones(zone_circles, turn_obj)
            fig.canvas.draw()
            plt.pause(self._interval)

        status = "[OK]" if self.result.success else "[FAILED]"
        title.set_text(
            f"Simulation complete  -  {self.result.total_turns} turns  "
            f"{status}  (close window to exit)"
        )
        fig.canvas.draw()

    # ------------------------------------------------------------------
    # Static drawing helpers
    # ------------------------------------------------------------------

    def _set_axis_limits(self, ax: "Axes") -> None:
        """Set axis limits with generous padding."""
        xs = [p[0] for p in self._positions.values()]
        ys = [p[1] for p in self._positions.values()]
        pad = 1.2
        ax.set_xlim(min(xs) - pad, max(xs) + pad)
        ax.set_ylim(min(ys) - pad, max(ys) + pad)

    def _draw_connections(self, ax: "Axes", plt: Any) -> None:
        """Draw connection lines between zones."""
        for connection in self.graph.connections.values():
            x1, y1 = self._positions[connection.zone_a]
            x2, y2 = self._positions[connection.zone_b]
            ax.plot(
                [x1, x2], [y1, y2],
                color="#4a6fa5",
                linewidth=1.8,
                zorder=1,
                alpha=0.7,
            )
            if connection.max_link_capacity > 1:
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                ax.text(
                    mx, my,
                    f"x{connection.max_link_capacity}",
                    color="#aab7d4",
                    fontsize=6,
                    ha="center",
                    va="center",
                    zorder=4,
                )

    def _draw_zones(self, ax: "Axes", plt: Any) -> dict[str, Any]:
        """Draw zone shapes and labels. Return artist map for highlighting."""
        circles: dict[str, Any] = {}
        r = self._NODE_RADIUS

        for name, zone in self.graph.zones.items():
            px, py = self._positions[name]
            fill = _zone_fill(zone)

            is_start = name == self.graph.start_name
            is_end = name == self.graph.end_name
            edge_color = (
                "#2ecc71" if is_start else "#e74c3c" if is_end else "#ecf0f1"
            )
            lw = 2.5 if (is_start or is_end) else 1.0

            if zone.zone_type is ZoneType.PRIORITY:
                artist = plt.Polygon(
                    [(px, py + r), (px + r, py), (px, py - r), (px - r, py)],
                    closed=True,
                    facecolor=fill,
                    edgecolor=edge_color,
                    linewidth=lw,
                    zorder=2,
                )
            else:
                artist = plt.Circle(
                    (px, py),
                    r,
                    facecolor=fill,
                    edgecolor=edge_color,
                    linewidth=lw,
                    zorder=2,
                )
            ax.add_patch(artist)
            circles[name] = artist

            short = name if len(name) <= 12 else name[:11] + "..."
            ax.text(
                px, py - r - 0.15,
                short,
                color="white",
                fontsize=self._FONT_ZONE,
                ha="center",
                va="top",
                zorder=5,
            )

            badge = self._zone_badge(zone)
            if badge:
                ax.text(
                    px, py,
                    badge,
                    color="white",
                    fontsize=6,
                    ha="center",
                    va="center",
                    zorder=5,
                    fontweight="bold",
                )

        return circles

    @staticmethod
    def _zone_badge(zone: Zone) -> str:
        """Return a short badge for the zone type."""
        if zone.zone_type is ZoneType.RESTRICTED:
            return "R"
        if zone.zone_type is ZoneType.PRIORITY:
            return "P"
        if zone.zone_type is ZoneType.BLOCKED:
            return "X"
        return ""

    # ------------------------------------------------------------------
    # Drone artists
    # ------------------------------------------------------------------

    def _init_drone_artists(self, ax: "Axes", plt: Any) -> dict[int, Any]:
        """Create drone circle+label artists at the initial positions."""
        artists: dict[int, Any] = {}
        placed: dict[str, int] = {}
        initial = self._drone_history[0]

        for drone_id in range(1, self.nb_drones + 1):
            target = initial[drone_id]
            px, py = self._drone_offset(target, placed)

            circ = plt.Circle(
                (px, py),
                self._DRONE_RADIUS,
                facecolor=_drone_color(drone_id),
                edgecolor="white",
                linewidth=0.8,
                zorder=6,
            )
            ax.add_patch(circ)
            txt = ax.text(
                px, py,
                f"D{drone_id}",
                color="white",
                fontsize=self._FONT_DRONE,
                ha="center",
                va="center",
                zorder=7,
                fontweight="bold",
            )
            artists[drone_id] = (circ, txt)

        return artists

    def _update_drone_artists(
        self,
        artists: dict[int, Any],
        state: dict[int, str],
    ) -> None:
        """Move all drone artists to their current-turn positions."""
        placed: dict[str, int] = {}
        for drone_id, target in sorted(state.items()):
            px, py = self._drone_offset(target, placed)
            circ, txt = artists[drone_id]
            circ.center = (px, py)
            txt.set_position((px, py))

    def _drone_offset(
        self,
        target: str,
        placed: dict[str, int],
    ) -> tuple[float, float]:
        """Spread multiple drones sharing a target position."""
        idx = placed.get(target, 0)
        placed[target] = idx + 1
        px, py = self._target_position(target)
        if idx == 0:
            return (px, py)
        angle = (idx - 1) * (2 * math.pi / 6)
        r = self._NODE_RADIUS * 0.55
        return (px + math.cos(angle) * r, py + math.sin(angle) * r)

    def _target_position(self, target: str) -> tuple[float, float]:
        """Return the canvas position for a zone or connection label."""
        if self.graph.has_zone(target):
            return self._positions[target]

        parts = target.split("-", 1)
        if len(parts) == 2:
            zone_a, zone_b = parts
            if self.graph.has_connection(zone_a, zone_b):
                x1, y1 = self._positions[zone_a]
                x2, y2 = self._positions[zone_b]
                return ((x1 + x2) / 2, (y1 + y2) / 2)

        return self._positions[self.graph.start_name]

    # ------------------------------------------------------------------
    # Zone highlighting
    # ------------------------------------------------------------------

    def _flash_active_zones(
        self,
        circles: dict[str, Any],
        turn_obj: Any,
    ) -> None:
        """Highlight zones that received a drone this turn."""
        if turn_obj is None:
            return
        active = {
            move.target
            for move in turn_obj.moves
            if self.graph.has_zone(move.target)
        }
        for name, artist in circles.items():
            if name in active:
                artist.set_linewidth(3.0)
                artist.set_edgecolor("#f1c40f")
            else:
                is_start = name == self.graph.start_name
                is_end = name == self.graph.end_name
                ec = (
                    "#2ecc71" if is_start
                    else "#e74c3c" if is_end
                    else "#ecf0f1"
                )
                artist.set_linewidth(2.5 if (is_start or is_end) else 1.0)
                artist.set_edgecolor(ec)

    # ------------------------------------------------------------------
    # Legend
    # ------------------------------------------------------------------

    def _draw_legend(self, fig: "Figure", mpatches: Any) -> None:
        """Add a compact zone-type legend."""
        patches = [
            mpatches.Patch(color="#bdc3c7", label="normal"),
            mpatches.Patch(color="#e74c3c", label="restricted (2 turns)"),
            mpatches.Patch(color="#00bcd4", label="priority"),
            mpatches.Patch(color="#7f8c8d", label="blocked"),
        ]
        fig.legend(
            handles=patches,
            loc="lower left",
            fontsize=8,
            framealpha=0.3,
            facecolor="#1a1a2e",
            labelcolor="white",
        )

    # ------------------------------------------------------------------
    # Drone history
    # ------------------------------------------------------------------

    def _build_drone_history(self) -> list[dict[int, str]]:
        """Build per-turn drone position snapshots.

        Returns:
            A list of snapshots (initial + one per turn).
            Each snapshot maps drone_id -> zone_name or connection label.
        """
        current: dict[int, str] = {
            i: self.graph.start_name for i in range(1, self.nb_drones + 1)
        }
        history: list[dict[int, str]] = [dict(current)]

        for turn in self.result.turns:
            snapshot = dict(current)
            for move in turn.moves:
                snapshot[move.drone_id] = move.target
            history.append(snapshot)
            current = snapshot

        return history
