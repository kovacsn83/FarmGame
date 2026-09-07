# FarmGame — Art Style Guide és grafikai audit

**Mérföldkő:** Graphics Overhaul M0

**Dátum:** 2026. szeptember 7.

**Státusz:** a jelenlegi projektből levezetett grafikai audit és megvalósítási javaslat. Az előírt célértékek a későbbi grafikai munkát irányítják; M0-ban nem kerültek be a játékba.

## 1. Vezetői megállapítás

A FarmGame jelenlegi világa jól továbbfejleszthető: négyzetrácsos, felülnézetes, visszafogott vidéki gazdaság, jól elkülönülő épületfunkciókkal és növénysorokkal. A terrakotta farmház, a csíkos piac, a szürke gazdasági épületek, a barna földutak és a tompa zöld fű együtt már használható vizuális alapot alkotnak. Nem indokolt sem izometrikus nézetre váltani, sem minden elemet újrarajzolni.

**Összesített szerkesztői értékelés: ★★★☆☆ — közepes, jó alapokkal.** Ez az egységesség és olvashatóság megítélése, nem a részletek számának vagy a fejlesztési munka mennyiségének osztályozása. A legfontosabb eltérések a pixelkezelésben, az árnyékolásban, az objektumok részletességében és a felület hierarchiájában vannak.

A cél: **nyugodt, földszínekre épülő, jól olvasható modern pixel-art stratégiai játék**, ahol a világ tárgyai tiszta sziluettekkel, a felület pedig egyszerű piktogramokkal és könnyen olvasható szöveggel kommunikál. A világ pixelrácsa és a UI szövege eltérő technikát használhat, ha ez tudatos és következetes.

### 1.1. Az audit módszere és határai

- A projekt képfájljainak teljes leltára, méret- és képmód-ellenőrzése; a 18 ikoncsalád és méretváltozataik, a fűváltozatok, a küldetéskép és az indítókép vizuális áttekintése.
- A rajzolást, képbetöltést, kamerát, UI-t és vizuális állapotokat meghatározó források áttekintése. A kódban rajzolt grafika ugyanolyan része az auditnak, mint a PNG-k.
- A meglévő Pygame-renderelők memóriabeli kirajzolása: Farmház I–III., raktár, piac, garázs, feldolgozó, tó; öt növény négy növekedési fázisa; három fafaj érés előtti és szüretelhető állapota; három állatfaj és öt jármű/munkagép négy iránya; mind a 16 útcsatlakozási maszk mintája.
- A HUD/toolbar és reprezentatív popupok — Ültetés, Gazdálkodási naptár, Város — memóriabeli vizuális ellenőrzése. A többi panel felépítését és állapotait forrásból vizsgáltam.
- A memóriabeli nézetek auditminták, nem új sprite-ok vagy új UI-tervek. Nem készültek mentett képek, nem indult mentést módosító játékfolyamat, nem változott grafikai vagy logikai forrásfájl.
- Ez nem teljes interaktív végigjátszás, minden mentésállapotot lefedő UI-teszt vagy mozgásvideós ellenőrzés. Az animációk időbeli értékelése kódvizsgálaton alapul. A kisebb ablakokkal kapcsolatos, külön jelölt kockázatok későbbi ellenőrzési feladatok.
- Külső stílusreferencia és új képgenerálás helyett a projekt saját grafikai nyelve az irányadó.

## 2. Grafikai leltár és technikai kiindulópont

### 2.1. Képfájlok: összesen 84

Az útvonalak ebben a fejezetben a projekt gyökeréhez viszonyítottak.

| Hely | Darab | Ellenőrzött méret / mód | Szerep |
| --- | ---: | --- | --- |
| `assets/images/icons/master/` | 18 | 1254×1254, RGBA | Nagy felbontású ikonforrások; nem világ-sprite-ok |
| `assets/images/icons/20/` | 18 | 20×20, RGBA | HUD-hoz használt és további rendelkezésre álló változatok |
| `assets/images/icons/24/` | 18 | 24×24, RGBA | Toolbar-ikonok és további változatok |
| `assets/images/icons/64/` | 18 | 64×64, RGBA | Nagyobb ikonváltozatok; a fő toolbar 24 px-es |
| `assets/images/terrain/grass/grass_01.png`–`grass_08.png` | 8 | 20×20, RGB | A világ tényleges fűcsempéi |
| `assets/images/terrain/grass/grass_preview.png` | 1 | 400×240, RGB | Előnézeti kép; a fűbetöltő nem ezt használja |
| `assets/images/quests/master/Tutorial.jpg` | 1 | 977×977, RGB | Festett jellegű küldetésportré forrása |
| `assets/images/quests/100/Tutorial-100.jpg` | 1 | 100×100, RGB | A küldetéspanel tényleges képe |
| `assets/images/splash/kn_app_studio.png` | 1 | 1024×1024, RGB | Stúdió-indítókép |

Az ikoncsaládok teljes listája és jelentése:

| Master fájlnév | Jelenlegi jelentés / használat | Auditmegjegyzés |
| --- | --- | --- |
| `animal_husbandry.png` | Állattartás | Tehénsziluett; a lábak a legkisebb méretben vékonyak |
| `bulldozer.png` | Bontóeszköz | Jellegzetes gépsziluett, jó elkülönítés |
| `calendar.png` | Gazdálkodási naptár | Apró belső osztások; 20 px-en külön vizsgálandó |
| `city.png` | Város | Több épülettömb, jól elkülönül a háztól |
| `cursor.png` | Info/kijelölő eszköz | Toolbar-piktogram, nem igazolt egyedi egérkurzor |
| `dropdown_menu.png` | Menü | Tiszta háromvonalas forma |
| `fruit_tree.png` | Gyümölcsös | Sűrű koronabelső; a negatív terek méretérzékenyek |
| `house.png` | Épületek | Erős, egyszerű házsziluett |
| `plant.png` | Ültetés | Jó levéljel, kevés részlet |
| `road.png` | Útépítés | Felfestéses útjel; a világ földútját csak általánosan jelképezi |
| `spraying.png` | Permetezés | Permetezőflakon, a pontok kis méretben gyengék |
| `time_pause.png` | Szünet | Egyértelmű két sáv |
| `time_speed_1x.png` | Normál idő | Egy háromszög |
| `time_speed_2x.png` | Gyorsított idő | Két háromszög |
| `time_speed_3x.png` | Korábbi/tartalék időfokozat | A képfájl létezik, de az aktuális választható fokozatok közt nincs 3× |
| `toolbar-fertilizer.png` | Trágyázás | Zsák és növényjel; a belső rajz kis méretben zsúfoltabb |
| `tractor.png` | Aratás | Oldalnézetes traktor; a tényleges aratógép kombájn, ezért jelentésbeli pontatlanság |
| `watering.png` | Locsolás | Olvasható kanna; a vízcseppek méretérzékenyek |

A 20/24/64 mappák ugyanennek a 18 családnak a változatait tartalmazzák. A fájlnevek méretutótagjai kötőjelesek vagy aláhúzásosak; az aktuális betöltés explicit neveket használ. A névnormalizálás későbbi karbantartási feladat lehet, önmagában nem vizuális prioritás.

### 2.2. A világ jelentős része procedurális grafika

