# Gliederung der Semesterarbeit SA 16 (T0, Stand 2026-10-17)

"Berechnung und experimentelle Untersuchung der Zahnfußspannung kurzfaserverstärkter
Kunststoffzahnräder", Betreuerin Liang Wang, Themensteller Prof. Stahl, Ende 27.10.2026.
Vorabversion mit allen Kapiteln am 20.10.2026 (Stand der Ergebnisse 19.10.), danach nur kleine
Änderungen. Festgelegt am 2026-10-14 (Plan), Entscheidungen des Nutzers eingearbeitet.

Legende der Spalte Abh.: **jetzt** = schreibbar; **FR** = nach den Fußrundungsläufen (Vollserien);
**LV** = nach der Auswertung der Laufversuche (L1 bis L4); **PH** = Platzhalter bis zur Zulieferung
des Nutzers. Dateien: eine `.tex` je Kapitel in `Kapitel/` (`kap1_einleitung.tex` bis
`kap8_zusammenfassung.tex`, `anhang_a.tex` bis `anhang_h.tex`), Bilder in `bilder/<kapitel>/`.

## Kapitel 1 Einleitung (2 S., zuletzt schreiben)

Motivation, Lücke laut Aufgabenstellung, Ziel, Aufbau. Quellen VDI 2736 Blatt 1/2, Hasl,
Illenberger, FVA 856 I, Kassem 2022. Keine Bilder.

## Kapitel 2 Stand der Wissenschaft und Technik (≈ 16 S., aus BA-0486 Kapitel 2, neu geordnet)

Bilder nur aus Quellen (mit Verweis), aus CADMOULD oder aus dem FVA-Bericht; eigene Bilder nur die
Stommel-Methodenbilder für PA46-GF30.

| Abschnitt | Inhalt | Quellen (vorhanden) | BA liefert | Bilder | Abh. |
|---|---|---|---|---|---|
| 2.1 Thermoplaste als Zahnradwerkstoff, PA46-GF30 (2 S.) | Einordnung, Temperatur/Feuchte/Dehnrate, Kurzglasfasern, Stanyl TW200F6, Vergleichswerkstoffe POM/PEEK | VDI 2736 Blatt 1, Ehrenstein, Erhard, Erhard/Strickle, Stommel Kap. 2, CAMPUS-Datenblatt, Illenberger, MA-0296 4.2.1 | 2.1, 2.2.1 (Text) | Tabelle Kennwerte aus Datenblatt und Matscape-Karten; Bild aus Quelle, falls nötig | jetzt |
| 2.2 Spritzgießen und Faserorientierung (3 S.) | Spritzgießen von Zahnrädern, Orientierungstensor, Anisotropie-Index, Zonenmodell und CT-Befund FVA 856 I, Prozess-Struktur-Kopplung als Prinzip | FVA 856 I Kap. 6, VDI 2736 Blatt 1, Kassem 2022/2023, Kassem analytisch | nichts | CADMOULD-Bilder der Füllung und Orientierung (PH), FVA 856 I Bild 16/17/18 "nach [..]" | jetzt, PH |
| 2.3 Werkstoffverhalten und Materialmodelle (3 S.) | Zugversuch nach Richtung/Rate/Temperatur, isotrop linear, elastisch-plastisch, orthotrop, Hill; Herleitung W1 bis W4 | Stommel Kap. 2, Abaqus-Doku, FVA 856 I Tab. 4, METG-Kurven | 2.2.2 | `stommel_methode_V2/spannung_dehnung_*`, `orientierungszustaende_*`; Tabelle Tab. 4 | jetzt |
| 2.4 Zahnradschäden und Zahnfußtragfähigkeit (1,5 S.) | Schadensarten, 30°-Tangente, Versagensdefinitionen, Einflüsse | VDI 2736 Blatt 2, Hasl, Illenberger, MA-0296, Klocke/Brecher, Linke | 2.2.3 | Quellbilder mit Verweis | jetzt |
| 2.5 Berechnung der Zahnfußbeanspruchung (5 S.) | 2.5.1 VDI 2736 Blatt 2 mit Y-Faktoren nach ISO 6336-3 B; 2.5.2 RIKOR, FVA-Workbench, FEM, Fußrundungsvarianten (elliptisch Frühe/Kassem/Landi, Bézier Roth/Opferkuch/Dong, bionisch Patente, Kassem 2023); 2.5.3 Bemessung nach Stommel et al. (statisch, zyklisch, Überlastfälle, Isotropie-Vorschrift, Erweiterungsbasis) | VDI 2736 Blatt 2, ISO 6336-1/-3, Niemann/Winter, Linke, FVA 30 XI/XII, FVA 892 I, FVA 484 V, Frühe, Hasl, Stommel Kap. 6, Kassem, Landi, Dong, Roth/Opferkuch, Sanders, Patente, FVA 241 XII | 2.3.1 bis 2.3.3 (Formeln am gerenderten Buch prüfen, K_M nach Gl. 6.21, Druckfaktor, Tab. 2.5) | Quellbilder der Fußgeometrien "nach [..]"; eigene Methodenbilder `nomogramm_qs`, `haigh_qs_80C`, `woehler_synthetisch_qs` "in Anlehnung an [Sto18]" | jetzt |
| 2.6 Experimentelle Tragfähigkeitsermittlung und Statistik (2 S.) | Laufversuch, Wöhlerlinie ohne Dauerfestigkeit, Belegung, log-Normalverteilung, Perlschnur DIN 50100, Weibull, Durchläufer | DIN 50100, VDI 2736 Blatt 4, Hasl, Illenberger, MA-0296 2.2/2.4/2.5 | nichts | Prinzipbild aus VDI 2736 Blatt 4 oder MA-0296 "nach [..]" | jetzt |
| 2.7 Problemstellung und Zielsetzung (1 S.) | Lücken und Ziele | aus 2.1 bis 2.6 | 2.4 | keines | jetzt |

