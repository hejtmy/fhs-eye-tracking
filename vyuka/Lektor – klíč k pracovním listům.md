# Klíč k pracovním listům

Čísla platí pro přílohy ve složce `prilohy/` a pro ukázkové příklady v Gaze Lab s výchozím nastavením. Vypočítal je skript `prilohy/vytvor_prilohy.py`; kdyby se ukázková data změnila, spusťte ho znovu a klíč zkontrolujte proti `prilohy/_klic_cisla.json`.

## PL 1 – Oči v akci

1. Vlastní oči v pohybu v zrcadle nevidíme, partner je vidí. Se zpožděnou kamerou pohyb vidět je. Během sakády mozek zrakový vjem potlačí (sakadická suprese); zpožděný obraz přijde až po sakádě, takže potlačen není.
2. Bez pohybu očí se dají přečíst jen písmena kolem křížku. Ostré vidění zajišťuje fovea, která pokrývá jen 1–2°; směrem k okraji ostrost rychle klesá, a to ani zvětšení písmen úplně nevyrovná, protože sousední písmena se ruší. Pozornost přesunout bez pohybu očí jde (covert pozornost), ale stojí to úsilí a oči mají tendenci uskočit.
3. Oči se při čtení pohybují skokem, na řádek připadá zhruba 5–10 skoků. Skok zpět je regrese: čtenář se vrací k něčemu, čemu nerozuměl.
4. Za prstem jedou oči plynule (smooth pursuit). Bez cíle to nejde a oči skáčou. Plynulý pohyb oko umí jen tehdy, když má co sledovat.
5. Očekávaný rozdíl: při volném prohlížení se pohled rozprostře po obalech; při hledání nejlevnějšího jde po cenovkách, nejprve popořadě, pak tam a zpět mezi nejnižšími; při výběru přeskakuje mezi dvěma favority (vzor A → B → A). Stejně jsou postavená simulovaná data v příkladu *Glasses: which product gets attention?*.

## PL 2 – Zrakový úhel a přesnost

- Tabulka: ve 200 cm odpovídá 1° asi 3,5 cm.
- Palec: šířka kolem 2 cm ve vzdálenosti 55–65 cm, tedy asi 2°.
- Příklad pro monitor 53 cm, 1920 px, vzdálenost 60 cm: pixel 0,028 cm; 1° = 1,05 cm = 38 px; celý monitor asi 48°.

| Přístroj | Přesnost | Chyba v cm | Chyba v px |
| --- | --: | --: | --: |
| Laboratorní | 0,5° | 0,5 | 19 |
| Glasses 2 | 0,6° | 0,6 | 23 |
| Webkamera | 4° | 4,2 | 152 |

- 3a: oči a ústa bývají od sebe 2–4°; laboratorní přístroj a brýle to zvládnou, webkamera ne.
- 3b: levou a pravou polovinu rozliší i webkamera.
- 3c: zvětšit podněty, dát je dál od sebe, nechat mezi nimi prázdné místo.
- 4: v 1 m je chyba 1,05 cm, ve 3 m 3,1 cm. Při volném pohybu se chyba v centimetrech mění se vzdáleností, takže AOI musí počítat s největší vzdáleností.

## PL 3 – Protokol nahrávání

Bez správných odpovědí. K otázkám na konci: kalibraci zhoršují řasenka, povislá víčka, tvrdé čočky, silné brýle a posun brýlí na nose. U validačního terče je při vzdálenosti 1 m odchylka 1 cm asi 0,6°. Při 40 lidech by se vyplatily automatické značky místo stopek, pevné pořadí úkolů s vyvážením a jasná pravidla, kdy nahrávku opakovat.

## PL 4 – Surová data

**Část A**

