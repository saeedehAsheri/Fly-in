PYTHON  = python3
VENV    = venv
BIN     = $(VENV)/bin
MAP    ?= maps/easy/01_linear_path.txt

.PHONY: install run debug clean lint lint-strict gui

# -------------------------------------------------------------------
# Setup: creates a virtual environment and installs all dependencies.
# On Debian/Ubuntu Linux, if this fails with "ensurepip not available",
# run:  sudo apt-get install python3-venv python3-tk
# -------------------------------------------------------------------
install:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt

# Run the simulation
run:
	$(BIN)/python main.py $(MAP)

# Run with graphical GUI
gui:
	$(BIN)/python main.py --gui $(MAP)

# Run in debug mode with pdb
debug:
	$(BIN)/python -m pdb main.py $(MAP)

# Remove all caches and the virtual environment
clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache $(VENV)

lint:
	$(BIN)/flake8 .
	$(BIN)/mypy . --warn-return-any --warn-unused-ignores \
	              --ignore-missing-imports --disallow-untyped-defs \
	              --check-untyped-defs

lint-strict:
	$(BIN)/flake8 .
	$(BIN)/mypy . --strict
