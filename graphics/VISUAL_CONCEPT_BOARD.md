# FarmGame — Visual Concept Board

**M0.1 · Kreatív iránytű · 2026. szeptember 7.**

**Generation 1 → Generation 2: ugyanaz a farm, következetesebb vizuális nyelv.**

> Nyugodt táj. Felismerhető gazdaság. Világos döntések.

Ez a koncepciólap az [Art Style Guide](ART_STYLE_GUIDE.md) kreatív társa: a kívánt érzést, formakaraktert és döntési sorrendet rögzíti. A részletes audit, mérettáblák, színkódok és technikai ellenőrzések továbbra is az Art Style Guide-ban találhatók. Az alábbiak célirányok, nem már megvalósított változtatások. Ez a munkafázis kizárólag dokumentáció.

## 1. A FarmGame karaktere

| Érzés | Mit jelent a képernyőn? |
| --- | --- |
| **Nyugodt** | A fű és a víz csendes háttér; kevés, lassú hangulati mozgás |
| **Rendezett** | Követhető utak, tiszta telekhatárok, egyértelmű növénysorok |
| **Természetközeli** | Tompa zöldek, meleg föld, terrakotta, fa és kékeszöld víz |
| **Stratégiai** | A gép, a termény és a munkaállapot gyorsabban olvasható, mint a dekoráció |
| **Modern pixel-art** | Tudatos pixelcsoportok, kevés anyagtónus, pontos elrendezés, olvasható UI |

A játékélmény a gazdaság megértéséről és gondos szervezéséről szól. A látvány segítse azt az érzést, hogy a játékos átlátja, hol mi történik, és képes jól időzíteni a következő lépést.

**A megőrzendő vizuális aláírás:** vöröses farmháztető · csíkos piaci ponyva · szürke gazdasági tetők · barna földutak · visszafogott zöld környezet · színnel és formával elkülönülő gépek.

A Generation 2 ezeket pontosítja. Egy felismerhető meglévő elemnél először a kontúrt, a fényt és az anyagokat hangoljuk össze; a teljes újratervezés csak akkor indokolt, ha a funkció továbbra sem olvasható.

## 2. Gameplay first — a legfontosabb döntési szabály

> **A játék olvashatósága fontosabb, mint a grafikai részletesség.**

**Figyelmi sorrend:** aktuális döntés és fontos állapot → tárgy és funkció → anyag → hangulati részlet.

| A játékos kérdése | A látvány válasza |
| --- | --- |
| Mit termeszt ez a mező? | Eltérő növénytömeg, sorritmus és fajra jellemző forma |
| Melyik gép dolgozik itt? | Felismerhető gépfront, munkafej és típushoz kötött főszín |
| Melyik épület mire való? | Jellegzetes tető és bejárati oldal; nem csak eltérő festés |
| Mit kell most észrevennem? | Kevés, következetes állapotjel; a díszítés nem versenyez vele |
| Melyik gombot használjam? | Egyszerű ikon, stabil hely, rövid és pontos megnevezés |

**Gyors próba minden új elemhez:** normál játékméretben, a valódi háttér előtt is felismerhető? Szín nélkül is van megkülönböztető alakja? A részlet segít a döntésben? Ha csak nagyítva működik, egyszerűsíteni kell.

Az érett növény látványa és az indítható aratás jelzése külön feladat. A grafika nem ígérhet elvégezhető műveletet, ha azt a játék aktuális állapota nem engedi.

## 3. Színhangulat — természetes alap, takarékos akcentus

**Háttér:** mohazöld + földbarna + tompa okker

**Karakter:** terrakotta + krém + meleg szürke + kékeszöld

**Figyelem:** kevés mélyzöld, borostyán és téglapiros, mindig jelentéssel

