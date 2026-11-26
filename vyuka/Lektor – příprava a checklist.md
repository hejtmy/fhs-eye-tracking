# Příprava a checklist

## Týden předem

- [ ] **Gaze Lab běží na adrese, kam se studenti dostanou.** Buď na serveru (viz `docs/deployment.md`), nebo na vašem notebooku ve stejné síti. Otevřete příklad *Four faces: first look and lasting look* a zkontrolujte, že se načte.
- [ ] **Skutečná nahrávka z Glasses 2 jde do Gaze Lab načíst.** Čtení souborů Tobii bylo v Gaze Lab zatím vyzkoušeno jen na simulovaných souborech. Vyzkoušejte předem obě cesty na jedné vlastní nahrávce: `livedata.json.gz` z SD karty a Data Export (TSV) z Pro Lab. Když se některá nenačte, zvolte v kroku Load formát *Table of samples* a sloupce přiřaďte ručně, nebo tuto část nechte jen v Pro Lab.
- [ ] **Tobii Pro Lab.** Ověřte, že zkušební licence platí v den výuky a že dovolí import nahrávek z Glasses 2, mapování na snapshot a export dat. Pro Lab běží jen na Windows. Zjistěte, kolik studentů má Windows; ostatní pracují ve dvojici nebo jen v Gaze Lab.
- [ ] **Brýle.** Nabitá baterie i náhradní, volná SD karta, kalibrační kartička, nosníky, Tobii Glasses Controller na tabletu nebo notebooku. Zkuste celý průchod PL 3 na sobě a změřte čas.
- [ ] **jamovi a Excel** na počítačích studentů. Pošlete jim předem odkaz na instalaci jamovi.
- [ ] **Článek** k PL 9 (doi: 10.1371/journal.pone.0341261) rozeslat jako PDF. Stačí metodická část.
- [ ] **Excel a čeština.** Soubory `*_excel.csv` mají středníky a desetinné čárky. V českém Excelu se otevřou dvojklikem správně. Kdo má Excel v angličtině, použije *Data → Z textu/CSV*. Totéž dělá v Gaze Lab tlačítko *CSV for Excel* vedle tlačítka *CSV*.

## Tisk

| Co | Kolik | Jak |
| --- | --: | --- |
| Pracovní listy PL 1–9 a Tahák | 5 sad | černobíle, jednostranně (píše se do nich) |
| `prilohy/scanpath_podklad.png` | 5 | barevně, A4 na šířku |
| `prilohy/periferni_videni_A4.png` | 3 | A4 na šířku, do dvojic |
| `prilohy/validacni_terc_A4.png` | 1 | A4 na šířku, na zeď |
| `prilohy/ctyri_obliceje_set_1.png` | 1 | A3 barevně, na zeď |
| `prilohy/regal.png` | 1 | A3 barevně, na zeď |
| Klíč pro lektora | 1 | |

Z Obsidianu se tiskne přes *Export do PDF*. Pracovní listy jsou psané tak, aby se každý vešel na jeden až dva listy A4.

## Do místnosti

- [ ] pravítka nebo svinovací metr (jeden do dvojice a jeden na měření vzdálenosti od zdi)
- [ ] kalkulačky (stačí v mobilu)
- [ ] pastelky nebo fixy ve čtyřech barvách
- [ ] kapesní zrcátka (nebo přední kamera mobilu)
- [ ] lepicí hmota nebo páska na tisky, páska na označení místa na podlaze 1 m od zdi
- [ ] stopky
- [ ] rovnoměrně osvětlená světlá zeď bez oken v zorném poli (kvůli zornici)

## Rozmístění pro nahrávání

Na jednu zeď vedle sebe ve výšce očí stojícího člověka: validační terč, čtyři obličeje, regál. Vedle nich prázdné místo zdi s malou tečkou (pro úlohu se zornicí). Na podlaze značka 1 m od zdi.

## Mezi blokem 2 a 3 (nebo mezi dvěma dny)

- [ ] Zkopírovat nahrávky z SD karty. Každá nahrávka má složku se souborem `livedata.json.gz`; soubory přejmenujte podle účastníka, všechny se totiž jmenují stejně.
- [ ] Importovat nahrávky do Pro Lab, přidat snapshoty a spustit mapování. Automatické mapování chvíli trvá, proto je lepší to udělat o přestávce nebo přes noc.
- [ ] Jednu nahrávku si zpracovat celou, abyste věděli, kde to drhne.

## Kdyby něco selhalo

| Co selže | Co dělat |
| --- | --- |
| Brýle se nezkalibrují | Zkuste jiného účastníka (řasenka, tvrdé kontaktní čočky a silné dioptrie dělají potíže). Když to nejde vůbec, pokračujte na simulovaných datech. |
| Pro Lab neimportuje | Nahrajte `livedata.json.gz` rovnou do Gaze Lab. Přijdete o mapování na obrázek, fixace a zornice zůstanou. |
| Gaze Lab neběží | PL 5 část A, PL 6 a PL 8 jsou na papíře a v Excelu. Pro PL 7 jsou připravené tabulky `*_jamovi.csv`. |
| Studenti nemají jamovi | Párový t-test jde i v Excelu funkcí `T.TEST(oblast1; oblast2; 2; 1)`. |