1. 1080 řádků; krok 16,7 ms; 60 Hz; pokus trvá 6 s (360 řádků).
2. Chybí 58 řádků, tedy 5,4 % (29 v pokusu 1, 29 v pokusu 2, žádný v pokusu 3). První mezera je na řádcích 27–42 v Excelu: 16 řádků, asi 267 ms. Je to mrknutí. Těsně před mezerou zornice prudce klesá (z 3,8 na 1,7 mm) a gaze_y roste, po mezeře se obojí vrací: víčko přejíždí přes zornici, takže přístroj vidí menší zornici a pohled „padá“ dolů.
3. Mimo obrazovku je 78 řádků, tedy 7,2 %: žádný v pokusu 1, 24 v pokusu 2, 54 v pokusu 3. Všechny mají gaze_y kolem 1190–1230, tedy pod dolním okrajem. Jsou to souvislé úseky o stabilní poloze, které vypadají jako fixace: účastník se díval pod monitor, například na klávesnici. Chyba měření by vypadala jako jednotlivé odlehlé body.
4. Fixace je vodorovný úsek, sakáda svislý skok. V pokusu 1 je od oka vidět kolem 15 fixací.

**Část B**

5. Sloupce dostanou jednotné názvy (time, x, y, pupil). Na stupeň připadá 40,3 px.
6. Krok odstraní 148 vzorků (0,5 %), všechny u P07. S tolerancí 300 px neodstraní téměř nic, protože pohledy pod obrazovku leží do 300 px od okraje. Otázka k diskusi: tento krok je určen pro chyby měření, kdežto P07 se skutečně díval jinam. Pro analýzu AOI na obrazovce je odstranění v pořádku, ale je to informace o účastníkovi, ne šum.
7. Zornice se před mrknutím zdánlivě zmenšuje a pohled klesá. Proto se odstraňuje i okolí mrknutí. V celém souboru je 81 mrknutí a odstraní se 918 vzorků (3,2 %).
8. Výchozí hranice je 75 ms. S 500 ms se přes mrknutí natáhne rovná čára: vypadá to jako data, ale je to výmysl, a mohou z toho vzniknout neexistující fixace.

## PL 5 – Od vzorků k fixacím

**Část A.** Úplná tabulka:

| n | čas (ms) | x (px) | y (px) | krok (px) | rychlost (°/s) | F / S |
|--:|--:|--:|--:|--:|--:|:-:|
| 1 | 0 | 962 | 536 | – | – | – |
| 2 | 17 | 961 | 541 | 4.9 | 7 | F |
| 3 | 33 | 965 | 546 | 6.4 | 10 | F |
| 4 | 50 | 956 | 546 | 8.4 | 13 | F |
| 5 | 67 | 949 | 528 | 19.3 | 29 | F |
| 6 | 83 | 954 | 535 | 8.4 | 13 | F |
| 7 | 100 | 957 | 545 | 10.8 | 16 | F |
| 8 | 117 | 952 | 534 | 12.8 | 19 | F |
| 9 | 133 | 960 | 541 | 11.2 | 17 | F |
| 10 | 150 | 958 | 546 | 5.8 | 9 | F |
| 11 | 167 | 1083 | 604 | 138.0 | 206 | **S** |
| 12 | 183 | 1376 | 751 | 328.3 | 489 | **S** |
| 13 | 200 | 1482 | 788 | 111.5 | 166 | **S** |
| 14 | 217 | 1485 | 778 | 10.9 | 16 | F |
| 15 | 233 | 1488 | 791 | 13.5 | 20 | F |
| 16 | 250 | 1487 | 792 | 1.6 | 2 | F |
| 17 | 267 | 1487 | 782 | 10.1 | 15 | F |
| 18 | 283 | 1488 | 791 | 8.9 | 13 | F |
| 19 | 300 | 1482 | 799 | 9.6 | 14 | F |
| 20 | 317 | 1484 | 796 | 3.3 | 5 | F |
| 21 | 333 | 1494 | 793 | 10.6 | 16 | F |
| 22 | 350 | 1488 | 805 | 13.6 | 20 | F |
| 23 | 367 | 1461 | 846 | 49.0 | 73 | **S** |
| 24 | 383 | 1474 | 848 | 12.8 | 19 | F |
| 25 | 400 | 1460 | 853 | 14.9 | 22 | F |
| 26 | 417 | 1460 | 841 | 12.5 | 19 | F |
| 27 | 433 | 1470 | 841 | 9.7 | 14 | F |
| 28 | 450 | 1477 | 853 | 13.9 | 21 | F |
| 29 | 467 | 1470 | 838 | 16.0 | 24 | F |
| 30 | 483 | 1467 | 846 | 8.3 | 12 | F |

