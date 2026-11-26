# Plán bloku

Celkem 600 minut: 540 minut výuky a 60 minut přestávek. Dá se odučit v jednom dlouhém dni, lépe ve dvou (bloky 1–3 a 4–6). Mezi dvěma dny pak stihnete nahrávky z brýlí v klidu naimportovat a namapovat.

| Blok | Téma | Minut | Slidy | Pracovní listy | Hlavní výstup |
| --- | --- | --: | --- | --- | --- |
| 1 | Úvod a pohyby očí | 75 | 1–7, 50 | PL 1, PL 9 (část A) | Student popíše fixaci a sakádu z vlastní zkušenosti |
| 2 | Eyetrackery a sběr dat | 105 | 8–19 | PL 2, PL 3 | Každý má vlastní nahrávku z brýlí |
| 3 | Surová data a předzpracování | 75 | 20–24, 47 | PL 4 | Student najde chybějící data a body mimo obrazovku |
| 4 | Fixace a sakády | 85 | 25–29 | PL 5 | Student ručně provede I-VT a ví, co dělá práh |
| 5 | AOI, metriky a scanpathy | 110 | 30–35, 46 | PL 6, PL 7 | Tabulka pro statistiku a párový t-test |
| 6 | Pupilometrie, vizualizace, vlastní studie | 90 | 36–51 | PL 8, PL 9 (část B) | Návrh vlastní studie |

Co je označeno **(jádro)**, nevynechávejte. Co je **(rozšíření)**, slouží jako rezerva pro rychlé studenty nebo se dá škrtnout, když dojde čas.

---

## Blok 1: Úvod a pohyby očí (75 min)

| Čas | Co | Jak |
| --: | --- | --- |
| 0–10 | Rozehřátí bez slidů **(jádro)** | PL 1, úkoly 1 a 2: zrcátko a písmena. Teprve potom řekněte, o čem blok je. |
| 10–30 | Výklad, slidy 3–7 | U slidu 4 se zastavte u rozdílu overt a covert pozornosti: studenti ho právě zažili v úkolu 2. |
| 30–45 | Pozorování ve dvojicích **(jádro)** | PL 1, úkoly 3 a 4: čtení a sledování prstu. |
| 45–55 | Yarbus na papíře **(jádro)** | PL 1, úkol 5: předpověď, kam se bude člověk dívat při třech různých zadáních. Papíry si schovejte, v bloku 5 se porovnají s nahrávkou. |
| 55–75 | Rozbor metod, první čtení | PL 9, část A. Studenti čtou jen metodickou část článku a vyplňují, čemu rozumí a čemu ne. Nevysvětlujte, odpovědi přijdou během dne. |

**Otázky k diskusi**

- Když se díváte na něčí obličej, kolik z něj v danou chvíli vidíte ostře?
- Proč nevidíme vlastní sakády, když je partner vidí bez potíží?
- Kdy „kam se dívám“ neznamená „na co myslím“? (zírání do prázdna, covert pozornost, čtení bez porozumění)

**Na co si dát pozor.** Studenti rádi přijmou větu „oči jsou oknem do mysli“ doslova. Úkol 2 v PL 1 ukazuje, že pozornost a pohled jdou od sebe oddělit, a k tomu se dá celý den vracet.

---

## Blok 2: Eyetrackery a sběr dat (105 min)

| Čas | Co | Jak |
| --: | --- | --- |
| 0–15 | Výklad, slidy 9–11 | Brýle nechte kolovat už během výkladu. |
| 15–35 | Zrakový úhel **(jádro)** | PL 2. Palec na natažené paži, přepočet na vlastní obrazovku, velikost AOI podle přesnosti přístroje. |
| 35–45 | Výklad, slidy 12–15 | Kalibraci jen krátce, hned ji uvidí. |
| 45–95 | Nahrávání brýlemi **(jádro)** | PL 3. Role se střídají, na jednoho účastníka asi 9 minut. Postup v [[Lektor – Tobii Glasses 2 a Pro Lab]]. |
| 95–105 | WebGazer **(rozšíření)** | Každý na svém notebooku kalibrační demo na webgazer.cs.brown.edu. Odhadněte chybu v centimetrech a přepočtěte na stupně podle PL 2. |

