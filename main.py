import sys
from dataclasses import dataclass
from pathlib import Path

from flyin.parser.exceptions import ParserError
from flyin.parser.map_parser import MapParser
from flyin.pathfinding.path_finder import PathFinder
from flyin.simulation.simulator import Simulator
from flyin.visualization.terminal_visualizer import TerminalVisualizer


@dataclass(frozen=True)
class CliOptions:
    """Parsed command-line options."""

    map_file: str
    max_turns: int = 1000
    visual: bool = False
    gui: bool = False
    capacity_info: bool = False
    verbose: bool = False
    max_paths: int = 8
    gui_interval: float = 1.0


def print_usage() -> None:
    """Print command usage."""
    print("Usage: python3 main.py [options] <map_file> [max_turns]")
    print("Options:")
    print("  --visual          Show colored terminal visualization")
    print("  --gui             Open graphical (matplotlib) animated display")
    print("  --gui-speed N     Seconds per turn in GUI mode (default 1.0)")
    print("  --capacity-info   Show zone and connection capacity usage")
    print("  --verbose         Show path, summary, and turn numbers")
    print("  --max-paths N     Candidate paths to schedule, default 8")
    print("Example: python3 main.py --visual --capacity-info ")
    print("       map/01_linear_path.txt")
    print("Example: python3 main.py --gui map/02_simple_fork.txt")


def parse_positive_int(raw_value: str, field_name: str) -> int:
    """Parse a positive integer command-line value."""
    if not raw_value.isdigit():
        raise ValueError(f"{field_name} must be a positive integer.")

    value = int(raw_value)

    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")

    return value


def parse_positive_float(raw_value: str, field_name: str) -> float:
    """Parse a positive float command-line value."""
    try:
        value = float(raw_value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be a positive number.") from error

    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")

    return value


def parse_args(argv: list[str]) -> CliOptions:
    """Parse command-line arguments."""
    visual = False
    gui = False
    capacity_info = False
    verbose = False
    max_paths = 8
    gui_interval = 1.0
    positional: list[str] = []
    index = 1

    while index < len(argv):
        arg = argv[index]

        if arg == "--visual":
            visual = True
        elif arg == "--gui":
            gui = True
        elif arg == "--capacity-info":
            capacity_info = True
        elif arg == "--verbose":
            verbose = True
        elif arg == "--max-paths":
            index += 1
            if index >= len(argv):
                raise ValueError("--max-paths requires a value.")
            max_paths = parse_positive_int(argv[index], "max_paths")
        elif arg == "--gui-speed":
            index += 1
            if index >= len(argv):
                raise ValueError("--gui-speed requires a value.")
            gui_interval = parse_positive_float(argv[index], "gui_speed")
        elif arg.startswith("--"):
            raise ValueError(f"Unknown option: {arg}")
        else:
            positional.append(arg)

        index += 1

    if len(positional) not in {1, 2}:
        raise ValueError("Invalid number of arguments.")

    map_file = positional[0]
    max_turns = 1000

    if len(positional) == 2:
        max_turns = parse_positive_int(positional[1], "max_turns")

    return CliOptions(
        map_file=map_file,
        max_turns=max_turns,
        visual=visual,
        gui=gui,
        capacity_info=capacity_info,
        verbose=verbose,
        max_paths=max_paths,
        gui_interval=gui_interval,
    )


def run(options: CliOptions) -> int:
    """Run parser, pathfinder, simulator, and optional visualization."""
    parser = MapParser()
    parsed_map = parser.parse_file(options.map_file)

    graph = parsed_map.graph
    nb_drones = parsed_map.nb_drones

    path_finder = PathFinder(graph)
    paths = path_finder.find_multiple_paths(max_paths=options.max_paths)

    if not paths:
        print("No valid path found from start hub to end hub.")
        return 1

    simulator = Simulator(graph=graph, nb_drones=nb_drones)
    result = simulator.run(paths=paths, max_turns=options.max_turns)

    visualizer = TerminalVisualizer(graph=graph, use_color=options.visual)

    if options.verbose or options.visual:
        print(f"Drones: {nb_drones}")
        print(f"Candidate paths: {len(paths)}")
        for index, path in enumerate(paths, start=1):
            print(f"Path {index}: {path}")
        print()

    if options.visual:
        print(visualizer.graph_summary())
        print()
        print(
            visualizer.render_result(
                result,
                capacity_info=options.capacity_info,
                verbose=True,
            ),
        )
    elif options.verbose or options.capacity_info:
        print(result.to_verbose_output(capacity_info=options.capacity_info))
    else:
        print(result.to_subject_output())

    if options.gui:
        try:
            from flyin.visualization.graph_visualizer import GraphVisualizer
            gv = GraphVisualizer(
                graph=graph,
                result=result,
                nb_drones=nb_drones,
                interval=options.gui_interval,
            )
            gv.show()
        except ImportError:
            print(
                "Warning: matplotlib is not installed. "
                "Run 'pip install matplotlib' to enable the GUI.",
                file=sys.stderr,
            )
        except RuntimeError as error:
            print(f"GUI error: {error}", file=sys.stderr)

    if not result.success:
        print("Simulation did not finish within max_turns.", file=sys.stderr)
        return 1

    return 0


def main() -> int:
    """Program entry point."""
    try:
        options = parse_args(sys.argv)
    except ValueError as error:
        print(f"Error: {error}")
        print_usage()
        return 1

    if not Path(options.map_file).is_file():
        print(f"Error: map file not found: {options.map_file}")
        return 1

    try:
        return run(options)
    except ParserError as error:
        print(f"Parser error: {error}")
        return 1
    except ValueError as error:
        print(f"Error: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
