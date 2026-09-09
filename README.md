# FarmGame

FarmGame is a top-down 2D farming and management game built with Python and
Pygame CE. Build a road-connected farm, grow seasonal crops and fruit trees,
raise animals, process raw materials, manage finances, and watch vehicles carry
out jobs across the map.

The project is under active development. Its systems are data-driven where
practical and backed by an extensive automated regression test suite.

## Features

### Farming and orchards

- Three field sizes: 4×4, 6×6, and 8×8, with larger sizes unlocked through
  Farmhouse upgrades.
- Five crops: Wheat, Corn, Tomato, Alfalfa, and Hops.
- Seasonal windows, two-stage Tomato harvests, recurring Alfalfa harvests,
  perennial Hops, and a reduced-yield late-harvest period.
- Planting, watering, fertilizing, spraying, and harvesting with visible field
  state and yield bonuses.
- 4×4 Orchards containing Apple, Cherry, or Plum trees, each with its own
  lifespan, harvest season, yield, price, and pixel-art canopy.
- A dedicated Fruit Harvester that works inside connected orchards.

### Animals

- Cattle, pigs, and chickens with species-specific feed, water, production,
  movement, and life cycles.
- Milk, eggs, manure, beef, pork, and chicken meat production.
- Connected Animal Pens and eight-week trough refills delivered from storage or
  purchased automatically.
- Automatic slaughter with storage-capacity protection and notifications.

### Buildings and upgrades

- Roads, Farmhouses, Warehouses, Markets, Garages, Animal Pens, Ponds,
  Orchards, and Processing Plants.
- A prerequisite-aware, three-column Farmhouse development tree.
- Farmhouse I–III visuals and automation upgrades for watering, fertilizing,
  spraying, and harvesting fields.
- Shared Garage upgrades provide 4, 8, or 12 spaces per Garage, with a central
  fleet view and automatic parking reassignment.
- Shared Warehouse upgrades provide 500, 1,000, or 1,500 capacity per Warehouse.
- Processing Plant II adds a second production line and expands internal
  storage from 200 to 400 units.
- Level-dependent maintenance bases for Farmhouses, Garages, Warehouses, and
  Processing Plants. Annual maintenance is 10%, charged in 52 weekly parts.
- Construction limits include a maximum of three Garages, two Warehouses, and
  two Processing Plants.

### Vehicles and logistics

- Tractors, combines, fruit harvesters, water tanks, and trailers.
- A shared FIFO dispatcher, road pathfinding, animated travel, and persistent
  vehicle tasks.
- Physical delivery of seeds, feed, water, and Processing Plant inputs.
- A compact graphical Garage view; parked vehicles remain hidden inside covered
  Garages while the panel shows their live parking state.

### Processing and trade

- Processing Plant recipes for Canned Tomato, Cheese, Apple Juice, and
  Mayonnaise.
- Continuous weekly production and independently selectable production lines
  that can stop without losing an in-progress batch.
- Market sales with selectable quantity, stock, unit price, and total revenue.
- A ten-level Restaurant that buys selected processed products at a
  level-dependent premium and changes level according to demand fulfilment.
- A City panel providing access to the Bank, Market, and Restaurant.

### Economy, progression, and saves

- Whole-dollar UI formatting with grouped thousands; calculations and save data
  retain full precision.
- An interactive 52-week financial summary with categorised income, expenses,
  net balance, farm value, and Bank access.
- Three sequential loan tiers with cent-based repayments, unlock progression,
  and completion notifications.
- A 22-step tutorial Quest chain covering construction, animals, field work,
  vehicles, and spraying. Each completed Quest awards $100.
- White notifications for important events and storage-capacity blocks.
- Versioned JSON saves, eight named slots, validation, and compatibility
  migrations.
- A developer console and deterministic multi-year simulation tool.

## Screenshots

Screenshots can be added to [`docs/screenshots`](docs/screenshots). Suggested
images include a farm overview, the Farmhouse upgrade tree, processing and
sales, orchards and animals, and the graphical Garage view.

```markdown
![FarmGame overview](docs/screenshots/farm-overview.png)
```

## Requirements

- Python 3.10 or newer
- Pygame CE 2.5.7

## Installation

```bash
git clone https://github.com/kovacsn83/FarmGame.git
cd FarmGame
python -m venv .venv
```

Activate the environment on Windows PowerShell:

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

Run from the repository root so asset paths resolve correctly:

```bash
python src/main.py
```

New games use a 1500 × 1000 resizable window and a scrollable 100 × 80 tile
world.

## Application data and user data

Read-only application resources—images, icons, fonts, and configuration
defaults—remain part of the installed game under `assets/` and `src/`.