Studenti počítají z hodnot zaokrouhlených na celé pixely, takže jim krok vyjde o několik desetin jinak. Na zařazení F nebo S to nemá vliv.

1. Tři fixace, dvě sakády.
2. Fixace 1: vzorky 1–10, 167 ms, střed asi (957, 540), tedy fixační křížek. Fixace 2: vzorky 14–22, 150 ms, střed asi (1487, 792). Fixace 3: vzorky 24–30, 117 ms, střed asi (1468, 846).
3. Středy fixací 2 a 3 jsou od sebe asi 57 px, tedy 1,4°. To je víc než 0,5°, pravidlo slučování by je nechalo zvlášť. Nejspíš jde o skutečnou malou sakádu uvnitř obrázku, která se při 60 Hz vešla do jediného vzorku. Stojí za to upozornit, že řádek 5 má 29 °/s: stačilo trochu víc šumu a vznikla by „sakáda“ uprostřed fixace.
4. Při 100 °/s zůstanou dvě fixace: 1–10 a 14–30. Delší má 17 vzorků, tedy 283 ms.
5. Zmizí fixace 3 (117 ms). Fixace 2 má právě 150 ms a zůstane.
6. Na první sakádu by připadl jeden až dva vzorky. Amplituda se ještě odhadnout dá, rychlost a trvání ne. Pro měření sakád je potřeba vyšší frekvence (slide 29).

**Část B** (příklad *From samples to fixations*)

| Práh | Počet fixací | Medián (ms) |
| --: | --: | --: |
| 10 °/s | 553 | 183 |
| 30 °/s | 549 | 217 |
| 100 °/s | 507 | 258 |
| I-DT (1°, 100 ms) | 539 | 242 |

Skutečný počet fixací v simulaci je **631** (medián 247 ms). Žádné nastavení ho netrefí: krátké fixace blízko sebe se slévají nebo je rozdělí mrknutí.

Vyšší práh přehlédne malé sakády, sousední fixace se spojí, takže jich je méně a jsou delší.

| | I-VT 10 | I-VT 30 | I-VT 100 | I-DT | Skutečnost |
| --- | --: | --: | --: | --: | --: |
| P06 | 0 | 91 | 58 | 0 | 73 |

P06 má trojnásobný šum. Při prahu 10 °/s je šum sám rychlejší než práh, takže žádný vzorek není „fixace“. I-DT s rozptylem 1° selže ze stejného důvodu. Při 30 °/s naopak šum fixace drobí a vyjde jich víc, než bylo.

Sakády: 431 sakád, korelace amplitudy a vrcholové rychlosti 0,94. Je to hlavní sekvence (slide 29). Body daleko od křivky bývají artefakty, například zbytky mrknutí.

## PL 6 – AOI a scanpath ručně

Vyřešený obrázek je v `prilohy/scanpath_klic_P02.png`.

Přiřazení fixací: 1 –, 2 Z, 3 V, 4 Z, 5 V, 6 V, 7 V, 8 V, 9 N, 10 V, 11 V, 12 V, 13 V, 14 S, 15 V, 16 N, 17 Z.

