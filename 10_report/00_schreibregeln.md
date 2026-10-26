# Schreibregeln der Semesterarbeit SA 16 (T1, Stand 2026-10-17)

Festgelegt am 2026-10-14 mit dem Nutzer; sie gelten für jeden Entwurf, den Claude schreibt, und für
die Prüfliste vor der Übergabe eines Abschnitts. Claude entwirft, der Nutzer redigiert.

## 1 Stimme

1. Vorbild ist der eigene Text der Bachelorarbeit BA-0486 (`00_literatur/01_beispielarbeiten`).
2. Unpersönlich und überwiegend passiv; kein "ich", kein "wir".
3. Sätze mit 15 bis 30 Wörtern, kurze Feststellungen, wenige lange Relativsätze, wechselnde
   Satzanfänge.
4. Keine Gedankenstriche. Doppelpunkt nur vor Formeln und Aufzählungen. Klammern nur für
   Abkürzungen und "vgl.".
5. Keine Werbeadjektive, keine Dreier-Aufzählungen als Rhythmus, keine Zusammenfassungssätze am
   Absatzende, keine wiederkehrenden Satzstrukturen.
6. Begriffe wie "Agent", "Gate", "Review", "Registry", "Pipeline" kommen im Text nicht vor.

## 2 Herkunft der Inhalte

1. Jeder Absatz steht auf einer Untersuchung, einer Tabelle, einem Bild, einer gelesenen Quelle
   oder auf Stichpunkten des Nutzers. Nichts wird frei erfunden.
2. Die Ergebniskapitel beschreiben Tabellen und Bilder Thema für Thema, in der Reihenfolge der
   Untersuchungen.
3. KI-gestützte Programmierung wird einmal im Methodenteil dezent genannt: Abaqus-Eingabedateien,
   Datenauswertung und Bildbau wurden mit Claude Code (Modell Fable 5.1) programmiert; die
   pydantic-Datenkontrakte der Kette leiten zum Ausblick über (Kontrakte für Messprotokolle und
   Rohdaten des Labors). Abgesprochen mit der Betreuerin.
4. Nicht formuliert wird, dass STplus-Quellcode oder Normen durch ein KI-System verarbeitet
   wurden. Der STplus-Abgleich ist ein eigenes Skript, das STplus im Stapelbetrieb mit variierten
   Eingabedateien aufruft und die Ergebnislisten einliest; damit wurden Randfälle untersucht.
5. Was der Nutzer noch liefert, steht als Platzhalter im Text: `\Note{PH: ...}` mit dem Namen der
   Zulieferung (S-Life, RIKOR, Workbench, CADMOULD-Bilder, Fotos, Nachher-Scans, Schliffbild).

## 3 Quellen

1. Zitiert wird nur, was als PDF in `00_literatur` liegt und gelesen wurde.
2. Jede aus der BA übernommene Aussage, Formel und Zahl wird an der Seite der Primärquelle geprüft.
3. Fehlende BA-Quellen lädt Claude aus dem Netz, wo sie frei sind; gesperrte meldet er dem Nutzer;
   sonst wird die Aussage auf eine vorhandene Quelle umgestellt oder gestrichen.
4. Zitierweise nach `FZG-Zitierrichtlinie.pdf`; Schlüssel wie im BA-Literaturverzeichnis
   ([Sto18], [Fru12]); Normen und Richtlinien als `@manual`, Webseiten als `@online`.
5. Titel, Autoren, Auflagen und Normbezeichnungen werden von der Titelseite abgeschrieben, nie aus
   dem Gedächtnis.

## 4 Formeln

Nach `Formeln_in_wissenschaftlichen_Arbeiten.pdf` (DIN 1338):

1. Jede Formel ist Teil des Satzes; Satzzeichen stehen nach der Formel.
2. Nummer je Kapitel; Verweis im Text als `\eqref{...}` ("Formel (3.1)").
3. Jedes Symbol steht einmal in der Nomenklatur (`Nomenklatur.tex`, erzeugt aus der Registry);
   keine Symboltabellen nach Formeln, die Umgebung `Gleichungsparameter` der Vorlage bleibt
   ungenutzt.
