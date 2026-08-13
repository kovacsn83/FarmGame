# FarmGame

FarmGame is a top-down 2D farming and management game built with Python and
Pygame CE. Build a connected farm, cultivate seasonal crops, raise animals,
manage storage and finances, and coordinate tractors and combines through an
animated vehicle task system.

The project is under active development. Its current focus is a stable,
modular foundation for expanding the simulation with further crops, animals,
vehicles, upgrades, and seasonal systems.

## Features

- A scrollable 100 × 80 tile world with camera culling and a resizable window.
- Roads, fields, and procedurally rendered buildings, including the Farmhouse,
  Warehouse, Market, Garage, Animal Pen, and Pond.
- Four seasonal crops: Wheat, Corn, Tomato, and Alfalfa.
- Planting, watering, fertilizing, crop growth, and animated harvesting.
- Cattle, pigs, and chickens with feed, water, production, movement, and life
  cycles.
- Tractors, combines, water tanks, and trailers managed through a shared FIFO
  dispatcher and road-based pathfinding.
- Inventory, market sales, maintenance costs, loans, and a central economy.
- A year/week time system, seasons, adjustable speed, and a farming calendar.
- A 21-step tutorial Quest chain with progress tracking.
- Versioned JSON saves with eight save slots and compatibility migrations.
- A developer console and a deterministic five-year simulation tool.

## Screenshots

Screenshots can be added to [`docs/screenshots`](docs/screenshots). Suggested
files for a public project page:

- `farm-overview.png` – a developed farm and the main HUD;
- `farming-calendar.png` – the seasonal farming calendar;
- `vehicles-and-fields.png` – tractors, implements, and field work;
- `animal-pens.png` – connected pens and animal husbandry.

Example Markdown after adding an image:

```markdown
![FarmGame overview](docs/screenshots/farm-overview.png)
```

## Requirements

- Python 3.10 or newer
- Pygame CE 2.5.7

## Installation

Clone the repository and enter the project directory:

```bash
git clone https://github.com/YOUR-USERNAME/FarmGame.git
cd FarmGame
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
& ".\.venv\Scripts\Activate.ps1"
```

On Linux or macOS:

```bash
source .venv/bin/activate
```

Install the dependency:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Running the game

Run the game from the repository root so asset paths resolve correctly:

```bash
python src/main.py
```

New games start in a 1500 × 1000 resizable window with a 100 × 80 tile world.
Local save files are written under `saves/`; this directory is intentionally
excluded from Git.

## Controls

| Action | Control |
| --- | --- |
| Use a tool or UI element | Left mouse button |
| Drag the camera over empty terrain | Hold and drag the left mouse button |
| Return to the Info tool | Right mouse button |
| Close a popup / open the game menu | `Esc` |
| Pause game time | `0` |
| Set 1× speed | `1` |
| Set 2× speed | `2` |
| Show or hide the Developer Console | `F3` |
| Developer crop-growth step | `G` |
| Developer quick save | `F5` |
| Developer quick load | `F9` |

The bottom toolbar provides Info, Road, Buildings, Planting, Watering,
Fertilizing, Harvesting, Animal Husbandry, and Bulldozer tools.

## Gameplay overview

Time advances in weeks, with 52 weeks per year. At 1× speed a week lasts 12
real seconds; at 2× speed it lasts 6 seconds. Weekly updates handle crop
growth, maintenance, loan repayments, animal consumption, and production.

Crops can only be planted and harvested in their configured seasonal windows.
Watering and fertilizing each provide a yield bonus. Field work is carried out
by vehicles: tractors plant and fertilize, tractors with water tanks irrigate,
and combines harvest mature crops.

Animals live in connected Animal Pen groups. Trough supplies are delivered by
tractors using trailers or water tanks. Animals consume supplies weekly,
produce goods, move independently within their pen, and follow species-specific
life cycles.

## Project structure

```text
FarmGame/
├── assets/                 Images and UI assets
├── docs/screenshots/       Public screenshots for the README
├── src/                    Game source code
│   ├── main.py             Initialization, event handling, and main loop
│   ├── game_state.py       Central references to the current game state
│   ├── world.py            World rendering and placement previews
│   ├── fields.py           Field state, growth, and harvest rules
│   ├── crops.py            Data-driven crop definitions
│   ├── buildings.py        Building definitions and placement rules
│   ├── animals.py          Animal data, movement, and production
│   ├── vehicle_manager.py  Shared dispatcher and vehicle coordination
│   ├── tractor.py          Vehicle task state machines and movement
│   ├── economy.py          Purchases, sales, and weekly economy
│   ├── time_system.py      Weeks, years, seasons, and speed
│   ├── quest_system.py     Tutorial Quest definitions and progress
│   ├── save_system.py      Save validation, serialization, and migration
│   └── ui.py               HUD, toolbar, panels, and popups
├── tests/                  Automated regression tests
├── tools/                  Headless simulation utilities
├── CHANGELOG.md            Development history
├── LICENSE                 MIT License
└── requirements.txt        Runtime dependencies
```

## Testing

Run the complete automated test suite from the project root:

```bash
python -m unittest discover -s tests
```

Check that all source and test modules compile:

```bash
python -m compileall -q src tests
```

Run the deterministic five-year simulation:

```bash
python -m tools.run_simulation --years 5 --seed 12345
```

Generated simulation reports are stored in `reports/` and are excluded from
version control.

## Contributing

Issues and focused pull requests are welcome. Before submitting a change,
please run the complete automated test suite and keep gameplay changes separate
from structural refactors where possible.

## License

FarmGame is available under the [MIT License](LICENSE).