| Terület | Ajánlott színérzet | Használati szabály |
| --- | --- | --- |
| Fű | Tompa középzöld, enyhe olívás árnyalat | Nagy, nyugodt alap; csak ritka tónusfoltok |
| Föld | Meleg barna, sötétebb barázda | A növényeknél kisebb belső kontraszt |
| Utak | Poros barna, homokos világosítás | A hálózat folytonossága fontosabb a kavicsmintánál |
| Tó | Kékeszöld, mélyebb tompa kék, halvány vízfény | A part és a mélység néhány nagy foltból álljon |
| Épületek | Terrakotta, krém, fa és meleg szürke | A meglévő funkcionális színkarakter maradjon |
| Gépek | Mérsékelt piros, sötétzöld, okkersárga, ezüst | Telítettebbek lehetnek a tájnál; egy főszín vezessen |
| Állatok | Marhabarna, sertésrózsaszín, csirkekrém | Természetes, jól elkülönülő testtömegek |
| UI | Törtfehér, meleg világosszürke, sötét szürkésbarna | Nyugodt felület, erős szövegkontraszt |
| Figyelmeztetés | Borostyán vagy sötét okker | Figyelmet kér, de nem vészjelzés; jel és szöveg kísérje |
| Pozitív esemény | Mély, természetes zöld | Rövid sikerjelzés, pipa vagy felirat; ne legyen zöld villanás az egész képernyő |
| Negatív esemény | Visszafogott téglapiros | Hiba vagy veszteség, egyértelmű magyarázattal |

Az aratási arany és a figyelmeztető okker rokon színcsalád: a különbséget a jel formája, helye és felirata tegye világossá. Az épület piros teteje nem hibaállapot. A szín jelentését mindig a környezetével együtt kell megtervezni.

Pontos színválasztáshoz az Art Style Guide **5. fejezete** az alap; ez a lap a paletta hangulati szerepeit mutatja, nem hoz létre párhuzamos színkódrendszert.

## 4. Nézet, fény és árnyék

**Nézet:** négyzetrácsos, ortografikus felülnézet. A tető, a gép felső tömege és a növénysor legyen a vezető forma. A jelenlegi nézet karakterét őrizzük meg.

| Fényképzet | Egységes szabály |
| --- | --- |
| **Fényforrás ↙** | A képernyő bal alsó oldala felől érkezik a fény |
| **Vetett árnyék ↗** | A tárgytól jobbra és felfelé nyúlik |
| **Erősség** | Rövid, visszafogott, áttetsző; kiindulásként körülbelül negyedfedettség |
| **Szín** | Sötét, enyhén zöldes szürke; a talajjal keveredve hasson |
| **Anyagfény** | Bal/alsó síkok világosabbak, jobb/felső síkok sötétebbek |

Minden új tárgy ugyanebben a fényben álljon. A gép elfordulhat, a nap iránya nem fordul vele. Az árnyék a tárgyat a talajhoz köti, ezért nem lehet vastag fekete matrica vagy elmosott fényudvar. A fa árnyéka hosszabb lehet az állaténál, de egyik sem nyelheti el a szomszédos tárgyat.

## 5. Pixel-art formanyelv

| Szempont | Követendő irány |
| --- | --- |
| Részletesség | Egy fő sziluett, egy funkcionális rész, kevés karakterelem |
| Kontúr | Anyaghoz illő sötét tónus; kis tárgyon jellemzően 1 px, épület főélén legfeljebb 2 px |
| Belső vonal | Vékonyabb vagy kisebb kontrasztú, mint a külső határ |
| Színátmenet | Két-három tudatos anyagtónus; foltok, nem folyamatos gradient |
| Dithering | Alapesetben mellőzzük: az ismétlődő pontmintázat zajt és hamis részletet ad |
| Textúra | Ritka, összefüggő pixelcsoport; a talaj legyen a legcsendesebb |
| Kontraszt | Háttér alacsony, tárgy közepes, fontos jelzés magas |
| Pixelkezelés | Éles világrajz, tudatos lépcsőzés; nincs simított sprite-szél vagy elmosás |

A 20 px-es világrács marad a lépték alapja. A részletek az alapnézethez készüljenek. A procedurálisan rajzolt grafika ugyanolyan megfelelő, mint a képfájl, ha ugyanazt a formanyelvet követi.

A UI olvasható, élsimított szövege és tiszta piktogramjai tudatos kivételek: nem kell minden betűt vagy ikont világ-sprite-ként kezelni.

## 6. Épületek — tetőből felismerhető funkció

**Tető → bejárat → anyag → kis karakterrészlet.** Ez legyen az épület olvasási sorrendje.