## Kapitel 3 Untersuchungsgegenstand und Methoden (≈ 16 S.)

| Abschnitt | Inhalt | Quellen | Bilder vorhanden | neu | Abh. |
|---|---|---|---|---|---|
| 3.0 Vorgehen (½ S.) | Ablauf der Arbeit als Bild (eigene Zeichnung, hier erlaubt) | – | – | Vorgehensbild | jetzt |
| 3.1 Prüfverzahnung kst-E und Prüfräder (2 S.) | Geometrietabelle aus STplus-Fall und Zeichnungen (Rad 2022-03-16, Ritzel 2022-06-23 und 2025-04-02; die Rig-Ritzel zeigen in GINA die Kopfrücknahme und Zahnweite der Zeichnung 2022), Ritzel 20MnCr5, Rad PA46-GF30 auf Einleger mit Taschen, Teilegruppen | Zeichnungen (Anhang), DIN ISO 21771, MA-0296 4.2.2, `parts.yaml`, `body_sections.yaml` | `bilder_V2/preview/position_*` | Stirnschnitt mit Bezeichnungen, Zahnkontur mit Fußrundung (T5-Skript), Radkörperschnitt | jetzt |
| 3.2 Prüfstand und Versuchsdurchführung (2 S.) | Kleinverspannungsprüfstand a = 52 mm nach SA-1272 (Aufbau, Verspannungskreis, Messwelle, Schmierung), Versuchsplanung (8/12/16 Nm am Rad, 3058 1/min, Belegung, Einlauf, Nachspannen), Abbruchkriterium, Vergleichsläufe POM/PEEK 2026 (Versuche der Betreuerin) und 2023 (Reitschuster/Fiederling, MA-0296) | SA-1272 Schurer, MA-0296 4.1.1, VDI 2736 Blatt 4, Prüfstandsblatt | keine | Bilder aus SA-1272 mit Verweis; Prüfstandsfoto (PH); Tabelle Versuchsplan (L1) | PH, LV |
| 3.3 Dokumentation der Prüfräder (1,5 S.) | GINA, Konturscan, Rauheit, Mikroskop, Messumfang | DIN ISO 1328-1, DIN 21773, ISO 21920, ADR-117 | `gina/*`, `konturscan/*`, `rauheit/*`, `inventory.md` | Übersichtstabelle (M6) | jetzt |
| 3.4 Analytische Berechnung (1,5 S.) | VDI 2736 Blatt 2, FVA-Workbench, RIKOR, S-Life Plastics: Programm, Version, Modell, Eingaben | VDI 2736 Blatt 2, ISO 6336-3, FVA 30, FVA 892, Stommel | keine | Eingabetabellen (PH für Werte) | PH |
| 3.5 Geometrie- und Werkzeugkette (1,5 S.) | Zahnkontur nach DIN ISO 21771, Prüfmaße DIN 21773, Abgleich gegen STplus mit dem Stapelskript, Normunterschiede als Verweis auf den Anhang, Fußrundungsvarianten als Konturersatz; KI-gestützte Programmierung und pydantic-Kette (Schreibregel 2.3) | DIN ISO 21771, DIN 867, DIN 3972, DIN 21773, Linke, FVA 604 I, STplus-Handbuch | NB 01 bis 04 | Konturvergleich gearcore/STplus, Konturen der Varianten | jetzt |
| 3.6 Simulationskette und FE-Modell (4 S.) | Kette METG → Matscape → CADMOULD → CONVERSE → Decks → Abaqus → Auswertung; Modell (Sektor, Schichten, Fesselung, Körper, starre Ritzelfläche mit Kante 0,1 mm als Modellwahl, Kontakt, eine Analyse je Stellung, W1 bis W4, Raten); Begründung der Einzelstellungen nach Stommel (Kap. 8: Abwälzen als Ausblick) | Stommel 2.3.1.1, 7.7, 8.2.2, Bathe, Dahmen/Reusken, Abaqus-Doku, FVA 856 I, ADR-116/119 | `bilder_V2/frozen_mesh_*`, `preview/*`, `load_case` | Flussbild (T6), Tabellen Stufen × Raten × Körper, CADMOULD-Parameter | jetzt |
| 3.7 Auswertung der Beanspruchung (2,5 S., nur Methode) | Extraktion, Pfadkurven als Größtwerte über die Breite, Normpunkte; Stommel wie veröffentlicht (Lastgeschichte, Route, Überlastfall, K-Quelle, Klasse); eigene anisotrope Erweiterung (Faserrahmen, σ_Hill, Klassenfrage); Validierung (Buchbeispiele, S-Life) | Stommel Kap. 6, Abaqus Hill, ADR-118 | `stommel_methode_V2/*` | Tabelle Einstellungen | jetzt |
| 3.8 Auswertung der Laufversuche (1,5 S., nur Methode) | Importer, Stufenschlüssel, Versagen, Regressionen, Streuung, 50 → 10 %, Weibull, Netze, Durchläufer, Abszissen, Temperaturmatrix | DIN 50100, VDI 2736 Blatt 4, Hasl, Illenberger, MA-0296 | keine | keines (Bilder in 6) | LV |

