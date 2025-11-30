# Nástin vizualizací a analýz eyetrackerových dat v R

Tento dokument slouží jako přehled možných přístupů k analýze a vizualizaci dat z oční kamery (eyetrackeru) v prostředí R. Zaměřujeme se na využití základních funkcí, ale i specializovaných balíků `eyer` a `eyetools`, a moderní vizualizaci pomocí `ggplot2`.

## 1. Příprava dat (Data Wrangling)
Před samotnou analýzou je nutné data vyčistit a připravit.
*   **Načítání dat:** Import z textových formátů (CSV, TXT) nebo proprietárních formátů (EDF, GazePoint, Tobii).
*   **Synchronizace:** Sjednocení časových os eyetrackeru a experimentálního softwaru (např. PsychoPy, E-Prime).
*   **Předzpracování (Preprocessing):**
    *   Filtrace artefaktů (mrkání, ztráta signálu).
    *   Vyhlazování dat (smoothing).
    *   Interpolace chybějících hodnot.
*   **Segmentace:** Rozdělení dat na jednotlivé pokusy (trialy) na základě event markerů.

## 2. Základní metriky a analýzy
Základní popisné statistiky pohybu očí.
*   **Fixace:** Identifikace míst, kde oko spočinulo (algoritmy I-VT, I-DT).
    *   Počet fixací.
    *   Průměrná délka fixace.
    *   Celková doba fixací.
*   **Sakády:** Rychlé pohyby očí mezi fixacemi.
    *   Amplituda (vzdálenost).
    *   Rychlost a zrychlení.
    *   Směr.
*   **Pupilometrie:** Změny velikosti zornice (reakce na světlo, kognitivní zátěž).
    *   Baseline korekce.
    *   Analýza fázických změn.

## 3. Analýza oblastí zájmu (AOI - Areas of Interest)
Klíčová část analýzy zkoumající, zda a jak dlouho se účastník díval na specifické části podnětu.
*   **Definice AOI:** Obdélníkové, kruhové nebo polygonální oblasti.
*   **Metriky:**
    *   **Time to First Fixation (TTFF):** Čas do první fixace v AOI.
    *   **Dwell Time:** Celkový čas strávený v AOI.
    *   **Fixation Count:** Počet fixací v AOI.
    *   **Revisits:** Počet návratů do AOI.
    *   **Sequence Analysis:** Pořadí navštívených AOI.

## 4. Vizualizace (ggplot2 & specializované balíky)
Grafické zobrazení dat pro kvalitativní kontrolu a prezentaci výsledků.

### Prostorové vizualizace (Spatial)
*   **Scanpath (Gaze Plot):** Trajektorie pohybu očí (fixace jako body, sakády jako čáry).
    *   *Využití:* Zobrazení strategie prohlížení jednotlivce.
*   **Heatmapa (Heatmap):** Teplotní mapa hustoty fixací.
    *   *Využití:* Agregace dat více účastníků, identifikace "hot spots".
*   **AOI Plot:** Zobrazení podnětu s vykreslenými hranicemi AOI.

### Časové vizualizace (Temporal)
*   **Gaze x Time:** Souřadnice X a Y v čase.
*   **Pupil x Time:** Vývoj velikosti zornice v čase (průměr přes trialy se stínováním směrodatné odchylky).

### Souhrnné vizualizace
*   **Bar ploty / Box ploty:** Porovnání metrik (např. Dwell Time) mezi podmínkami nebo skupinami.
*   **Binning:** Rozdělení obrazovky na mřížku a statistika pro každou buňku.

## 5. Balíky v R
*   **Base R:** Flexibilní, ale vyžaduje více kódu (viz `claude.R`).
*   **`eyetools`:** Komplexní nástroj pro zpracování a analýzu, podpora pro různé trackery.
*   **`eyer`:** Balík pro jednotnou reprezentaci eyetracking dat, snadná manipulace a vizualizace.
*   **`saccades`:** Detekce fixací a sakád.
*   **`ggplot2`:** Univerzální nástroj pro tvorbu publikačních grafů.

## 6. Ukázka pracovního postupu (Workflow)
1.  Načtení surových dat.
2.  Přiřazení informací o trialech (podmínka, podnět).
3.  Detekce fixací (pokud nejsou v datech).
4.  Definice AOI pro jednotlivé podněty.
5.  Výpočet metrik pro každou AOI a trial.
6.  Statistická analýza (ANOVA, LMM) a vizualizace výsledků.