4. Symbol kursiv, jeder Index aufrecht (`d_\mathrm{b}`, `\sigma_\mathrm{F}`), Einheiten aufrecht
   und ohne Klammer, Dezimalkomma im deutschen Text.
5. Jeder Zahlenwert einer Größe (Geometrie, Last, Spannung, Winkel, Faktor, Zeit) steht im
   Mathemodus mit `{,}` als Dezimalkomma, die Einheit aufrecht nach einem schmalen Abstand:
   `$52$\,mm`, `$0{,}2034$`, `$21{,}463$°`, `$16$\,Nm`, `$1{,}25\,m_{\mathrm{n}}$`; das gilt auch in
   Tabellen und Bildunterschriften. In der Textschrift bleiben Anzahlen (36 Räder, 20 Schichten),
   Teilenummern, Daten, Jahreszahlen, Normnummern, Seitenzahlen und Werkstoffbezeichnungen
   (20MnCr5, PA46-GF30). Prüfung und Umstellung: `scripts/thesis_numbers.py [--fix]` (Nutzer,
   2026-10-17).

## 5 Bilder und Tabellen

1. "Bild" statt "Abbildung" (`\figurename` der Klasse), Quelle am Ende der Bildunterschrift in
   eckigen Klammern über `\cite`.
2. Hausstil: FZG-Richtlinie zuerst, TUM-Gestaltung wo die FZG nichts sagt; Linien 0,9 pt, Marker
   3 pt aus dem Hauszyklus; vergleichbare Diagramme teilen die Achsenskalierung; Werte in der
   Legende; deutsche Beschriftung mit Dezimalkomma.
3. Legenden in den Worten eines Mitarbeiters am Lehrstuhl (Körper, Schichtung, Kopfkante,
   Werkstoffstufe, Dehnrate), nie "Serie" oder "Referenz".
4. Stand der Technik ohne eigene Zeichnungen: Bilder aus Quellen "nach [..]", aus CADMOULD oder
   dem FVA-Bericht; Ausnahme die Stommel-Methodenbilder für PA46-GF30 "in Anlehnung an [Sto18]".
5. Bilder liegen als PDF (aus SVG) oder PNG 300 dpi in `10_report/bilder/<kapitel>/`, ausgewählt
   über `10_report/bilder/bilder.yaml` und kopiert von `scripts/build_thesis_figures.py`.
6. Überflüssig gewordene Bildversuche werden gelöscht, sobald überarbeitete Fassungen vorliegen.
7. Tabellen (Nutzer, 2026-10-26): Kopfzeile mit schwarzer Linie darunter, zwischen den Zeilen des
   Körpers eine hellgraue Linie (`\arrayrulecolor{black!30}` nach der Kopflinie, `\hline` nach jeder
   Zeile, `\arrayrulecolor{black}` vor `\end{tabular}`), damit die Zeilen auseinanderzuhalten sind.
   Erzeugte Tabellen bekommen sie aus `scripts/thesis_appendix_tables.py` (`RULE_COLOUR`). Das
   Formelverzeichnis bleibt ohne Linien. Im Anhang beginnt jeder Abschnitt auf einer neuen Seite.

## 6 Prüfliste je Abschnitt (vor der Übergabe)

1. Herkunft jeder Aussage benannt (Quelle und Seite, Ergebnisdatei oder Stichpunkt).
2. Jede Zahl gegen die Tabelle oder die Ergebnisdatei geprüft.
3. Jedes Symbol in der Nomenklatur; jede Abkürzung beim ersten Auftreten erklärt.
4. Suchlauf nach KI-typischer Sprache: Gedankenstriche, Doppelpunkt-Ketten, Dreier, Sätze über
   30 Wörter, gleiche Satzanfänge, Zusammenfassungssätze.
5. Verweise über `\figref`, `\tabref`, `\eqref`, `\secref`; jedes Label löst auf.
6. Platzhalter als `\Note{PH: ...}` sichtbar, keine stillen Lücken.
