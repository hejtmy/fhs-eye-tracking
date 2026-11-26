# PL 6 – AOI a scanpath ručně

Jméno: ........................................

K listu patří barevný tisk obrázku se čtyřmi obličeji a souřadnicovou sítí. Účastník P02 si obrázek 6 sekund volně prohlížel. Tabulka obsahuje jeho fixace (simulovaná data).

## Oblasti zájmu (AOI)

| AOI | Obličej | x od–do | y od–do |
| :-: | --- | --- | --- |
| **V** | veselý | 200–760 | 90–490 |
| **Z** | zlostný | 1160–1720 | 90–490 |
| **N** | neutrální | 200–760 | 590–990 |
| **S** | smutný | 1160–1720 | 590–990 |

## Fixace účastníka P02

| n | začátek (ms) | trvání (ms) | x (px) | y (px) | AOI |
|--:|--:|--:|--:|--:|:-:|
| 1 | 0 | 233 | 960 | 543 |  |
| 2 | 317 | 150 | 1407 | 398 |  |
| 3 | 583 | 83 | 481 | 325 |  |
| 4 | 783 | 217 | 1570 | 146 |  |
| 5 | 1117 | 250 | 445 | 325 |  |
| 6 | 1417 | 183 | 369 | 331 |  |
| 7 | 1683 | 150 | 501 | 313 |  |
| 8 | 1917 | 150 | 374 | 229 |  |
| 9 | 2167 | 150 | 345 | 714 |  |
| 10 | 2417 | 100 | 481 | 285 |  |
| 11 | 2600 | 267 | 459 | 102 |  |
| 12 | 2950 | 117 | 558 | 241 |  |
| 13 | 3567 | 467 | 436 | 290 |  |
| 14 | 4150 | 183 | 1483 | 729 |  |
| 15 | 4450 | 183 | 437 | 361 |  |
| 16 | 4733 | 383 | 578 | 778 |  |
| 17 | 5233 | 583 | 1493 | 281 |  |

## 1. Nakreslete scanpath

Do obrázku zakreslete každou fixaci jako kroužek s pořadovým číslem (delší fixace = větší kroužek) a spojte je čarami v pořadí. Čtyřmi barvami obtáhněte hranice AOI.

## 2. Přiřaďte fixace

Do posledního sloupce tabulky napište ke každé fixaci písmeno AOI. Fixace mimo všechny oblasti označte pomlčkou.

## 3. Spočítejte metriky

| | V | Z | N | S |
| --- | --: | --: | --: | --: |
| Počet fixací (fixation count) | | | | |
| Celková doba (dwell time, ms) | | | | |
| Čas do první fixace (TTFF, ms) | | | | |
| Trvání první fixace (ms) | | | | |
| Počet návštěv | | | | |
| Počet návratů (revisits) = návštěvy − 1 | | | | |

a) Na který obličej se účastník podíval nejdřív? ..............

b) Na kterém strávil nejvíc času? ..............

c) Je to tentýž obličej? Co to říká o rozdílu mezi TTFF a dwell time?

......................................................................................................................

## 4. Řetězec AOI

Zapište pořadí návštěv jako řetězec písmen. Několik fixací po sobě ve stejné oblasti je jedna návštěva, fixace mimo oblasti vynechte.

P02: ..............................................

## 5. Porovnejte dva lidi

Účastník P01 měl na stejném obrázku řetězec **VZVNV**. Vezměte z řetězce P02 prvních šest písmen.

P01: V Z V N V

P02: ...  ...  ...  ...  ...  ...

Levenshteinova vzdálenost je nejmenší počet úprav (vložení, smazání nebo záměna jednoho písmene), kterými z jednoho řetězce uděláte druhý.

a) Kolik úprav potřebujete? ..............   Jakých? ..............................................

b) Řetězce ABAB a BABA mají vzdálenost 2, přitom vypadají jako stejné chování. Jakou slabinu této míry to ukazuje?

......................................................................................................................

## 6. Matice přechodů

Projděte celý řetězec P02 a za každou dvojici sousedních písmen udělejte čárku do příslušného políčka (řádek = odkud, sloupec = kam).

| z ↓ / do → | V | Z | N | S | Součet |
| :-: | :-: | :-: | :-: | :-: | :-: |
| **V** | – | | | | |
| **Z** | | – | | | |
| **N** | | | – | | |
| **S** | | | | – | |

a) Vydělte každý řádek jeho součtem. Kam jde pohled nejčastěji po veselém obličeji? .............. (.......... %)

b) Který obličej funguje jako „křižovatka“, přes kterou se pohled vrací? ..............

c) Z devíti přechodů jednoho člověka se pravděpodobnosti odhadují špatně. Kolik dat byste chtěli?

......................................................................................................................

## 7. Totéž v Pro Lab (pokud máte vlastní nahrávku)

Otevřete metriky exportované z Pro Lab pro úkol se čtyřmi obličeji a doplňte svůj řádek:

| | V | Z | N | S |
| --- | --: | --: | --: | --: |
| Počet fixací | | | | |
| Dwell time (ms) | | | | |
| TTFF (ms) | | | | |

V čem se vaše prohlížení lišilo od P02?

......................................................................................................................
