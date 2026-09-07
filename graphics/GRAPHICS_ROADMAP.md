# FarmGame — Graphics Roadmap

## Aktuális állapot

| Mérföldkő | Státusz | Eredmény |
| --- | --- | --- |
| M0 — Grafikai audit és Art Style Guide | Kész | [Részletes műszaki és művészeti alap](ART_STYLE_GUIDE.md) |
| M0.1 — Visual Concept Board | Kész | [Generation 1 → Generation 2 kreatív iránytű](VISUAL_CONCEPT_BOARD.md) |
| **M1 — Environment Polish** | **Kész — 2026. szeptember 7.** | Környezeti paletta, utak, tó, kerítések és fák célzott finomítása; regresszió- és teljesítményellenőrzés |

Az M1 tényleges hatókörét a felhasználó Environment Polish feladata határozza meg. Ez felváltja az M0/M0.1 dokumentumok korábbi, épületet és traktort is érintő referenciaminta-javaslatát. A korábbi roadmap jövőbeli témái továbbra is javaslatok; a soron következő mérföldkő pontos tartalma külön feladatban rögzítendő.

## M1 — Mi változott, és miért?

| Terület | Változtatás | Grafikai indok |
| --- | --- | --- |
| Fű | A betöltési tartalékszín a tényleges fűcsempe főszínére változott | Hiányzó kép esetén sincs élénkzöld stílustörés; a nyolc meglévő PNG és stabil elosztás megtartható |
| Talaj | Kisebb kontraszt a barázdán és a talaj világos/sötét belső élén | A növények továbbra is a fő információhordozók; a fajrajzok és kezelési/aratási jelek változatlanok |
| Utak | Visszafogottabb nyom- és peremtónus, állandó perempozíció, kevesebb textúrapont | Nyugodtabb burkolat; a textúra nem szakítja meg a keréknyomot; a szomszédok illeszkedése stabil |
| Kereszteződések | Eltűnt az erős középső világos pont | Kevésbé foltos csomópont, jól követhető úthálózat |
| Tó és part | Közvetlen 120×120 px-es rajz, simítás nélkül; földszínhez közelebb álló part; rövid vízfény a körbefutó belső kontúr helyett | A tó illeszkedik a pixelrajzokhoz, miközben a négy organikus változat és a nyugodt víz megmarad |
| Karám- és gyümölcsöskerítés | Az M1 utáni felhasználói finomítással 2 helyett 3 px-es faelem, kis bal/alsó anyagfény, rövid jobb felső áttetsző árnyék | Határozottabb körvonal; az összeolvadó területek belső éle továbbra sem rajzolódik |
| Farmházi telekkerítés | Az M1 utáni felhasználói finomítással 2 helyett 3 px-es keret | A zöld, sövényszerű karakter marad; az udvari elemek helyzete a vastagítástól nem változik |
| Fák | Megmaradt a három faj mérete, lombszíne és külső formája; lépcsőzött lombfény, közös áttetsző talajárnyék | A fény a bal alsó oldalról jön; az árnyék fűre, talajra és hóra is természetesen keveredik |
| Bokrok és kisebb dekoráció | Nincs új faj vagy dekoráció; az út apró részletei ritkultak | A projektben nincs meglévő bokorrenderelő; M1 nem növeli a vizuális zajt |

Az épületkörnyezetben meglévő fűalap maradt, nem készültek új földfoltok, burkolatok vagy épületdekorációk. A fa-, kerítés- és tóváltozások statikusak. Nincs új animáció vagy effekt. PNG, ikon, jármű, állat és UI nem módosult. Mentésformátum, foglalás, növekedés, szüret, útkeresés és gazdasági szabály nem változott.

## Teljesítmény

Reprodukálható mérőeszköz: `tools/benchmark_environment.py`. Alapfelbontás 1500×1000, világméret 100×80 csempe; 120 fa, 30 gyümölcsös, 20 mező, különböző épületek és úthálózat. 20 bemelegítő képkocka után 5×120 render, az öt kör képkockánkénti átlagának mediánja. A referencia a munkakezdéskor másolt `src`, alapja a `647b794` commit; a két mérés azonos scriptet és asseteket használ.

| Mérés | M1 előtt | M1 után |
| --- | ---: | ---: |
| Első render | 11,150 ms | 10,556 ms |
| Bemelegített render medián | 7,888 ms | 7,425 ms |

A mért környezeti CPU-renderidő **körülbelül 5,9%-kal csökkent**. Ez helyi, headless Pygame-mérés; nem teljes szimulációs FPS, nem hardverfüggetlen garancia. Ebben az azonos környezetű összehasonlításban nincs teljesítményromlás.

A fák legfeljebb hat 48×48 px-es RGBA felületet használnak (kb. 54 KiB nyers pixeladat), a kerítések legfeljebb tizenhat 24×24 px-eset (kb. 36 KiB). A kerítéshatárok legfeljebb nyolc elrendezését tároljuk; összeépítés és bontás értékalapú új kulcsot kap. Bemelegített állapotban fánként és látható kerítéscsempénként egy blit történik. A tó 2× köztes felülete és kicsinyítése megszűnt. Nincs új nagy textúra vagy képkockánként generált árnyékfelület.