| Kategória | Tényleges elemek | Fő forrás |
| --- | --- | --- |
| Épületek | Farmház I–III. és régi lábnyom kezelése, raktár, piac, garázs, feldolgozó | `src/building_renderers.py`, `src/buildings.py` |
| Udvari részletek | Farmház kerítése, beálló, mellékgarázs, medence | `src/building_renderers.py` |
| Növények | Búza, kukorica, paradicsom, lucerna, komló; négy vizuális növekedési fázis | `src/field_renderer.py`, `src/crops.py` |
| Gyümölcsfák | Alma, cseresznye, szilva; fajonkénti lombkorona és érett gyümölcs | `src/orchards.py` |
| Állatok | Szarvasmarha, sertés, csirke; négy irány, egyes fajoknál stabil egyedi eltérések | `src/animal_renderer.py`, `src/animals.py` |
| Gépek | Traktor, kombájn, gyümölcsszüretelő, locsolótartály, pótkocsi | `src/tractor.py`, `src/vehicle_types.py` |
| Pótkocsi-rakomány | Üres plató, lucerna és a többi nem üres típushoz közös másik színezés | `src/tractor.py`, `_draw_trailer` |
| Utak | Négyirányú csatlakozások, végek, sarkok, kereszteződések, nyomvályúk, négy textúraváltozat | `src/road_renderer.py` |
| Kerítések | Összeolvadó karám- és gyümölcsöshatárok; külön farmházi keret | `src/world.py`, `src/building_renderers.py` |
| Víz / terep | Organikus tópart, sekély/mély víz, statikus vízvonalak; fű és művelt talaj | `src/building_renderers.py`, `src/world.py`, `src/field_renderer.py` |
| Etető / itató | 14×7 px-es vályúk, töltöttségi ábrázolás, vízfény | `src/animal_troughs.py` |
| Interakciós jelölések | Rács, elhelyezési/bontási keret, aratási keret, talajkezelési pontok | `src/world.py`, `src/field_renderer.py`, `src/orchards.py` |
| UI | HUD, toolbar, információs és választópanelek, piac/eladás, fejlesztés, bank, pénzügy, étterem, naptár, küldetés, értesítés, tooltip | `src/ui.py`, kapcsolódó állapotmodulok |
| Menü / overlay | Indítókép, főmenü, játékmenu, mentés/betöltés, megerősítés, szövegbevitel, fejlesztői konzol | `src/startup_ui.py`, `src/game_menu.py`, `src/save_slots_ui.py`, `src/developer_console.py` |

Nem találtam külön hegy-, szikla-, erdő-, vadnövény-, híd-, időjárás- vagy részecske-spritekészletet. A Város, Bank és Étterem jelenleg UI-szolgáltatásként szerepelnek; nem hiányzó, már implementált világépület-sprite-ként értékelendők. Külön betöltött sprite sheet vagy képkockás animációs képsor sem található az assetleltárban.

### 2.3. Méret és perspektíva: ami ma ténylegesen létezik

- `TILE_SIZE = 20`; a világ 100×80 csempe, vagyis 2000×1600 világpixel.
- Alapablak: 1500×1000; felső HUD és alsó toolbar egyaránt 50 px magas. A kamera eltolja a nézetet, a jelenlegi kamerakód nem alkalmaz perspektivikus vetítést vagy zoomot.
- Az épületek többcsempés felülnézeti rajzok; a tető dominál, a bejárat és rámpa alul segíti az azonosítást.
- Az állatok 20×20-as, a járművek 24×24-es átlátszó munkafelületből készülnek, 90°-os forgatásokkal. A tényleges festett sziluett a vászonnál kisebb lehet.
- A nagy ikonforrások simított piktogramok, nem nagyított 20 px-es pixelrajzok. A UI szövege élsimított; a fő program `SysFont(None, 24)` betűt használ.
- A tó 2× felbontáson készül, majd `smoothscale` kicsinyíti. Az épületek, növények és gépek jellemzően közvetlen egészpixeles alakzatokból állnak.

## 3. Grafikai audit kategóriánként

Értékelési skála: **★★★★★ nagyon jól sikerült; ★★★★☆ jó; ★★★☆☆ közepes; ★★☆☆☆ fejlesztendő; ★☆☆☆☆ újratervezendő.** A kevés animáció és dekoráció önmagában nem hiba: a stratégiai áttekinthetőség előnyt élvez.

### 3.1. Épületek — ★★★★☆ jó

**Jól sikerült:** a pirosas farmház, a piros–krém csíkos piac és a szürkés ipari tetők funkció szerint elkülönülnek. A raktár rámpája, a piac pultja és a feldolgozó kapuja kevés elemből ad karaktert. A Farmház III. telke a mellékgarázzsal, beállóval és medencével jól jelzi az előrelépést.

**Kilóg:** az épületek többnyire 2 px-es kontúrja mellett a telekkeret 4 px vastag. A piac és a raktár apró tárgyai részletesebbek a garázs tömbjénél. A garázs és a feldolgozó hasonló szürkés tetőfelületei első pillantásra kevésbé karakteresek. A raktár- és garázsszintek nem kapnak külön olyan látványos világváltozatot, mint a farmház; ez információs lehetőség, nem automatikus igény három új épületre.

**Kis javítás később:** közös kontúrszabály, következetes tetősík-fény, azonos kapu- és fémanyagpaletta; a garázs és feldolgozó elkülönítése egy-egy nagy jellegzetességgel. Szintenként legfeljebb egy jól látható tető- vagy bejárati változás, ha a szintet a világban is szükséges olvasni. A meglévő alaprajzok maradjanak.

### 3.2. Szántóföldek és növények — ★★★★☆ jó

**Jól sikerült:** a barázdák egységes alapot adnak, az öt növény külön renderelőt kapott. A búza kalászos sora, a kukorica magasabb szára, a paradicsom terméspontjai és a komló támrendszere megkülönböztethető. Négy vizuális fázis támogatja a növekedés követését; a stabil variáció nem villog.

**Kilóg:** a korai fázisok szükségszerűen hasonlóak; a lucerna és a komló zöldje fű előtt kevésbé különül el. Az erős sötét barázdák kis növények mellett uralják a képet. A barna/kék/sárga kezelési pontok önmagukban főleg színkódok; a trágyázás jelölése a talajon gyenge lehet. A `CROPS.colors` nem azonos a teljes tényleges rendererpalettával, ezért az nem használható önmagában grafikai színszabványként.

**Kis javítás később:** enyhén csökkentett barázdakontraszt, fajonként egy állandó, méretben is látszó alaki jegy, a kezelési jelölők szín mellett alak szerinti elkülönítése. A négy fázis, az arathatóság és a késői aratás már létező jelentése maradjon; az érett kinézet nem jelenthet automatikusan indítható munkát.

### 3.3. Gyümölcsfák — ★★★☆☆ közepes

**Jól sikerült:** alma, cseresznye és szilva külön lombszínt és részben külön sziluettet használ. A szilva széles, négykaréjos koronája eltér a cseresznye szabálytalanabb alakjától. A gyümölcs és a szüreti keret a tényleges szüretelhetőséghez kötött.

**Kilóg:** a korona egymásra rajzolt körökből áll, a világos folt körszerű emblémának hat. Ez egyszerűbb formanyelv a mezők és tetők anyagábrázolásánál. Az alma és a cseresznye apró piros termése önmagában nem elég fajjel. A fiatal, termőkorú és elöregedett fa nem kap önálló, életkort követő lombsziluettet a jelenlegi rajzolóban.

**Kis javítás később:** néhány nagy, lépcsőzött lombfolt a koncentrikus körhatás helyett; fajonként stabil külső forma; a világos rész a bal alsó oldalon maradjon. A kor és az évszak külön vizuális tengely legyen, a szüret állapotát továbbra is a játék szolgáltassa.

### 3.4. Állatok — ★★★☆☆ közepes

**Jól sikerült:** barna marha, rózsaszín sertés, krém csirke: gyors színazonosítás. Közös négyirányú nézet, azonos sprite-vászon és árnyéksegéd. A kis egyedi marha- és sertésváltozatok nem növelik túl a részletsűrűséget.

**Kilóg:** a 20 px-es vásznak miatt a csirke viszonylag nagy a marhához képest, miközben a fej- és lábrészletek nagyon kicsik. Nincs külön járásképsor; az irányok ugyanannak a rajznak a forgatásai. Az árnyék eltér az épületekétől, de legalább jobbra-felfelé tolódik.

