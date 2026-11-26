# PL 5 – Od vzorků k fixacím

Jméno: ........................................

## Část A: algoritmus I-VT ručně

Tabulka obsahuje 30 po sobě jdoucích vzorků jednoho účastníka (60 vzorků za sekundu, tedy jeden vzorek každých 16,7 ms). Na této obrazovce odpovídá 1° přibližně 40 pixelům. Data jsou simulovaná.

**Postup pro každý řádek:**

1. **krok** = vzdálenost od předchozího vzorku: √((x − x₀)² + (y − y₀)²)
2. **rychlost** = krok ÷ 40 × 60, tedy **krok × 1,5** (ve stupních za sekundu)
3. rychlost **nad 30 °/s** je sakáda (S), jinak fixace (F)

Řádky 9–20 dopočítejte, ostatní už jsou hotové. U všech řádků doplňte F nebo S.

| n | čas (ms) | x (px) | y (px) | krok (px) | rychlost (°/s) | F / S |
|--:|--:|--:|--:|--:|--:|:-:|
| 1 | 0 | 962 | 536 | – | – |  |
| 2 | 17 | 961 | 541 | 4.9 | 7 |  |
| 3 | 33 | 965 | 546 | 6.4 | 10 |  |
| 4 | 50 | 956 | 546 | 8.4 | 13 |  |
| 5 | 67 | 949 | 528 | 19.3 | 29 |  |
| 6 | 83 | 954 | 535 | 8.4 | 13 |  |
| 7 | 100 | 957 | 545 | 10.8 | 16 |  |
| 8 | 117 | 952 | 534 | 12.8 | 19 |  |
| 9 | 133 | 960 | 541 |  |  |  |
| 10 | 150 | 958 | 546 |  |  |  |
| 11 | 167 | 1083 | 604 |  |  |  |
| 12 | 183 | 1376 | 751 |  |  |  |
| 13 | 200 | 1482 | 788 |  |  |  |
| 14 | 217 | 1485 | 778 |  |  |  |
| 15 | 233 | 1488 | 791 |  |  |  |
| 16 | 250 | 1487 | 792 |  |  |  |
| 17 | 267 | 1487 | 782 |  |  |  |
| 18 | 283 | 1488 | 791 |  |  |  |
| 19 | 300 | 1482 | 799 |  |  |  |
| 20 | 317 | 1484 | 796 |  |  |  |
| 21 | 333 | 1494 | 793 | 10.6 | 16 |  |
| 22 | 350 | 1488 | 805 | 13.6 | 20 |  |
| 23 | 367 | 1461 | 846 | 49.0 | 73 |  |
| 24 | 383 | 1474 | 848 | 12.8 | 19 |  |
| 25 | 400 | 1460 | 853 | 14.9 | 22 |  |
| 26 | 417 | 1460 | 841 | 12.5 | 19 |  |
| 27 | 433 | 1470 | 841 | 9.7 | 14 |  |
| 28 | 450 | 1477 | 853 | 13.9 | 21 |  |
| 29 | 467 | 1470 | 838 | 16.0 | 24 |  |
| 30 | 483 | 1467 | 846 | 8.3 | 12 |  |

### Otázky

1. Kolik fixací jste našli? ..............   Kolik sakád? ..............

2. Doplňte tabulku fixací:

| Fixace | Od vzorku | Do vzorku | Trvání (ms) = počet vzorků × 16,7 | Přibližný střed (x, y) |
| --: | --: | --: | --: | --- |
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

3. Jedna ze „sakád“ trvá jediný vzorek. Jak daleko jsou od sebe středy fixací před ní a po ní? .............. px, tedy .............. °

   Je to podle vás skutečná sakáda? Co by s ní udělalo pravidlo „sluč fixace bližší než 0,5°“?

   ......................................................................................................................

4. Zvyšte práh na **100 °/s** a oklasifikujte znovu. Kolik fixací vyjde teď? ..............   Jak dlouhá je nejdelší? .............. ms

5. Nastavte minimální délku fixace na **150 ms**. Které fixace z bodu 2 zmizí?

   ......................................................................................................................

6. Přístroj s 30 Hz by zaznamenal jen každý druhý řádek. Kolik vzorků by připadlo na první sakádu? ..............   Co z toho plyne pro měření sakád?

   ......................................................................................................................

## Část B: Gaze Lab

Otevřete příklad *From samples to fixations* (hledání oranžového kolečka, 8 účastníků, 120 Hz).

### 7. Práh rychlosti

Vyberte krok *Detect fixations by speed (I-VT)* a měňte *threshold*. Počet fixací čtěte na kartě kroku, medián trvání v hlášení vpravo.

| Práh (°/s) | Počet fixací | Medián trvání (ms) |
| --: | --: | --: |
| 10 | | |
| 30 | | |
| 100 | | |

Proč s vyšším prahem fixací ubývá a prodlužují se?

......................................................................................................................

### 8. Dva algoritmy

Druhá větev používá *Detect fixations by spread (I-DT)*. Počet fixací: ..............   Medián trvání: .............. ms

Otevřete *Fixation durations* u obou kroků. V čem se rozložení liší?

......................................................................................................................

### 9. Účastník se špatnými daty

V datovém panelu zvolte *Participant* P06 a u obou algoritmů zapište počet fixací (tabulka *Fixations*, počet řádků).

| | I-VT 10 °/s | I-VT 30 °/s | I-VT 100 °/s | I-DT |
| --- | --: | --: | --: | --: |
| P06 | | | | |

Podívejte se na *Signal over time* u P06. Proč některá nastavení nenajdou vůbec nic?

......................................................................................................................

### 10. Sakády

Vyberte *Detect saccades* a otevřete tabulku *Saccades*. Stáhněte ji tlačítkem *CSV for Excel* a vložte bodový graf: amplitude_deg na vodorovné ose, peak_velocity na svislé.

Co graf ukazuje? ..............................................................................

Jak byste podle něj poznali vadná data? ..............................................................

### 11. Skutečný počet

Data jsou simulovaná, takže skutečný počet fixací je známý. Lektor ho napíše na tabuli: ..............

Které nastavení se mu přiblížilo nejvíc? ..............................   Trefilo ho některé přesně?  ano / ne

## Shrnutí

Co všechno musí být v metodické části, aby někdo jiný došel ke stejnému počtu fixací?

......................................................................................................................

......................................................................................................................
