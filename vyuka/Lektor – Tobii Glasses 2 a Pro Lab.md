# Tobii Glasses 2 a Pro Lab: postup

Názvy položek v menu se mezi verzemi Pro Lab mírně liší. Projděte si postup předem na své verzi a případné rozdíly si sem dopište.

## 1. Nahrávání (blok 2)

Brýle Glasses 2 zaznamenávají 50 nebo 100 vzorků za sekundu podle modelu. Scénická kamera má rozlišení 1920 × 1080 a vodorovný zorný úhel 82°.

1. Účastník si nasadí brýle a vyberete nosník, se kterým sedí pevně a neklouzají.
2. V Tobii Glasses Controller založte projekt (například `FHS vyuka`) a účastníka.
3. Kalibrace: účastník se dívá na střed kalibrační kartičky, kterou držíte asi metr před ním.
4. Kontrola: požádejte ho, ať se podívá na váš prst a na roh dveří. Kroužek pohledu v živém náhledu má sedět. Když nesedí, kalibraci opakujte.
5. Spusťte nahrávání a projděte úkoly z [[PL 3 – Protokol nahrávání]].
6. Zastavte nahrávání. Brýle nesundávejte dřív, než je nahrávka uložená.

**Značky úkolů.** Analýza potřebuje vědět, kdy který úkol začal a skončil. Nejjednodušší postup: experimentátor před každým úkolem nahlas řekne „start“ a po něm „konec“ (scénická kamera nahrává i zvuk) a zapisovatel píše čas na stopkách. Přesné značky se pak doplní v Pro Lab.

## 2. Import a značky v Pro Lab

1. Nový projekt typu Glasses, import nahrávek z SD karty.
2. Otevřete nahrávku v záložce Analyze. Přehrajte ji a u každého úkolu vložte vlastní událost (Custom Event) na začátek a na konec. Pojmenujte je takto, Gaze Lab je pak rozpozná bez nastavování:

| Úkol | Začátek | Konec |
| --- | --- | --- |
| Validační terč | `validace_start` | `validace_end` |
| Čtyři obličeje | `obliceje_start` | `obliceje_end` |
| Regál, volné prohlížení | `freeview_start` | `freeview_end` |
| Regál, najdi nejlevnější | `cheapest_start` | `cheapest_end` |
| Regál, vyber si | `choice_start` | `choice_end` |
| Počítání, příklad 1–6 | `lehka1_start`, `stredni1_start`, `tezka1_start`, … | `lehka1_end`, … |

Tohle je dobrá práce pro studenty: každý si označí vlastní nahrávku a přitom vidí, jak vypadá jeho pohled ve videu (slide 28).

## 3. Mapování na snapshot

Pohled v nahrávce je v souřadnicích scénické kamery, která se hýbe s hlavou. Aby šly kreslit AOI, musí se pohled přenést na nehybný obrázek.

1. Přidejte snapshoty: `ctyri_obliceje_set_1.png` a `regal.png` (stejné soubory, které visí na zdi). Snapshot regálu pojmenujte `Shelf`.
2. Spusťte automatické (asistované) mapování na úsek mezi značkami daného úkolu. Funguje dobře, když je podnět ve videu ostrý a dobře osvětlený.
3. Zkontrolujte výsledek. Kde mapování chybí nebo je vedle, doplňte body ručně klikáním (slide 28).
4. Na snapshot nakreslete AOI. U obličejů `Angry`, `Sad`, `Happy`, `Neutral`, u regálu podle výrobků (`Oat flakes`, `Muesli`, `Cornflakes`, `Granola`, `Porridge`, `Bran`).

## 4. Filtr fixací v Pro Lab (blok 4)

V nastavení Gaze filter přepínejte:

| Filtr | Práh | K čemu |
| --- | --- | --- |
| Raw | žádný | každý vzorek zvlášť |
| Tobii I-VT (Fixation) | 30 °/s | sedící účastník, obrazovka |
| Tobii I-VT (Attention) | 100 °/s | brýle, pohyb hlavy |

Nechte studenty přehrát stejných 10 sekund nahrávky se všemi třemi a spočítat kroužky na obrazovce. Odpovídá to slidu 27.

## 5. Export

**Metriky (Metrics export).** Tabulka po účastnících a AOI: počet fixací, celková doba, čas do první fixace. Otevře se v Excelu a dá se rovnou porovnat s ručním výpočtem z PL 6.

**Data (Data export, TSV), jeden soubor na nahrávku.** Zaškrtněte aspoň: Recording timestamp, Sensor, Participant name, Event, Gaze point X/Y, Pupil diameter left/right, Eye movement type, Eye movement type index, Mapped gaze data X/Y pro snapshot a sloupce AOI hit.

## 6. Z Pro Lab do Gaze Lab

1. V Gaze Lab: *Examples → Analyse your own recording*.
2. V kroku *Load recording* nahrajte exportované TSV soubory a jako obrázek podnětu nahrajte snapshot.
3. V nastavení sloupců zvolte pro X a Y sloupce *Mapped gaze data* daného snapshotu.
4. Přidejte kroky: *Cut trials from markers* → *Fill short gaps* → *Detect fixations by speed (I-VT)* s prahem kolem 50 °/s → *Areas from file columns* → *Measure attention per area* → *Build a table for statistics*.

Pro regál je to stejný postup jako v příkladu *Glasses: which product gets attention?*. Studenti tak porovnají vlastní nahrávku se simulovanou studií.

**Bez Pro Lab.** `livedata.json.gz` z SD karty jde do Gaze Lab nahrát přímo. Dostanete fixace, sakády, mrkání a zornici. Chybí mapování na obrázek, takže AOI nakreslit nejde. Pro úlohu se zornicí to stačí, úseky jednotlivých příkladů pak vyberete podle času ze zápisu v PL 3.

## Zornice z brýlí (blok 6)

V Data exportu jsou sloupce Pupil diameter left a right v milimetrech. Pro PL 8 stačí v Excelu:

1. nechat jen řádky, kde Sensor je Eye Tracker,
2. spočítat průměr obou očí,
3. podle značek nebo časů ze zápisu označit u každého příkladu 2 sekundy před zadáním (baseline) a dobu počítání.

Pět studentů krát šest příkladů je málo na statistiku a dost na to, aby bylo vidět, jestli zornice s obtížností roste.