**Kis javítás később:** a csirke festett testének visszafogott kicsinyítése ugyanazon vásznon, erősebb fej/test arányok, fajonként egy felismerési jegy. A logikai helyigény és a mozgási szabály nem következik a rajz méretéből, nem módosítandó grafikai egységesítés címén.

### 3.5. Járművek és munkagépek — ★★★☆☆ közepes

**Jól sikerült:** a piros traktor, zöld kombájn, sárga gyümölcsszüretelő, ezüst tartály és barna pótkocsi jól elkülönül. A kabin, kerék és munkavégző rész kevés pixelből is felismerhető. A garázs parkolónézete ugyanazt a grafikát használja, ami jó következetességi alap.

**Kilóg:** a gépek vetett árnyéka lefelé, `(0, +3)` irányban jelenik meg, szemben az épületek jobb felső árnyékával. A 24 px-es gépvászon szélesebb a 20 px-es útcsempénél, ezért fordulókban és vontatmánnyal az átfedések külön figyelmet kívánnak. A pótkocsi nem üres rakományainál a rajzoló csak lucerna és egy közös másik szín között tesz különbséget; az összes felsorolt árutípusnak nincs egyedi látványa.

**Kis javítás később:** árnyékirány javítása, közös gumi/felni/kabin tónusok, jól olvasható gépfront. A rakományt először néhány anyagcsoportra bontott nagy folt különböztesse meg; ne minden termékhez apró tárgyrajz. Ne szélesítsük az utat pusztán a sprite-vászon mérete miatt.

### 3.6. Utak — ★★★★☆ jó

**Jól sikerült:** földszínek, folytonos keréknyomok, szomszédságból számolt csatlakozások és stabil változatok. A 16 maszk lefedi az elszigetelt csempét, végeket, egyeneseket, kanyarokat és elágazásokat. A bal/alsó világosabb perem illik a jelenlegi fényirányhoz.

**Kilóg:** a 20 px-es csempén a két keréknyom, a szegély, kövek és foltok együtt helyenként sűrűek. A rövid végek és csomópontok apró mintái eltérő textúrasűrűséget adnak. A UI útikon felfestéses burkolatot sugall, míg a világban földút van.

**Kis javítás később:** kevesebb erős belső pötty, a csomópont közepén nyugodtabb felület, a 16×4 maszk/változat kombináció peremellenőrzése. Az útikon jelentésének finomítása alacsonyabb prioritású, mint a hálózat folytonossága.

### 3.7. Kerítések és telekhatárok — ★★☆☆☆ fejlesztendő

**Jól sikerült:** az összeérő karámok és gyümölcsösök csak közös külső kerítést kapnak, nincsenek felesleges belső falak. A terület határa egyértelmű.

**Kilóg:** a barna, 4 px-es vonal és a farmház zöld, szintén 4 px-es kerete inkább vastag területjelölés, mint ugyanabba a világba tartozó anyag. A vastagság egy csempe ötöde, kis állatok és növények mellett túl hangsúlyos. Azonos oldalfény és anyagtónus nincs minden kerítésen.

**Kis javítás később:** a jelenlegi vonal helyén 2 px-es fő elem, ritka 3–4 px-es sarok/oszlop; egységes faanyag, vagy a farmházi zöld határ tudatos sövényként kezelése. Ne keletkezzen új kapu- vagy átjárhatósági szabály, és maradjon meg az összevont területhatár.

### 3.8. Tavak és víz — ★★★☆☆ közepes

**Jól sikerült:** természetes körvonal, elkülönülő part, sekély és mély víz, visszafogott hullámvonalak. A színek illenek a földszínekhez, a tó nem uralja a pályát. A farmházi medence és az itató vízként felismerhető.

**Kilóg:** a tó simított széle technikailag eltér az egészpixeles világtárgyaktól. A körbefutó, egymásba ágyazott vízsávok kissé kontúrtérképszerűek. A tó, medence és itató külön vízpalettát használ, közös anyagcsalád nélkül.

**Kis javítás később:** a jelenlegi alak megtartása mellett tudatos pixelperem, kevesebb folytonos belső sáv, közös víztónusok. A vízvonalak jelenleg statikusak; az animált csillanás későbbi, opcionális finomítás.

### 3.9. Fű, talaj és udvari tereprészletek — ★★★★☆ jó

**Jól sikerült:** a nyolc kis kontrasztú fűcsempe nyugodt alapot ad. A fő árnyalat például a `grass_01.png` fájlban `#5B8B49`; kevés sötétebb/világosabb folt töri meg. A talaj, út és udvari burkolat külön anyagként olvasható.

**Kilóg:** a betöltési tartalék `COLOR_GRASS = #228B22` jóval élénkebb a tényleges fűnél. Assetbetöltési hibánál ezért a hangulat is megváltozik. Nagy homogén mezőn a csempeismétlődés észrevehető lehet, bár a jelenlegi determinisztikus keverés ezt mérsékli. A beálló részletesebb burkolata mellett az egyéb udvarok üresek; ez nem indokol automatikus dekorálást.

**Kis javítás később:** a tartalékszín illesztése a fűhöz, szomszédos csempék széleinek ellenőrzése, ritka textúrafoltok. A talaj részletsűrűsége mindig alacsonyabb legyen az interaktív tárgyakénál.

### 3.10. Etetők és itatók — ★★★★☆ jó

**Jól sikerült:** a keret, belső mélyedés, takarmány és víz kevés pixelből is elkülönül, a töltöttség a tartalom rajzában jelenik meg. Jó példa a funkciót szolgáló részletre.

**Kilóg:** 14×7 px-en a sötét keret és a sötét üres belső összeolvadhat; a víz tónusa különbözik a többi vízfelülettől.

**Kis javítás később:** egységes fa/víz színpár, egy világos belső él, az üres és teli állapot egyértelmű alakja. A tooltip maradjon a pontos mennyiség forrása.

### 3.11. Ikonok — ★★★★☆ jó

**Jól sikerült:** az összes ikon sötét, egymáshoz illő piktogram, több kész célmérettel. Átlátszó hátterük tisztán működik a világos gombokon. A menü, ház, levél és időjel különösen egyszerűen olvasható.

**Kilóg:** a nagy tömör jelek optikailag súlyosabbak az állat, permetező és kanna finom részeinél. Az élsimított piktogram nem pixel-art sprite, de önmagában ez nem probléma. Az aratás traktorjele szemantikailag pontatlanabb, mint a többi ikon.

**Kis javítás később:** 20 és 24 px-en külön pixelkorrekció, azonos optikai margó és sötét tónus, a legkisebb lyukak/pontok egyszerűsítése. Az aratás jelét később kombájn- vagy kalászjelhez igazítani. Nem szükséges az egész ikoncsalád cseréje vagy a világ nézetére forgatása.

### 3.12. HUD és toolbar — ★★★☆☆ közepes

**Jól sikerült:** a felső információs és alsó eszközsáv elkülönül, a gombcsoportok logikusak. A város bal oldali és a bontás jobb oldali elhelyezése értelmes. Az aktív gomb halványzöld; az idő és pénz szövegesen is megjelenik.

**Kilóg:** a hideg szürke sáv kevésbé kötődik a világ meleg színeihez. A 30 px-es gombokon a 2 px-es keret erős. Az információhierarchia többnyire helyzetből származik, nem tipográfiából; hosszú pénz- és készletszöveg mellett a kisebb ablak külön ellenőrzést kíván.

**Kis javítás később:** melegebb semleges sáv, visszafogottabb alapkeret és egységes kijelölés. A sávok helye és mérete első körben maradjon; a pénz, raktár és idő kapjon következetes címke–érték hierarchiát.

### 3.13. Popupok, gombok és adatnézetek — ★★★☆☆ közepes