| | V | Z | N | S |
| --- | --: | --: | --: | --: |
| Počet fixací | 10 | 3 | 2 | 1 |
| Dwell time (ms) | 1950 | 950 | 533 | 183 |
| TTFF (ms) | 583 | 317 | 2167 | 4150 |
| Trvání první fixace (ms) | 83 | 150 | 150 | 183 |
| Návštěvy | 4 | 3 | 2 | 1 |
| Návraty | 3 | 2 | 1 | 0 |

- Nejdřív zlostný (317 ms), nejdéle veselý (1950 ms). TTFF měří, co pohled přitáhne; dwell time, kde pohled zůstává. Jsou to dvě různé otázky.
- Řetězec P02: **ZVZVNVSVNZ** (10 návštěv).
- Prvních šest písmen P02 je ZVZVNV, P01 má VZVNV. Vzdálenost je **1**: stačí na začátek vložit Z. Jinak je pořadí stejné.
- ABAB a BABA: míra trestá posun v čase, i když je strategie totožná. Navíc nevidí délku fixací ani vzdálenost oblastí.

Matice přechodů P02 (9 přechodů):

| z ↓ / do → | V | Z | N | S | Součet |
| :-: | :-: | :-: | :-: | :-: | :-: |
| **V** | – | 1 | 2 | 1 | 4 |
| **Z** | 2 | – | 0 | 0 | 2 |
| **N** | 1 | 1 | – | 0 | 2 |
| **S** | 1 | 0 | 0 | – | 1 |

- Po veselém jde pohled nejčastěji na neutrální (2 ze 4, 50 %).
- Křižovatkou je veselý obličej: téměř každý přechod vede z něj nebo do něj.
- Devět přechodů je málo. V příkladu v Gaze Lab je jich 528 od deseti lidí a i tam jsou některá políčka řídká.

## PL 7 – Čtyři obličeje

Průměry přes účastníky:

| Obličej | first_fixation_ms | dwell_pct | dwell_pct po 3. sekundě |
| --- | --: | --: | --: |
| Angry | 597 | 18,4 | 9,1 |
| Happy | 1764 | 27,3 | 31,0 |
| Neutral | 2023 | 25,3 | 32,2 |
| Sad | 2196 | 22,6 | 27,7 |

Párové t-testy (n = 10):

| Srovnání | t(9) | p | d |
| --- | --: | --: | --: |
| first_fixation_ms: Angry × Happy | −8,13 | < 0,001 | 2,6 |
| dwell_pct: Angry × Happy | −3,34 | 0,009 | 1,1 |
| dwell_pct po 3. sekundě: Angry × Happy | −11,5 | < 0,001 | |

- Jeden řádek tabulky *AOI metrics* je jeden účastník, jeden pokus a jedna oblast. Ve *Wide* je jeden řádek jeden účastník.
- Párový test proto, že každý účastník viděl všechny obličeje.
- Upozorněte na jednu věc: first_fixation_ms je prázdné, když se účastník na obličej v pokusu vůbec nepodíval. Průměr se pak počítá jen z pokusů, kde se podíval, což čas uměle zkracuje.
- Zlostný obličej přitáhne první pohled, ale pak se mu lidé vyhýbají. Po třetí sekundě na něj připadá polovina podílu. Je to vzorec vigilance a vyhýbání ze slidu 5. Zde je do simulovaných dat vložen záměrně.
- Přechody: ze zlostného jde pohled nejčastěji na veselý (47 ze 113, 42 %). Na zlostný se pohled vrací nejméně ze všech (59 přechodů z 528).
- Kdyby obličeje neměnily pozice, nedal by se vliv emoce oddělit od zvyku začínat vlevo nahoře.

Část C, co vyjde po změně:

| Změna | first_fixation: t | dwell_pct: t | Poznámka |
| --- | --: | --: | --- |
| původní nastavení | −8,13 | −3,34 | 1286 fixací |
| AOI jen na obličej (kruh 250 px) | −9,07 | −3,47 | podíly klesnou (Angry 14,7 %, Happy 22,8 %), časy do první fixace se prodlouží |
| práh I-VT 100 °/s | −8,17 | −3,52 | fixací jen 793, závěr stejný |
| bez *Fill short gaps* | −8,08 | −3,25 | 1301 fixací |
| bez P07 | −7,45 | −3,59 | df = 8 |

Závěr se tu nezmění ani jednou, čísla ano. Počet fixací se změnou prahu spadne o třetinu, kdežto dwell time a čas do první fixace skoro ne: metriky založené na čase v oblasti jsou vůči volbě algoritmu odolnější než počty fixací. V reálných datech s menším efektem by stejná změna mohla výsledek přehoupnout přes hranici významnosti, a proto patří tato rozhodnutí do metodické části.

## PL 8 – Zornice a počítání

1. Po čase 0 zornice během 1–1,5 s roste a drží se do konce úlohy. Propady jsou okraje mrknutí, mezery mrknutí sama. Chybí 2,5 % hodnot.
3. Zornice reaguje pomalu, plného rozšíření dosáhne až po více než sekundě.

| Účastník | Pokus | Obtížnost | Baseline | Při úloze | Změna |
| :-: | :-: | --- | --: | --: | --: |
| A | 1 | těžká | 3,41 | 3,79 | +0,38 |
| A | 2 | lehká | 3,43 | 3,42 | −0,01 |
| A | 3 | střední | 3,42 | 3,58 | +0,17 |
| A | 4 | těžká | 3,40 | 3,80 | +0,40 |
| A | 5 | střední | 3,37 | 3,61 | +0,24 |
| A | 6 | lehká | 3,42 | 3,47 | +0,04 |
| B | 1 | střední | 4,09 | 4,27 | +0,18 |
| B | 2 | těžká | 4,07 | 4,38 | +0,31 |
| B | 3 | lehká | 4,12 | 4,13 | +0,01 |
| B | 4 | lehká | 4,13 | 4,08 | −0,05 |
| B | 5 | těžká | 4,07 | 4,40 | +0,33 |
| B | 6 | střední | 4,03 | 4,20 | +0,17 |

| | Lehká | Střední | Těžká |
| --- | --: | --: | --: |
| A: při úloze | 3,44 | 3,60 | 3,79 |
| B: při úloze | 4,11 | 4,24 | 4,39 |
| A: změna | +0,02 | +0,21 | +0,39 |
| B: změna | −0,02 | +0,18 | +0,32 |

- Účastník B má při lehké úloze zornici 4,11 mm, účastník A při těžké 3,79 mm. Bez korekce by vyšlo, že lehká úloha zatěžuje víc. Rozdíly mezi lidmi jsou větší než účinek úlohy.
- Změna roste s obtížností u obou. Průběh je v `prilohy/zornice_klic.png`; propady v křivkách jsou okraje mrknutí, které se v Excelu neodstraňovaly.
- Tabulka vlivů: světlo zornici zužuje a je to mnohem silnější vliv než zátěž, proto pohled na jednu tečku na rovnoměrné zdi. Mrknutí dělá propady, které je třeba odstranit i s okolím. Mluvení a pohyb zornici rozšiřují, proto se počítá potichu a hodnotí se doba před odpovědí. Tréma a kofein zvedají celkovou úroveň, což z části řeší baseline před každým příkladem.

## PL 9 – Rozbor metod a vlastní studie

Část A doplňte podle článku. V diskusi se ptejte hlavně na to, co v metodách chybí: přesnost zjištěná validací, pravidla vyřazování, algoritmus a prahy pro fixace, velikost AOI ve stupních.

U části B kontrolujte tři věci: jestli metrika opravdu odpovídá na otázku, jestli jsou AOI větší než chyba zvoleného přístroje, a jestli pravidla pro vyřazování vznikla před sběrem dat.