- **Tetők:** nagy, nyugodt síkok; a gerinc és néhány panelosztás elég. A csíkos piac és terrakotta farmház maradjon karakterhordozó.
- **Falak:** visszafogott, keskeny jelzések a tető mellett; ne keveredjen magas oldalnézeti homlokzat a felülnézettel.
- **Bejáratok:** egyszerű kapu, pult vagy rámpa a következetes alsó oldalon. A funkciót egy nagy forma közölje.
- **Árnyékok:** közös irány és áttetszőség; ne kapjon minden épület saját megvilágítást.
- **Színek:** közös fa-, vakolat- és fémcsalád, megtartott épületazonossággal.
- **Textúrák:** kevés szerkezeti vonal; tetőcserepek, téglák és szegecsek tömege helyett nagy anyagfoltok.

A fejlesztett szintet szükség esetén egy világos változás jelezze, ne egyre több apró dekoráció. Ez a szabályrendszer nem tervez új épületet vagy alaprajzot.

## 7. Járművek — a munkaeszköz adja a karaktert

**Felismerési sorrend:** gépfront és munkafej → testarány → főszín → kerék és kabin.

| Szempont | Új gépekhez is követhető szabály |
| --- | --- |
| Méretarány | A jelenlegi 24×24 px-es gépvászon a referencia; az út, vontatmány és parkoló mellett kell megítélni |
| Részletesség | Látszódjon, merre halad és milyen munkát végez; motorrács és csavar csak ezután |
| Színvilág | Egy fő gépszín, közös gumi-, fém- és kabintónusok |
| Felismerhetőség | Az új típusnak legyen megkülönböztető munkafeje vagy testformája; új szín önmagában kevés |
| Irányok | Mind a négy fő irányban ugyanaz a gépkarakter és stabil fény |

Egy későbbi nagy gép nem attól lesz hiteles, hogy több útcsempét eltakar. Méretnövelés csak olvasható arányokkal és külön ellenőrzéssel történjen; a rajz mérete önmagában nem módosítja a játék helyigényét.

Az állatok ugyanezt az egyszerűséget kövessék: a marha erősebb testtömegű, a sertés kerekebb, a csirke kisebb és könnyedebb legyen. Színük mellett a fejük és testarányuk is azonosítsa őket.

## 8. Növények — öt eltérő mezőkarakter

| Növény | Grafikai karakter | Amit meg kell őrizni kis méretben |
| --- | --- | --- |
| **Búza** | Karcsú, függőleges szálak; éréskor aranyló kalásztömeg | Összefüggő sorritmus és meleg érett szín, kevés különálló pixel |
| **Kukorica** | Magasabb, ritkább szárak; oldalra nyúló levelek | A búzánál robusztusabb sziluett, nem csak másik sárga árnyalat |
| **Paradicsom** | Alacsony, tömör bokor; kevés jól látszó vörös termésfolt | Kerekded növénytömeg és a termés pontszerű akcentusa |
| **Lucerna** | Alacsony, puha zöld csomók, ismétlődő összefüggő állomány | A talajtól és fűtől elkülönülő tömeg; ne váljon általános gyeptextúrává |
| **Komló** | Felfelé futó inda és ritmikus támrendszer | A tartószerkezet mint fajjel; ne legyen finom dróthálóval tele a mező |

A négy növekedési fázis a tömeg és forma változásával is különüljön el. A fajra jellemző motívum ugyanakkora maradjon kisebb és nagyobb mezőn; a nagy mező több növényt mutat, nem felnagyított növényeket.

A gyümölcsfáknál a koronasziluett hordozza a fajt, a gyümölcs az aktuális termést. A lomb néhány nagy foltból álljon. Életkor, évszak és szüretelhetőség külön vizuális információ: egy őszi korona nem jelent automatikusan érett gyümölcsöt.

## 9. UI — csendes keret a döntések körül

| Elem | Vizuális irány |
| --- | --- |
| HUD | Stabil felső információs sáv; jól elválasztott idő, pénz és készlet; erősebb érték, halkabb címke |
| Popup | Törtfehér lap, tiszta cím, rendezett szakaszok; a tartalomhoz igazodó térközök |
| Gomb | Egyszerű sík felület; felismerhető alap, hover, aktív és tiltott állapot |
| Ikon | A meglévő sötét piktogramcsalád folytatása; egy jel egy jelentés, méretenként ellenőrzött belső terek |