**Jól sikerült:** közös törtfehér háttér, sötét keret, világosszürke kártyák és halványzöld hover. A Város három azonos gombja, a választók kártyái és a naptár idősávjai egyszerűek. A piac, pénzügy, fejlesztési fa és garázs saját adattípusukhoz igazodó nézetet kapnak. A garázs valódi géprajzainak újrahasználata megtartandó.

**Kilóg:** 20/24 px-es panelpadding, 1/2/3 px-es keretek, eltérő sor- és gombmagasságok keverednek. Sok címsor és törzssor ugyanazzal a fonttal készül. A választók szövegesek, ezért a világban látott tárggyal való kapcsolat gyengébb. A növényválasztó magassága korlátozott, a kártyák viszont fix sorban épülnek, és a közös `SelectionPanel` nem ad görgetést: kisebb ablakban levágott alsó tartalom kockázata látszik a kódból. Ez nem minden panelre általánosítható, több más nézet saját görgetéssel rendelkezik.

**Kis javítás később:** egységes térközrendszer, látható címhierarchia, következetes alap/hover/aktív/tiltott/hiba állapotok. A kisablakos tartalomelérés rendezése előzze meg a kártyadíszítést. Meglévő világrajz kis előnézete későbbi lehetőség, de csak akkor, ha valóban gyorsítja a választást.

### 3.14. Tooltip, értesítés és fejlesztői overlay — ★★★☆☆ közepes

**Jól sikerült:** a tooltip tördel, és az ablak széléhez igazodik; az értesítés visszafogott világos felület. A termelési, tárolási és időbeli részletek szövegben rendelkezésre állnak.

**Kilóg:** a tiszta fekete tooltip és fehér szöveg jó kontrasztú, de erősebb a többi UI-nál. A fejlesztői konzol külön 16 px-es betűt és 100 px magas overlayt használ; az alsó hírsávval együtt vizuális versenyt okozhat. A konzol fejlesztői funkció, nem farmdekoráció.

**Kis javítás később:** közös sötét tooltip-token, egységes padding és információs sorrend. A hírek fontosság szerint rendezett, kevés párhuzamos sorral működjenek. A konzol stílusa maradjon visszafogott; láthatósági viselkedésének változtatása külön feladat.

### 3.15. Kurzorok, rács és állapotkeretek — ★★★☆☆ közepes

**Jól sikerült:** az elhelyezés, kijelölés és aratási lehetőség külön keretekkel jelzett. Az aratás aranybarna, a késői aratás visszafogott piros kerete illik a világba.

**Kilóg:** az elhelyezési tiszta sárga/piros és a rács élénk zöldje feltűnőbb a többi grafikánál. A 3 px-es preview, 2 px-es mezőkeret és 4 px-es kerítés több jelentést hasonló körvonalnyelven közöl. A `cursor.png` az Info eszköz ikonja; külön `set_cursor` alapú egyedi kurzorrendszert nem találtam.

**Kis javítás később:** a szerepekhez rendelt külön keretminta és kontrollált színek. A tiltott és engedélyezett elhelyezés alakban is térjen el, például sarokjel és kereszt segítségével. A későbbi egyedi kurzor kicsi legyen, a kattintási pontja pontosan dokumentált; jelenleg nem elsődleges hiány.

### 3.16. Effektek és animációk — ★★★☆☆ közepes

**Jól sikerült:** nincs állandó vibrálás, túlzó füst vagy csillogás. A járműveknek van időalapú mozgásuk és irányváltásuk, az állatok időzítve változtatnak helyet és irányt. A trágyázó gép körül négy barna pont jelzi a műveletet. A talajkezelések és növekedés állapotváltásai gazdasági információt adnak.

**Kilóg:** a mozgó testek statikus forgatott képek; nincs lábciklus, kerékciklus vagy külön munkavégző képsor. Az állatok helyváltoztatása nem bizonyít folyamatos járásinterpolációt. A trágyázás pontjai a géphez kötött statikus jelzések, nem életciklussal rendelkező részecskék. A tó vízvonalai sem animáltak.

**Kis javítás később:** először a már zajló munka megkülönböztethető, ritka mozgásjelzése, utána 2–4 képkockás állatjárás vagy munkagép-részmozgás. Az animáció a szimuláció állapotát kövesse, ne határozza meg a termelés vagy mozgás időzítését.

### 3.17. Küldetéskép, indítókép és menük — ★★★☆☆ közepes

**Jól sikerült:** a portré barátságos vidéki hangulatot hoz; a stúdiólogó tiszta. A főmenü a popupok alapanyagait használja, így kapcsolódik a játék UI-jához. A mentési helyek üres, kijelölt és sérült állapota különbözik.

**Kilóg:** a küldetésportré részletes, festett emberábrázolása a legnagyobb stílusugrás a pixeles világhoz képest. A 100×100-as portré nagyobb figyelmet kaphat, mint a tényleges játékobjektumok. A fekete stúdiókép külön vizuális nyelv, de márkajelzésként elfogadható. A splash képarányt tartó, középre vágó kitöltése eltérő ablakarányokon ellenőrzendő.

**Kis javítás később:** elsőként a küldetéskép keretének, helyigényének és telítettségének illesztése; hosszabb távon egyszerűbb, korlátozott palettájú portréstílus. A stúdiólogót nem kell pixel-arttá alakítani. A mentés/betöltés szövegbeviteli és megerősítési állapotai ugyanazt a UI-szabályt kövessék, mint a többi panel.

## 4. A végleges vizuális stílus szabályai

### 4.1. Megtartandó alapelvek

1. **Felismerés előbb, díszítés utána.** Egy tárgy típusát sziluett és nagy színfolt azonosítsa. A játékosnak ne kelljen apró részleteket megszámolnia.
2. **A világ háttér, a döntés előtér.** Fű és talaj alacsony kontrasztú; az objektum erősebb; az aktuális interakció a legerősebb.
3. **Egységes anyagok.** Ugyanaz a fa, fém, víz és talaj ugyanabba a színcsaládba tartozzon több objektumon is.
4. **Kevés, jelentéssel bíró részlet.** Tárgyanként egy fő forma, egy funkcionális rész és legfeljebb egy kis karakterelem legyen az alap.
5. **A grafika állapotot mutat.** Évszak, díszítő animáció vagy színváltás nem módosíthat költséget, hozamot, útvonalat, helyigényt vagy kattinthatóságot.
6. **Nem kötelező PNG-re átállni.** A procedurális rajz megtartható, ha teljesíti ugyanazt a pixel-, paletta- és méretszabályt. A fájlformátum nem művészeti minőségmérő.

### 4.2. Perspektíva és kamera

**Végleges alapnézet: ortografikus, 90°-os felülnézet a talajsíkhoz képest, négyzetrácson.** Ez a kamera felülnézeti irányát írja le, nem egy jelenleg állítható 3D-kameraparamétert. A jelenlegi 2D eltolásos kamera megtartandó; nincs szükség 30–45°-os vagy izometrikus átalakításra.

- Épületen a tető legyen a domináns sík. A bejárat, pult vagy rakodórámpa az alsó, képernyő felé eső oldalon maradhat mint egységes stilizált jelzés.
- A tető látható felületének javasolt aránya 70–85% az épülettesten belül. Ez rajzi arány, nem foglalási szabály. Kerüljük az egyik épületen magas homlokzat, a másikon tiszta tetőnézet keverését.
- Járműveken a motorháztető, kabin és munkafej felülről látszódjon. A négy fő irány maradjon. A szemből/oldalról rajzolt UI-piktogramoknak nem kell ezt követniük.
- Fáknál a korona helyzete a 2×2-es fahely közepéhez kötődjön. Ne nőjön a törzs hosszú oldalnézeti oszloppá.
- Ne vezessünk be távolsággal csökkenő méretet, perspektivikus útösszetartást vagy kameraforgatást a grafikai egységesítés részeként.
- Későbbi zoom esetén a világ egész számú nagyítása legyen az első támogatott út. A UI saját olvasható méretét tartsa. A zoom megvalósítása külön fejlesztési döntés.