## Kapitel 4 Voruntersuchungen (≈ 8 S.)

| Abschnitt | Inhalt | Bilder vorhanden | neu | Abh. |
|---|---|---|---|---|
| 4.1 Netzkonvergenz und Elementtyp (2 S.) | Leiter, Extrapolation, C3D8/C3D8R/C3D8I, NLGEOM-Befund, Regel je Stufe, Schichten | `bilder_V2/convergence/*` | Tabelle | jetzt |
| 4.2 Eingriffsauflösung und Kopfkante (1,5 S.) | 60-je-Teilung-Studie, Rand, Abbrüche an der scharfen Kante, Rundung 0,1 mm mit Sensitivität, Nachtlauf 13.10.: Netz- gegen Rundungseffekt (36/54 Reihen × 0,02/0,05/0,1 mm) | `bilder_V2/study_*`, `series_*/analyse/vergleich_referenz_*`, `konturscan/pinion/kopfkante_95912_*`, `pilot_*_hoehe*` | Vergleichsbild | jetzt |
| 4.3 Werkstoffstufen, Dehnraten und Radkörper (2 S.) | W1 → W2, W3/W4, DY1/DY2, Taschen- gegen Ringkörper, Schichteffekt | `vergleich_koerper_AtoE/*`, `pilot_*_dy1dy2_*/analyse/*` | Auswahl | jetzt |
| 4.4 Prüfräder vor dem Versuch (2 S.) | GINA-Befunde, Zahnweite, Kopfrundung 0,21 mm, Kopfrücknahme, Kante, Rauheit | `gina/*`, `konturscan/*`, `rauheit/*` | Tabelle Kernräder | jetzt |
| 4.5 Temperaturverhalten am Prüfstand (½ S.) | Matrix 3 × 2 (kst-E_63), Öl- und Kastentemperatur, Bezug 80 °C | keine | Balkenbild (L4) | LV |

Die Faserorientierung gegen das CT ist 5.1 (Ergebnis der Simulationskette, ADR-119); eine
Verschiebung nach Kapitel 4 bleibt ohne Textänderung möglich.

## Kapitel 5 Ergebnisse der Berechnung (≈ 12 S.)

