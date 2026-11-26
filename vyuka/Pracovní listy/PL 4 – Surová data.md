# PL 4 – Surová data

Jméno: ........................................

## Část A: Excel

Otevřete soubor `surova_data_excel.csv`. Je to záznam jednoho účastníka (P07) ze tří pokusů úlohy se čtyřmi obličeji. Obrazovka má 1920 × 1080 pixelů, bod [0, 0] je vlevo nahoře. Data jsou simulovaná.

| Sloupec | Význam |
| --- | --- |
| participant, trial, stimulus | účastník, pořadí pokusu, název obrázku |
| time_ms | čas od začátku nahrávání v milisekundách |
| gaze_x, gaze_y | poloha pohledu na obrazovce v pixelech |
| pupil_mm | průměr zornice v milimetrech |

### 1. Co je jeden řádek?

a) Kolik řádků má soubor? ..............

b) O kolik milisekund se liší čas dvou sousedních řádků? .............. ms

c) Kolik vzorků za sekundu tedy přístroj zaznamenal? .............. Hz  (1000 ÷ krok)

d) Jak dlouhý je jeden pokus? .............. s

### 2. Chybějící data

Některé řádky mají prázdné gaze_x. Přístroj v tu chvíli oko neviděl.

a) Kolik řádků chybí? ..............   Nápověda: `=COUNTBLANK(E2:E1081)`

b) Kolik je to procent? .............. %

c) Najděte první souvislou mezeru. Kolik řádků má a kolik je to milisekund? .............. řádků, .............. ms

d) Co se nejspíš stalo? ..............................................................................

e) Podívejte se na gaze_y a pupil_mm v několika řádcích těsně před mezerou a těsně po ní. Čeho si všimnete?

......................................................................................................................

### 3. Body mimo obrazovku

a) Do nového sloupce napište vzorec, který pozná pohled mimo obrazovku:

`=KDYŽ(NEBO(E2<0; E2>1920; F2<0; F2>1080); 1; 0)`

Kolik takových řádků je? ..............   Kolik procent? .............. %

b) Ve kterých pokusech jsou? ..............................

c) Kterým směrem se účastník díval? ..............................

d) Je to chyba měření, nebo chování účastníka? Podle čeho to poznáte?

......................................................................................................................

### 4. Graf

Vyberte sloupce time_ms a gaze_x pro pokus 1 a vložte bodový graf s čarami.

a) Jak v grafu vypadá fixace? ..............................................................

b) Jak vypadá sakáda? ..............................................................

c) Kolik fixací v pokusu 1 odhadujete od oka? ..............

## Část B: Gaze Lab

Otevřete Gaze Lab, zvolte *Examples* a příklad *Four faces: first look and lasting look*. Vpravo nahoře v datovém panelu vyberte *Participant* P07.

### 5. Krok *Load recording*

a) Přepněte mezi *File as read* a *Output*. Co se se sloupci stalo?

......................................................................................................................

b) Vpravo pod *What this step did*: kolik pixelů připadá na jeden stupeň? ..............

### 6. Krok *Remove off-screen gaze*

a) Kolik vzorků krok odstranil u všech účastníků dohromady? ..............

b) Zvětšete toleranci (*Tolerance beyond the edge*) na 300 px. Co se stalo a proč?

......................................................................................................................

### 7. Krok *Detect and remove blinks*

Otevřete *Signal over time* a zapněte *Show input in grey*. Přibližte si jedno mrknutí (červený pruh).

a) Co se děje se zornicí těsně před mrknutím? ..............................................

b) Krok odstraňuje i 50 ms před a po mrknutí. Proč?

......................................................................................................................

### 8. Krok *Fill short gaps*

a) Nejdelší mezera, která se doplní, je .............. ms.

b) Nastavte ji na 500 ms a podívejte se na signál. Co je na výsledku špatně?

......................................................................................................................

## Shrnutí

Tři rozhodnutí, která jsem při čištění dat udělal/a a která by měla být v metodické části:

1. ..................................................................................................................
2. ..................................................................................................................
3. ..................................................................................................................