### 4.3. Pixelrács, sprite-méretek és részletesség

**Alapszabály: 1 logikai világpixel = 1 pixel az alapnézetben.** A meglévő 20 px-es csempét nem célszerű pusztán divatos 16/32 px-es szabvány miatt megváltoztatni.

| Elem | Megtartandó alapméret | Rajzi cél |
| --- | --- | --- |
| Fű, út | 20×20 px | Éles csempeperem, folyamatos illeszkedés |
| Mező | 4×4 / 6×6 / 8×8 csempe = 80 / 120 / 160 px oldal | Ugyanakkora növénymotívumok ismétlése; nem felnagyított 4×4-es kép |
| Farmház telek | 8×8 = 160×160 px | A szabad udvar maradjon olvasható |
| Farmház test | I.: 3×3; II–III.: 4×4 csempe | A jelenlegi 4 px-es belső ráhagyással a rajzi footprint 52×52, illetve 72×72 px; az árnyék külön értendő |
| Raktár | 5×4 = 100×80 px | Nagy tető és rakodófront |
| Piac | 4×3 = 80×60 px | Csíkos ponyva mint fő ismertetőjel |
| Garázs, karám, gyümölcsös | 4×4 = 80×80 px | Eltérő funkció, közös lépték |
| Feldolgozó | 6×5 = 120×100 px | Kapu és nagy ipari tető, kevés gépészeti részlet |
| Tó | 6×6 = 120×120 px | Organikus vízforma a változatlan foglaláson belül |
| Fahely | 2×2 = 40×40 px | Körülbelül 28–34 px-es lombsziluett; világos peremtartalék |
| Állat | 20×20 px vászon | Fajonként eltérő festett testméret, közös rögzítési pont |
| Jármű / munkagép | 24×24 px vászon | Tiszta fősziluett; út- és vontatmányátfedés ellenőrzése |
| Vályú | 14×7 px | Töltöttség és anyag olvasható maradjon |
| HUD / toolbar ikon | 20 / 24 px | Méretenként ellenőrzött piktogram, változatlan kezdeti gombhelyek |

**Kontúrok:** kis világtárgyon 1 px, épület fősziluettjén legfeljebb 2 px. Belső szerkezeti vonal általában 1 px és kisebb kontrasztú, mint a külső él. Kerítés fő rúdja 2 px, ritka oszlop 3–4 px lehet. A 3 px-es interakciós keret külön információs réteg, nem anyagkontúr.

**Forma:** nagy, összefüggő pixelcsoportok; tudatos lépcsőzés. A 2–3 px-es folt általában jobb, mint több elszórt egyetlen pixel. Egyedi 1 px-es részlet csak szem, mag, rövid él vagy hasonló jelentés esetén indokolt.

**Színmennyiség:** kis objektumon javasolt 4–8 jól elkülönülő szín, nagy épületen 8–12, közös anyagcsaládokból. Egy anyag többnyire alap-, árnyék- és fénytónust kapjon. Ez munkakeret, nem merev globális színlimit. Simított UI-szöveg és áttetsző vetett árnyék nem számít bele az objektum festett színeibe.

**Szűrés:** a világban nincs elmosás, bilineáris kicsinyítés, fényudvar vagy automatikus gradient. A tó később közvetlenül célfelbontáson rajzolható. A procedurális kör/ellipszis megengedett, de a végeredmény pixelcsoportjait kell megítélni. A UI szövege és az egyszerű piktogramok élsimítása tudatos kivétel; a stúdiókép képaránytartó simítása szintén elfogadható.

**Rögzítés:** minden grafikai családhoz legyen dokumentált vászonméret, talajhoz kötött origó, festett befoglaló és árnyékráhagyás. A vászon, a látvány és a logikai foglalás külön fogalmak. Nagyobb rajz nem jelent nagyobb ütközést vagy építési költséget.

## 5. Ajánlott színpaletta

A táblázat **kiinduló célpaletta**, a jelenlegi hangulatból levezetve. A „meglévő” érték a megjelölt forrásban ténylegesen szerepel; az „új cél” későbbi illesztési javaslat. A teljes projekt jelenleg ennél több árnyalatot használ, ezért nem javasolt egyetlen automatikus színcsere minden asseten.

### 5.1. Világ és anyagok

| Szerep | HEX | Eredet / használati irány |
| --- | --- | --- |
| Fű alap | `#5B8B49` | Meglévő, `grass_01.png` domináns színe |
| Fű sötét | `#507D40` | Új cél, ritka alacsony kontrasztú folt |
| Fű világos | `#709557` | Új cél, kis felületen |
| Lomb alap | `#3E843A` | Meglévő alma-lombszín |
| Lomb fény | `#529A48` | Meglévő alma-lombfény |
| Lomb mély / cseresznye | `#2D6936` | Meglévő cseresznye-lomb |
| Szilvalomb | `#306544` | Meglévő, hűvösebb fajkarakter |
| Művelt talaj | `#896943` | Meglévő `FIELD_SOIL_COLOR` |
| Talaj/barázda sötét | `#694B30` | Meglévő `FIELD_FURROW_COLOR`; nagy felületen mérsékelendő |
| Talaj fény | `#A48459` | Meglévő `FIELD_HIGHLIGHT_COLOR` |
| Út alap | `#857056` | Meglévő `ROAD_BASE_COLOR` |
| Út tömörített sáv | `#947E61` | Meglévő `ROAD_COMPACTED_COLOR` |
| Útnyom | `#655241` | Meglévő `ROAD_TRACK_COLOR` |
| Faanyag alap | `#977F5B` | Meglévő piaci alap; közös faanyaghoz kiindulópont |
| Faanyag sötét | `#704826` | Meglévő kerítésszín |
| Meleg kontúr | `#4C2B1C` | Meglévő farmházkontúr; csak megfelelő anyagon |
| Tető terrakotta | `#CD5B36` | Meglévő farmháztető-fény |
| Tető árnyék | `#AE422B` | Meglévő farmháztető-sötét |
| Fal / vászon krém | `#E7DCC3` | Meglévő piacponyva |
| Piaci vörös | `#BE3D35` | Meglévő ponyvaszín |
| Fém / ipari tető | `#7E7E74` | Meglévő garázstető-fény |
| Fém árnyék | `#616460` | Meglévő garázstető-sötét |
| Hideg szerkezeti kontúr | `#373937` | Meglévő garázskontúr |
| Víz sekély | `#5B99A4` | Meglévő tó |
| Víz alap | `#418599` | Meglévő tó |
| Víz mély | `#306F8C` | Meglévő tó |
| Víz fény | `#84B8BB` | Meglévő tó; kis vonalak, nem fehér csillogás |
| Traktorpiros | `#C44335` | Új cél a jelenlegi élénk `#DC2323` mérséklésére |
| Kombájnzöld | `#266937` | Meglévő gépszín |
| Gépsárga | `#DEB02B` | Meglévő gyümölcsszüretelő-szín |
| Gumi | `#292A28` | Új cél a tiszta közeli fekete enyhítésére |
| Kabinüveg | `#464E4E` | Meglévő szüretelő-kabinszín; közös kiindulópont |
| Marhabarna | `#995E39` | Meglévő |
| Sertésrózsaszín | `#DE9199` | Meglévő |
| Csirkekrém | `#EFE4BE` | Meglévő |
| Érett termés piros | `#B0372D` | Meglévő almatermés |
| Szilva termés | `#53377E` | Meglévő |
| Arathatóság arany | `#B08034` | Meglévő funkcionális keret; ne legyen általános dekoráció |
| Késői aratás / veszély | `#A63E34` | Meglévő késői aratási keret |

A fa- és gépszínek nem jelentik az összes tárgy mechanikus átszínezését. A vörös tető, piaci ponyva és traktor maradjon külön anyag és külön sziluett. A lomb sötétebb tömege, a fű világosabb alapja és a gépek telítettebb akcentusa együtt adjon hierarchiát.