Az alsó eszközsáv maradjon áttekinthető. A kijelölést és hibát szín mellett alak, keret vagy felirat is közölje. Az apró díszítések helyett a magyar szöveg, a számok és a tartalomelérés kapjon helyet. Kisebb ablakban se tűnjön el fontos művelet.

Az ikon a műveletet nevezze meg pontosan; az aratás jele például az aratásra utaljon, ne általában bármely traktorra. A küldetésportré hangulati kiegészítés: a cél és előrehaladás legyen hangsúlyosabb nála. Új UI-elemek tervezése vagy elkészítése nem része ennek a lapnak.

## 10. Animáció — életjel, nem figyelemverseny

| Terület | Későbbi ajánlás | Korlát |
| --- | --- | --- |
| Szél | Néhány lomb- vagy növénycsoport rövid, ritka elmozdulása | Ne hullámozzon egyszerre az egész farm |
| Víz | Kevés lassú hullámvonal vagy váltakozó fényfolt | Ne villogjon fehéren, ne változzon folyton a teljes tó |
| Növények | Finom mozdulat az érettebb tömegeken | Ne rontsa a faj és növekedési állapot olvasását |
| Járművek | Először a működő munkafej vagy kerék takarékos mozgása | A gép helyzete és iránya maradjon stabilan értelmezhető |
| Állatok | Rövid járásciklus és ritka nyugalmi mozdulat | A fajsziluett ne változzon minden képkockán |
| Effektek | Rövid, helyi jelzés ott, ahol valódi művelet történik | Ne fedje el a munkaterületet vagy a státuszjelet |

Ha állóképen nem érthető a tárgy, az animáció nem oldja meg az alaprajz problémáját. Kevés, akár 2–4 képkocka is elegendő lehet. A játékvilág mozgása kövesse a szünetet és az idősebességet; a UI visszajelzése közben maradjon használható. A dekoratív képsor nem vezérelhet termelést vagy útvonalat.

## 11. Későbbi hangulati rétegek

**Állandó marad:** tárgyazonosság, sziluett, alaplépték, fényirány, állapotjelek olvashatósága.

**Változhat:** környezeti tónus, lomb, virág, hófedés és ritka időjárási részlet.

| Réteg | Kreatív irány | Megőrzendő olvashatóság |
| --- | --- | --- |
| Napszak | Nappal legyen a referencia; hajnal és alkony enyhe meleg/hűvös környezeti eltérést kaphat | Az első változat ne forgassa a közös fényt; éjszaka se sötétedjen el a munkaterület |
| Tavasz | Friss, tompa zöld; kevés virágfolt | Virág és gyümölcs különbözzön |
| Nyár | A jelenlegi karakterhez közeli teljes lomb és meleg föld | Ez legyen a többi évszak összehasonlítási alapja |
| Ősz | Olíva, okker, réz; ritkuló lomb | Az aratási jel ne olvadjon a környezetbe |
| Tél | Törtfehér hófoltok, hűvös árnyalatok, egyszerű ágforma | Út, kerítés, csirke és gép hóban is látszódjon |
| Időjárás | Kevés esővonal, enyhén nedvesebb talaj; borult időben mérsékeltebb anyagfény | Nincs sűrű köd, teljes képernyős csillogás vagy tárgyakat rejtő csapadék |

Ezek cserélhető hangulati rétegek legyenek, ne teljesen új grafikai készletek minden kombinációhoz. A UI és a funkcionális színek ne kapjanak globális napszak- vagy időjárásszűrőt. Valódi napjárás, tófagyás vagy időjárási játékszabály külön tervezési döntés; itt egyik sincs implementálva.

## 12. Amit kerülünk

