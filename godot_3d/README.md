# FarmGame 3D – első megjelenítési prototípus

Külön kísérlet, **nem a teljes FarmGame Godot-portja**. A 2D-s Python/Pygame
játék és a `0.1.3` verzió változatlan. A prototípusban sem pénz, sem termelés,
sem háttérben futó FarmGame-szimuláció nincs: csak szintetikus bemutatóadatok.

## Megnyitás és indítás

Godot **4.5 vagy újabb 4.x Standard** (nem szükséges .NET). Ellenőrzéshez
Godot 4.5.1 Standard Windows x64 került használatba. A Compatibility renderer
OpenGL-lel működik, külső modellek, Blender és bővítmények nélkül.

1. Godot Project Manager → Import → válaszd a mappa `project.godot` fájlját.
2. Import & Edit, majd **F6** a nyitott főjelenethez vagy **F5** a projekthez.
3. A 2D-s játék indításához továbbra is a megszokott `src/main.py` tartozik.

Parancssorból, saját Godot elérési úttal:

```powershell
& 'C:/path/to/Godot.exe' --editor --path 'C:/Projects/FarmGame-3D/godot_3d'
& 'C:/path/to/Godot.exe' --path 'C:/Projects/FarmGame-3D/godot_3d'
```

A fejlesztéshez letöltött hordozható tesztpéldány helye a helyi worktree-ben:
`tmp/godot-tools/runtime/Godot_v4.5.1-stable_win64.exe`. Ez nem része a Gitnek,
nem új FarmGame EXE-build és nem rendszertelepítés. Másik gépen saját Godot kell.

## Vezérlés

| Művelet | Vezérlés |
|---|---|
| Mozgás a térkép felett | WASD vagy nyilak; jobb egérgomb + húzás |
| Vízszintes forgatás | Q/E vagy középső egérgomb + vízszintes húzás |
| Döntés | Középső egérgomb + függőleges húzás, 35–60° |
| Zoom | Egérgörgő, korlátozott ortografikus méret |
| Alaphelyzet | R / Home vagy HUD-gomb |
| Csempe, épület kijelölése | Bal egérgomb |
| Logikai rács | G vagy HUD-kapcsoló |
| Traktor demó megállítása | HUD-gomb – csak az animációt állítja meg |
| Kilépés | Esc vagy az ablak bezárása |

A kamera fókusza a térképhatárokon belül marad. A széleken a kamera kifelé
is láthat; nincs talajszintű, belső vagy karaktervezérelt nézet. A HUD-panelek
feletti egérműveletek nem jelölnek ki mögöttük csempét.

## Koordináták és referenciaadatok

- Logikai térkép: **100 oszlop × 80 sor**, a jelenlegi 2D-s katalógusból.
- `col → X`, `row → Z`, felfelé `Y`; egy csempe egy Godot-egység/metrikus méter.
- Csempe közepe: `(col + 0.5, 0, row + 0.5)`, indexelés nullától.
- A korábbi 20 pixeles 2D-s méret csak forrásmetaadat, nem 3D-s fizikai méret.
- A kijelölés 3D-s sugárlekérdezést használ; az épületekhez csak kijelölési
  ütközőtérfogat tartozik, nem játékmeneti ütközés vagy építési rendszer.

`data/reference.json` a központi Python-katalógus származtatott pillanatképe.
Nem párhuzamos gazdasági szabályrendszer. Ellenőrzése/újragenerálása a repo gyökeréből:

```powershell
& C:/Projects/FarmGame/.venv/Scripts/python.exe -B godot_3d/tools/export_reference.py --check
& C:/Projects/FarmGame/.venv/Scripts/python.exe -B godot_3d/tools/export_reference.py
```

A bemutató Farmház 8×8-as telke I. szintű, 3×3-as házat mutat. Raktár 5×4,
Garázs 4×4, Feldolgozó üzem 6×5, Takarmánykeverő 12×8 (bal alsó 4×4-es üzemi
rész és L alakú udvar). A 4×4, 6×6, 8×8 mezők egyszerre látszanak, kizárólag
méretbemutatóként – ez nem jelent fejlesztési szintek feloldását a valódi játékban.
A fixture épületei nem fedik egymást, útszomszédságukat külön teszt ellenőrzi.
Nincs interaktív építés; az eredeti elhelyezési logika nem lett újraimplementálva.

## Mi demonstrációs és mi hiányzik?

A talaj, utak, növények, épületek, traktor és kameranézet Godot primitívekből
készül. A traktor egy előre megadott, ellenőrzött úthurokon mozog. Ez **nem**
az eredeti útkereső, Dispatcher, szállítás vagy járműsebesség másolata.

Még nincs átültetve: gazdaság, áralkalmazás/fenntartás, növény- és állati
termelés, feladatkezelés, valódi szállítás, Feldolgozó/Étterem/Takarmánykeverő
működés, fejlesztések, játékidő, küldetések, mentések, Challenge és online Top 10.
Az eredeti implementációk továbbra is a referencia és változatlanul megvannak.

A futó prototípus nem olvas felhasználói mentést, nem ír a FarmGame
adatkönyvtárába, nem módosít sémát, nem hálózatozik és nincs backend-végpontja.
Az engine saját user könyvtára külön `FarmGame3DPrototype`; fájlnaplózás tiltva.
Csak az opcionális tesztképernyőkép ír a külön worktree `tmp/` mappájába.

## Tesztek

```powershell
& C:/Projects/FarmGame/.venv/Scripts/python.exe -B godot_3d/tools/check_prototype.py
& 'C:/path/to/Godot.exe' --headless --path godot_3d --editor --quit
& 'C:/path/to/Godot.exe' --headless --path godot_3d --script res://tests/smoke_test.gd
```

Grafikus ellenőrzés képernyőképpel (nem headless, automatikusan kilép):

```powershell
& 'C:/path/to/Godot.exe' --path godot_3d --script res://tests/smoke_test.gd -- --capture
```

A futás végén a `3D CHECKS` sor adja a tényleges eredményt. A képernyőkép a
worktree `tmp/farmgame-3d-preview.png` fájlja, nincs commitolva. A tesztben
a kamera minden fő iránya, a ray/csempe-megfelelés, az épületkijelölés, a
zoom/döntés korlátai, inputesemények és demóútvonal is szerepel.

## Következő lépés

Először kézzel próbáld ki a kamerát és a méretarányokat. Utána külön,
csak olvasó Python → Godot állapot-pillanatkép szerződést érdemes tervezni.
Ez a meglévő szimulációt tekintené hitelesnek; nem kell egyszerre Godotban
újraírni a gazdasági és játékmeneti rendszereket. Mentéskompatibilitás és
interaktív parancsok csak külön tervvel és paritástesztekkel következzenek.

API-referencia: [Godot Camera3D 4.5](https://docs.godotengine.org/en/4.5/classes/class_camera3d.html),
[Godot parancssor 4.5](https://docs.godotengine.org/en/4.5/tutorials/editor/command_line_tutorial.html).
