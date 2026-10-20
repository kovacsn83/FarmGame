# Ellenőrzési jegyzőkönyv – 2026-10-20

## Elkülönítés

- Stabil referenciaág: `codex/technical-stabilization`.
- Kiinduló commit: `5a230548db822cb1ef4f0627284f2b16ab0498f2`.
- A függőben lévő 2D-s Takarmánykeverő-változások előbb külön lezárva és
  feltöltve kerültek ebbe a commitba, a felhasználó jóváhagyásával.
- Kísérleti ág: `feature/farmgame-3d`, külön Git-worktree-ben.
- A 3D-s commit csak a `godot_3d/` mappát adja hozzá; sem `src/`, sem az
  eredeti `tests/`, sem a 2D-s dokumentáció nem módosul a referenciaállapothoz képest.
- Nincs verzióemelés, 2D-s EXE-build, mentésmódosítás vagy hálózati játékadatküldés.

## Futtatási környezet

Godot 4.5.1 Standard Windows x64, hivatalos `godotengine/godot` kiadási archívum.
Letöltés után SHA512 ellenőrzés a hivatalos `SHA512-SUMS.txt` alapján.
Nem rendszertelepítés: hordozható példány a worktree figyelmen kívül hagyott
`tmp/godot-tools/` mappájában. Grafikus renderer: OpenGL Compatibility,
Intel Iris Xe. A hordozható motor és a generált importcache nem kerül Gitbe.

## Eredmények

- A lezárt 2D-s kiinduló állapoton **895/895 Python kliensoldali teszt** sikeres.
- **5/5 új Python szerződés-/adatellenőrzés** sikeres: katalógusparitás,
  épületméretek/elrendezés/útszomszédság, demóútvonal, izoláció, projektkonfiguráció.
- Godot editor headless import sikeres, nincs GDScript parse- vagy futási hiba.
- Godot runtime tesztek: koordináták, kamera, határok, zoom, döntés, ray-alapú
  épületkijelölés, HUD/input elkülönítés, rács és traktorútvonal sikeres.
  Az aktuális ellenőrzésszámot a teszt végén a `3D CHECKS` sor közli.
- Grafikus teszt valódi Godot-ablakkal és képernyőkép-mentéssel is végrehajtva.
  A renderelt kép vizuálisan ellenőrizve; nem a headless kimenetből következtettünk rá.
- `git diff --check` és a referenciaághoz képesti, eredeti fájlokra korlátozott
  diff üres/sikeres a commit előtt.

Az automatikus tesztek nem helyettesítik a hosszabb, emberi kamerakezelési
próbát. Teljes játékmeneti paritást nem állítunk: a prototípus nem implementál
gazdasági vagy szimulációs rendszereket, csak megjelenítést és bemutató mozgást.