- Túlzsúfolt sprite-ok, egyforma súlyú apró részletek és mindenütt hangsúlyos kontúrok.
- Állandó vagy szinkronizált animáció az egész farmon; figyelmet követelő díszítő effektek.
- Fekete, túl hosszú vagy túl erős árnyék; tárgyanként eltérő napirány.
- Fotorealisztikus textúra, simított világ-sprite és festett részletgazdagság keverése a kis pixelrajzokkal.
- Neonfű, erősen telített nagy felületek, indokolatlan fehér csillanások.
- Ditheringgel, kavicsokkal, levelekkel vagy tetőmintával megtöltött üres felületek.
- Pusztán szín alapján megkülönböztetett gép, termény vagy UI-állapot.
- Díszes faablakok, nehéz keretek és olyan portré, amely elvonja a figyelmet a feladatról.
- Izometrikus fordulat, automatikus méretnövelés vagy új játékszabály a stílusegységesítés mellékhatásaként.
- A Generation 1 felismerhető karakterének lecserélése egy másik játék hangulatára.

## 13. Grafikai prioritás és az első mérföldkő

| Sorrend | Fókusz | Miért most? |
| --- | --- | --- |
| **1.** | Közös fény, anyag és pixelkezelés kis referenciamintán | A legtöbb későbbi döntést befolyásolja; korán kiderül, működik-e az evolúciós irány |
| **2.** | UI-olvashatóság és tartalomelérés | A játékos döntéseit közvetlenül segíti; megelőzi a puszta díszítést |
| **3.** | Kerítések, tóperem és terepillesztések | Gyakran ismétlődnek, ezért kis korrekció nagy területen javít az összképen |
| **4.** | Gépek és állatok sziluettje, léptéke, árnyéka | Mozgás közben is gyorsan kell azonosítani őket |
| **5.** | Növények, fák és állapotjelzések | Megerősíti a gazdaság olvashatóságát és előkészíti az évszakokat |
| **6.** | Épületcsalád célzott finomítása | A meglévő épületek jó alapok; elég a karakterek és anyagok pontosítása |
| **7.** | Ikonjelentések és portré összhangja | A működő piktogramcsalád megtartható, a hangulati eltérések célzottan csökkenthetők |
| **8.** | Visszafogott animáció és effekt | Stabil, olvasható állóképre érdemes életet építeni |
| **9.** | Teljes szezonális és későbbi hangulati rétegek | A megszilárdult alapon nem sokszorozódnak meg a formai hibák |

Ez fontossági sorrend; a részletes M1–M9 ütemezést az Art Style Guide **10. fejezete** tartalmazza. Az évszakos rétegezés előkészítése már az elején szükséges, a teljes szezonkészlet később készül.

### Javasolt M1 — Generation 2 referenciaminta

**Utólagos státusz:** ezt az eredeti javaslatot a felhasználó **M1 — Environment Polish** feladata váltotta fel. A környezeti mérföldkő elkészült; az aktuális eredményeket a [Graphics Roadmap](GRAPHICS_ROADMAP.md) rögzíti. Az itt leírt referenciaminta a kreatív előzmény része.

Egy kis összehasonlító jelenetben a **meglévő farmház, traktor, gyümölcsfa és tó**, valamint az alattuk lévő fű/föld/út kapjon közös fényt, anyagpalettát és pixelkezelést. Ne teljes kategóriák cseréjével kezdődjön a munka. A referencia mutassa meg, mennyi finomítás elég a jelenlegi karakter megőrzéséhez.

**M1 akkor sikeres, ha** normál méretben minden tárgy legalább olyan felismerhető, mint korábban; az árnyékok ugyanarra mutatnak; a tó és a tárgyak pixelkezelése összeillik; a háttér csendes marad; és sem a foglalás, sem a játékmenet nem változik. Ez a következő munka javaslata, nem az M0.1 részeként elkészített grafika.

## 14. A három alapelv, amely minden döntést vezet

1. **Olvashatóság:** a játékos értse meg előbb a tárgyat és az állapotot, mint hogy észrevenné a díszítést.
2. **Folytonosság:** a Generation 2 a FarmGame meglévő karakterét fejlessze tovább.
3. **Következetesség:** közös nézet, fény, anyag és állapotnyelv fogja össze a világot és a felületet.

Az Art Style Guide megadja a részletes megvalósítási kereteket. Ez a koncepciólap abban segít, hogy a kereteken belül **melyik kreatív döntés szolgálja legjobban a FarmGame-et**.
