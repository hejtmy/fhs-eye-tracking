# Eye-tracking v psychologickém výzkumu: výukový blok (10 hodin)

Materiály k bloku pro 5 studentů, kteří neprogramují. K dispozici jsou jedny brýle Tobii Pro Glasses 2, zkušební verze Tobii Pro Lab, aplikace Gaze Lab (běží v prohlížeči), Excel a jamovi.

## Jak je blok postavený

Každý ze šesti bloků prezentace má stejný rytmus: krátký výklad ze slidů, aktivita bez techniky (papír, tužka, vlastní oči), a pak totéž na datech. Studenti tak každý krok analýzy nejdřív udělají ručně a teprve potom ho nechají udělat software.

Celým blokem se táhne jedna nit: **vlastní nahrávka**. V bloku 2 se každý student jednou nahraje brýlemi při čtyřech krátkých úkolech a v blocích 3–6 se k této nahrávce vrací. Kdyby brýle nebo Pro Lab selhaly, každá aktivita má záložní simulovaná data.

## Pro lektora

- [[Lektor – plán bloku]]: časový plán, scénář každého bloku, otázky k diskusi
- [[Lektor – příprava a checklist]]: co nainstalovat, vytisknout a vyzkoušet předem
- [[Lektor – Tobii Glasses 2 a Pro Lab]]: postup nahrávání a zpracování krok za krokem
- [[Lektor – klíč k pracovním listům]]: správné odpovědi a čísla

## Pro studenty (k tisku)

| List | Blok | Co se dělá | Potřebuje |
| --- | --- | --- | --- |
| [[PL 1 – Oči v akci]] | 1 | Pozorování vlastních očních pohybů | zrcátko nebo mobil, tisk |
| [[PL 2 – Zrakový úhel a přesnost]] | 2 | Přepočty cm ↔ stupně ↔ pixely | pravítko, kalkulačka |
| [[PL 3 – Protokol nahrávání]] | 2 | Nahrávání brýlemi, role ve skupině | brýle, tisky |
| [[PL 4 – Surová data]] | 3 | Co je v souboru, chybějící data, body mimo obrazovku | Excel |
| [[PL 5 – Od vzorků k fixacím]] | 4 | I-VT ručně, pak v Gaze Lab | kalkulačka, Gaze Lab |
| [[PL 6 – AOI a scanpath ručně]] | 5 | Metriky, řetězec AOI, matice přechodů | pastelky, tisk |
| [[PL 7 – Čtyři obličeje od dat ke statistice]] | 5 | Gaze Lab → tabulka → párový t-test | Gaze Lab, jamovi |
| [[PL 8 – Zornice a počítání]] | 6 | Baseline, korekce, srovnání obtížností | brýle, Excel |
| [[PL 9 – Rozbor metod a vlastní studie]] | 1 a 6 | Čtení metodické části, návrh studie | článek |
| [[Tahák – slovníček a Gaze Lab]] | stále | Pojmy česky a anglicky, ovládání aplikace | |

Tiskne se pro každého studenta jedna sada. PL 6 potřebuje navíc barevný tisk `prilohy/scanpath_podklad.png` (A4 na šířku).

## Přílohy

Složka `prilohy/` obsahuje data a obrázky k tisku. Vytváří je skript `prilohy/vytvor_prilohy.py` ze simulovaných ukázkových dat Gaze Lab, takže čísla v listech a v klíči odpovídají tomu, co studenti uvidí v aplikaci.

| Soubor | K čemu |
| --- | --- |
| `surova_data_excel.csv` | PL 4, otevře se dvojklikem v českém Excelu |
| `zornice_pocitani_excel.csv` | PL 8, záloha, kdyby vlastní nahrávka nevyšla |
| `ctyri_obliceje_jamovi.csv`, `ctyri_obliceje_po3s_jamovi.csv`, `hledani_jamovi.csv` | PL 7, záloha pro jamovi |
| `scanpath_podklad.png` | PL 6, podklad ke kreslení |
| `scanpath_klic_P01.png`, `scanpath_klic_P02.png`, `zornice_klic.png` | klíč pro lektora |
| `validacni_terc_A4.png` | PL 3, terč s devíti body na zeď |
| `periferni_videni_A4.png` | PL 1, písmena rostoucí od středu |
| `ctyri_obliceje_set_1.png`, `ctyri_obliceje_set_2.png`, `regal.png` | PL 3, podněty na zeď (ideálně A3) a snapshoty do Pro Lab |

Všechna data v přílohách jsou **simulovaná**. Slouží k nácviku postupu, ne k závěrům o lidech.