| Abschnitt | Inhalt | Bilder vorhanden | neu | Abh. |
|---|---|---|---|---|
| 5.1 Faserorientierung aus der Spritzgießsimulation (2,5 S.) | Zonen gegen CT, Umfang, CT-Zonen-Datei, 2 × 2-Schema Werkstoffquelle × Richtungsquelle | `faserorientierung/*`, `faserorientierung_vollrad/*`, `orientierung_ct/auswertung_T3/*`, `vergleich_orientierung_AtoE/*`, `vergleich_orientierung_tab4_AtoE/*` | Schliffbild PH | jetzt, PH |
| 5.2 Beanspruchung über dem Wälzweg (3 S.) | Pfadkurven, Lage der Maxima, Kantenkontakt, Nebenzahn, Stufenvergleich | `series_*/analyse/vergleich_stufen_*`, `path_W*` | Ergebnistabelle; σ1-Karte über Fuß und Breite (prüfen) | jetzt |
| 5.3 Bemessung nach Stommel et al. (3 S.) | 5.3.1 Methode wie veröffentlicht auf W2 (Hauptlinie) und W1; 5.3.2 anisotrope Erweiterung: W3/W4 unter Hill, W1 unter Hill als Methodenvergleich, Klassenfrage, Lage des kritischen Knotens; 5.3.3 Globalmaxima außerhalb des Fußes (FE-22), Überlastfälle F1 bis F4, S-Life-Vergleich (E4, 24 Berichte liegen vor) | `stommel_W2_QS/*`, `stommel_hill_*`, `stommel/vergleich_slife.md` | Karten 16 Nm und Hill, Tabellen, F1 bis F4 (C6) | jetzt |
| 5.4 Einfluss der Zahnfußgeometrie (2,5 S.) | Konturen elliptisch/Bézier/bionisch gegen Trochoide, W1 bis W4 × QS/DY1/DY2 an A bis E relativ zur Standardfußrundung (fünf von sechs Varianten liegen vor, Stand 2026-10-17), ebenes Modell gegen 3D, Stommel am kritischen Knoten je Variante (Vollserien) | `vergleich_fussrundung_AtoE/*`, `fussrundung_sweep/*` | Konturbild, Tabelle | jetzt (A bis E), FR (Stommel) |
| 5.5 Vergleich der Berechnungsverfahren (1,5 S.) | σ_F je Drehmoment: VDI 2736, RIKOR, FVA-Workbench, FE, Stommel | keine | L8-Bild, L7-Tabelle (C7), PH für RIKOR/Workbench | PH |

## Kapitel 6 Ergebnisse der Laufversuche (≈ 6 S.)

| Abschnitt | Inhalt | neu | Abh. |
|---|---|---|---|
| 6.1 Versuchsprogramm und Übersicht (1 S.) | Tabelle je Lauf, Stichtag | L1 | LV |
| 6.2 Schadensbilder (1,5 S.) | Fotos und Mikroskopbilder des Nutzers, Vergleich MA-0296, Verschleiß aus Nachher-Scans (M5, PH) | Bilder vom Nutzer | PH |
| 6.3 Wöhlerlinien (2,5 S.) | drei Abszissen, 50 %- und 10 %-Linien, Streuung, Durchläufer, Netze | L2, L3 | LV |
| 6.4 Vergleichswerkstoffe (1 S.) | POM/PEEK 2026 (Betreuerin) und 2023 (MA-0296) neben PA46-GF30 | L3, L5 | LV |

## Kapitel 7 Diskussion (≈ 5 S.)

7.1 Genauigkeit der Verfahren (L7-Tabelle, synthetische Linie gegen Versuch, lokale Wöhlerlinie,
Versagensdefinitionen); 7.2 Anwendbarkeit und Modellgrenzen (Isotropie-Vorschrift, Klassenfrage,
Orientierung eines Zahns gegen Rad, Mapping gegen CT, starre Ritzelfläche, Kante, Sektor, keine
Reibung); 7.3 Fertigungseinfluss und Fußgeometrie.

## Kapitel 8 Zusammenfassung und Ausblick (2 S.)

Ausblick: Abwälzen in einer Simulation (Vorbelastung und Reibung in einem Lauf; in der Zeit zu
komplex neben Materialmodellen und der Kopfkanten-Iteration, deshalb nach dem Buch jede Stellung
einzeln), M7-Varianten V1 bis V4, Schliffbild, Pulsator, zweite Drehzahl, Werkzeugkette und
pydantic-Datenkontrakte für Messprotokolle und Rohdaten des Labors als Brücke zur Masterarbeit.

## Anhang

A Zeichnungen, B Normunterschiede und Geometrietabellen, C FE-Einstellungen, D Matscape-Karten und
Stommel-Klassentabellen, E Konvergenztabellen, F Nachtlauf- und Pilottabellen, G GINA- und
Rauheitsprotokolle, H Prüfstandsprotokoll.

Summe Haupttext etwa 65 Seiten. Reihenfolge der Entwürfe: 3, 4, 2, 5, 6, 7, 8, 1.

## Zulieferungen des Nutzers (Platzhalter `\Note{PH: ...}` im Text)

1. CONVERSE-Zuordnungen: erledigt (18 Dateien, 2026-10-14).
2. S-Life-Ausgaben: erledigt (24 Berichte, E4 ausgewertet).
3. CADMOULD-Bilder (Füllung, Orientierung) für 2.2; Fotos und Mikroskopbilder der Schäden für 6.2;
   Prüfstandsfoto für 3.2; Nachher-Scans (M5); Schliffbild, falls vorhanden.
4. RIKOR-Werte der Betreuerin und FVA-Workbench-Werte (L6a) für 5.5.
5. Stichtag der Laufversuche und PEEK-Typ der Läufe 2026 und 2023; Ablageort der Laufversuchsdaten (L1).
6. Klassenwahl unter Hill (verstärkt gegen duktil) für den Text.
7. Gesperrte Quellen-PDFs, die Claude meldet.