Writable user data has a separate, executable-location-independent root. On
Windows this is `%LOCALAPPDATA%\FarmGame`; if `LOCALAPPDATA` is unavailable,
FarmGame uses `.farmgame` below the current user's home directory. At startup
the game creates `saves/`, `logs/`, and `screenshots/` below that root. On first
start it also asks for a player name and creates `%LOCALAPPDATA%\FarmGame\player.json`.
This installation-wide local profile contains the chosen display name, creation
time, profile schema version, and an automatically generated persistent UUID.
The UUID contains no machine or Windows-account information and prepares later
online features without adding any network connection today. The reserved
`settings.json` file is not created yet.

The SaveSystem reads and writes `%LOCALAPPDATA%\FarmGame\saves` on Windows.
The repository-level `saves/` directory is now a legacy source: on startup its
slot files are copied into user data when the destination does not yet exist.
User-data saves always win filename conflicts, and legacy files are never
deleted. The JSON save schema is unchanged.

## Controls

| Action | Control |
| --- | --- |
| Use a tool, button, or world object | Left mouse button |
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

The toolbar provides City, Info, Road, Buildings, Planting, Watering,
Fertilizing, Spraying, Harvesting, Animal Husbandry, Orchard, and Bulldozer
tools. Mouse-wheel input scrolls supported panels and does not buy upgrades.

## Gameplay overview

Time advances in 52-week years. At 1× speed a week lasts 12 real seconds; at
2× speed it lasts 6 seconds. Weekly updates handle growth, production,
maintenance, loan repayments, animal needs, the Restaurant, and automation.

Field and orchard actions create tasks for compatible vehicles. Tractors plant,
fertilize, spray, and deliver goods; water tanks enable irrigation; combines
harvest fields; and fruit harvesters service orchards. Tasks wait safely when a
required vehicle or storage capacity is unavailable.

Products move through shared Warehouses, Processing Plants, the Market, and the
Restaurant. Automatic purchases use the normal market price plus the configured
delivery cost. Transactions remain visible in the rolling financial report.

## Project structure

```text
FarmGame/
├── assets/                 Images, icons, terrain, and UI artwork
├── docs/screenshots/       Public screenshots for this README
├── src/                    Game source code
│   ├── main.py             Initialization, input, and main loop
│   ├── game_state.py       Central state and upgrade synchronisation
│   ├── fields.py           Field state, growth, and harvest rules
│   ├── crops.py            Crop definitions
│   ├── orchards.py         Fruit-tree lifecycle and harvest rules
│   ├── buildings.py        Buildings, capacity, placement, and demolition
│   ├── processing.py       Recipes, production lines, and internal storage
│   ├── animals.py          Animal movement, production, and life cycles
│   ├── vehicle_manager.py  Fleet, dispatcher, and parking coordination
│   ├── tractor.py          Vehicle task state machines and movement
│   ├── economy.py          Purchases, sales, farm value, and maintenance
│   ├── financial_history.py  Categorised transaction history
│   ├── bank.py             Tiered loans and repayments
│   ├── restaurant.py       Restaurant demand and progression
│   ├── time_system.py      Weeks, years, seasons, and speed
│   ├── quest_system.py     Tutorial Quest definitions and rewards
│   ├── save_system.py      Save validation, serialization, and migration
│   └── ui.py               HUD, toolbar, panels, and popups
├── tests/                  Automated regression tests
├── tools/                  Headless simulation utilities
├── CHANGELOG.md            Development history
├── LICENSE                 MIT License
└── requirements.txt        Runtime dependency pins
```

## Testing

Run the regression suite and compilation check from the project root:

```bash
python -m unittest discover -s tests -b
python -m compileall -q src tests
```

Run the deterministic five-year simulation:

```bash
python -m tools.run_simulation --years 5 --seed 12345
```

Simulation reports are stored in `reports/` and excluded from version control.

## Application and user data

Bundled application resources such as images and configuration defaults remain
read-only files inside the installed game. Writable user data has a separate,
central location: `%LOCALAPPDATA%\FarmGame` on Windows, with `saves`, `logs`,
and `screenshots` subdirectories. If `LOCALAPPDATA` is unavailable, FarmGame
falls back to `.farmgame` in the current user's home directory.

The user-data paths for future `player.json` and `settings.json` files are
reserved but those files are not created yet. During this first migration
stage, the active SaveSystem deliberately continues to use the repository's
existing `saves/` directory; no existing save is copied, moved, or deleted.

## Contributing

Issues and focused pull requests are welcome. Before submitting a change, run
the automated tests and keep gameplay changes separate from structural
refactors where possible.

## License

FarmGame is available under the [MIT License](LICENSE).