**Souběžně s nahráváním.** Nahrává se vždy jeden člověk, tři mají role a pátý má volno. Pátý student mezitím dělá WebGazer nebo dokončuje PL 2.

**Otázky k diskusi**

- Brýle mají udávanou přesnost kolem 0,6°, webkamera 2–5°. Jak velké AOI si můžete dovolit s každým z nich?
- Co se stane s přesností, když si účastník po kalibraci posune brýle na nose?
- Slidy 17–19: proč se u čtyř obrázků střídají pozice?

**Citlivý obsah.** Čtveřice obrázků ze slidu 17 obsahuje autonehodu a studenti jsou zde zároveň účastníky. Pro nahrávání proto používejte čtyři schematické obličeje (`ctyri_obliceje_set_1.png`), které mají stejnou logiku úlohy a v Gaze Lab k nim existují simulovaná data. Původní podněty ukažte jen jako příklad na slidu.

---

## Blok 3: Surová data a předzpracování (75 min)

| Čas | Co | Jak |
| --: | --- | --- |
| 0–10 | Výklad, slidy 21–23 | U slidu 22 nechte spočítat: 60 Hz × 6 s × 8 pokusů × 10 lidí. |
| 10–40 | Excel **(jádro)** | PL 4, část A. Soubor `surova_data_excel.csv`. |
| 40–50 | Výklad, slide 24 | Mrkání, interpolace, filtrování. |
| 50–75 | Gaze Lab poprvé **(jádro)** | PL 4, část B. Příklad *Four faces*, kroky Load, Remove off-screen gaze, Detect and remove blinks, Fill short gaps. |

**Otázky k diskusi**

- Účastník P07 se díval pod obrazovku. Je to chyba měření, nebo chování? Mají se ta data smazat?
- Mezera 75 ms se doplní, mezera 300 ms ne. Proč je hranice právě někde tady?
- Kolik procent chybějících dat je důvod účastníka vyřadit? (Neexistuje jedno číslo. Důležité je rozhodnout se před sběrem dat a napsat to do metod.)

**Vlastní nahrávka (rozšíření).** Kdo je hotov dřív, nahraje do Gaze Lab `livedata.json.gz` své nahrávky z SD karty a podívá se, kolik procent vzorků chybí.

---

## Blok 4: Fixace a sakády (85 min)

| Čas | Co | Jak |
| --: | --- | --- |
| 0–10 | Výklad, slide 26 | Jen princip: rychlost pod prahem je fixace. |
| 10–35 | I-VT ručně **(jádro)** | PL 5, část A. 30 vzorků, kalkulačka. Kdo je hotov, zkusí práh 100 °/s. |
| 35–65 | Gaze Lab **(jádro)** | PL 5, část B. Příklad *From samples to fixations*. Každá dvojice dostane jiný práh a počty se píší na tabuli. |
| 65–75 | Výklad, slidy 27–29 | Slide 27 teď dává smysl: tři nastavení, tři různé výsledky. |
| 75–85 | Pro Lab nebo hlavní sekvence **(rozšíření)** | Na vlastní nahrávce přepněte Gaze filter mezi Raw, Tobii I-VT (Fixation) a Tobii I-VT (Attention). Nebo v Gaze Lab tabulka Saccades a graf amplitudy proti rychlosti. |

**Tabule.** Sloupce: práh, počet fixací, medián trvání. Řádky doplňují dvojice. Na konci připište skutečný počet (631, viz klíč). Žádný práh ho netrefí přesně, a to je hlavní sdělení bloku.

**Otázky k diskusi**

