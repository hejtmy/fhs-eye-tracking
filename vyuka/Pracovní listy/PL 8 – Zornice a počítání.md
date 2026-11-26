# PL 8 – Zornice a počítání

Jméno: ........................................

**Otázka.** Roste zornice s obtížností příkladu, který člověk počítá zpaměti?

Pracujte buď s vlastní nahrávkou z brýlí (sloupce Pupil diameter v exportu z Pro Lab a časy z PL 3), nebo se záložním souborem `zornice_pocitani_excel.csv`. Návod níže je psaný pro záložní soubor: dva simulovaní účastníci (A, B), šest pokusů každý, 50 vzorků za sekundu.

| Sloupec | | Význam |
| --- | --- | --- |
| A | ucastnik | A nebo B |
| B | pokus | 1 až 6 |
| C | obtiznost | lehká, střední, těžká |
| D | cas_ms | čas od zadání příkladu; záporný čas je ticho před zadáním |
| E | zornice_mm | průměr zornice |

## 1. Podívejte se na data

Vyfiltrujte účastníka A, pokus 1 a vložte bodový graf s čarami: cas_ms proti zornice_mm.

a) Co se se zornicí stane po čase 0? ..............................................................

b) V grafu jsou prudké propady a mezery. Co to je? ..............................................

c) Kolik procent hodnot zornice chybí v celém souboru? .............. %

## 2. Baseline

Baseline je průměrná velikost zornice těsně před úlohou, tady ve dvou sekundách před zadáním. Vedle dat si udělejte malou tabulku (účastník ve sloupci H, pokus ve sloupci I) a použijte vzorec:

`=AVERAGEIFS(E:E; A:A; H2; B:B; I2; D:D; "<0")`

## 3. Velikost zornice při úloze

Průměr v době počítání, od 1,5 do 6 sekund po zadání:

`=AVERAGEIFS(E:E; A:A; H2; B:B; I2; D:D; ">=1500"; D:D; "<6000")`

Proč ne hned od času 0? ..............................................................................

## 4. Korekce

Změna = zornice při úloze − baseline. Doplňte:

| Účastník | Pokus | Obtížnost | Baseline (mm) | Při úloze (mm) | Změna (mm) |
| :-: | :-: | --- | --: | --: | --: |
| A | 1 | | | | |
| A | 2 | | | | |
| A | 3 | | | | |
| A | 4 | | | | |
| A | 5 | | | | |
| A | 6 | | | | |
| B | 1 | | | | |
| B | 2 | | | | |
| B | 3 | | | | |
| B | 4 | | | | |
| B | 5 | | | | |
| B | 6 | | | | |

## 5. Srovnání obtížností

Průměr ze dvou pokusů:

| | Lehká | Střední | Těžká |
| --- | --: | --: | --: |
| A: při úloze (mm), bez korekce | | | |
| B: při úloze (mm), bez korekce | | | |
| A: změna proti baseline (mm) | | | |
| B: změna proti baseline (mm) | | | |

a) Porovnejte nekorigované hodnoty: účastník B při lehké úloze a účastník A při těžké. Kdo má větší zornici? ..............

b) Co by vyšlo, kdybyste bez korekce zprůměrovali data lidí, z nichž každý dělal jinou obtížnost?

......................................................................................................................

c) Roste změna zornice s obtížností u obou účastníků?  ano / ne

## 6. Co může výsledek zkazit

U každé položky napište, jak by ovlivnila zornici a jak jste to v nahrávání ošetřili (nebo neošetřili).

| Vliv | Co udělá se zornicí | Jak ošetřit |
| --- | --- | --- |
| Světlo v místnosti, pohled z okna | | |
| Pohled na světlý nebo tmavý podnět | | |
| Mrknutí | | |
| Mluvení a pohyb během úlohy | | |
| Tréma, že mě ostatní sledují | | |
| Káva před výukou | | |

## 7. Vlastní nahrávka

Pokud máte vlastní data, zopakujte kroky 2–5 pro sebe. Baseline jsou 3 sekundy ticha před zadáním, úloha je čas od dočtení zadání do odpovědi (časy z PL 3).

| | Lehká | Střední | Těžká |
| --- | --: | --: | --: |
| Moje změna proti baseline (mm) | | | |

Vyšlo to podle očekávání? Pokud ne, čím to mohlo být?

......................................................................................................................
