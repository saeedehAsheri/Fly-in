*This project has been created as part of the 42 curriculum by sasheri.*

# Fly-in

## Description

Fly-in is a Python 3.10+ project that routes a fleet of drones from a start hub to an end hub on a custom graph of connected zones. The program parses map files, builds its own graph structure, finds useful paths, schedules drone movement turn by turn, respects zone and connection capacities, handles restricted and blocked zones, and provides terminal visual feedback.

The main goal is to move all drones to the end hub in as few simulation turns as possible while keeping every movement valid.

## Instructions

### Setup (first time — Mac and Linux)

All dependencies are installed into an isolated virtual environment.
No system-wide installs are needed.

```bash
make install
```

This creates `venv/` and installs `flake8`, `mypy`, and `matplotlib` inside it.

> **Linux note:** if you get *"ensurepip not available"*, first run:
> `sudo apt-get install python3-venv python3-tk`

### Running the simulation

```bash
# Plain output (required subject format)
make run MAP=map/01_linear_path.txt

# Or directly:
venv/bin/python main.py map/01_linear_path.txt
```

### All command-line options

```text
python3 main.py [options] <map_file> [max_turns]

--visual          Colored terminal output (ANSI colors per zone type)
--capacity-info   Show zone and connection capacity usage each turn
--verbose         Show paths, turn numbers, success summary
--gui             Animated graphical window (requires desktop / $DISPLAY)
--gui-speed N     Seconds per turn in GUI mode (default: 1.0)
--max-paths N     Candidate paths for the scheduler (default: 8)
```

### Common usage examples

```bash
# Colored terminal with capacity diagnostics
venv/bin/python main.py --visual --capacity-info --verbose map/.../02_simple_fork.txt

# Full debug info
venv/bin/python main.py --visual --capacity-info --verbose map/.../03_priority_puzzle.txt

# Graphical animated display (Mac or Linux desktop)
make gui MAP=map/02_simple_fork.txt
# or slower animation:
venv/bin/python main.py --gui --gui-speed 1.5 map/.../01_maze_nightmare.txt
```

### Lint

```bash
make lint
```

### Clean

```bash
make clean    # removes __pycache__, .mypy_cache, and venv/
```

The default output follows the subject format: one line per simulation turn, with movement tokens like `D1-zone` or `D2-zoneA-zoneB` for a drone flying toward a restricted zone.

## Example input

```text
nb_drones: 2

start_hub: start 0 0 [color=green]
hub: waypoint1 1 0 [color=blue]
hub: waypoint2 2 0 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal
```

## Example output

```text
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
```

## Algorithm explanation

The implementation is split into four main parts:

1. **Parser**: reads the map file format described in the subject. It validates drone count, zones, metadata, capacities, duplicate zones, duplicate connections, invalid zone types, and malformed lines.
2. **Graph**: stores zones and bidirectional connections using custom dictionaries and adjacency lists. No graph libraries such as `networkx` or `graphlib` are used.
3. **Pathfinding**: uses Dijkstra for the best weighted path and a bounded DFS to collect several useful simple paths. Paths are sorted by movement cost, priority-zone preference, and length. This allows the simulator to distribute drones over multiple routes instead of using only one bottleneck path.
4. **Simulation**: schedules all drones turn by turn. It enforces `max_drones` for zones, `max_link_capacity` for connections, unlimited start/end hubs, blocked-zone avoidance, and two-turn movement into restricted zones. Within each turn, drones making normal (non-restricted) moves are processed first so that zones being vacated count as freed before restricted-zone transit capacity is checked. This two-phase ordering maximises throughput through bottleneck restricted zones.

Restricted zones are handled as multi-turn movement. On the first turn, the drone is displayed on the connection toward the restricted zone. On the next turn, the drone reaches that restricted zone and cannot move again during the same turn.

## Visual representation

The project includes two visualization systems in `flyin/visualization/`.

**Terminal visualizer** (`--visual`):

- Colored zone labels based on `color=<value>` metadata.
- Default colors for blocked (gray), restricted (red), and priority (cyan) zones.
- A map summary showing zones, coordinates, zone types, capacities, and connections.
- Colored simulation turns with turn numbers.
- Optional `--capacity-info` output showing zone occupancy and connection usage per turn.

**Graphical visualizer** (`--gui`, requires matplotlib):

- Animated matplotlib window showing the full zone graph and all drones moving turn by turn.
- Zones drawn as colored circles (diamonds for priority zones) using their `color=` metadata.
- Drones shown as labeled colored markers; multiple drones in the same zone are spread in a ring.
- Active zones highlighted in yellow on each turn.
- Connection capacity labels shown inline.
- Speed controlled with `--gui-speed` (seconds per turn).


## Project structure

```text
flyin/
├── domain/
├── parser/
├── pathfinding/
├── simulation/
└── visualization/
main.py
map/
README.md
Makefile
```

## Resources and AI usage

Resources used:

- Python documentation for dataclasses, typing, pathlib, heapq, and collections.
- 42 Fly-in subject and evaluation sheet.
- General algorithm knowledge about Dijkstra, DFS, and turn-based scheduling.
- https://en.wikipedia.org/wiki/Multi-agent_pathfinding

AI was used as a support tool to review structure, suggest test cases, improve explanations. The implementation decisions, project understanding, and final validation remain the responsibility of the learner.