Futtatás a projekt Python-környezetében:

```powershell
python -B tools/benchmark_environment.py
# Opcionális összehasonlítás egy korábban kimásolt src könyvtárral:
python -B tools/benchmark_environment.py --source C:\Temp\farmgame-before-src
```

## Ellenőrzések

- **585 teszt sikeres** a teljes `unittest` csomagban, ebből 6 új környezeti regresszióteszt.
- Mind a 16 útmaszk, mind a 4 variáns, minden csatlakozó irány és szomszédkombináció központi sávjának pixelilleszkedése ellenőrizve.
- Mind a 4 tóváltozat: helyes méret, átlátszó külső rész, tömör vízbelső, simítás nélküli alpha és különböző stabil forma.
- Kerítés: összeépítéskor nincs közös belső él, bontás után visszatér; cache és rajzolás nem módosítja a területadatot. Szabálytalan L alakú terület vizuálisan is ellenőrizve.
- Mindhárom fafaj érett/nem érett rajza, fűre/talajra/hóra kevert árnyéka; változatlan állapotadat és kameraeltolás melletti pixelpozíció.
- HUD/toolbar, Város, Ültetés, Naptár, Állattartás és Gyümölcsös választó: azonos állapottal renderelve az előtte/utána képek SHA-256 értéke megegyezik. A további UI-források változatlanok, meglévő regressziótesztjeik sikeresek.
- A meglévő mentés/betöltés, korábbi mentésváltozatok és objektumállapotok tesztjei a teljes csomag részeként sikeresek; a `save_system.py` nem változott. Felhasználói mentést nem írtunk felül.
- Vegyes farm előtte/utána nézete, az összes út- és tóváltozat, faállapotok és kerítések vizuálisan ellenőrizve. Az ideiglenes képek nem kerülnek az assetek vagy a Git commit közé.
- Zoom nincs implementálva a jelenlegi kamerában; a meglévő eltolásos kamera működése ellenőrizve. Nem készült új zoomrendszer.
- Az épület- és növényrajzoló függvények forrása változatlan, a kivétel kizárólag a tó renderelője; az érintett közös modulokban csak a fent felsorolt környezeti konstansok és funkciók módosultak.

## Érintett fájlok

- `src/constants.py` — fű tartalékszíne.
- `src/field_renderer.py` — kizárólag a talaj három tónusa.
- `src/road_renderer.py` — útanyag és textúra finomítása.
- `src/building_renderers.py` — tó/part és a farmházi telekkerítés vastagsága.
- `src/environment_renderer.py` — új, kis gyorsítótárazott környezeti segédmodul.
- `src/world.py` — a közös kerítésrajzoló használata.
- `src/orchards.py` — statikus faábrázolás és áttetsző környezeti árnyék.
- `tests/test_environment_rendering.py` — új környezeti ellenőrzések.
- `tests/test_orchard_trees.py` — az árnyékellenőrzés áttetsző keveréshez igazítása.
- `tools/benchmark_environment.py` — reprodukálható renderbenchmark.
- `graphics/GRAPHICS_ROADMAP.md` — jelen állapot- és eredményjelentés.
- `graphics/ART_STYLE_GUIDE.md`, `graphics/VISUAL_CONCEPT_BOARD.md` — az M0/M0.1 dokumentumok Gitbe vétele, hivatkozás az aktuális M1 hatókörre.

## Következő lépés

### M1 utáni felhasználói finomítások

- A Karám, Gyümölcsös és Farmház kerítése 2-ről 3 px-re vastagodott; az udvari elemek helyzete változatlan. A 22 kapcsolódó teszt sikeres.
- Külön felhasználói kérésre az épületek korábbi fedő zöld árnyéka semleges, 25%-os áttetsző sötétítésre változott. Az alatta lévő út, veteményes vagy fű színe és textúrája megmarad. Az eltolás továbbra is jobbra-felfelé mutat; az épülettestek rajza változatlan.
- Az épületárnyék méret és szín szerint gyorsítótárazott, legfeljebb 32 felülettel; nem készül új felület minden képkockán. Három új árnyékteszt vizsgálja a különböző talajokat, az öt épülettípust és a háttértől független cache-t. Az árnyékjavítás után 20 kapcsolódó teszt sikeres. Érintett fájlok: `src/building_renderers.py`, `tests/test_building_shadows.py`, jelen dokumentum. A fenti teljesítménymérés az eredeti M1 állapotra vonatkozik.

Az M1 környezeti alapja kész. A következő javasolt terület a UI olvashatósága és kisablakos tartalomelérése, majd a gépek és állatok egységesítése. Ezek ebben a mérföldkőben nem indultak el; a részletes hatókör új feladatban jelölhető ki.