- V ruční tabulce je „sakáda“ dlouhá jeden vzorek. Je to sakáda? Co s ní udělá minimální délka fixace a slučování?
- Proč se u brýlí používá práh 100 °/s a ne 30 °/s?
- Účastník P06: při prahu 10 °/s nemá žádnou fixaci. Co to říká o volbě prahu pro zašuměná data?

---

## Blok 5: AOI, metriky a scanpathy (110 min)

| Čas | Co | Jak |
| --: | --- | --- |
| 0–10 | Výklad, slidy 31–33 | Definice metrik. |
| 10–45 | Vše ručně **(jádro)** | PL 6. Kreslení scanpathu, AOI, metriky, řetězec, matice přechodů. |
| 45–55 | Výklad, slidy 34–35 | Levenshtein a matice přechodů už studenti mají spočítané. |
| 55–95 | Od dat ke statistice **(jádro)** | PL 7. Gaze Lab, příklad *Four faces*, export tabulky, párový t-test v jamovi. |
| 95–110 | Citlivost výsledku **(jádro)** | PL 7, část C. Zmenšit AOI nebo změnit práh a test zopakovat. |

**Otázky k diskusi**

- Zlostný obličej má nejkratší čas do první fixace a zároveň nejmenší podíl dwell time. Jak je to možné? (Odpověď je na slidu 5: vigilance a vyhýbání.)
- Co by se stalo s tímto výsledkem, kdybyste měli jen heatmapu?
- Kde má AOI končit: na okraji obličeje, nebo na okraji rámečku? Co když má přístroj přesnost 1°?

**Vlastní nahrávka (rozšíření).** V Pro Lab nakreslete AOI na snapshot čtyř obličejů a vyexportujte metriky pro pět nahraných lidí. Porovnejte s předpověďmi z PL 1, úkol 5 (regál).

---

## Blok 6: Pupilometrie, vizualizace a vlastní studie (90 min)

| Čas | Co | Jak |
| --: | --- | --- |
| 0–10 | Výklad, slide 37 | Zátěž, světlo, baseline. |
| 10–40 | Zornice a počítání **(jádro)** | PL 8. Vlastní data z bloku 2, nebo záložní `zornice_pocitani_excel.csv`. |
| 40–55 | Vizualizace, slidy 39–41 **(jádro)** | V Gaze Lab u stejných dat přepínejte *Gaze on the stimulus*, *Heatmap* a *Signal over time*. U každého pohledu jedna věc, kterou ukazuje, a jedna, kterou skrývá. |
| 55–60 | Software, slidy 43–45 | Jen přehled. |
| 60–85 | Vlastní studie **(jádro)** | PL 9, část B. Každý navrhne studii a dva ji krátce představí. Pak návrat k článku z bloku 1: čemu z metod teď rozumíte? |
| 85–90 | Závěr | Co si odnáším, co mi není jasné. |

**Otázky k diskusi**

- Účastník B má při lehké úloze větší zornici než účastník A při těžké. Co z toho plyne pro srovnávání lidí?
- Kdyby účastník při počítání hleděl na monitor s měnícím se jasem, co by se stalo se signálem?
- Heatmapa vypadá přesvědčivě. Co všechno o ní musíte vědět, než jí uvěříte? (počet lidí, délka záznamu, šířka rozmazání, barevná škála)

---

## Varianty

**Když brýle nefungují.** Blok 2 nahraďte ukázkou ze slidu 28 a WebGazerem. Všechny další aktivity běží na simulovaných datech beze změny.

**Když není internet nebo server.** Gaze Lab spusťte na svém notebooku (`docker compose up -d`) a promítejte. PL 7 se dá dokončit ze záložních tabulek pro jamovi.

**Když zbývá čas.** Studenti zpracují vlastní nahrávku od začátku do konce: Pro Lab export → Gaze Lab → tabulka → jamovi. Postup je v [[Lektor – Tobii Glasses 2 a Pro Lab]].