### 5.2. UI célpaletta

| Szerep | HEX | Alapelv |
| --- | --- | --- |
| Panelháttér | `#F5F5F0` | Meglévő `INFO_PANEL_BACKGROUND` megtartása |
| Kártya / alapgomb | `#E8E8E1` | Meglévő kártyaszín |
| HUD / toolbar | `#DDDED4` | Új, kissé melegebb semleges cél |
| Hover | `#DCE6D2` | Meglévő kártyahover |
| Kijelölt háttér | `#D3E5D0` | Meglévő kész fejlesztés színe mint közös kiindulópont |
| Fő szöveg / ikon | `#38363C` | Az ikonforrások sötét tónusához illő cél |
| Másodlagos szöveg | `#5D6258` | Új cél; ne legyen halvány, nehezen olvasható felirat |
| Keret | `#60665B` | Új közös kerettónus |
| Akcentus / siker | `#376941` | Meglévő processing-pipa színe |
| Figyelmeztetés szöveg | `#805D26` | Új, világos háttéren sötét okker |
| Hiba szöveg | `#A5372D` | Meglévő eladási hibaszín |
| Tooltip háttér | `#30352E` | Új, lágyabb sötét; rajta `#F5F5F0` szöveg |

Szín soha ne legyen az egyetlen állapotjel. Hiba mellé szöveg vagy kereszt, kijelölés mellé keret/pipa, tiltás mellé olvasható magyarázat tartozzon. A növénykezelési barna, kék és sárga jelölőnek is legyen külön alakja. A célpaletta kontrasztját a végleges szövegméreten és tényleges háttérrel kell ellenőrizni; ez a dokumentum nem állít mért akadálymentességi megfelelőséget.

## 6. Fény és árnyékolás

### 6.1. Közös fényirány

**A fény a képernyő bal alsó sarkából érkezik.** Képernyő-koordinátában +x jobbra, +y lefelé; a fény felé mutató irány `(-1, +1)`, a vetett árnyék iránya `(+1, -1)`. Ez megtartja a `PROCEDURAL_LIGHT_DIRECTION` jelenlegi szándékát.

| Család | Jelenlegi eltolás / árnyék | Későbbi egységesítés |
| --- | --- | --- |
| Épület | `(4, -4)`, fedő zöld `#3D693A` | Irány marad, talajfüggetlen áttetsző árnyék |
| Fa | `(6, -6)`, fedő sötétzöld `#374830` | Irány és relatív hossz marad, közös árnyékanyag |
| Állat | `(1, -1)`, `(35,31,27,55)` RGBA | Rövid talajárnyék, közös színcsalád |
| Gép | `(0, +3)`, `(35,35,35,55)` RGBA | Jobbra-felfelé mutató, például `(2, -2)` eltolás |

### 6.2. Szín, hossz és keménység

- Közös vetett árnyék kiinduló színe: **`#30382D`**, alfa 55–75 a 0–255 tartományban, körülbelül 22–29% fedettség. A talajon és a téli felületen külön ellenőrzendő célérték.
- Kis állat: tengelyenként 1 px eltolás; gép: 2 px; épület: 4 px; fa: 6 px. Ezek javasolt **eltolások**, nem az árnyék teljes méretei. Átlós hosszuk rendre körülbelül 1,4 / 2,8 / 5,7 / 8,5 px.
- Az árnyék méretét a talajra támaszkodó test aránya adja; a csirkéé ne legyen marhaméretű, a gépé ne legyen indokolatlanul széles kör.
- Nincs Gaussian blur vagy több egymásra tett puha glória. Egy éles, visszafogott áttetsző alakzat elegendő. Anyagba rajzolt sötét tetősík nem ugyanaz, mint a vetett árnyék.
- A fénytónus a bal/alsó, a sötét anyagsík a jobb/felső oldalt hangsúlyozza. Ne használjunk minden peremen egyszerre világos kontúrt.
- A gép irányváltásával a talajárnyék fényiránya nem fordulhat el. A forgatott sprite-ba festett irányfüggő csúcsfényt is felül kell vizsgálni: külön irányrajz vagy világkoordinátás fényréteg tarthatja stabilan.
- A fedő zöld árnyékok kiváltása azért fontos, mert úton, talajon és havon másként viselkednének. A tárgy alá kevert közös árnyék mindegyik alaphoz alkalmazkodik.

### 6.3. Rétegezési szerződés

A jelenlegi `main.py` külön sorrendben rajzolja a világot/épületeket, vályúkat, állatokat, kerítéseket, fákat és gépeket. Ez nem általános, mélység szerint rendezett jelenet. A későbbi célrétegek: talaj és út → talajállapot → vetett árnyékok → tárgytestek → a tárgytól függő kerítésrészek → interakciós jelölések → UI.

Ez művészeti cél, nem M0-s renderhurok-módosítás. Későbbi átálláskor külön kell ellenőrizni a kerítés mögötti állatot, fa mellett haladó szüretelőt, épület melletti gépet és telekhatárra lógó árnyékot. Egy utoljára rajzolt árnyék ne sötétítse el a mellette álló másik tárgy tetejét. A talajhoz tartozó szüreti keret a korona alatt maradhat; az aktuális kijelölés legyen jól olvasható.

## 7. Évszakokra előkészített grafika

### 7.1. Már van mire építeni

A `time_system.py` már négy évszakot és heti tartományokat definiál: tél 1–8. és 48–52. hét; tavasz 9–21.; nyár 22–34.; ősz 35–47. A naptár ezekhez külön színcsaládokat mutat. A gyümölcsösben éves érési/szüreti állapot is létezik. **A négy évszak teljes világ-grafikája viszont még nincs meg:** a fű, tető és lomb jelenlegi rajzolása nem általános szezonális változatkészlet.

### 7.2. Előkészítési szabály

A jövőbeli grafikai család állandó eleme legyen a talajhoz rögzítés, sziluettmag, perspektíva, méret és fényirány. Cserélhető eleme legyen az anyagpaletta, lomb/virág, gyümölcs és hófedés. Nem kell minden kombinációt külön teljes képfájlként elkészíteni.

Javasolt logikai vizuális rétegek: **alaptest + faj/variáns + növekedés/életkor + évszak + termelési állapot + interakciós jelölés**. Ez tervezési modell, nem előírt új mentésformátum.

- A törzs, tető, kerítés és géptest alapját egyszer kell megtervezni.
- Lomb, virág és hó külön, ugyanahhoz az origóhoz illesztett réteg lehet.
- A hó csak a kijelölt vízszintes felületeket fedje: tető, talajfolt, kerítés teteje. Ne fesse át az egész képet fehérre.
- A fajok koronaformája télen, gyümölcs nélkül is különbözzön. A téli ágforma ne változtassa meg a fahelyet.
- Procedurális megoldásnál a szezon és a ténylegesen rajzolt állapot bekerülhet a rendercache kulcsába. Ne készüljön új véletlen textúra minden képkockán vagy évszakváltáskor.
- Ha később fájlalapú változat készül, a névben és metaadatban következetesen különüljön el a család, faj, állapot, évszak és irány; ne készüljenek előre üres fájlok minden lehetséges kombinációhoz.

### 7.3. Szezonális megjelenési terv

| Évszak | Fű / talaj | Fák és növények | Épületek, út, víz | Olvashatósági feltétel |
| --- | --- | --- | --- | --- |
| Tavasz | Kissé frissebb, de tompa zöld | Világosabb friss lomb; ritka virágfolt megfelelő állapotban | Kevés sötétebb nedves talajfolt | Virág ne legyen összetéveszthető érett terméssel |
| Nyár | A jelenlegi paletta legyen az alapreferencia | Teljes lomb, termés csak a tényleges állapot szerint | Meglévő meleg út és kékeszöld víz | A gépek a teljes lomb mellett is jól látszanak |
| Ősz | Olívásabb fű, kis okker foltok | Fajonként visszafogott arany/réz lomb, csökkenő lombtömeg | Kevés levélfolt a széleken | Az aratási aranykeret ne olvadjon a lombba |
| Tél | Törtfehér hó és áttűnő föld/út | Egyszerű ágforma; faj- és korfüggő sziluett | Részleges hó a tetőn, olvasható kapu, sötétebb útvonal | Csirke, kerítés, kijelölés és jármű minden alapon elkülönül |

