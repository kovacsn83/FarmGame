# FarmGame Challenge API

A FarmGame baráti Alpha ranglistájának különálló FastAPI backendje. A szerver
PostgreSQLben tárolja a 10 éves Challenge eredményeit; a Pygame kliens ebben a
fejlesztési lépésben még nem kapcsolódik hozzá automatikusan.

Production API: <https://farmgame-production.up.railway.app>

- Állapot: <https://farmgame-production.up.railway.app/health>
- Swagger dokumentáció: <https://farmgame-production.up.railway.app/docs>

## Technológia

- FastAPI és Uvicorn
- SQLAlchemy 2
- PostgreSQL (`psycopg` 3)
- Alembic adatbázis-migráció
- SQLite kizárólag helyi fejlesztéshez és izolált teszteléshez

## Helyi indítás

A parancsokat a `server` könyvtárban futtasd:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:DATABASE_URL = "postgresql://user:password@localhost:5432/farmgame"
alembic upgrade head
uvicorn app.main:app --reload
```

Ha `DATABASE_URL` nincs megadva, a fejlesztői indítás helyi
`farmgame_leaderboard.db` SQLite-adatbázist használ. Production/Railway alatt
mindig PostgreSQL `DATABASE_URL` szükséges. A Swagger felület a `/docs`, az
OpenAPI-leírás az `/openapi.json` címen érhető el.

## Környezeti változók

- `DATABASE_URL` – Railway PostgreSQL kapcsolat; titokként/environment
  variable-ként add meg, ne commitold.
- `PORT` – Railway biztosítja. A start command automatikusan ezt használja.

API-kulcs az első Alpha verzióban nincs. A `player_id` azonosító, nem
hitelesítési token.

## Adatbázis és migráció

Az első Alembic-migráció létrehozza a `challenge_results` táblát. Egy futamot a
következő adatbázis-szintű UNIQUE constraint véd a duplikációtól:

```text
challenge_type + challenge_years + game_id
```

Az első elfogadott eredmény változatlan marad; későbbi beküldés nem írhatja
felül. Egy játékos több különböző `game_id` eredményt is beküldhet.

## Endpointok

### `GET /health`

Az API és az adatbázis-kapcsolat állapotát ellenőrzi érzékeny adatok nélkül.

### `POST /api/v1/challenges/ten-year/submit`

Közvetlenül fogadja a FarmGame helyi Challenge-rekord hét mezőjét:

```json
{
  "player_id": "3c8d50d3-3834-44ef-89c7-a74445676d33",
  "player_name": "Norbi",
  "game_id": "6644c88d-1dc1-42f8-97ba-82d7c5435663",
  "game_version": "0.1.0",
  "farm_value": 482350,
  "challenge_years": 10,
  "completed_at": "2026-09-09T13:24:00+02:00"
}
```

Sikeres beküldés HTTP 201 választ és az aktuális helyezést adja. Az endpointból
következő `challenge_type=ten_year`, valamint a szerver által generált
`submitted_at` nincs a kliens requestben. Ismételt futam HTTP 409 választ kap
`challenge_result_already_submitted` hibakóddal.

### `GET /api/v1/challenges/ten-year/leaderboard`

Alapból a Top 10-et adja; a `limit` 1–100 között állítható. Az opcionális
`game_version` paraméter előkészíti a verziónkénti szűrést. Rendezés:

1. `farm_value DESC`
2. `completed_at ASC`
3. `submitted_at ASC`
4. belső rekordazonosító `ASC`

Így azonos értéknél a korábban teljesített eredmény kerül előrébb. A publikus
válasz nem tartalmaz `player_id` vagy `game_id` értéket.

## Railway telepítés

1. Hozz létre Railway projektet a GitHub repositoryból.
2. A szolgáltatás Root Directory értéke legyen `/server`.
3. Adj hozzá Railway PostgreSQL szolgáltatást.
4. A backend szolgáltatás kapja meg a PostgreSQL által biztosított
   `DATABASE_URL` változót.
5. A verziózott `railway.json` előbb lefuttatja az Alembic-migrációt, majd
   elindítja az Uvicornt. A jelenlegi Railway szolgáltatásnál a start command
   explicit `8000`-es portot használ, amely megegyezik a public domain target
   portjával.
6. A deployment után ellenőrizd a `/health` és `/docs` útvonalakat.

Semmilyen connection stringet vagy jelszót ne adj hozzá a repositoryhoz.

## Tesztek

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

A tesztek ideiglenes SQLite-adatbázist használnak, és nem igényelnek valódi
Railway/PostgreSQL kapcsolatot.
