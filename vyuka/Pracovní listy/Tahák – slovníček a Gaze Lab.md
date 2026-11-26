# Tahák – slovníček a Gaze Lab

## Pojmy

| Česky | Anglicky | Co to je |
| --- | --- | --- |
| vzorek | sample | jeden řádek surových dat: čas, x, y, zornice |
| vzorkovací frekvence | sampling rate (Hz) | počet vzorků za sekundu |
| přesnost | accuracy | o kolik je naměřený pohled vedle skutečného (°) |
| preciznost | precision | jak moc vzorky „skáčou“ při pohledu na jeden bod (°) |
| zrakový úhel | visual angle | velikost viděná okem ve stupních; 1° je asi 1,75 cm na metr |
| fixace | fixation | pohled stojí na místě, obvykle 100–500 ms |
| sakáda | saccade | rychlý skok mezi fixacemi, 20–100 ms |
| mrknutí | blink | 100–400 ms bez dat, okolní vzorky jsou zkreslené |
| kalibrace | calibration | přístroj se učí oči konkrétního člověka |
| validace | validation | kontrola, jak dobře kalibrace dopadla |
| oblast zájmu | area of interest (AOI) | vymezená část podnětu |
| čas do první fixace | time to first fixation (TTFF) | za jak dlouho pohled poprvé dopadl do AOI |
| doba setrvání | dwell time | součet trvání všech fixací v AOI |
| návrat | revisit | další vstup pohledu do AOI |
| cesta pohledu | scanpath | fixace a sakády jednoho člověka v pořadí |
| matice přechodů | transition matrix | jak často pohled přešel z jedné AOI do druhé |
| výchozí úroveň | baseline | velikost zornice těsně před úlohou |
| pokus | trial | jedno předvedení podnětu |
| podmínka | condition | varianta úlohy, kterou porovnáváme |

## Typické hodnoty

| | |
| --- | --- |
| Fixace při prohlížení obrázku | 200–400 ms |
| Fixace při čtení | kolem 200 ms |
| Rychlost sakády | 300–500 °/s |
| Práh I-VT, obrazovka | 30 °/s |
| Práh I-VT, brýle | 100 °/s |
| Minimální délka fixace | 60–100 ms |
| Oblast ostrého vidění | 1–2° |

## Gaze Lab: obrazovka

- **Vlevo** je pipeline: kroky analýzy shora dolů. Pod ní knihovna kroků, které lze přidat.
- **Uprostřed** jsou data u vybraného kroku. Přepínač *Input / Output* ukazuje data před krokem a po něm. Vedle jsou záložky s obrázky a tabulkami.
- **Vpravo** je popis kroku, jeho nastavení, hlášení o tom, co udělal, a otázka k zamyšlení.

Každá změna nastavení se hned přepočítá.

## Gaze Lab: kroky

| V aplikaci | Česky |
| --- | --- |
| Load recording | načíst nahrávku |
| Cut trials from markers | rozdělit na pokusy podle značek |
| Trim trials in time | nechat jen časové okno z každého pokusu |
| Remove off-screen gaze | odstranit pohled mimo obrazovku |
| Detect and remove blinks | najít a odstranit mrknutí |
| Fill short gaps | doplnit krátké mezery |
| Reduce noise | vyhladit šum |
| Baseline-correct pupil | odečíst baseline zornice |
| Detect fixations by speed (I-VT) | fixace podle rychlosti |
| Detect fixations by spread (I-DT) | fixace podle rozptylu |
| Detect saccades | najít sakády |
| Draw areas of interest | nakreslit oblasti zájmu |
| Areas from file columns | oblasti zájmu ze sloupců souboru (Tobii AOI hit) |
| Measure attention per area | metriky pro každou oblast |
| Count transitions between areas | přechody mezi oblastmi |
| Find viewing patterns | opakující se pořadí oblastí |
| Summarise each trial | souhrn za každý pokus |
| Build a table for statistics | tabulka pro statistiku |

## Gaze Lab: tlačítka a pohledy

| V aplikaci | K čemu |
| --- | --- |
| Examples | připravené příklady a vlastní nahrávka |
| Participant / Trial | výběr účastníka a pokusu v datovém panelu |
| Show input in grey | pod výsledkem šedě vykreslí data před krokem |
| Signal over time | průběh x, y a zornice v čase |
| Gaze on the stimulus | pohled na obrázku podnětu |
| Heatmap | teplotní mapa |
| Fixation durations | rozložení délek fixací |
| Dwell time per area | doba setrvání podle oblastí |
| Transition matrix | matice přechodů |
| Branch | druhá větev analýzy ze stejných dat |
| CSV | tabulka pro jamovi, JASP a R |
| CSV for Excel | stejná tabulka se středníky a desetinnými čárkami |
| Save | uloží pipeline se vším nastavením |
| Export results | zip se všemi tabulkami |

## Sloupce v tabulce AOI metrics

| Sloupec | Význam |
| --- | --- |
| fixation_count | počet fixací v oblasti |
| dwell_ms | doba setrvání v ms |
| dwell_pct | podíl z celkového času fixací v pokusu (%) |
| visits | počet návštěv |
| first_fixation_ms | čas do první fixace (prázdné = nikdy) |
| first_fixation_duration | trvání první fixace |
| mean_fixation_ms | průměrné trvání fixace |