Kiegészítő, még nem implementált szezonális célárnyalatok: tavaszi fű `#719854`, őszi fű `#858A4C`, lombokker `#B28B45`, rézlomb `#A8673F`, hó `#E3E7DE`, hóárnyék `#BACAC9`. Ezek kis kiegészítő paletták; az épületek és gépek funkcionális színei maradjanak stabilak.

Az évszakváltás ne színezze át globális képernyőszűrővel a UI-t, a hibajeleket és a gépeket. Befagyott tó, járható jég, eltűnő termés vagy állatok téli viselkedése külön játékmeneti kérdés; ez a grafikai terv nem vezet be ilyen szabályt. Hasonlóan, egy tavaszi virágzás nem írhatja felül a gyümölcs éves állapotát.

## 8. Egységes UI-irányelvek

### 8.1. Megtartandó felépítés

A felső HUD, alsó toolbar, középre rendezett adatpanelek és kártyás választók rendszere maradjon. Ne kapjon a UI deszkatextúrát, szegecssort, részletes faablakkeretet vagy térbeli gombokat. A modern hatást a pontos elrendezés és következetes visszajelzés adja.

### 8.2. Térköz és tipográfia

- Alap térközmodul: 4 px; jellemző belső távolságok 8, 12, 16, 24 px. Nagy panelen 24 px, tömör panelen 16 px padding; a kivételt az adatsűrűség indokolja.
- Panel főkeret 2 px, kártya/gomb alapkeret 1 px, aktív/fókusz keret 2 px. A 3 px-es keret csak különösen fontos kijelölésre, tudatosan.
- A meglévő 20/24 px-es ikonméret és 30 px-es toolbar-gomb az első egységesítési körben maradjon. A festett ikon körül legyen legalább körülbelül 2 px optikai levegő.
- Szöveges gomb célmagassága 36–40 px; hosszabb magyar feliratnál a tartalomhoz igazodó szélesség. Ne legyen csak a kattinthatóság miatt alig látható felirat.
- Egy olvasható sans-serif család, legfeljebb három szerep: cím 26–28, fő szöveg 22–24, másodlagos adat 18–20 névleges Pygame-fontméret. Ezek kiinduló méretek, a renderelt betű tényleges magasságát kell ellenőrizni.
- Az élsimított szöveg tudatos kivétel a világ pixel-art szabálya alól. Fontválasztásnál `ő`, `ű`, `Ő`, `Ű`, pénzjelek, számjegyek és hosszú terméknevek legyenek a mintában.
- Ne függjön a végleges tipográfia ellenőrizetlen rendszerfont-helyettesítéstől. Konkrét betűcsalád kijelölése külön UI-munkalépés; M0 nem ad új fontassetet.
- Az adatérték legyen erősebb a címkénél; táblázatban a számok jobbra igazodjanak, az egységek és tizedesek formázása maradjon következetes.

### 8.3. Állapotok és panelcsaládok

| Elem | Egységesítési irány |
| --- | --- |
| HUD | Idő, pénz és készlet külön vizuális blokk; rövid címke, erős érték |
| Toolbar | Alap, hover, aktív és tiltott állapot megkülönböztethető; az aktív jel ne csak háttérszín legyen |
| Épület-, növény-, állat- és faválasztó | Azonos kártyafejléc és címke–érték ritmus; a tartalom ne lógjon ki kisebb ablakban |
| Raktár / feldolgozó | Készlet, kapacitás, munkaállapot külön szakasz; közös állapotszínek és világos mértékegységek |
| Garázs | Meglévő valódi géprajzok megtartása; foglalt/üres slot és darabszám egységes hierarchiával |
| Piac / eladás / étterem | Ár és mennyiség igazított oszlopban; a beviteli hiba ugyanazt a jelet és színt használja |
| Bank / pénzügy | Pozitív/negatív összeg szín mellett előjellel és felirattal; összesítés erősebb, mint a sorok |
| Fejlesztési fa | Zárolt, elérhető és kész állapot szín mellett piktogrammal/felirattal; a kapcsolóvonal másodlagos |
| Naptár | A vetés és aratás időszaka szín mellett felirattal vagy jelmagyarázattal is értelmezhető legyen |
| Tooltip | Rövid cím, állapot, majd részletek; közös sötét háttér és padding; ne takarja a vizsgált tárgyat |
| Értesítés | Rövid üzenet, visszafogott prioritásjel; nem igényel állandó animációt |
| Küldetés | A cél és előrehaladás hangsúlyosabb a portrénál; a kész állapot pipa és szöveg együtt |
| Mentés / betöltés / megerősítés | Közös gombállapotok, olvasható bevitel és kijelölés; a sérült és üres hely ne legyen összetéveszthető |

Első körben a megjelenő információ, gombok száma és funkciója nem változik. Új pipa, fókuszjel vagy előnézet csak későbbi UI-mérföldkőben készülhet. A görgethetőség és tartalomelérés rendezése is külön megvalósítási feladat, nem része az M0 dokumentumkészítésnek.

## 9. Prioritási lista

1. **Közös pixel-, fény-, árnyék- és anyagszabály alkalmazása egy kis reprezentatív mintán.** A legnagyobb rendszerbeli eltérés több kategóriát érint. Egy gép, egy épület, egy fa és a tó összehangolása megmutatja az irányt tömeges újrarajzolás nélkül.
2. **UI-olvashatóság és szűk ablakos tartalomelérés.** A levágott vagy nehezen áttekinthető adat fontosabb probléma, mint bármely dekoratív hiány. Először növényválasztó, sűrű feldolgozó/fejlesztési nézetek és hosszú HUD-adatok; majd közös hierarchia és állapotok.
3. **Kerítések, tóperem, fű–út–talaj illeszkedése.** Nagy területen ismétlődnek, ezért kis javítás is látványos. A vastag területkeretek és a simított vízperem most erősebben kilógnak, mint a legtöbb épület.
4. **Járművek és állatok egységesítése.** Mozgás közben gyakran kerülnek egymás mellé; árnyék, sziluett, irány és fajonkénti lépték közvetlenül segíti az olvasást.
5. **Fák és növényállapotok finomítása, szezonális alaprétegek.** A gyümölcskorona körhatása és a kis állapotjelölők javítandók; ekkor kell elkerülni a későbbi évszakos újramunkát.
6. **Épületek célzott továbbfejlesztése.** A meglévő család az egyik legerősebb rész; előbb a garázs/feldolgozó karakter és a szintjelzés javuljon, ne új farmházzal kezdődjön a teljes átrajzolás.
7. **Ikonok célméretű finomítása és küldetésportré illesztése.** A piktogramcsalád nagy része megtartható. A portré erős stíluseltérés, de kisebb funkcionális kockázat, mint az adatok és mozgó tárgyak olvashatósága.
8. **Visszafogott animációk és effektek.** Csak stabil statikus grafika és állapotnyelv után; így nem a díszítő mozgás fedi el a formai problémákat.
9. **A négy évszak teljes grafikai kiterjesztése.** A felkészítés korán megtörténik, a teljes változatkészlet a nyári referencia megszilárdulása után készül. Ez csökkenti a négy évszakra megsokszorozódó javításokat.

## 10. Hosszú távú fejlesztési roadmap

