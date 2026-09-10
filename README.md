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
- A local ten-year Challenge records one immutable Farm Value snapshot after
  Year 10, then lets the same farm continue without a time limit.
- Every farm has a persistent UUID `game_id`, distinct from the player profile
  and save slot, ready for later Challenge duplicate protection.
- White notifications for important events and storage-capacity blocks.
- Versioned JSON saves, eight named slots, validation, and compatibility
  migrations.
- A developer console and deterministic multi-year simulation tool.

### Online Challenge API layer

The client-side `src/online_api.py` module provides isolated calls for the
public Challenge service: a health check, the ten-year Top 10 leaderboard, and
submission of an existing local Challenge result. The production base URL is
`https://farmgame-production.up.railway.app`; development builds can override
it with the `FARMGAME_API_BASE_URL` environment variable.

Every request uses a 3-second connection timeout and a 5-second read timeout,
HTTPS certificate validation, and a `FarmGame/<game version>` User-Agent.
Connection failures, timeouts, invalid responses, validation errors, server
errors, and duplicate submissions are returned as structured `ApiResult`
values. No network call runs automatically at startup or Challenge completion,
so gameplay, saves, profiles, and local Challenge results remain offline-first.

At the Year 10 completion boundary the finished local result is persisted first,
game time pauses, and a dedicated completion dialog offers an optional online
submission. HTTP work runs on a daemon worker thread while all Pygame and local
state updates remain on the main thread. Submission metadata is stored in the
user-data Challenge result file by `game_id + challenge_years`, so choosing
Later, going offline, restarting the game, or opening another save slot cannot
lose or duplicate submission state. The Game Data panel provides the same
shared submission action for results that have not yet been uploaded.

The Game Data panel also opens the online **10-year Challenge – Top 10** view.
Its background worker performs one leaderboard request when opened and one more
only when the player chooses Refresh or Retry. The popup preserves backend rank
and ordering, uses the shared money formatter, and handles loading, empty,
offline, timeout, server-error, and invalid-response states without affecting
offline gameplay.

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
- Requests 2.32.5

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

Run the Python development version from the repository root:

```bash
python src/main.py
```

Asset paths are resolved relative to the source installation, so the runtime
does not depend on the process working directory.

## Windows release build

The portable Windows distribution uses PyInstaller in `onedir` mode. This
keeps Pygame assets and runtime libraries easy to inspect, starts faster than a
one-file bundle, and generally causes fewer antivirus false positives.

Install the separate build dependencies, then run the build script:

```powershell
python -m pip install -r requirements-build.txt
.\scripts\build_windows.bat
```

The script cleans only the repository's generated `build/` and `dist/`
directories, creates the no-console executable, verifies representative
runtime assets and forbidden private files, and produces:

```text
dist/FarmGame/FarmGame.exe
dist/FarmGame-0.1.1-Windows.zip
```

The archive name and Windows metadata use the same `src/game_version.py`
version as the game UI. The client assets are bundled; `server/`, tests, saves,
profiles, local Challenge results, databases, and environment files are
excluded. UPX compression is disabled. Because this first executable is not
digitally signed, Windows SmartScreen may display a warning, and some antivirus
products may occasionally report a false positive.

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
│   ├── game_identity.py    Persistent per-farm UUID generation
│   ├── game_version.py     Manually managed release version
│   ├── challenge.py        Local Challenge snapshots and status
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

## FarmGame versioning

The single release-version source is `src/game_version.py`. FarmGame uses
manually managed `MAJOR.MINOR.PATCH` versions and currently identifies itself
as **Alpha v0.1.1**. `MAJOR` denotes broad compatibility or full-release
milestones, `MINOR` a substantial feature milestone, and `PATCH` a corrective
release for an already distributed build.

Git commits do not increase the game version. Version changes are deliberate
release decisions made only after a development package has been completed and
tested. New slot saves record the game version as informational metadata while
the independent numeric save-schema version continues to control data
compatibility. This source can later also supply EXE builds, archive names,
GitHub Releases, update checks, and leaderboard submissions.

## Contributing

Issues and focused pull requests are welcome. Before submitting a change, run
the automated tests and keep gameplay changes separate from structural
refactors where possible.

## License

FarmGame is available under the [MIT License](LICENSE).
