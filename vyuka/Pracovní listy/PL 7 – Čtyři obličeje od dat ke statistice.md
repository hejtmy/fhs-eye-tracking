# PL 7 – Čtyři obličeje: od dat ke statistice

Jméno: ........................................

**Výzkumná otázka.** Deset účastníků si osmkrát po šest sekund prohlíželo čtyři obličeje (zlostný, smutný, veselý, neutrální). Přitahuje zlostný obličej pohled jako první? A dívají se na něj lidé i nejdéle? Data jsou simulovaná.

Otevřete v Gaze Lab příklad *Four faces: first look and lasting look*.

**Pozor na větve.** Po kroku *Fill short gaps* se pipeline dělí. Odsazená větev začíná krokem *Trim trials in time* a pracuje jen s časem po třetí sekundě (638 fixací). Hlavní větev pokračuje pod ní krokem *Detect fixations by speed (I-VT)* s 1 286 fixacemi. Některé kroky se proto v seznamu jmenují stejně dvakrát. Pokud není řečeno jinak, pracujte v **hlavní větvi**.

## Část A: pipeline

### 1. Projděte kroky shora dolů a ke každému napište jednou větou, co dělá.

| Krok | Co dělá |
| --- | --- |
| Load recording | |
| Remove off-screen gaze | |
| Detect and remove blinks | |
| Fill short gaps | |
| Detect fixations by speed (I-VT) | |
| Draw areas of interest | |
| Measure attention per area | |
| Build a table for statistics | |

### 2. Oblasti zájmu

Vyberte *Draw areas of interest* a otevřete editor. Přepínejte mezi obrázky.

a) Proč má každý obrázek vlastní sadu oblastí? ..............................................................

b) Co by se stalo, kdyby obličeje byly vždy na stejném místě a lidé se rádi dívali nejdřív vlevo nahoru?

......................................................................................................................

### 3. Metriky

Vyberte *Measure attention per area* a otevřete tabulku *AOI metrics*. Co je jeden řádek tabulky?

......................................................................................................................

Který sloupec odpovídá na otázku „kam se podívali nejdřív“? ..............................

Který na otázku „kde se dívali nejdéle“? ..............................

### 4. Průměry

Vyberte *Build a table for statistics*. V tabulce je jeden řádek pro každého účastníka a obličej. Otevřete také pohled *Dwell time per area* u předchozího kroku. Odhadněte z tabulky nebo spočítejte v Excelu průměry přes účastníky:

| Obličej | first_fixation_ms | dwell_pct |
| --- | --: | --: |
| Angry (zlostný) | | |
| Happy (veselý) | | |
| Neutral | | |
| Sad (smutný) | | |

## Část B: statistika v jamovi

### 5. Tabulka pro test

V kroku *Build a table for statistics* přepněte *Layout* na *Wide* a stáhněte tabulku tlačítkem **CSV** (ne *CSV for Excel*). Co je teď jeden řádek? ..............................

### 6. Párový t-test

V jamovi: *Analyses → T-Tests → Paired Samples T-Test*. Zaškrtněte také *Descriptives* a *Effect size*.

| Srovnání | Průměr 1 | Průměr 2 | t | df | p | Cohenovo d |
| --- | --: | --: | --: | --: | --: | --: |
| first_fixation_ms: Angry × Happy | | | | | | |
| dwell_pct: Angry × Happy | | | | | | |

a) Proč párový test, a ne test pro dvě nezávislé skupiny?

......................................................................................................................

b) Napište výsledek jednou větou tak, jak by stál v článku.

......................................................................................................................

### 7. První pohled a pozdější pohled

Druhá větev pipeline začíná krokem *Trim trials in time* a nechává z každého pokusu jen čas po třetí sekundě. Vyberte poslední krok této větve.

| Obličej | dwell_pct celý pokus | dwell_pct po 3. sekundě |
| --- | --: | --: |
| Angry | | |
| Happy | | |

Co se stalo se zlostným obličejem? Jak se tomuto vzorci říká (slide 5)?

......................................................................................................................

### 8. Přechody

Vyberte *Count transitions between areas* a otevřete *Transition matrix*. Kam jde pohled nejčastěji ze zlostného obličeje? ..............   A kam se z ostatních obličejů vrací nejméně? ..............

## Část C: drží výsledek?

Vraťte se do hlavní větve a změňte **jednu** věc. Každá dvojice jinou:

- [ ] zmenšit všechny oblasti jen na samotný obličej (kruh)
- [ ] práh I-VT změnit z 30 na 100 °/s
- [ ] vynechat krok *Fill short gaps*
- [ ] vyřadit účastníka P07

Co jste změnili: ..............................................................

| Srovnání | t původně | t po změně | p původně | p po změně |
| --- | --: | --: | --: | --: |
| first_fixation_ms: Angry × Happy | | | | |
| dwell_pct: Angry × Happy | | | | |

Změnil se závěr? .............. Která metrika je na vaši změnu citlivější a proč?

......................................................................................................................

## Odevzdání

Tlačítkem *Save* uložte pipeline a soubor pošlete lektorovi. Je v něm každé nastavení, které jste použili.