**M1 státuszfrissítés:** a felhasználó később az **M1 — Environment Polish** feladatot jelölte ki első megvalósításként. Ez elkészült; tényleges hatóköre, mérései és tesztjei az [aktuális Graphics Roadmapben](GRAPHICS_ROADMAP.md) találhatók. Az alábbi táblázat az eredeti M0 tervezési javaslat, nem a teljesített mérföldkövek nyilvántartása.

A mérföldkövek kimenet és elfogadási feltétel szerint értendők; nincsenek bizonytalan naptári ígéretek. A prioritási sorrend a problémák fontosságát mutatja, a roadmap az egymásra épülő megvalósítást. M0 után minden pont külön körülhatárolt grafikai munka.

| Mérföldkő | Tartalom és kézzelfogható eredmény | Függőség | Elfogadási feltétel |
| --- | --- | --- | --- |
| **M0 — Audit és Art Style Guide** | Jelen dokumentum; leltár, célpaletta, szabályok, terv | Jelenlegi projekt | Kizárólag ez a Markdown-fájl változik |
| **M1 — Referencia és közös szabályok** | Kis mintakészlet a meglévő farmházból, traktorból, fából, tóból és talajból; anyag- és árnyékszabályok alkalmazása; szezonrétegek specifikációja | M0 | Natív méreten egységes pixelkezelés, bal alsó fény, változatlan helyigény |
| **M2 — UI alapegységesítés** | HUD, gomb-, kártya-, tooltip- és szövegszerepek; problémás kisablakos tartalomelérés rendezése; ikonok célméretű korrekciója | M1 közös palettája | A kijelölt ablakméreteken minden szükséges adat és vezérlő elérhető; állapotok szín nélkül is értelmezhetők |
| **M3 — Terep, víz és határok** | Fű/fallback illesztés, útváltozatok ellenőrzése, egységes kerítések, pixelpontos tó és közös vízanyag | M1 | Útcsatlakozások folytonosak, nincs feltűnő csempevarrat; kerítés és tó nem uralja az objektumokat |
| **M4 — Gépek és állatok** | Öt géptípus és három állatfaj egységes statikus grafikája; négy irány; pótkocsi rakománycsoportok; garázsnézet követése | M1, M3 | Négy irányban felismerhető típusok, stabil fény, jól látható vontatmány; változatlan mozgás és parkolás |
| **M5 — Növények és gyümölcsös** | Öt növény négy fázisa, kezelési jelek, három fa koronája; életkor/évszak/termés különválasztott vizuális rétege | M1, M3 | A faj és fontos állapot natív méreten olvasható; a szüreti/aratási jel a valódi állapotot követi |
| **M6 — Épületcsalád finomítása** | Garázs, feldolgozó, raktár és piac anyag- és kontúregységesítése; szükséges szintjelzések; farmházi udvar illesztése | M1, M3 | A funkciók és indokolt szintek felismerhetők; nincs extra zsúfoltság vagy foglalásváltozás |
| **M7 — Mozgás és munkajelzés** | Kevés képkockás állat-/gépmozgás, indokolt műveleti jelzések, opcionális vízanimáció | M4–M6 | Mozgásállapot, megállás, szünet és gyorsított idő vizuálisan következetes; dekoráció nem vezérli a szimulációt |
| **M8 — Négy évszak** | Tavasz, ősz, tél rétegei a nyári referencia mellé; talaj, lomb, tető, kerítés, víz összehangolása | M3, M5, M6 | Ugyanaz a farm mind a négy évszakban olvasható; hó nem rejti el az utat, gépet vagy státuszt |
| **M9 — Végső összehangolás** | Küldetéskép és menük végleges illesztése; teljes vegyes farm ellenőrzése; felesleges díszítés visszavágása | M2–M8 | Egységes összkép, stabil részletsűrűség, dokumentált és tovább bővíthető szabályok |

### 10.1. Munkamód minden későbbi mérföldkőben

Először egy-két reprezentatív elem, majd ellenőrzés natív méreten és a meglévő környezetben; csak utána terjedjen ki a változás a teljes családra. A régi és új változat ugyanazon háttéren, azonos állapotban legyen összehasonlítható. Egy mérföldkő ne változtasson egyszerre léptéket, palettát, perspektívát és UI-elrendezést.

Minden későbbi grafikai család rövid adatlapja tartalmazza: azonosító és forrás, vászon/csempeméret, origó, festett határok, palettaszerepek, kontúr, fény/árnyék, irányváltozatok, állapotok, évszakrétegek, valamint a megengedett UI-újrahasználat. Ezek külön dokumentumokként csak későbbi feladatban készüljenek.

### 10.2. Ellenőrzési kapuk

| Ellenőrzési helyzet | Mit kell látni? |
| --- | --- |
| Natív 1× méret; nagyítás csak hibakeresésre | Típus és fontos állapot apró részletek nélkül is felismerhető |
| 1500×1000 alapablak, majd 1280×720 és 800×600 ellenőrző célméret | A kisebb méretek támogatása külön megerősítendő; nincs elveszett művelet vagy levágott lényeges tartalom |
| Világos fű, sötét föld, út és téli hó | Kontúr, árnyék és állat/gép elkülönül |
| Mind a 16 útmaszk, mind a 4 textúraváltozat, hosszú utak | Nincs csatlakozási törés vagy feltűnő ismétlődő csomó |
| Mindhárom mezőméret, öt növény, négy fázis | A részletméret állandó; a növekedés és arathatóság nem keveredik |
| Kezelt/kezeletlen mező, aratható/késői/blokkolt munka | Szín mellett szöveg vagy alak is segít; a jelzés nem hazudik a munkakezdésről |
| Három fafaj, érett és nem érett termés, négy évszak | A fajsziluett és a termelési állapot külön olvasható |
| Három állatfaj, négy irány, sűrű karám, vályú mellett | Állat és kerítés nem olvad össze; a fajarány következetes |
| Öt géptípus, négy irány, forduló, vontatmány, parkoló | Árnyék iránya állandó, gépfront és kapcsolódás olvasható |
| Farmház I–III., raktár/garázs/üzem releváns szintjei | A szinthez kötött grafika nem változtatja meg a foglalást vagy a funkciót |
| Hosszú magyar felirat, nagy pénzösszeg, tele raktár | Tördelés, igazítás, kontraszt és mértékegység rendezett |
| Alap/hover/aktív/tiltott/hiba/kész UI-állapot | Következetes vizuális nyelv, nem csak színkülönbség |
| Szünet, normál és gyorsított idő | Az animáció a megállást és sebességet követi, nincs céltalan vibrálás |
| Sűrű vegyes farm és visszafogott dekoráció | A gyakori döntések fontosabbak a hangulati effekteknél |

A későbbi implementációhoz kapcsolódó, már létező ellenőrzési támpontok többek között: `tests/test_field_renderer.py`, `tests/test_road_building.py`, `tests/test_orchard_harvest_border.py`, `tests/test_orchard_seasons.py`, `tests/test_animal_movement_obstacles.py`, `tests/test_garage_popup_layout.py`, `tests/test_toolbar_layout.py`, `tests/test_tooltip_layout.py`, `tests/test_startup_flow.py`, `tests/test_save_slots_ui.py`, `tests/test_speed_timing.py`. Ezek a működési regressziók ellen segítenek, de nem helyettesítik a vizuális ellenőrzést. M0-ban nem történt játékteszt-futtatás vagy tesztfájl-módosítás.

## 11. M0 lezárási feltétele

Az M0 eredménye kizárólag a `graphics/ART_STYLE_GUIDE.md`. A dokumentum nem ír elő azonnali assetcserét, új sprite-ot, új UI-elemet vagy játéklogikai változtatást. A legfontosabb következő lépés egy kis, ellenőrizhető grafikai referencia egységesítése a már meglévő felülnézettel, 20 px-es világráccsal és bal alsó fényiránnyal. A teljes grafikai fejlesztést ezután ugyanennek a szabálykészletnek kell vezetnie.
