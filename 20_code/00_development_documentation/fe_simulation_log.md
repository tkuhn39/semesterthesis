# Simulationstagebuch (generiert)

Stand 2026-10-09 13:42; Quelle `C:/GitHub-tkuhn39/semesterthesis/80_output/fe/kst_e`; Notizen `fe_simulation_notes.yaml`; erzeugt von `build_fe_decks.py log`. Ein Abschnitt je Ordner in der Reihenfolge der letzten Bearbeitung, mit Zweck und Ergebnis aus den Notizen, Netz und Einstellungen aus `manifest.json`, dann zwei Tabellen: **Läufe** je Stellungsdatei mit Status aus `.sta` (complete, not completed mit dem letzten geschriebenen Inkrement, open = ohne Schlusszeile: läuft oder abgestürzt), Inkrementen je Schritt, Rechenzeit (Wanduhr aus `run_log.txt`, sonst aus der Zeitbilanz der `.dat`), Warnungen negativer Eigenwerte aus `.msg` und Endzeit; **Kennwerte** des letzten gedruckten Lastschritts aus `<job>_fields.json` (RM3-Abweichung gegen z_2/z_1·T_1, Drehung des Ritzels am Grundkreis in µm, größter Kontaktdruck mit Zahnhälfte und Ort, größte Fußspannung σ1 mit Fußrundung, Ort und Tangentenwinkel zur Zahnmittellinie, kleinste σ3 mit Fußrundung, größte Kopfverschiebung mit Zahn), für Läufe ohne Felddatei aus der `.dat` (Moment, Drehung, Druck ohne Ort). Löser: linear oder NLGEOM, N2S = Knoten-zu-Fläche mit SMOOTH, S2S = Fläche-zu-Fläche, DIRECT/PENALTY = Zwangsbedingung, LS = Line Search.

Läufe: 203 vollständig, 26 abgebrochen, 7 offen, 273 Dateien nicht gerechnet; 54 Ordner.

## 2026-10-05 16:43 `pinion_surface_7teeth_80layers`

**Zweck:** Starre Ritzelfläche, 7 Zähne, 80 Schichten (Netzdatei, kein Lauf). **Ergebnis:** Netzdatei.

Nicht gerechnet: 1 Dateien (`pinion_surface`).

## 2026-10-05 17:23 `wheel_5teeth_12rings_80layers`

**Zweck:** Erstes Radnetz aus der Referenztopologie, 5 Zähne, 12 Ringe, 80 Schichten (Netzdatei, kein Lauf). **Ergebnis:** Netzdatei.

Nicht gerechnet: 1 Dateien (`wheel_mesh`).

## 2026-10-06 10:15 `convergence`

**Zweck:** Konvergenzstudie in der Learning Edition: Einzahn-Sektor eben (CPE4, CPE4R, CPE4I) gegen den eigenen Solver. **Ergebnis:** Übereinstimmung mit dem eigenen Solver 7e-5 (CPE4) und 1e-5 (CPE4I). (gerechnet: Learning Edition; Befunde FE-09, FE-10)

**Läufe**

| Datei      | Stellung | Stufe | Rate | Variante | Löser  | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|------------|----------|-------|------|----------|--------|----------|-----------------------|--------|---------|------------------|
| `le_cpe4`  |          |       |      |          | linear | complete | 1                     | 1      | 0       | 2026-10-06 10:15 |
| `le_cpe4i` |          |       |      |          | linear | complete | 1                     | 1      | 0       | 2026-10-06 10:15 |
| `le_cpe4r` |          |       |      |          | linear | complete | 1                     | 1      | 0       | 2026-10-06 10:15 |

## 2026-10-06 11:03 `full_licence`

**Zweck:** Konvergenzdecks für die Vollversion: fünf Stufen, drei Elementtypen, Volldecks mit 20, 40, 80 Schichten (Vorlage, nicht gerechnet). **Ergebnis:** Vorlage; gerechnet in full_licence_result.

Nicht gerechnet: 21 Dateien (`plane_base_cpe4`, `plane_base_cpe4i`, `plane_base_cpe4r`, `plane_t2_cpe4`, `plane_t2_cpe4i`, `plane_t2_cpe4r` …).

## 2026-10-06 16:11 `full_licence_result`

**Zweck:** Dieselben Konvergenzdecks, gerechnet auf der Vollversion 2026-10-06. **Ergebnis:** Richardson über die Abaqus-Reihe bestätigt die eigene Studie; 20, 40 und 80 Schichten innerhalb 0,05 % für Kopfverschiebung und Fußspannung. (gerechnet: Vollversion; Befunde FE-09, FE-10)

**Läufe**

| Datei                  | Stellung | Stufe | Rate | Variante | Löser  | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|------------------------|----------|-------|------|----------|--------|----------|-----------------------|--------|---------|------------------|
| `plane_base_cpe4`      |          |       |      |          | linear | complete | 1                     | 1      | 0       | 2026-10-06 16:07 |
| `plane_base_cpe4i`     |          |       |      |          | linear | complete | 1                     | 0      | 0       | 2026-10-06 16:07 |
| `plane_base_cpe4r`     |          |       |      |          | linear | complete | 1                     | 0      | 0       | 2026-10-06 16:07 |
| `plane_t2_cpe4`        |          |       |      |          | linear | complete | 1                     | 1      | 0       | 2026-10-06 16:07 |
| `plane_t2_cpe4i`       |          |       |      |          | linear | complete | 1                     | 0      | 0       | 2026-10-06 16:07 |
| `plane_t2_cpe4r`       |          |       |      |          | linear | complete | 1                     | 0      | 0       | 2026-10-06 16:08 |
| `plane_t3_cpe4`        |          |       |      |          | linear | complete | 1                     | 0      | 0       | 2026-10-06 16:08 |
| `plane_t3_cpe4i`       |          |       |      |          | linear | complete | 1                     | 0      | 0       | 2026-10-06 16:08 |
| `plane_t3_cpe4r`       |          |       |      |          | linear | complete | 1                     | 0      | 0       | 2026-10-06 16:08 |
| `plane_t4_cpe4`        |          |       |      |          | linear | complete | 1                     | 1      | 0       | 2026-10-06 16:08 |
| `plane_t4_cpe4i`       |          |       |      |          | linear | complete | 1                     | 1      | 0       | 2026-10-06 16:08 |
| `plane_t4_cpe4r`       |          |       |      |          | linear | complete | 1                     | 0      | 0       | 2026-10-06 16:08 |
| `plane_u2_cpe4`        |          |       |      |          | linear | complete | 1                     | 1      | 0       | 2026-10-06 16:09 |
| `plane_u2_cpe4i`       |          |       |      |          | linear | complete | 1                     | 0      | 0       | 2026-10-06 16:09 |
| `plane_u2_cpe4r`       |          |       |      |          | linear | complete | 1                     | 1      | 0       | 2026-10-06 16:09 |
| `solid_20layers_c3d8i` |          |       |      |          | linear | complete | 1                     | 1      | 0       | 2026-10-06 16:09 |
| `solid_20layers_c3d8r` |          |       |      |          | linear | complete | 1                     | 2      | 0       | 2026-10-06 16:09 |
| `solid_40layers_c3d8i` |          |       |      |          | linear | complete | 1                     | 4      | 0       | 2026-10-06 16:10 |
| `solid_40layers_c3d8r` |          |       |      |          | linear | complete | 1                     | 3      | 0       | 2026-10-06 16:10 |
| `solid_80layers_c3d8i` |          |       |      |          | linear | complete | 1                     | 7      | 0       | 2026-10-06 16:11 |
| `solid_80layers_c3d8r` |          |       |      |          | linear | complete | 1                     | 6      | 0       | 2026-10-06 16:11 |

## 2026-10-06 17:41 `pilot_20layers_error`

**Zweck:** Pilot 1 der Stellungsdatei: 20 Schichten, NLGEOM=YES, Fläche-zu-Fläche, Penalty. **Ergebnis:** SEAT und 8 Nm konvergiert (197 s), 12 Nm bricht im ersten Inkrement mit negativen Eigenwerten ab. (gerechnet: Vollversion; Befunde FE-14)

Netz: 81690 Knoten, 71640 Elemente (C3D8I), 20 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser       | Status                       | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-------------|------------------------------|-----------------------|--------|---------|------------------|
| `pos_001` | C        | W1    | QS   |          | NLGEOM, S2S | not completed (step 3 inc 1) | 6, 6, 5               |        | 37      | 2026-10-06 17:41 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt  | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001` | LOAD_8NM | -0.30 %  | 55.6       | 57.1           | T3 RIGHT, r 26.10, z -6.8 | 56.5       | T2_T3, r 24.83, z -3.8, Tangente 45° | -68.4      | T3_T4      | 67.0    | T3   |

## 2026-10-06 18:40 `pilot_20layers_error_2`

**Zweck:** Pilot 2: wie Pilot 1, aber geometrisch linear. **Ergebnis:** bis 12 Nm durch, 16 Nm bricht in Inkrement 2 durch eine Kontaktoszillation einer Flankenknotenspalte ab. (gerechnet: Vollversion; Befunde FE-14, FE-15, FE-16)

Netz: 81690 Knoten, 71640 Elemente (C3D8I), 20 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser       | Status                       | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-------------|------------------------------|-----------------------|--------|---------|------------------|
| `pos_001` | C        | W1    | QS   |          | linear, S2S | not completed (step 4 inc 2) | 6, 6, 6, 7            | 347    | 0       | 2026-10-06 18:40 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001` | LOAD_12NM | -0.49 %  | 70.1       | 67.8           | T4 RIGHT, r 25.90, z -4.5 | 71.4       | T2_T3, r 24.83, z +0.0, Tangente 45° | -83.6      | T3_T4      | 84.0    | T3   |

## 2026-10-06 19:01 `pilot_20layers_variants`

**Zweck:** Sechs Löser- und Kontaktvarianten derselben Stellung C (Vorlage). **Ergebnis:** Vorlage; gerechnet in pilot_20layers_variants_gerechnet.

Netz: 81690 Knoten, 71640 Elemente (C3D8I), 20 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 6 Stellungsdateien

Nicht gerechnet: 6 Dateien (`pos_001_ls`, `pos_001_direct`, `pos_001_n2s`, `pos_001_nlgeom_ls`, `pos_001_nlgeom_direct`, `pos_001_nlgeom_n2s`).

## 2026-10-06 19:44 `pilot_20layers_variants_gerechnet`

**Zweck:** Sechs Löser- und Kontaktvarianten derselben Stellung C auf der Vollversion (2026-10-06). **Ergebnis:** nur Knoten-zu-Fläche mit NLGEOM=NO läuft alle Schritte durch; jede NLGEOM=YES-Variante zeigt negative Eigenwerte ab dem ersten Lastinkrement. (gerechnet: Vollversion; Befunde FE-14, FE-15, FE-16)

Netz: 81690 Knoten, 71640 Elemente (C3D8I), 20 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 6 Stellungsdateien

**Läufe**

| Datei                   | Stellung | Stufe | Rate | Variante      | Löser               | Status                       | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-------------------------|----------|-------|------|---------------|---------------------|------------------------------|-----------------------|--------|---------|------------------|
| `pos_001_ls`            | C        | W1    | QS   | ls            | linear, S2S, LS     | not completed (step 4 inc 2) | 6, 6, 6, 7            | 393    | 0       | 2026-10-06 19:24 |
| `pos_001_direct`        | C        | W1    | QS   | direct        | linear, S2S, DIRECT | not completed (step 3 inc 5) | 6, 6, 10              | 290    | 0       | 2026-10-06 19:17 |
| `pos_001_n2s`           | C        | W1    | QS   | n2s           | linear, N2S 0.2     | complete                     | 6, 6, 6, 6            | 187    | 0       | 2026-10-06 19:27 |
| `pos_001_nlgeom_ls`     | C        | W1    | QS   | nlgeom_ls     | NLGEOM, S2S, LS     | not completed (step 3 inc 1) | 6, 6, 5               | 251    | 37      | 2026-10-06 19:36 |
| `pos_001_nlgeom_direct` | C        | W1    | QS   | nlgeom_direct | NLGEOM, S2S, DIRECT | not completed (step 3 inc 1) | 6, 6, 5               | 319    | 67      | 2026-10-06 19:32 |
| `pos_001_nlgeom_n2s`    | C        | W1    | QS   | nlgeom_n2s    | NLGEOM, N2S 0.2     | not completed (step 3 inc 7) | 6, 6, 14              | 440    | 105     | 2026-10-06 19:44 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei                   | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-------------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001_ls`            | LOAD_12NM | -0.49 %  | 70.1       | 67.8           | T4 RIGHT, r 25.90, z -4.5 | 71.4       | T2_T3, r 24.83, z +0.0, Tangente 45° | -83.6      | T3_T4      | 84.0    | T3   |
| `pos_001_direct`        | LOAD_8NM  | -0.43 %  | 55.1       | 58.2           | T3 RIGHT, r 26.10, z -6.8 | 56.7       | T2_T3, r 24.83, z -3.8, Tangente 45° | -67.1      | T3_T4      | 66.4    | T3   |
| `pos_001_n2s`           | LOAD_16NM | -1.26 %  | 83.1       | 74.9           | T3 RIGHT, r 26.10, z +0.0 | 83.4       | T2_T3, r 24.83, z +0.0, Tangente 45° | -99.2      | T3_T4      | 98.9    | T3   |
| `pos_001_nlgeom_ls`     | LOAD_8NM  | -0.30 %  | 55.6       | 57.1           | T3 RIGHT, r 26.10, z -6.8 | 56.5       | T2_T3, r 24.83, z -3.8, Tangente 45° | -68.4      | T3_T4      | 67.0    | T3   |
| `pos_001_nlgeom_direct` | LOAD_8NM  | -0.31 %  | 55.4       | 58.1           | T3 RIGHT, r 26.10, z -6.8 | 56.5       | T2_T3, r 24.83, z -3.8, Tangente 45° | -68.5      | T3_T4      | 67.0    | T3   |
| `pos_001_nlgeom_n2s`    | LOAD_8NM  | -1.05 %  | 55.8       | 58.9           | T3 RIGHT, r 26.10, z -6.8 | 56.1       | T2_T3, r 24.83, z -3.8, Tangente 45° | -69.3      | T3_T4      | 66.9    | T3   |

## 2026-10-07 07:29 `le_tests/element_nlgeom/c3d8i`

**Zweck:** Elementtest: C3D8I mit NLGEOM=YES und NO. **Ergebnis:** NLGEOM=YES: 29 Warnungen negativer Eigenwerte ab 8 Nm Inkrement 1. (gerechnet: Learning Edition; Befunde FE-14)

Netz: 414 Knoten, 220 Elemente (C3D8I), 2 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 2 Stellungsdateien

**Läufe**

| Datei                | Stellung | Stufe | Rate | Variante   | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|----------------------|----------|-------|------|------------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_001_n2s`        | C        | W1    | QS   | n2s        | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 1      | 0       | 2026-10-07 07:29 |
| `pos_001_nlgeom_n2s` | C        | W1    | QS   | nlgeom_n2s | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 0      | 30      | 2026-10-07 07:29 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei                | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|----------------------|-----------|----------|------------|----------------|---------------------------|------------|---------------------------|------------|------------|---------|------|
| `pos_001_n2s`        | LOAD_16NM | -1.32 %  | 94.9       | 78.3           | T1 RIGHT, r 26.00, z -7.5 |            |                           |            |            | 113.9   | T1   |
| `pos_001_nlgeom_n2s` | LOAD_16NM | -1.23 %  | 96.2       | 80.1           | T1 RIGHT, r 26.00, z -7.5 |            |                           |            |            | 116.3   | T1   |

## 2026-10-07 07:29 `le_tests/element_nlgeom/c3d8`

**Zweck:** Elementtest: C3D8 mit NLGEOM=YES und NO. **Ergebnis:** keine Warnung, beide durch. (gerechnet: Learning Edition; Befunde FE-14)

Netz: 414 Knoten, 220 Elemente (C3D8), 2 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 2 Stellungsdateien

**Läufe**

| Datei                | Stellung | Stufe | Rate | Variante   | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|----------------------|----------|-------|------|------------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_001_n2s`        | C        | W1    | QS   | n2s        | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 0      | 0       | 2026-10-07 07:29 |
| `pos_001_nlgeom_n2s` | C        | W1    | QS   | nlgeom_n2s | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 1      | 0       | 2026-10-07 07:29 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei                | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|----------------------|-----------|----------|------------|----------------|---------------------------|------------|---------------------------|------------|------------|---------|------|
| `pos_001_n2s`        | LOAD_16NM | -1.36 %  | 95.0       | 76.0           | T1 RIGHT, r 26.00, z -7.5 |            |                           |            |            | 115.1   | T1   |
| `pos_001_nlgeom_n2s` | LOAD_16NM | -1.25 %  | 96.1       | 76.4           | T1 RIGHT, r 26.00, z -7.5 |            |                           |            |            | 117.6   | T1   |

## 2026-10-07 07:30 `le_tests/element_nlgeom/c3d8r`

**Zweck:** Elementtest: C3D8R mit NLGEOM=YES und NO. **Ergebnis:** keine Warnung, beide durch. (gerechnet: Learning Edition; Befunde FE-14)

Netz: 414 Knoten, 220 Elemente (C3D8R), 2 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 2 Stellungsdateien

**Läufe**

| Datei                | Stellung | Stufe | Rate | Variante   | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|----------------------|----------|-------|------|------------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_001_n2s`        | C        | W1    | QS   | n2s        | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 0      | 0       | 2026-10-07 07:29 |
| `pos_001_nlgeom_n2s` | C        | W1    | QS   | nlgeom_n2s | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 0      | 0       | 2026-10-07 07:30 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei                | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|----------------------|-----------|----------|------------|----------------|---------------------------|------------|---------------------------|------------|------------|---------|------|
| `pos_001_n2s`        | LOAD_16NM | -1.57 %  | 99.1       | 68.8           | T1 RIGHT, r 26.00, z +0.0 |            |                           |            |            | 132.7   | T1   |
| `pos_001_nlgeom_n2s` | LOAD_16NM | -1.45 %  | 100.6      | 68.8           | T1 RIGHT, r 26.00, z -7.5 |            |                           |            |            | 138.7   | T1   |

## 2026-10-07 07:34 `pilot_20layers_c3d8_variants`

**Zweck:** C3D8 statt C3D8I, linear und NLGEOM=YES (Vorlage). **Ergebnis:** Vorlage; gerechnet in pilot_20layers_c3d8_variants_gerechnet.

Netz: 81690 Knoten, 71640 Elemente (C3D8), 20 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 2 Stellungsdateien

Nicht gerechnet: 2 Dateien (`pos_001_n2s`, `pos_001_nlgeom_n2s`).

## 2026-10-07 07:59 `pilot_20layers_c3d8_variants_gerechnet`

**Zweck:** Bestätigung des Elementtests auf dem feinen Netz: C3D8 linear und NLGEOM=YES. **Ergebnis:** beide Dateien alle Schritte ohne negativen Eigenwert; NLGEOM ≤ 0,7 %, C3D8 gegen C3D8I < 1 %. (gerechnet: Vollversion; Befunde FE-10, FE-14)

Netz: 81690 Knoten, 71640 Elemente (C3D8), 20 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 2 Stellungsdateien

**Läufe**

| Datei                | Stellung | Stufe | Rate | Variante   | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|----------------------|----------|-------|------|------------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_001_n2s`        | C        | W1    | QS   | n2s        | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 157    | 0       | 2026-10-07 07:57 |
| `pos_001_nlgeom_n2s` | C        | W1    | QS   | nlgeom_n2s | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 174    | 0       | 2026-10-07 07:59 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei                | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|----------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001_n2s`        | LOAD_16NM | -1.28 %  | 83.2       | 74.9           | T3 RIGHT, r 26.10, z +0.0 | 75.8       | T2_T3, r 24.83, z +0.0, Tangente 45° | -90.4      | T3_T4      | 99.0    | T3   |
| `pos_001_nlgeom_n2s` | LOAD_16NM | -1.16 %  | 83.6       | 74.4           | T3 RIGHT, r 26.10, z +0.0 | 75.6       | T2_T3, r 24.83, z +0.0, Tangente 45° | -92.4      | T3_T4      | 100.1   | T3   |

## 2026-10-07 08:08 `pilot_20layers`

**Zweck:** Pilot mit der Regel je Werkstoffstufe (W1 linear C3D8I, Knoten-zu-Fläche), 20 Schichten, Bohrung 18,10 (Vorlage). **Ergebnis:** Vorlage; gerechnet in pilot_20layers_gerechnet.

Netz: 81690 Knoten, 71640 Elemente (C3D8I), 20 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien

Nicht gerechnet: 1 Dateien (`pos_001`).

## 2026-10-07 08:08 `pilot_40layers`

**Zweck:** Pilot 40 Schichten (Vorlage). **Ergebnis:** Vorlage; gerechnet in pilot_40layers_gerechnet.

Netz: 159490 Knoten, 143280 Elemente (C3D8I), 40 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien

Nicht gerechnet: 1 Dateien (`pos_001`).

## 2026-10-07 08:09 `pilot_80layers`

**Zweck:** Pilot 80 Schichten (Vorlage). **Ergebnis:** Vorlage; gerechnet in pilot_80layers_gerechnet.

Netz: 315090 Knoten, 286560 Elemente (C3D8I), 80 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien

Nicht gerechnet: 1 Dateien (`pos_001`).

## 2026-10-07 08:09 `pilot_20layers_deepbore`

**Zweck:** Pilot mit tiefer Bohrung 12,38 mm (Vorlage). **Ergebnis:** Vorlage; gerechnet in pilot_20layers_deepbore_gerechnet.

Netz: 84630 Knoten, 74360 Elemente (C3D8I), 20 Schichten, Bohrung r 12.381 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien

Nicht gerechnet: 1 Dateien (`pos_001`).

## 2026-10-07 08:20 `pilot_20layers_smooth_variants`

**Zweck:** Knoten-zu-Fläche mit SMOOTH 0,2 und SMOOTH 0 (Vorlage). **Ergebnis:** Vorlage; gerechnet in pilot_20layers_smooth_variants_gerechnet.

Netz: 81690 Knoten, 71640 Elemente (C3D8I), 20 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 2 Stellungsdateien

Nicht gerechnet: 2 Dateien (`pos_001_n2s`, `pos_001_n2s_smooth0`).

## 2026-10-07 08:29 `pilot_20layers_smooth_variants_gerechnet`

**Zweck:** Ursache des Fläche-zu-Fläche-Abbruchs: Facettenknicke der starren Fläche oder die Formulierung. **Ergebnis:** SMOOTH 0 bricht in Abaqus 2025 vor dem ersten Inkrement ab (Normalenvektor null, Segmentation Fault); SMOOTH 0,2 läuft. (gerechnet: Vollversion; Befunde FE-14)

Netz: 81690 Knoten, 71640 Elemente (C3D8I), 20 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 2 Stellungsdateien

**Läufe**

| Datei                 | Stellung | Stufe | Rate | Variante    | Löser           | Status                  | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------------------|----------|-------|------|-------------|-----------------|-------------------------|-----------------------|--------|---------|------------------|
| `pos_001_n2s`         | C        | W1    | QS   | n2s         | linear, N2S 0.2 | complete                | 6, 6, 6, 6            | 185    | 0       | 2026-10-07 08:29 |
| `pos_001_n2s_smooth0` | C        | W1    | QS   | n2s_smooth0 | linear, N2S 0   | open (odb without .sta) |                       | 17     | 0       | 2026-10-07 08:29 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei         | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|---------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001_n2s` | LOAD_16NM | -1.26 %  | 83.1       | 74.9           | T3 RIGHT, r 26.10, z +0.0 | 83.4       | T2_T3, r 24.83, z +0.0, Tangente 45° | -99.2      | T3_T4      | 98.9    | T3   |

## 2026-10-07 08:35 `pilot_20layers_deepbore_gerechnet`

**Zweck:** Pilot mit tiefer Bohrung 12,38 mm: Steifigkeitsfrage der Bohrungstiefe. **Ergebnis:** 177 s, alle Schritte; Momente gleich, Ritzeldrehung +2,0 %, CPRESS innerhalb 0,2 %. (gerechnet: Vollversion; Befunde FE-08)

Netz: 84630 Knoten, 74360 Elemente (C3D8I), 20 Schichten, Bohrung r 12.381 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_001` | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 190    | 0       | 2026-10-07 08:35 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001` | LOAD_16NM | -1.22 %  | 84.7       | 74.8           | T3 RIGHT, r 26.10, z -6.8 | 82.4       | T2_T3, r 24.83, z +0.0, Tangente 45° | -99.4      | T3_T4      | 100.5   | T3   |

## 2026-10-07 08:45 `pilot_40layers_gerechnet`

**Zweck:** Pilot 40 Schichten über die Breite. **Ergebnis:** 416 s, alle Schritte; Momente und Drehung gegenüber 20 Schichten auf vier Stellen gleich. (gerechnet: Vollversion; Befunde FE-08)

Netz: 159490 Knoten, 143280 Elemente (C3D8I), 40 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_001` | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 434    | 0       | 2026-10-07 08:45 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001` | LOAD_16NM | -1.26 %  | 83.1       | 75.2           | T3 RIGHT, r 26.10, z -6.8 | 83.4       | T2_T3, r 24.83, z +0.0, Tangente 45° | -99.2      | T3_T4      | 98.9    | T3   |

## 2026-10-07 09:09 `pilot_80layers_gerechnet`

**Zweck:** Pilot 80 Schichten über die Breite. **Ergebnis:** 1258 s, alle Schritte; CPRESS max +1 % gegenüber 20 Schichten. (gerechnet: Vollversion; Befunde FE-08)

Netz: 315090 Knoten, 286560 Elemente (C3D8I), 80 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_001` | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 1287   | 0       | 2026-10-07 09:09 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001` | LOAD_16NM | -1.26 %  | 83.1       | 75.5           | T3 RIGHT, r 26.10, z -6.9 | 83.4       | T2_T3, r 24.83, z +0.0, Tangente 45° | -99.2      | T3_T4      | 98.9    | T3   |

## 2026-10-07 10:01 `pilot_20layers_smooth0p01`

**Zweck:** Knoten-zu-Fläche mit der kleinsten lauffähigen Glättung SMOOTH 0,01 (Vorlage). **Ergebnis:** Vorlage; gerechnet in pilot_20layers_smooth0p01_gerechnet.

Netz: 81690 Knoten, 71640 Elemente (C3D8I), 20 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien

Nicht gerechnet: 1 Dateien (`pos_001_n2s_smooth0p01`).

## 2026-10-07 10:11 `pilot_20layers_smooth0p01_gerechnet`

**Zweck:** SMOOTH 0,01: trennt Facettenknicke von der Fläche-zu-Fläche-Formulierung. **Ergebnis:** läuft alle Schritte, Ergebnisse gleich SMOOTH 0,2 innerhalb 0,1 %: die Facettenknicke sind nicht die Ursache, die Formulierung ist es. (gerechnet: Vollversion; Befunde FE-14)

Netz: 81690 Knoten, 71640 Elemente (C3D8I), 20 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien

**Läufe**

| Datei                    | Stellung | Stufe | Rate | Variante       | Löser            | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|--------------------------|----------|-------|------|----------------|------------------|----------|-----------------------|--------|---------|------------------|
| `pos_001_n2s_smooth0p01` | C        | W1    | QS   | n2s_smooth0p01 | linear, N2S 0.01 | complete | 6, 6, 6, 6            | 185    | 0       | 2026-10-07 10:11 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei                    | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|--------------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001_n2s_smooth0p01` | LOAD_16NM | -1.26 %  | 83.1       | 74.8           | T3 RIGHT, r 26.10, z -6.8 | 83.4       | T2_T3, r 24.83, z +0.0, Tangente 45° | -99.2      | T3_T4      | 98.9    | T3   |

## 2026-10-07 10:45 `le_tests/positions_3teeth_1layers`

**Zweck:** Stellungen A bis E mit 3 Zähnen (Vorlage). **Ergebnis:** nicht rechenbar: über der 1000-Knoten-Grenze der Learning Edition.

Netz: 728 Knoten, 298 Elemente (C3D8I), 1 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien

Nicht gerechnet: 5 Dateien (`pos_001`, `pos_002`, `pos_003`, `pos_004`, `pos_005`).

## 2026-10-07 10:47 `le_tests/positions_1teeth_2layers`

**Zweck:** Stellungen A bis E auf dem groben Einzahnmodell: Platzierung und Instanzdrehung. **Ergebnis:** alle fünf durch; an E Kontakt an der scharfen Ritzelkopfkante (1 Zahn, keine Lastaufteilung). (gerechnet: Learning Edition)

Netz: 414 Knoten, 220 Elemente (C3D8I), 2 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_001` | A        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 0      | 0       | 2026-10-07 10:46 |
| `pos_002` | B        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 0      | 0       | 2026-10-07 10:46 |
| `pos_003` | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 1      | 0       | 2026-10-07 10:47 |
| `pos_004` | D        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 0      | 0       | 2026-10-07 10:47 |
| `pos_005` | E        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 12, 6, 6           | 1      | 0       | 2026-10-07 10:47 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|---------------------------|------------|------------|---------|------|
| `pos_001` | LOAD_16NM | -2.99 %  | 146.8      | 78.2           | T1 RIGHT, r 26.60, z -7.5 |            |                           |            |            | 169.0   | T1   |
| `pos_002` | LOAD_16NM | -2.28 %  | 130.4      | 72.4           | T1 RIGHT, r 26.30, z -7.5 |            |                           |            |            | 153.7   | T1   |
| `pos_003` | LOAD_16NM | -1.32 %  | 94.9       | 78.3           | T1 RIGHT, r 26.00, z -7.5 |            |                           |            |            | 113.9   | T1   |
| `pos_004` | LOAD_16NM | -0.18 %  | 77.0       | 101.3          | T1 RIGHT, r 25.70, z -7.5 |            |                           |            |            | 87.7    | T1   |
| `pos_005` | LOAD_16NM | +5.99 %  | 103.9      | 118.7          | T1 RIGHT, r 26.00, z -7.5 |            |                           |            |            | 120.0   | T1   |

## 2026-10-07 10:50 `pilot_20layers_positions`

**Zweck:** Stellungen A bis E auf dem feinen Netz (Vorlage). **Ergebnis:** Vorlage; gerechnet in pilot_20layers_positions_gerechnet.

Netz: 81690 Knoten, 71640 Elemente (C3D8I), 20 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien

Nicht gerechnet: 5 Dateien (`pos_001`, `pos_002`, `pos_003`, `pos_004`, `pos_005`).

## 2026-10-07 10:58 `frozen_mesh_20layers_bore33`

**Zweck:** Eingefrorenes Netz des Ringkörpers (20 Schichten, Bohrung 33 mm) für das CONVERSE-Mapping; Stellung C, W1. **Ergebnis:** Mapping des Nutzers erzeugt (91_Converse/wheel_mesh_QS/DY1/DY2.cof); gerechnet in frozen_mesh_20layers_bore33_gerechnet (dasselbe Deck wie Stellung 66 der 60-je-Teilung-Studie).

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien

Nicht gerechnet: 1 Dateien (`pos_001`).

## 2026-10-07 11:55 `le_tests/grid_1tooth_8perpitch`

**Zweck:** Stellungsgitter 8 je Teilung auf dem groben Einzahnmodell: Test der Auswertung über dem Eingriffsweg. **Ergebnis:** 17 Stellungen durch; Kurven und Auflösungstabelle geprüft. (gerechnet: Learning Edition)

Netz: 414 Knoten, 220 Elemente (C3D8I), 2 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 16 Nm; 17 Stellungsdateien (grid, 8 je Teilung)

**Läufe**

| Datei     | Stellung  | Stufe | Rate | Variante | Löser           | Status                        | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|-----------|-------|------|----------|-----------------|-------------------------------|-----------------------|--------|---------|------------------|
| `pos_001` | ρ1 7.048  | W1    | QS   |          | linear, N2S 0.2 | not completed (step 2 inc 1)  | 6, 5                  |        | 0       | 2026-10-07 11:54 |
| `pos_002` | ρ1 7.417  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6               | 0      | 0       | 2026-10-07 11:54 |
| `pos_003` | A         | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6               | 0      | 0       | 2026-10-07 11:54 |
| `pos_004` | ρ1 8.155  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6               | 0      | 0       | 2026-10-07 11:54 |
| `pos_005` | B         | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6               | 0      | 0       | 2026-10-07 11:54 |
| `pos_006` | ρ1 8.524  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6               | 1      | 0       | 2026-10-07 11:55 |
| `pos_007` | ρ1 8.893  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6               | 1      | 0       | 2026-10-07 11:55 |
| `pos_008` | ρ1 9.262  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6               | 0      | 0       | 2026-10-07 11:55 |
| `pos_009` | C         | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6               | 0      | 0       | 2026-10-07 11:55 |
| `pos_010` | ρ1 9.631  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6               | 0      | 0       | 2026-10-07 11:55 |
| `pos_011` | ρ1 10.000 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6               | 1      | 0       | 2026-10-07 11:55 |
| `pos_012` | ρ1 10.369 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6               | 0      | 0       | 2026-10-07 11:55 |
| `pos_013` | D         | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6               | 0      | 0       | 2026-10-07 11:55 |
| `pos_014` | ρ1 11.107 | W1    | QS   |          | linear, N2S 0.2 | not completed (step 2 inc 12) | 6, 20                 |        | 5       | 2026-10-07 11:55 |
| `pos_015` | E         | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 12, 6              | 0      | 0       | 2026-10-07 11:55 |
| `pos_016` | ρ1 11.476 | W1    | QS   |          | linear, N2S 0.2 | not completed (step 2 inc 1)  | 6, 5                  |        | 0       | 2026-10-07 11:55 |
| `pos_017` | ρ1 11.845 | W1    | QS   |          | linear, N2S 0.2 | not completed (step 2 inc 1)  | 6, 5                  |        | 0       | 2026-10-07 11:55 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt                              | RM3 Abw.  | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|--------------------------------------|-----------|------------|----------------|---------------------------|------------|---------------------------|------------|------------|---------|------|
| `pos_001` | LOAD_8NM (abgebrochen bei t = 0.000) | -100.00 % | 10.0       |                |                           |            |                           |            |            | 0.0     | T1   |
| `pos_002` | LOAD_16NM                            | -3.43 %   | 167.2      | 80.8           | T1 RIGHT, r 26.60, z -7.5 |            |                           |            |            | 187.0   | T1   |
| `pos_003` | LOAD_16NM                            | -2.99 %   | 146.8      | 78.2           | T1 RIGHT, r 26.60, z -7.5 |            |                           |            |            | 169.0   | T1   |
| `pos_004` | LOAD_16NM                            | -2.50 %   | 132.6      | 69.4           | T1 RIGHT, r 26.60, z -7.5 |            |                           |            |            | 154.8   | T1   |
| `pos_005` | LOAD_16NM                            | -2.28 %   | 130.4      | 72.4           | T1 RIGHT, r 26.30, z -7.5 |            |                           |            |            | 153.7   | T1   |
| `pos_006` | LOAD_16NM                            | -2.04 %   | 119.8      | 77.9           | T1 RIGHT, r 26.30, z -7.5 |            |                           |            |            | 143.3   | T1   |
| `pos_007` | LOAD_16NM                            | -2.02 %   | 107.0      | 77.0           | T1 RIGHT, r 26.30, z -7.5 |            |                           |            |            | 125.7   | T1   |
| `pos_008` | LOAD_16NM                            | -1.40 %   | 99.4       | 76.1           | T1 RIGHT, r 26.00, z -7.5 |            |                           |            |            | 118.9   | T1   |
| `pos_009` | LOAD_16NM                            | -1.32 %   | 94.9       | 78.4           | T1 RIGHT, r 26.00, z -7.5 |            |                           |            |            | 113.9   | T1   |
| `pos_010` | LOAD_16NM                            | -1.35 %   | 88.9       | 77.9           | T1 RIGHT, r 26.00, z -7.5 |            |                           |            |            | 105.8   | T1   |
| `pos_011` | LOAD_16NM                            | -1.37 %   | 81.6       | 76.4           | T1 RIGHT, r 26.00, z -7.5 |            |                           |            |            | 92.5    | T1   |
| `pos_012` | LOAD_16NM                            | -0.73 %   | 77.6       | 81.1           | T1 RIGHT, r 25.70, z -7.5 |            |                           |            |            | 90.1    | T1   |
| `pos_013` | LOAD_16NM                            | -0.18 %   | 77.0       | 101.3          | T1 RIGHT, r 25.70, z -7.5 |            |                           |            |            | 87.7    | T1   |
| `pos_014` | LOAD_8NM (abgebrochen bei t = 0.673) | -22.70 %  | 32.0       | 59.7           | T1 RIGHT, r 25.70, z -7.5 |            |                           |            |            | 32.5    | T1   |
| `pos_015` | LOAD_16NM                            | +5.98 %   | 103.9      | 118.7          | T1 RIGHT, r 26.00, z -7.5 |            |                           |            |            | 120.0   | T1   |
| `pos_016` | LOAD_8NM (abgebrochen bei t = 0.000) | -100.00 % | 10.0       |                |                           |            |                           |            |            | 0.0     | T1   |
| `pos_017` | LOAD_8NM (abgebrochen bei t = 0.000) | -100.00 % | 10.0       |                |                           |            |                           |            |            | 0.0     | T1   |

## 2026-10-07 11:56 `study_20layers_bore33_60perpitch`

**Zweck:** Auflösungsstudie der Stellungen: 133 Stellungen, 60 je Teilung, W1, 20 Schichten; Teilgitter 60/30/20/15/12/10 (Vorlage). **Ergebnis:** Vorlage; gerechnet in study_20layers_bore33_60perpitch_gerechnet.

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 133 Stellungsdateien (grid, 60 je Teilung)

Nicht gerechnet: 133 Dateien (`pos_001`, `pos_002`, `pos_003`, `pos_004`, `pos_005`, `pos_006` …).

## 2026-10-07 12:09 `pilot_20layers_positions_gerechnet`

**Zweck:** Stellungen A bis E auf dem feinen Netz: Kinematik, Lastaufteilung, Kantenlast des Ritzelkopfs. **Ergebnis:** alle fünf durch (162 bis 180 s); Kraft in den Doppeleingriffszonen innerhalb 0,2° der Eingriffslinie; Kantenlast des scharfen Ritzelkopfs an B und E. (gerechnet: Vollversion; Befunde FE-15, FE-16, FE-17)

Netz: 81690 Knoten, 71640 Elemente (C3D8I), 20 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_001` | A        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 177    | 0       | 2026-10-07 11:57 |
| `pos_002` | B        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 186    | 0       | 2026-10-07 12:00 |
| `pos_003` | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 186    | 0       | 2026-10-07 12:03 |
| `pos_004` | D        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 181    | 0       | 2026-10-07 12:06 |
| `pos_005` | E        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 192    | 0       | 2026-10-07 12:09 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001` | LOAD_16NM | -0.37 %  | 66.7       | 125.7          | T4 RIGHT, r 25.70, z -6.8 | 69.7       | T3_T4, r 24.83, z -6.8               | -85.0      | T4_T5      | 75.2    | T3   |
| `pos_002` | LOAD_16NM | +0.09 %  | 65.9       | 160.0          | T4 RIGHT, r 25.70, z -6.8 | 65.0       | T3_T4, r 24.85, z -6.8               | -78.5      | T4_T5      | 76.1    | T3   |
| `pos_003` | LOAD_16NM | -1.26 %  | 83.1       | 74.9           | T3 RIGHT, r 26.10, z +0.0 | 83.4       | T2_T3, r 24.83, z +0.0, Tangente 45° | -99.2      | T3_T4      | 98.9    | T3   |
| `pos_004` | LOAD_16NM | -0.39 %  | 67.6       | 125.1          | T3 RIGHT, r 25.70, z -6.8 | 70.4       | T2_T3, r 24.83, z -6.8               | -83.0      | T3_T4      | 75.9    | T2   |
| `pos_005` | LOAD_16NM | +0.07 %  | 66.7       | 159.2          | T3 RIGHT, r 25.70, z -6.8 | 65.5       | T2_T3, r 24.85, z -6.8               | -76.4      | T3_T4      | 76.9    | T2   |

## 2026-10-07 18:07 `frozen_mesh_20layers_bore33_pocket`

**Zweck:** Eingefrorenes Netz des Taschenkörpers nach Zeichnung (Nabe, Steg, Taschen); Stellung C, W1 (Vorlage). **Ergebnis:** Mapping des Nutzers erzeugt (91_Converse/wheel-pocket_mesh_QS/DY1/DY2.cof); gerechnet in frozen_mesh_20layers_bore33_pocket_gerechnet.

Netz: 83650 Knoten, 72932 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien (pilot, 12 je Teilung)

Nicht gerechnet: 1 Dateien (`pos_001`).

## 2026-10-07 18:20 `frozen_mesh_20layers_bore33_pocket_gerechnet`

**Zweck:** Taschenkörper an C, W1, linear, C3D8I, Knoten-zu-Fläche: erster Lauf des Radkörpers nach Zeichnung. **Ergebnis:** 215 s, alle Schritte, keine negativen Eigenwerte; Stützmoment −1,2 bis −1,0 % (Δψ, FE-15), Kopfverschiebung 77,5 / 95,9 / 114,2 µm; Vergleich zum Ringkörper mit derselben Bohrung in frozen_mesh_20layers_bore33_gerechnet (Drehung und Kopfverschiebung +13 bis +16 %, Fußspannungen +3 bis +10 %, Druckmaximum in der Breitenmitte statt in der Randschicht). (gerechnet: Vollversion; Befunde FE-15, FE-18)

Netz: 83650 Knoten, 72932 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien (pilot, 12 je Teilung)

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_001` | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 215    | 0       | 2026-10-07 18:20 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001` | LOAD_16NM | -0.98 %  | 96.0       | 80.1           | T4 RIGHT, r 26.00, z +0.0 | 86.0       | T2_T3, r 24.83, z +0.0, Tangente 45° | -105.7     | T3_T4      | 114.2   | T3   |

## 2026-10-07 18:46 `le_tests/orientation`

**Zweck:** Funktionstest: eine über eine Distribution definierte Orientierung dreht mit der Instanz. **Ergebnis:** Verhältnis B/A 1,000: die Orientierung dreht mit. (gerechnet: Learning Edition)

**Läufe**

| Datei         | Stellung | Stufe | Rate | Variante | Löser  | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|---------------|----------|-------|------|----------|--------|----------|-----------------------|--------|---------|------------------|
| `orientation` |          |       |      |          | linear | complete | 1                     | 1      | 0       | 2026-10-07 18:46 |

## 2026-10-07 18:46 `le_tests/pair_coarse`

**Zweck:** Grobes Paar (1 Zahn, 2 Schichten) mit der vollständigen Struktur der Stellungsdatei. **Ergebnis:** SEAT, 8, 12, 16 Nm durch; Stützmoment −7933 / −11881 / −15788 N mm. (gerechnet: Learning Edition)

Netz: 414 Knoten, 220 Elemente (C3D8I), 2 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien (pilot, 12 je Teilung)

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_001` | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 0      | 0       | 2026-10-07 18:46 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|---------------------------|------------|------------|---------|------|
| `pos_001` | LOAD_16NM | -1.32 %  | 94.9       | 78.3           | T1 RIGHT, r 26.00, z -7.5 |            |                           |            |            | 113.9   | T1   |

## 2026-10-07 18:46 `le_tests/pair_coarse_pocket`

**Zweck:** Dasselbe grobe Paar auf dem Taschenkörper (je ein Ring Nabe/Tasche/Felge, 4 Schichten). **Ergebnis:** alle Schritte durch, keine Warnung zum beschnittenen Netz; Stützmoment −7890 / −11830 / −15773 N mm. (gerechnet: Learning Edition; Befunde FE-18)

Netz: 445 Knoten, 252 Elemente (C3D8I), 4 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien (pilot, 12 je Teilung)

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_001` | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 0      | 0       | 2026-10-07 18:46 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|---------------------------|------------|------------|---------|------|
| `pos_001` | LOAD_16NM | -1.42 %  | 100.5      | 79.1           | T1 RIGHT, r 26.00, z +0.0 |            |                           |            |            | 117.1   | T1   |

## 2026-10-07 18:46 `le_tests/pair_coarse_w3`

**Zweck:** W3 mit synthetischer Orientierungsdatei (+x im Part, Feldvariablen 0,6/0,1): dreht die Faserorientierung mit der Instanz, stimmen die Feldvariablen. **Ergebnis:** 108 Stichprobenelemente, Instanz +91,53° gedreht, Abweichung 0,0000°, Feldvariablen auf 3,6e-8: ja. (gerechnet: Learning Edition)

Netz: 414 Knoten, 220 Elemente (C3D8I), 2 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W3, Raten SYN; Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien (pilot, 12 je Teilung)

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_001` | C        | W3    | SYN  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 0      | 0       | 2026-10-07 18:46 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|---------------------------|------------|------------|---------|------|
| `pos_001` | LOAD_16NM | -1.10 %  | 85.1       | 87.3           | T1 RIGHT, r 26.00, z -7.5 |            |                           |            |            | 105.8   | T1   |

## 2026-10-07 23:06 `study_20layers_bore33_60perpitch_gerechnet`

**Zweck:** Auflösungsstudie der Stellungen auf der Vollversion (2026-10-07, 12:46 bis 23:07): wie viele Stellungen je Teilung, damit Ort und Wert der Maxima über dem Eingriffsweg trotz Zahnbiegung (verlängerter Eingriff) nicht am Gitter hängen. **Ergebnis:** 122 von 133 durch (181 bis 415 s, Mittel 229 s), 11 abgebrochen (409 bis 819 s). Verlängerter Eingriff: bei 16 Nm setzt der nächste Zahn 1,65 mm vor A auf, der scharfe Ritzelkopf bleibt 1,5 mm hinter E auf dem auslaufenden Zahn, kein Einzeleingriff mehr (an C 89/477/88 N); Fußspannungsmaximum des Rads bei C (1,62 bis 1,64 mm ab A), nicht bei B. Teilgitter gegen 60 je Teilung bei 16 Nm (Drehung, CPRESS, σ1, |σ3|, Kopfverschiebung): 30 je Teilung Ort innerhalb 0,02 mm und Wert innerhalb 0,15 %; 20 je Teilung 0,05 mm und 1,6 % (|σ3|, Spitze); 15 je Teilung 0,1 mm und 2,1 %; 12 je Teilung 0,3 % (Lage); 10 je Teilung 2,5 %. Bei 8 Nm sind die Maxima Spitzen an den Übergängen der Paarzahl, dort 30 je Teilung bis 1,7 %, 20 je Teilung trifft die Spitzen des 60er-Gitters. Empfehlung 20 je Teilung plus A bis E (47 Stellungen über −0,5 bis +0,5 Teilung). Die 11 Abbrüche liegen periodisch an drei Bahnorten je Teilung (0,59 bis 0,64, 1,13 bis 1,18 und 1,57 mm ab A der Paare −1, 0, +1): die scharfe Kopfkante des Ritzels sitzt dann auf einer Knotenreihe der Flanke des auslaufenden Zahns (r 25,698/25,800/25,901 mm, Randschichten z ±6,75 und ±7,5) hinter E; der Knoten auf dem Knick der Masterfläche flattert (Penetrationsfehler, 16 Iterationen, Rückschnitt bis 1e-6), die negativen Eigenwerte dieser 11 Läufe sind Begleiterscheinung (0 in den 122 durchgelaufenen). Sektorrand: Lastaufteilung und Fußspannung der Nachbarzähne T2/T4 weichen 1 bis 2 % von T3 ab (feste Schnittflächen); Auswertung am mittleren Zahn T3. (gerechnet: Vollversion; Befunde FE-14, FE-15, FE-16, FE-17)

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 133 Stellungsdateien (grid, 60 je Teilung)

**Läufe**

| Datei     | Stellung  | Stufe | Rate | Variante | Löser           | Status                        | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|-----------|-------|------|----------|-----------------|-------------------------------|-----------------------|--------|---------|------------------|
| `pos_001` | ρ1 6.310  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 194    | 0       | 2026-10-07 12:49 |
| `pos_002` | ρ1 6.359  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 191    | 0       | 2026-10-07 12:52 |
| `pos_003` | ρ1 6.408  | W1    | QS   |          | linear, N2S 0.2 | not completed (step 4 inc 8)  | 6, 6, 6, 17           | 559    | 121     | 2026-10-07 13:02 |
| `pos_004` | ρ1 6.457  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 210    | 0       | 2026-10-07 13:06 |
| `pos_005` | ρ1 6.506  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 209    | 0       | 2026-10-07 13:10 |
| `pos_006` | ρ1 6.556  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 217    | 0       | 2026-10-07 13:14 |
| `pos_007` | ρ1 6.605  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 222    | 0       | 2026-10-07 13:18 |
| `pos_008` | ρ1 6.654  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 226    | 0       | 2026-10-07 13:22 |
| `pos_009` | ρ1 6.703  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 218    | 0       | 2026-10-07 13:26 |
| `pos_010` | ρ1 6.752  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 219    | 0       | 2026-10-07 13:30 |
| `pos_011` | ρ1 6.802  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 227    | 0       | 2026-10-07 13:34 |
| `pos_012` | ρ1 6.851  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 213    | 0       | 2026-10-07 13:38 |
| `pos_013` | ρ1 6.900  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 219    | 0       | 2026-10-07 13:42 |
| `pos_014` | ρ1 6.949  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 217    | 0       | 2026-10-07 13:46 |
| `pos_015` | ρ1 6.998  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 212    | 0       | 2026-10-07 13:50 |
| `pos_016` | ρ1 7.048  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 235    | 0       | 2026-10-07 13:54 |
| `pos_017` | ρ1 7.097  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 225    | 0       | 2026-10-07 13:58 |
| `pos_018` | ρ1 7.146  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 231    | 0       | 2026-10-07 14:02 |
| `pos_019` | ρ1 7.195  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 237    | 0       | 2026-10-07 14:06 |
| `pos_020` | ρ1 7.244  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 217    | 0       | 2026-10-07 14:10 |
| `pos_021` | ρ1 7.294  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 231    | 0       | 2026-10-07 14:15 |
| `pos_022` | ρ1 7.343  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 255    | 0       | 2026-10-07 14:19 |
| `pos_023` | ρ1 7.392  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 231    | 0       | 2026-10-07 14:23 |
| `pos_024` | ρ1 7.441  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 227    | 0       | 2026-10-07 14:27 |
| `pos_025` | ρ1 7.490  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 241    | 0       | 2026-10-07 14:32 |
| `pos_026` | ρ1 7.540  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 287    | 0       | 2026-10-07 14:37 |
| `pos_027` | ρ1 7.589  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 10           | 415    | 0       | 2026-10-07 14:44 |
| `pos_028` | ρ1 7.638  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 293    | 0       | 2026-10-07 14:50 |
| `pos_029` | ρ1 7.687  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 263    | 0       | 2026-10-07 14:54 |
| `pos_030` | ρ1 7.736  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 224    | 0       | 2026-10-07 14:58 |
| `pos_031` | A         | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 225    | 0       | 2026-10-07 15:02 |
| `pos_032` | ρ1 7.835  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 247    | 0       | 2026-10-07 15:07 |
| `pos_033` | ρ1 7.884  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 218    | 0       | 2026-10-07 15:11 |
| `pos_034` | ρ1 7.933  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 217    | 0       | 2026-10-07 15:15 |
| `pos_035` | ρ1 7.982  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 239    | 0       | 2026-10-07 15:19 |
| `pos_036` | ρ1 8.032  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 226    | 0       | 2026-10-07 15:23 |
| `pos_037` | ρ1 8.081  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 221    | 0       | 2026-10-07 15:27 |
| `pos_038` | ρ1 8.130  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 247    | 0       | 2026-10-07 15:32 |
| `pos_039` | ρ1 8.179  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 242    | 0       | 2026-10-07 15:36 |
| `pos_040` | ρ1 8.228  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 243    | 0       | 2026-10-07 15:41 |
| `pos_041` | B         | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 238    | 0       | 2026-10-07 15:45 |
| `pos_042` | ρ1 8.278  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 233    | 0       | 2026-10-07 15:49 |
| `pos_043` | ρ1 8.327  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 231    | 0       | 2026-10-07 15:54 |
| `pos_044` | ρ1 8.376  | W1    | QS   |          | linear, N2S 0.2 | not completed (step 3 inc 21) | 6, 6, 35              | 605    | 54      | 2026-10-07 16:04 |
| `pos_045` | ρ1 8.425  | W1    | QS   |          | linear, N2S 0.2 | not completed (step 2 inc 11) | 6, 20                 | 819    | 8       | 2026-10-07 16:18 |
| `pos_046` | ρ1 8.474  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 9, 6, 6            | 353    | 0       | 2026-10-07 16:24 |
| `pos_047` | ρ1 8.524  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 223    | 0       | 2026-10-07 16:28 |
| `pos_048` | ρ1 8.573  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 218    | 0       | 2026-10-07 16:32 |
| `pos_049` | ρ1 8.622  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 237    | 0       | 2026-10-07 16:36 |
| `pos_050` | ρ1 8.671  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 225    | 0       | 2026-10-07 16:40 |
| `pos_051` | ρ1 8.720  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 210    | 0       | 2026-10-07 16:44 |
| `pos_052` | ρ1 8.770  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 229    | 0       | 2026-10-07 16:48 |
| `pos_053` | ρ1 8.819  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 241    | 0       | 2026-10-07 16:53 |
| `pos_054` | ρ1 8.868  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 240    | 0       | 2026-10-07 16:57 |
| `pos_055` | ρ1 8.917  | W1    | QS   |          | linear, N2S 0.2 | not completed (step 4 inc 10) | 6, 6, 6, 21           | 514    | 44      | 2026-10-07 17:06 |
| `pos_056` | ρ1 8.966  | W1    | QS   |          | linear, N2S 0.2 | not completed (step 2 inc 11) | 6, 20                 | 803    | 8       | 2026-10-07 17:20 |
| `pos_057` | ρ1 9.016  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 229    | 0       | 2026-10-07 17:24 |
| `pos_058` | ρ1 9.065  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 233    | 0       | 2026-10-07 17:28 |
| `pos_059` | ρ1 9.114  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 229    | 0       | 2026-10-07 17:32 |
| `pos_060` | ρ1 9.163  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 229    | 0       | 2026-10-07 17:37 |
| `pos_061` | ρ1 9.212  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 233    | 0       | 2026-10-07 17:41 |
| `pos_062` | ρ1 9.262  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 241    | 0       | 2026-10-07 17:45 |
| `pos_063` | ρ1 9.311  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 236    | 0       | 2026-10-07 17:49 |
| `pos_064` | ρ1 9.360  | W1    | QS   |          | linear, N2S 0.2 | not completed (step 3 inc 17) | 6, 6, 30              | 648    | 17      | 2026-10-07 18:01 |
| `pos_065` | ρ1 9.409  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 195    | 0       | 2026-10-07 18:04 |
| `pos_066` | C         | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 181    | 0       | 2026-10-07 18:07 |
| `pos_067` | ρ1 9.458  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 182    | 0       | 2026-10-07 18:11 |
| `pos_068` | ρ1 9.508  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 198    | 0       | 2026-10-07 18:14 |
| `pos_069` | ρ1 9.557  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 223    | 0       | 2026-10-07 18:18 |
| `pos_070` | ρ1 9.606  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 222    | 0       | 2026-10-07 18:22 |
| `pos_071` | ρ1 9.655  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 215    | 0       | 2026-10-07 18:26 |
| `pos_072` | ρ1 9.704  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 223    | 0       | 2026-10-07 18:30 |
| `pos_073` | ρ1 9.754  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 220    | 0       | 2026-10-07 18:34 |
| `pos_074` | ρ1 9.803  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 213    | 0       | 2026-10-07 18:38 |
| `pos_075` | ρ1 9.852  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 216    | 0       | 2026-10-07 18:42 |
| `pos_076` | ρ1 9.901  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 213    | 0       | 2026-10-07 18:46 |
| `pos_077` | ρ1 9.950  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 217    | 0       | 2026-10-07 18:50 |
| `pos_078` | ρ1 10.000 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 249    | 0       | 2026-10-07 18:55 |
| `pos_079` | ρ1 10.049 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 233    | 0       | 2026-10-07 18:59 |
| `pos_080` | ρ1 10.098 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 244    | 0       | 2026-10-07 19:03 |
| `pos_081` | ρ1 10.147 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 244    | 0       | 2026-10-07 19:08 |
| `pos_082` | ρ1 10.196 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 231    | 0       | 2026-10-07 19:12 |
| `pos_083` | ρ1 10.246 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 235    | 0       | 2026-10-07 19:16 |
| `pos_084` | ρ1 10.295 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 227    | 0       | 2026-10-07 19:20 |
| `pos_085` | ρ1 10.344 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 207    | 0       | 2026-10-07 19:24 |
| `pos_086` | ρ1 10.393 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 209    | 0       | 2026-10-07 19:28 |
| `pos_087` | ρ1 10.442 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 220    | 0       | 2026-10-07 19:32 |
| `pos_088` | ρ1 10.492 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 273    | 0       | 2026-10-07 19:37 |
| `pos_089` | ρ1 10.541 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 9            | 336    | 0       | 2026-10-07 19:43 |
| `pos_090` | ρ1 10.590 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 8, 6            | 291    | 0       | 2026-10-07 19:48 |
| `pos_091` | ρ1 10.639 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 227    | 0       | 2026-10-07 19:52 |
| `pos_092` | ρ1 10.689 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 218    | 0       | 2026-10-07 19:56 |
| `pos_093` | D         | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 218    | 0       | 2026-10-07 20:00 |
| `pos_094` | ρ1 10.787 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 235    | 0       | 2026-10-07 20:04 |
| `pos_095` | ρ1 10.836 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 200    | 0       | 2026-10-07 20:08 |
| `pos_096` | ρ1 10.885 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 214    | 0       | 2026-10-07 20:12 |
| `pos_097` | ρ1 10.935 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 241    | 0       | 2026-10-07 20:16 |
| `pos_098` | ρ1 10.984 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 215    | 0       | 2026-10-07 20:20 |
| `pos_099` | ρ1 11.033 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 202    | 0       | 2026-10-07 20:24 |
| `pos_100` | ρ1 11.082 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 229    | 0       | 2026-10-07 20:28 |
| `pos_101` | ρ1 11.131 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 228    | 0       | 2026-10-07 20:32 |
| `pos_102` | ρ1 11.181 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 227    | 0       | 2026-10-07 20:36 |
| `pos_103` | E         | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 217    | 0       | 2026-10-07 20:40 |
| `pos_104` | ρ1 11.230 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 217    | 0       | 2026-10-07 20:44 |
| `pos_105` | ρ1 11.279 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 207    | 0       | 2026-10-07 20:48 |
| `pos_106` | ρ1 11.328 | W1    | QS   |          | linear, N2S 0.2 | not completed (step 3 inc 17) | 6, 6, 30              | 516    | 52      | 2026-10-07 20:57 |
| `pos_107` | ρ1 11.377 | W1    | QS   |          | linear, N2S 0.2 | not completed (step 2 inc 11) | 6, 21                 | 658    | 4       | 2026-10-07 21:08 |
| `pos_108` | ρ1 11.427 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 9, 6, 6            | 339    | 0       | 2026-10-07 21:14 |
| `pos_109` | ρ1 11.476 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 190    | 0       | 2026-10-07 21:18 |
| `pos_110` | ρ1 11.525 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 199    | 0       | 2026-10-07 21:21 |
| `pos_111` | ρ1 11.574 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 211    | 0       | 2026-10-07 21:25 |
| `pos_112` | ρ1 11.623 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 208    | 0       | 2026-10-07 21:29 |
| `pos_113` | ρ1 11.673 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 192    | 0       | 2026-10-07 21:32 |
| `pos_114` | ρ1 11.722 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 213    | 0       | 2026-10-07 21:36 |
| `pos_115` | ρ1 11.771 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 214    | 0       | 2026-10-07 21:40 |
| `pos_116` | ρ1 11.820 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 225    | 0       | 2026-10-07 21:44 |
| `pos_117` | ρ1 11.869 | W1    | QS   |          | linear, N2S 0.2 | not completed (step 3 inc 20) | 6, 6, 33              | 550    | 50      | 2026-10-07 21:54 |
| `pos_118` | ρ1 11.919 | W1    | QS   |          | linear, N2S 0.2 | not completed (step 2 inc 8)  | 6, 15                 | 409    | 5       | 2026-10-07 22:01 |
| `pos_119` | ρ1 11.968 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 221    | 0       | 2026-10-07 22:05 |
| `pos_120` | ρ1 12.017 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 226    | 0       | 2026-10-07 22:09 |
| `pos_121` | ρ1 12.066 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 204    | 0       | 2026-10-07 22:13 |
| `pos_122` | ρ1 12.115 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 209    | 0       | 2026-10-07 22:16 |
| `pos_123` | ρ1 12.165 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 213    | 0       | 2026-10-07 22:20 |
| `pos_124` | ρ1 12.214 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 223    | 0       | 2026-10-07 22:24 |
| `pos_125` | ρ1 12.263 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 221    | 0       | 2026-10-07 22:28 |
| `pos_126` | ρ1 12.312 | W1    | QS   |          | linear, N2S 0.2 | not completed (step 3 inc 10) | 6, 6, 19              | 558    | 14      | 2026-10-07 22:38 |
| `pos_127` | ρ1 12.361 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 227    | 0       | 2026-10-07 22:42 |
| `pos_128` | ρ1 12.411 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 217    | 0       | 2026-10-07 22:46 |
| `pos_129` | ρ1 12.460 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 213    | 0       | 2026-10-07 22:50 |
| `pos_130` | ρ1 12.509 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 225    | 0       | 2026-10-07 22:54 |
| `pos_131` | ρ1 12.558 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 221    | 0       | 2026-10-07 22:58 |
| `pos_132` | ρ1 12.607 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 215    | 0       | 2026-10-07 23:02 |
| `pos_133` | ρ1 12.657 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 226    | 0       | 2026-10-07 23:06 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt                              | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|--------------------------------------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001` | LOAD_16NM                            | -0.07 %  | 77.5       | 125.5          | T5 RIGHT, r 25.90, z +0.0 | 77.1       | T3_T4, r 24.83, z -3.8, Tangente 45° | -89.8      | T4_T5      | 93.0    | T4   |
| `pos_002` | LOAD_16NM                            | -0.26 %  | 76.9       | 116.5          | T5 RIGHT, r 25.90, z -6.8 | 76.5       | T3_T4, r 24.83, z +0.0, Tangente 45° | -89.8      | T4_T5      | 92.0    | T4   |
| `pos_003` | LOAD_12NM                            | -0.21 %  | 64.3       | 70.9           | T5 RIGHT, r 25.90, z -6.8 | 64.2       | T3_T4, r 24.83, z -3.8, Tangente 45° | -76.1      | T4_T5      | 76.8    | T4   |
| `pos_004` | LOAD_16NM                            | -1.11 %  | 81.8       | 74.5           | T4 RIGHT, r 26.10, z +0.0 | 81.4       | T3_T4, r 24.83, z +0.0, Tangente 45° | -100.2     | T4_T5      | 97.6    | T4   |
| `pos_005` | LOAD_16NM                            | -1.23 %  | 81.5       | 74.9           | T4 RIGHT, r 26.10, z +0.0 | 81.3       | T3_T4, r 24.83, z +0.0, Tangente 45° | -100.7     | T4_T5      | 97.3    | T4   |
| `pos_006` | LOAD_16NM                            | -1.37 %  | 81.2       | 74.4           | T4 RIGHT, r 26.10, z +0.0 | 81.2       | T3_T4, r 24.83, z +0.0, Tangente 45° | -101.2     | T4_T5      | 96.8    | T4   |
| `pos_007` | LOAD_16NM                            | -1.50 %  | 80.8       | 73.8           | T4 RIGHT, r 26.10, z +0.0 | 81.0       | T3_T4, r 24.83, z +0.0, Tangente 45° | -101.7     | T4_T5      | 96.3    | T4   |
| `pos_008` | LOAD_16NM                            | -1.59 %  | 80.6       | 74.8           | T4 RIGHT, r 26.00, z +0.0 | 80.9       | T3_T4, r 24.83, z +0.0, Tangente 45° | -102.1     | T4_T5      | 95.9    | T4   |
| `pos_009` | LOAD_16NM                            | -1.69 %  | 80.5       | 76.0           | T4 RIGHT, r 26.00, z +0.0 | 80.9       | T3_T4, r 24.83, z +0.0, Tangente 45° | -102.6     | T4_T5      | 95.4    | T4   |
| `pos_010` | LOAD_16NM                            | -1.79 %  | 80.4       | 77.2           | T4 RIGHT, r 26.00, z +0.0 | 80.8       | T3_T4, r 24.85, z +0.0, Tangente 40° | -103.2     | T4_T5      | 95.0    | T4   |
| `pos_011` | LOAD_16NM                            | -1.91 %  | 80.9       | 78.0           | T4 RIGHT, r 26.00, z +0.0 | 81.5       | T3_T4, r 24.85, z +0.0, Tangente 40° | -104.8     | T4_T5      | 95.5    | T4   |
| `pos_012` | LOAD_16NM                            | -1.84 %  | 79.6       | 76.9           | T4 RIGHT, r 26.00, z +0.0 | 80.6       | T3_T4, r 24.83, z -6.8, Tangente 45° | -103.5     | T4_T5      | 94.0    | T4   |
| `pos_013` | LOAD_16NM                            | -1.77 %  | 78.4       | 75.8           | T4 RIGHT, r 26.00, z +0.0 | 79.7       | T3_T4, r 24.83, z -6.8, Tangente 45° | -102.2     | T4_T5      | 92.5    | T4   |
| `pos_014` | LOAD_16NM                            | -1.70 %  | 77.3       | 75.2           | T4 RIGHT, r 25.90, z +0.0 | 78.9       | T3_T4, r 24.83, z -6.8, Tangente 45° | -101.0     | T4_T5      | 91.0    | T4   |
| `pos_015` | LOAD_16NM                            | -1.64 %  | 76.3       | 75.9           | T3 RIGHT, r 26.89, z -7.5 | 78.1       | T3_T4, r 24.83, z -6.8, Tangente 45° | -99.7      | T4_T5      | 89.5    | T4   |
| `pos_016` | LOAD_16NM                            | -1.56 %  | 75.3       | 76.3           | T4 RIGHT, r 25.90, z +0.0 | 77.3       | T3_T4, r 24.83, z -6.8, Tangente 45° | -98.5      | T4_T5      | 88.0    | T4   |
| `pos_017` | LOAD_16NM                            | -1.50 %  | 74.4       | 76.8           | T4 RIGHT, r 25.90, z +0.0 | 76.4       | T3_T4, r 24.83, z -6.8, Tangente 45° | -97.1      | T4_T5      | 86.5    | T4   |
| `pos_018` | LOAD_16NM                            | -1.42 %  | 73.5       | 76.6           | T4 RIGHT, r 25.90, z +0.0 | 75.8       | T3_T4, r 24.83, z -6.8, Tangente 45° | -96.1      | T4_T5      | 85.4    | T4   |
| `pos_019` | LOAD_16NM                            | -1.37 %  | 72.4       | 75.7           | T4 RIGHT, r 25.90, z +0.0 | 75.1       | T3_T4, r 24.83, z -6.8, Tangente 45° | -94.9      | T4_T5      | 84.1    | T4   |
| `pos_020` | LOAD_16NM                            | -1.31 %  | 71.5       | 74.7           | T4 RIGHT, r 25.90, z +0.0 | 74.4       | T3_T4, r 24.83, z -6.8, Tangente 45° | -93.8      | T4_T5      | 82.8    | T4   |
| `pos_021` | LOAD_16NM                            | -1.25 %  | 70.6       | 74.4           | T4 RIGHT, r 25.80, z +0.0 | 73.7       | T3_T4, r 24.83, z -6.8, Tangente 45° | -92.7      | T4_T5      | 81.5    | T4   |
| `pos_022` | LOAD_16NM                            | -1.18 %  | 69.8       | 74.9           | T4 RIGHT, r 25.80, z +0.0 | 73.1       | T3_T4, r 24.83, z -6.8, Tangente 45° | -91.6      | T4_T5      | 80.3    | T4   |
| `pos_023` | LOAD_16NM                            | -1.12 %  | 69.1       | 75.5           | T4 RIGHT, r 25.80, z +0.0 | 72.5       | T3_T4, r 24.83, z -6.8, Tangente 45° | -90.6      | T4_T5      | 79.1    | T4   |
| `pos_024` | LOAD_16NM                            | -1.05 %  | 68.5       | 76.0           | T4 RIGHT, r 25.80, z +0.0 | 71.9       | T3_T4, r 24.83, z -6.8, Tangente 45° | -89.6      | T4_T5      | 78.0    | T4   |
| `pos_025` | LOAD_16NM                            | -0.98 %  | 67.9       | 75.9           | T4 RIGHT, r 25.80, z +0.0 | 71.6       | T3_T4, r 24.83, z -6.8, Tangente 45° | -89.0      | T4_T5      | 77.2    | T4   |
| `pos_026` | LOAD_16NM                            | -0.86 %  | 67.3       | 75.8           | T4 RIGHT, r 25.80, z -6.0 | 69.8       | T3_T4, r 24.83, z +0.0, Tangente 45° | -88.1      | T4_T5      | 76.1    | T4   |
| `pos_027` | LOAD_16NM                            | -0.06 %  | 68.0       | 95.1           | T4 RIGHT, r 25.70, z -6.8 | 65.1       | T3_T4, r 24.83, z -6.8, Tangente 45° | -88.4      | T4_T5      | 75.1    | T3   |
| `pos_028` | LOAD_16NM                            | -0.23 %  | 68.1       | 108.0          | T4 RIGHT, r 25.70, z -6.8 | 68.2       | T3_T4, r 24.83, z -6.8, Tangente 45° | -87.9      | T4_T5      | 75.7    | T3   |
| `pos_029` | LOAD_16NM                            | -0.49 %  | 68.0       | 116.3          | T4 RIGHT, r 25.70, z -6.8 | 70.5       | T3_T4, r 24.83, z -6.8, Tangente 45° | -87.3      | T4_T5      | 76.2    | T4   |
| `pos_030` | LOAD_16NM                            | -0.42 %  | 67.8       | 121.4          | T4 RIGHT, r 25.70, z -6.8 | 70.1       | T3_T4, r 24.83, z -6.8, Tangente 45° | -86.7      | T4_T5      | 76.0    | T3   |
| `pos_031` | LOAD_16NM                            | -0.37 %  | 67.6       | 126.0          | T4 RIGHT, r 25.70, z -6.8 | 69.4       | T3_T4, r 24.83, z -6.8, Tangente 45° | -85.8      | T4_T5      | 76.0    | T3   |
| `pos_032` | LOAD_16NM                            | -0.33 %  | 67.4       | 130.8          | T4 RIGHT, r 25.70, z -6.8 | 68.8       | T3_T4, r 24.83, z -6.8, Tangente 45° | -85.0      | T4_T5      | 76.0    | T3   |
| `pos_033` | LOAD_16NM                            | -0.28 %  | 67.3       | 135.6          | T4 RIGHT, r 25.70, z -6.8 | 68.3       | T3_T4, r 24.85, z -6.8, Tangente 40° | -84.2      | T4_T5      | 76.0    | T3   |
| `pos_034` | LOAD_16NM                            | -0.23 %  | 67.1       | 139.5          | T4 RIGHT, r 25.70, z -6.8 | 68.0       | T3_T4, r 24.85, z -6.8, Tangente 40° | -83.7      | T4_T5      | 76.0    | T3   |
| `pos_035` | LOAD_16NM                            | -0.17 %  | 67.0       | 143.0          | T4 RIGHT, r 25.70, z -6.8 | 67.6       | T3_T4, r 24.85, z -6.8, Tangente 40° | -83.1      | T4_T5      | 76.1    | T3   |
| `pos_036` | LOAD_16NM                            | -0.13 %  | 66.8       | 146.5          | T4 RIGHT, r 25.70, z -6.8 | 67.1       | T3_T4, r 24.85, z -6.8, Tangente 40° | -82.4      | T4_T5      | 76.4    | T3   |
| `pos_037` | LOAD_16NM                            | -0.07 %  | 66.7       | 149.9          | T4 RIGHT, r 25.70, z -6.8 | 66.6       | T3_T4, r 24.85, z -6.8, Tangente 40° | -81.7      | T4_T5      | 76.6    | T3   |
| `pos_038` | LOAD_16NM                            | -0.01 %  | 66.7       | 153.3          | T4 RIGHT, r 25.70, z -6.8 | 66.1       | T3_T4, r 24.85, z -6.8, Tangente 40° | -81.0      | T4_T5      | 76.7    | T3   |
| `pos_039` | LOAD_16NM                            | +0.05 %  | 66.8       | 156.6          | T4 RIGHT, r 25.70, z -6.8 | 65.6       | T3_T4, r 24.85, z -6.8, Tangente 40° | -80.4      | T4_T5      | 76.8    | T3   |
| `pos_040` | LOAD_16NM                            | +0.08 %  | 66.7       | 159.6          | T4 RIGHT, r 25.70, z -6.8 | 64.9       | T3_T4, r 24.85, z -6.8, Tangente 40° | -79.5      | T4_T5      | 76.9    | T3   |
| `pos_041` | LOAD_16NM                            | +0.09 %  | 66.7       | 160.3          | T4 RIGHT, r 25.70, z -6.8 | 64.7       | T3_T4, r 24.85, z -6.8, Tangente 40° | -79.4      | T4_T5      | 77.0    | T3   |
| `pos_042` | LOAD_16NM                            | +0.12 %  | 66.8       | 162.7          | T4 RIGHT, r 25.70, z -6.8 | 64.3       | T3_T4, r 24.85, z -6.8, Tangente 40° | -78.7      | T4_T5      | 77.4    | T3   |
| `pos_043` | LOAD_16NM                            | +0.15 %  | 66.8       | 165.8          | T4 RIGHT, r 25.70, z -6.8 | 63.6       | T3_T4, r 24.85, z -6.8, Tangente 40° | -77.9      | T4_T5      | 77.7    | T3   |
| `pos_044` | LOAD_8NM                             | +0.32 %  | 35.0       | 98.1           | T4 RIGHT, r 25.70, z -6.8 | 31.7       | T3_T4, r 24.85, z -6.8, Tangente 40° | -38.6      | T4_T5      | 40.2    | T3   |
| `pos_045` | LOAD_8NM (abgebrochen bei t = 0.424) | -55.94 % | 16.8       | 60.9           | T4 RIGHT, r 25.70, z -6.8 | 13.5       | T2_T3, r 24.82, z -4.5, Tangente 49° | -16.0      | T4_T5      | 18.8    | T3   |
| `pos_046` | LOAD_16NM                            | +0.52 %  | 72.5       | 181.9          | T4 RIGHT, r 25.80, z -6.8 | 64.4       | T2_T3, r 24.82, z -5.2, Tangente 49° | -75.2      | T4_T5      | 84.9    | T3   |
| `pos_047` | LOAD_16NM                            | +0.52 %  | 72.8       | 182.3          | T4 RIGHT, r 25.80, z -6.8 | 65.2       | T2_T3, r 24.82, z -5.2, Tangente 49° | -74.2      | T4_T5      | 85.5    | T3   |
| `pos_048` | LOAD_16NM                            | +0.56 %  | 73.1       | 182.8          | T4 RIGHT, r 25.80, z -6.8 | 66.0       | T2_T3, r 24.82, z -5.2, Tangente 49° | -73.3      | T4_T5      | 86.1    | T3   |
| `pos_049` | LOAD_16NM                            | +0.56 %  | 73.2       | 182.8          | T4 RIGHT, r 25.80, z -6.8 | 66.7       | T2_T3, r 24.82, z -5.2, Tangente 49° | -72.1      | T4_T5      | 86.5    | T3   |
| `pos_050` | LOAD_16NM                            | +0.55 %  | 73.4       | 182.7          | T4 RIGHT, r 25.80, z -6.8 | 67.3       | T2_T3, r 24.82, z -5.2, Tangente 49° | -70.9      | T4_T5      | 86.8    | T3   |
| `pos_051` | LOAD_16NM                            | +0.56 %  | 73.7       | 182.7          | T4 RIGHT, r 25.80, z -6.8 | 68.0       | T2_T3, r 24.82, z -5.2, Tangente 49° | -70.3      | T3_T4      | 87.1    | T3   |
| `pos_052` | LOAD_16NM                            | +0.58 %  | 74.0       | 182.7          | T4 RIGHT, r 25.80, z -6.8 | 68.7       | T2_T3, r 24.82, z -5.2, Tangente 49° | -71.2      | T3_T4      | 87.4    | T3   |
| `pos_053` | LOAD_16NM                            | +0.59 %  | 74.3       | 182.6          | T4 RIGHT, r 25.80, z -6.8 | 69.5       | T2_T3, r 24.82, z -5.2, Tangente 49° | -72.4      | T3_T4      | 88.1    | T3   |
| `pos_054` | LOAD_16NM                            | +0.57 %  | 74.5       | 182.1          | T4 RIGHT, r 25.80, z -6.8 | 70.3       | T2_T3, r 24.82, z -5.2, Tangente 49° | -73.6      | T3_T4      | 88.6    | T3   |
| `pos_055` | LOAD_12NM                            | +0.62 %  | 59.2       | 144.4          | T4 RIGHT, r 25.80, z -6.8 | 55.6       | T2_T3, r 24.82, z -5.2, Tangente 49° | -58.9      | T3_T4      | 70.3    | T3   |
| `pos_056` | LOAD_8NM (abgebrochen bei t = 0.588) | -39.41 % | 29.8       | 48.4           | T4 RIGHT, r 25.80, z -6.8 | 27.1       | T2_T3, r 24.83, z -4.5, Tangente 45° | -30.0      | T3_T4      | 34.8    | T3   |
| `pos_057` | LOAD_16NM                            | +0.47 %  | 82.0       | 160.0          | T4 RIGHT, r 25.90, z -6.8 | 79.6       | T2_T3, r 24.82, z -5.2, Tangente 49° | -87.1      | T3_T4      | 98.1    | T3   |
| `pos_058` | LOAD_16NM                            | +0.41 %  | 82.2       | 154.3          | T4 RIGHT, r 25.90, z -6.8 | 80.2       | T2_T3, r 24.82, z -5.2, Tangente 49° | -88.1      | T3_T4      | 98.1    | T3   |
| `pos_059` | LOAD_16NM                            | +0.33 %  | 82.1       | 147.8          | T4 RIGHT, r 25.90, z -6.8 | 80.7       | T2_T3, r 24.82, z -4.5, Tangente 49° | -89.0      | T3_T4      | 98.3    | T3   |
| `pos_060` | LOAD_16NM                            | +0.14 %  | 81.4       | 139.1          | T4 RIGHT, r 25.90, z -6.8 | 80.0       | T2_T3, r 24.83, z -3.8, Tangente 45° | -88.9      | T3_T4      | 97.4    | T3   |
| `pos_061` | LOAD_16NM                            | -0.01 %  | 80.7       | 130.6          | T4 RIGHT, r 25.90, z -6.8 | 79.4       | T2_T3, r 24.83, z -3.8, Tangente 45° | -88.9      | T3_T4      | 96.6    | T3   |
| `pos_062` | LOAD_16NM                            | -0.19 %  | 80.1       | 121.9          | T4 RIGHT, r 25.90, z -6.8 | 78.7       | T2_T3, r 24.83, z -3.8, Tangente 45° | -88.9      | T3_T4      | 95.7    | T3   |
| `pos_063` | LOAD_16NM                            | -0.37 %  | 79.4       | 113.1          | T4 RIGHT, r 25.90, z -6.8 | 78.1       | T2_T3, r 24.83, z -3.8, Tangente 45° | -88.9      | T3_T4      | 94.6    | T3   |
| `pos_064` | LOAD_8NM                             | -0.22 %  | 52.4       | 56.2           | T3 RIGHT, r 26.20, z -6.8 | 52.2       | T2_T3, r 24.83, z -3.8, Tangente 45° | -61.0      | T3_T4      | 62.4    | T3   |
| `pos_065` | LOAD_16NM                            | -1.22 %  | 84.1       | 74.7           | T3 RIGHT, r 26.10, z -6.8 | 82.9       | T2_T3, r 24.83, z +0.0, Tangente 45° | -99.1      | T3_T4      | 99.9    | T3   |
| `pos_066` | LOAD_16NM                            | -1.24 %  | 84.0       | 74.8           | T3 RIGHT, r 26.10, z -6.8 | 82.9       | T2_T3, r 24.83, z +0.0, Tangente 45° | -99.2      | T3_T4      | 99.8    | T3   |
| `pos_067` | LOAD_16NM                            | -1.33 %  | 83.7       | 74.9           | T3 RIGHT, r 26.10, z +0.0 | 82.8       | T2_T3, r 24.83, z +0.0, Tangente 45° | -99.6      | T3_T4      | 99.5    | T3   |
| `pos_068` | LOAD_16NM                            | -1.46 %  | 83.3       | 74.4           | T3 RIGHT, r 26.10, z +0.0 | 82.7       | T2_T3, r 24.83, z +0.0, Tangente 45° | -100.1     | T3_T4      | 99.0    | T3   |
| `pos_069` | LOAD_16NM                            | -1.58 %  | 82.9       | 73.9           | T3 RIGHT, r 26.10, z +0.0 | 82.5       | T2_T3, r 24.83, z +0.0, Tangente 45° | -100.6     | T3_T4      | 98.4    | T3   |
| `pos_070` | LOAD_16NM                            | -1.68 %  | 82.7       | 74.8           | T3 RIGHT, r 26.00, z +0.0 | 82.4       | T2_T3, r 24.83, z +0.0, Tangente 45° | -101.0     | T3_T4      | 97.9    | T3   |
| `pos_071` | LOAD_16NM                            | -1.77 %  | 82.5       | 76.0           | T3 RIGHT, r 26.00, z +0.0 | 82.3       | T2_T3, r 24.83, z +0.0, Tangente 45° | -101.5     | T3_T4      | 97.4    | T3   |
| `pos_072` | LOAD_16NM                            | -1.86 %  | 82.4       | 77.2           | T3 RIGHT, r 26.00, z +0.0 | 82.2       | T2_T3, r 24.83, z +0.0, Tangente 45° | -102.0     | T3_T4      | 97.0    | T3   |
| `pos_073` | LOAD_16NM                            | -1.94 %  | 82.3       | 77.7           | T3 RIGHT, r 26.00, z +0.0 | 82.4       | T2_T3, r 24.83, z +0.0, Tangente 45° | -102.8     | T3_T4      | 96.9    | T3   |
| `pos_074` | LOAD_16NM                            | -1.85 %  | 81.0       | 76.6           | T3 RIGHT, r 26.00, z +0.0 | 81.5       | T2_T3, r 24.83, z -6.8, Tangente 45° | -101.5     | T3_T4      | 95.3    | T3   |
| `pos_075` | LOAD_16NM                            | -1.78 %  | 79.8       | 75.5           | T3 RIGHT, r 26.00, z +0.0 | 80.7       | T2_T3, r 24.83, z -6.8, Tangente 45° | -100.2     | T3_T4      | 93.8    | T3   |
| `pos_076` | LOAD_16NM                            | -1.72 %  | 78.7       | 75.9           | T2 RIGHT, r 26.89, z -7.5 | 79.8       | T2_T3, r 24.83, z -6.8, Tangente 45° | -98.9      | T3_T4      | 92.3    | T3   |
| `pos_077` | LOAD_16NM                            | -1.65 %  | 77.7       | 76.7           | T2 RIGHT, r 26.89, z -7.5 | 79.0       | T2_T3, r 24.83, z -6.8, Tangente 45° | -97.7      | T3_T4      | 90.8    | T3   |
| `pos_078` | LOAD_16NM                            | -1.58 %  | 76.7       | 76.0           | T3 RIGHT, r 25.90, z +0.0 | 78.2       | T2_T3, r 24.83, z -6.8, Tangente 45° | -96.4      | T3_T4      | 89.3    | T3   |
| `pos_079` | LOAD_16NM                            | -1.52 %  | 75.7       | 76.5           | T3 RIGHT, r 25.90, z +0.0 | 77.3       | T2_T3, r 24.83, z -6.8, Tangente 45° | -95.1      | T3_T4      | 87.7    | T3   |
| `pos_080` | LOAD_16NM                            | -1.44 %  | 74.8       | 76.3           | T3 RIGHT, r 25.90, z +0.0 | 76.7       | T2_T3, r 24.83, z -6.8, Tangente 45° | -94.1      | T3_T4      | 86.6    | T3   |
| `pos_081` | LOAD_16NM                            | -1.38 %  | 73.8       | 75.4           | T3 RIGHT, r 25.90, z +0.0 | 76.0       | T2_T3, r 24.83, z -6.8, Tangente 45° | -92.9      | T3_T4      | 85.3    | T3   |
| `pos_082` | LOAD_16NM                            | -1.32 %  | 72.8       | 74.5           | T3 RIGHT, r 25.90, z +0.0 | 75.3       | T2_T3, r 24.83, z -6.8, Tangente 45° | -91.8      | T3_T4      | 84.0    | T3   |
| `pos_083` | LOAD_16NM                            | -1.26 %  | 71.9       | 74.0           | T3 RIGHT, r 25.80, z +0.0 | 74.6       | T2_T3, r 24.83, z -6.8, Tangente 45° | -90.7      | T3_T4      | 82.8    | T3   |
| `pos_084` | LOAD_16NM                            | -1.19 %  | 71.1       | 74.5           | T3 RIGHT, r 25.80, z +0.0 | 74.0       | T2_T3, r 24.83, z -6.8, Tangente 45° | -89.6      | T3_T4      | 81.5    | T3   |
| `pos_085` | LOAD_16NM                            | -1.12 %  | 70.4       | 75.1           | T3 RIGHT, r 25.80, z +0.0 | 73.4       | T2_T3, r 24.83, z -6.8, Tangente 45° | -88.6      | T3_T4      | 80.3    | T3   |
| `pos_086` | LOAD_16NM                            | -1.06 %  | 69.8       | 75.7           | T3 RIGHT, r 25.80, z +0.0 | 72.8       | T2_T3, r 24.83, z -6.8, Tangente 45° | -87.6      | T3_T4      | 79.2    | T3   |
| `pos_087` | LOAD_16NM                            | -0.99 %  | 69.1       | 75.5           | T3 RIGHT, r 25.80, z +0.0 | 72.5       | T2_T3, r 24.83, z -6.8, Tangente 45° | -86.9      | T3_T4      | 78.4    | T3   |
| `pos_088` | LOAD_16NM                            | -0.63 %  | 68.8       | 78.9           | T3 RIGHT, r 25.70, z -7.5 | 69.2       | T2_T3, r 24.83, z +0.0, Tangente 45° | -86.2      | T3_T4      | 76.6    | T3   |
| `pos_089` | LOAD_16NM                            | -0.15 %  | 69.5       | 97.1           | T3 RIGHT, r 25.70, z -6.8 | 67.0       | T2_T3, r 24.83, z -6.8, Tangente 45° | -86.3      | T3_T4      | 76.3    | T2   |
| `pos_090` | LOAD_16NM                            | -0.35 %  | 69.4       | 108.8          | T3 RIGHT, r 25.70, z -6.8 | 70.1       | T2_T3, r 24.83, z -6.8, Tangente 45° | -85.9      | T3_T4      | 76.9    | T3   |
| `pos_091` | LOAD_16NM                            | -0.51 %  | 69.2       | 115.8          | T3 RIGHT, r 25.70, z -6.8 | 71.3       | T2_T3, r 24.83, z -6.8, Tangente 45° | -85.2      | T3_T4      | 77.4    | T3   |
| `pos_092` | LOAD_16NM                            | -0.43 %  | 69.0       | 120.8          | T3 RIGHT, r 25.70, z -6.8 | 70.9       | T2_T3, r 24.83, z -6.8, Tangente 45° | -84.6      | T3_T4      | 76.9    | T2   |
| `pos_093` | LOAD_16NM                            | -0.39 %  | 68.7       | 125.5          | T3 RIGHT, r 25.70, z -6.8 | 70.2       | T2_T3, r 24.83, z -6.8, Tangente 45° | -83.7      | T3_T4      | 76.9    | T2   |
| `pos_094` | LOAD_16NM                            | -0.34 %  | 68.5       | 130.2          | T3 RIGHT, r 25.70, z -6.8 | 69.6       | T2_T3, r 24.83, z -6.8, Tangente 45° | -82.9      | T3_T4      | 77.0    | T2   |
| `pos_095` | LOAD_16NM                            | -0.30 %  | 68.4       | 135.0          | T3 RIGHT, r 25.70, z -6.8 | 69.1       | T2_T3, r 24.83, z -6.8, Tangente 45° | -82.1      | T3_T4      | 77.0    | T2   |
| `pos_096` | LOAD_16NM                            | -0.24 %  | 68.2       | 138.8          | T3 RIGHT, r 25.70, z -6.8 | 68.8       | T2_T3, r 24.83, z -6.8, Tangente 45° | -81.6      | T3_T4      | 77.0    | T2   |
| `pos_097` | LOAD_16NM                            | -0.19 %  | 68.1       | 142.4          | T3 RIGHT, r 25.70, z -6.8 | 68.3       | T2_T3, r 24.83, z -6.8, Tangente 45° | -80.9      | T3_T4      | 77.1    | T2   |
| `pos_098` | LOAD_16NM                            | -0.14 %  | 67.9       | 145.8          | T3 RIGHT, r 25.70, z -6.8 | 67.8       | T2_T3, r 24.83, z -6.8, Tangente 45° | -80.2      | T3_T4      | 77.3    | T2   |
| `pos_099` | LOAD_16NM                            | -0.09 %  | 67.8       | 149.3          | T3 RIGHT, r 25.70, z -6.8 | 67.3       | T2_T3, r 24.83, z -6.8, Tangente 45° | -79.5      | T3_T4      | 77.5    | T2   |
| `pos_100` | LOAD_16NM                            | -0.02 %  | 67.8       | 152.5          | T3 RIGHT, r 25.70, z -6.8 | 66.7       | T2_T3, r 24.83, z -6.8, Tangente 45° | -78.9      | T3_T4      | 77.7    | T2   |
| `pos_101` | LOAD_16NM                            | +0.04 %  | 67.8       | 155.9          | T3 RIGHT, r 25.70, z -6.8 | 66.2       | T2_T3, r 24.85, z -6.8, Tangente 40° | -78.2      | T3_T4      | 77.8    | T2   |
| `pos_102` | LOAD_16NM                            | +0.06 %  | 67.7       | 158.9          | T3 RIGHT, r 25.70, z -6.8 | 65.5       | T2_T3, r 24.85, z -6.8, Tangente 40° | -77.3      | T3_T4      | 77.8    | T2   |
| `pos_103` | LOAD_16NM                            | +0.07 %  | 67.7       | 159.6          | T3 RIGHT, r 25.70, z -6.8 | 65.3       | T2_T3, r 24.85, z -6.8, Tangente 40° | -77.1      | T3_T4      | 77.9    | T2   |
| `pos_104` | LOAD_16NM                            | +0.10 %  | 67.7       | 162.0          | T3 RIGHT, r 25.70, z -6.8 | 64.8       | T2_T3, r 24.85, z -6.8, Tangente 40° | -76.4      | T3_T4      | 78.2    | T2   |
| `pos_105` | LOAD_16NM                            | +0.13 %  | 67.8       | 165.1          | T3 RIGHT, r 25.70, z -6.8 | 64.2       | T2_T3, r 24.85, z -6.8, Tangente 40° | -75.6      | T3_T4      | 78.6    | T2   |
| `pos_106` | LOAD_8NM                             | +0.31 %  | 35.5       | 97.7           | T3 RIGHT, r 25.70, z -6.8 | 32.0       | T2_T3, r 24.85, z -6.8, Tangente 40° | -37.5      | T3_T4      | 40.6    | T2   |
| `pos_107` | LOAD_8NM (abgebrochen bei t = 0.386) | -60.23 % | 15.5       | 54.1           | T3 RIGHT, r 25.70, z -6.8 | 12.8       | T1_T2, r 24.82, z -4.5, Tangente 49° | -14.0      | T3_T4      | 17.2    | T2   |
| `pos_108` | LOAD_16NM                            | +0.46 %  | 73.3       | 180.8          | T3 RIGHT, r 25.80, z -6.8 | 66.7       | T1_T2, r 24.82, z -4.5, Tangente 49° | -73.0      | T3_T4      | 85.6    | T2   |
| `pos_109` | LOAD_16NM                            | +0.50 %  | 73.6       | 181.3          | T3 RIGHT, r 25.80, z -6.8 | 67.5       | T1_T2, r 24.82, z -4.5, Tangente 49° | -72.0      | T3_T4      | 86.2    | T2   |
| `pos_110` | LOAD_16NM                            | +0.54 %  | 73.8       | 181.7          | T3 RIGHT, r 25.80, z -6.8 | 68.2       | T1_T2, r 24.82, z -4.5, Tangente 49° | -71.0      | T3_T4      | 86.8    | T2   |
| `pos_111` | LOAD_16NM                            | +0.53 %  | 74.0       | 181.7          | T3 RIGHT, r 25.80, z -6.8 | 68.9       | T1_T2, r 24.82, z -4.5, Tangente 49° | -69.8      | T3_T4      | 87.2    | T2   |
| `pos_112` | LOAD_16NM                            | +0.52 %  | 74.1       | 181.6          | T3 RIGHT, r 25.80, z -6.8 | 69.6       | T1_T2, r 24.82, z -4.5, Tangente 49° | -69.4      | T2_T3      | 87.5    | T2   |
| `pos_113` | LOAD_16NM                            | +0.54 %  | 74.4       | 181.6          | T3 RIGHT, r 25.80, z -6.8 | 70.3       | T1_T2, r 24.82, z -4.5, Tangente 49° | -70.2      | T2_T3      | 87.7    | T2   |
| `pos_114` | LOAD_16NM                            | +0.55 %  | 74.7       | 181.6          | T3 RIGHT, r 25.80, z -6.8 | 70.9       | T1_T2, r 24.82, z -4.5, Tangente 49° | -71.1      | T2_T3      | 88.0    | T2   |
| `pos_115` | LOAD_16NM                            | +0.56 %  | 75.0       | 181.4          | T3 RIGHT, r 25.80, z -6.8 | 71.8       | T1_T2, r 24.82, z -4.5, Tangente 49° | -72.4      | T2_T3      | 88.7    | T2   |
| `pos_116` | LOAD_16NM                            | +0.53 %  | 75.1       | 181.0          | T3 RIGHT, r 25.80, z -6.8 | 72.6       | T1_T2, r 24.82, z -4.5, Tangente 49° | -73.5      | T2_T3      | 89.1    | T2   |
| `pos_117` | LOAD_8NM                             | +0.61 %  | 42.9       | 88.9           | T3 RIGHT, r 25.80, z -6.8 | 40.6       | T1_T2, r 24.82, z -4.5, Tangente 49° | -42.3      | T2_T3      | 50.4    | T2   |
| `pos_118` | LOAD_8NM (abgebrochen bei t = 0.570) | -41.17 % | 29.4       | 45.7           | T3 RIGHT, r 25.80, z -6.8 | 27.2       | T1_T2, r 24.83, z -4.5, Tangente 45° | -29.3      | T2_T3      | 34.2    | T2   |
| `pos_119` | LOAD_16NM                            | +0.44 %  | 82.4       | 158.0          | T3 RIGHT, r 25.90, z -6.8 | 81.8       | T1_T2, r 24.82, z -4.5, Tangente 49° | -86.9      | T2_T3      | 98.4    | T2   |
| `pos_120` | LOAD_16NM                            | +0.38 %  | 82.6       | 152.3          | T3 RIGHT, r 25.90, z -6.8 | 82.5       | T1_T2, r 24.82, z -4.5, Tangente 49° | -87.8      | T2_T3      | 98.4    | T2   |
| `pos_121` | LOAD_16NM                            | +0.25 %  | 82.2       | 144.8          | T3 RIGHT, r 25.90, z -6.8 | 82.4       | T1_T2, r 24.82, z -3.8, Tangente 49° | -88.2      | T2_T3      | 98.1    | T2   |
| `pos_122` | LOAD_16NM                            | +0.06 %  | 81.4       | 136.1          | T3 RIGHT, r 25.90, z -6.8 | 81.7       | T1_T2, r 24.82, z -3.8, Tangente 49° | -88.2      | T2_T3      | 97.2    | T2   |
| `pos_123` | LOAD_16NM                            | -0.10 %  | 80.7       | 127.6          | T3 RIGHT, r 25.90, z -6.8 | 81.0       | T1_T2, r 24.82, z -3.8, Tangente 49° | -88.1      | T2_T3      | 96.3    | T2   |
| `pos_124` | LOAD_16NM                            | -0.27 %  | 80.0       | 118.8          | T3 RIGHT, r 25.90, z -6.8 | 80.3       | T1_T2, r 24.83, z -3.8, Tangente 45° | -88.2      | T2_T3      | 95.3    | T2   |
| `pos_125` | LOAD_16NM                            | -0.45 %  | 79.3       | 110.1          | T3 RIGHT, r 25.90, z -6.8 | 79.8       | T1_T2, r 24.83, z +0.0, Tangente 45° | -88.1      | T2_T3      | 94.3    | T2   |
| `pos_126` | LOAD_8NM                             | -0.24 %  | 52.5       | 56.3           | T2 RIGHT, r 26.20, z +0.0 | 53.3       | T1_T2, r 24.83, z -3.8, Tangente 45° | -60.8      | T2_T3      | 62.4    | T2   |
| `pos_127` | LOAD_16NM                            | -1.30 %  | 83.7       | 74.8           | T2 RIGHT, r 26.10, z +0.0 | 84.6       | T1_T2, r 24.83, z +0.0, Tangente 45° | -98.1      | T2_T3      | 99.2    | T2   |
| `pos_128` | LOAD_16NM                            | -1.40 %  | 83.3       | 75.1           | T2 RIGHT, r 26.10, z +0.0 | 84.5       | T1_T2, r 24.83, z +0.0, Tangente 45° | -98.6      | T2_T3      | 98.9    | T2   |
| `pos_129` | LOAD_16NM                            | -1.54 %  | 82.8       | 74.6           | T2 RIGHT, r 26.10, z +0.0 | 84.3       | T1_T2, r 24.83, z +0.0, Tangente 45° | -99.0      | T2_T3      | 98.3    | T2   |
| `pos_130` | LOAD_16NM                            | -1.66 %  | 82.4       | 74.1           | T2 RIGHT, r 26.10, z +0.0 | 84.2       | T1_T2, r 24.83, z +0.0, Tangente 45° | -99.5      | T2_T3      | 97.7    | T2   |
| `pos_131` | LOAD_16NM                            | -1.75 %  | 82.1       | 74.8           | T2 RIGHT, r 26.00, z +0.0 | 84.1       | T1_T2, r 24.83, z +0.0, Tangente 45° | -100.0     | T2_T3      | 97.1    | T2   |
| `pos_132` | LOAD_16NM                            | -1.84 %  | 81.9       | 76.1           | T2 RIGHT, r 26.00, z +0.0 | 84.0       | T1_T2, r 24.83, z +0.0, Tangente 45° | -100.4     | T2_T3      | 96.6    | T2   |
| `pos_133` | LOAD_16NM                            | -1.93 %  | 81.7       | 77.3           | T2 RIGHT, r 26.00, z +0.0 | 83.9       | T1_T2, r 24.83, z +0.0, Tangente 45° | -100.9     | T2_T3      | 96.1    | T2   |

## 2026-10-09 08:51 `pilot_20layers_gerechnet`

**Zweck:** Ringkörper mit der alten Bohrung r 18,10 an C, W1 linear C3D8I, Knoten-zu-Fläche: Einfluss der Bohrungstiefe gegen den Ringkörper mit Bohrung 33 (frozen_mesh_20layers_bore33_gerechnet). **Ergebnis:** 209 s, alle Schritte, keine negativen Eigenwerte; gegenüber Bohrung 33: Stützmoment gleich (0,03 %), Ritzeldrehung −0,9 bis −1,1 % (55,5/70,3/83,1 gegen 56,0/71,0/84,0 µm), CPRESS innerhalb 0,2 %, σ1 am Fuß +0,3 bis +0,6 %, Kopfverschiebung −0,9 %: die Bohrung 18,10 → 16,5 ist ein 1-%-Effekt. (gerechnet: Vollversion; Befunde FE-08)

Netz: 81690 Knoten, 71640 Elemente (C3D8I), 20 Schichten, Bohrung r 18.100 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_001` | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 209    | 0       | 2026-10-09 08:51 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001` | LOAD_16NM | -1.26 %  | 83.1       | 74.9           | T3 RIGHT, r 26.10, z +0.0 | 83.4       | T2_T3, r 24.83, z +0.0, Tangente 45° | -99.2      | T3_T4      | 98.9    | T3   |

## 2026-10-09 09:30 `frozen_mesh_20layers_bore33_gerechnet`

**Zweck:** Ringkörper an C, Bohrung 33, W1 linear C3D8I, Knoten-zu-Fläche: Referenz für den Taschenkörper mit derselben Bohrung und Reproduzierbarkeitsprobe gegen Stellung 66 der Studie (gleiches Netz, gleiches Deck bis auf CFORCE im Feldrequest). **Ergebnis:** 177 s, alle Schritte; auf alle ausgegebenen Stellen gleich Stellung 66 der Studie (RM3 −7910,43/−11835,99/−15800,93 N mm, Drehung 56,0/71,0/84,0 µm, CPRESS 59,09/67,68/74,80 MPa, σ1 max T2_T3 56,10/70,45/82,91 MPa, Kopf 66,9/84,5/99,8 µm). Taschenkörper gegen Ring (8/12/16 Nm): Ritzeldrehung +15,4/+13,1/+14,3 %, Kopfverschiebung +15,8/+13,5/+14,4 %, σ1 max T2_T3 +5,9/+3,2/+3,8 %, |σ3| max T3_T4 +10,4/+6,0/+6,5 %, CPRESS der Hauptkontaktzahn T3 +4,0/+2,0/+2,3 %; der Taschenkörper verlagert das Druckmaximum von z ±6,75 (Randschicht) auf z = 0 (Mitte, über dem Steg) und gibt bei 16 Nm dem Kantenkontakt des auslaufenden Zahns T4 121,5 statt 88,4 N (CPRESS 80,1 statt 56,3 MPa). (gerechnet: Vollversion; Befunde FE-15, FE-17, FE-18)

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS (eine Karte); Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_001` | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 177    | 0       | 2026-10-09 09:30 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001` | LOAD_16NM | -1.24 %  | 84.0       | 74.8           | T3 RIGHT, r 26.10, z -6.8 | 82.9       | T2_T3, r 24.83, z +0.0, Tangente 45° | -99.2      | T3_T4      | 99.8    | T3   |

## 2026-10-09 09:50 `study_20layers_bore33_60perpitch_retry_penalty`

**Zweck:** Wiederholung der 11 abgebrochenen Stellungen der Studie (3, 44, 45, 55, 56, 64, 106, 107, 117, 118, 126) plus drei durchgelaufene Kontrollen (2, 46, 66 = C) mit Penalty-Durchsetzung der harten Kontaktbedingung (PENALTY=LINEAR statt direkter Lagrange-Multiplikatoren), sonst identisch (Vorlage, 2026-10-09). **Ergebnis:** Vorlage; Netz und Stellungen byteidentisch mit der Studie, nur die Zeile *SURFACE BEHAVIOR unterscheidet sich; gerechnet in study_20layers_bore33_60perpitch_retry_penalty_gerechnet (nach pos_003 abgebrochen).

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 14 Stellungsdateien (grid, 60 je Teilung)

Nicht gerechnet: 14 Dateien (`pos_002`, `pos_003`, `pos_044`, `pos_045`, `pos_046`, `pos_055` …).

## 2026-10-09 10:05 `study_20layers_bore33_60perpitch_retry_round0p05`

**Zweck:** Dieselben 14 Stellungen mit der Kopfkante des starren Ritzels auf 0,05 mm gerundet (Entgratung als Modellannahme der starren Fläche, mindestens vier Facetten je Bogen), Kontaktdurchsetzung wie in der Studie (Vorlage, 2026-10-09). **Ergebnis:** Vorlage; Radnetz und Decks identisch mit der Studie, nur pinion_surface.inp hat 932 statt 897 Profilknoten; gerechnet in study_20layers_bore33_60perpitch_retry_round0p05_gerechnet (nach pos_003 abgebrochen).

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 14 Stellungsdateien (grid, 60 je Teilung)

Nicht gerechnet: 14 Dateien (`pos_002`, `pos_003`, `pos_044`, `pos_045`, `pos_046`, `pos_055` …).

## 2026-10-09 10:21 `pilot_20layers_bore33_w2w4_qs`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 82425 Knoten, 72320 Elemente (C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W2, W4, Raten QS; Momente am Rad 8, 12, 16 Nm; 10 Stellungsdateien (grid, 60 je Teilung)

Nicht gerechnet: 10 Dateien (`pos_001_W2_QS`, `pos_001_W4_QS`, `pos_031_W2_QS`, `pos_031_W4_QS`, `pos_066_W2_QS`, `pos_066_W4_QS` …).

## 2026-10-09 10:34 `study_20layers_bore33_60perpitch_retry_penalty_gerechnet`

**Zweck:** Penalty-Durchsetzung (PENALTY=LINEAR) gegen das Flattern der Kopfkante: Kontrolle pos_002 und die abgebrochene pos_003, vom Nutzer nach pos_003 gestoppt (2026-10-09). **Ergebnis:** Hilft nicht: pos_003 bricht wieder bei 16 Nm ab (Schrittzeit 0,160 statt 0,206, 10 min, 125 Warnungen negativer Eigenwerte) an denselben Knoten 7293/77943 (T5 rechte Flanke, r 25,901, z ±6,75), die Art der Kontaktbedingung ist nicht die Ursache, der Knick der Masterfläche ist es. Nachgiebigkeit der Penalty an der Kontrolle pos_002 gegen die Studie: Stützmoment innerhalb 0,03 %, Ritzeldrehung +0,4 % (50,7/65,0/77,2 gegen 50,5/64,7/76,9 µm), CPRESS am Hauptkontakt −2,4/−1,8/−1,8 %, am Kantenkontakt −0,9 %, Normalkräfte je Zahn innerhalb 0,5 N, σ1 am Fuß +0,1 %, Kopfverschiebung +0,2 %. pos_044 wurde im Schritt SEAT abgebrochen (kein Ergebnis); die path_*-Dateien des Ordners sind mit drei Stellungen ohne Aussage. (gerechnet: Vollversion; Befunde FE-14, FE-17)

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 14 Stellungsdateien (grid, 60 je Teilung)

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser                    | Status                        | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|--------------------------|-------------------------------|-----------------------|--------|---------|------------------|
| `pos_002` | ρ1 6.359 | W1    | QS   |          | linear, N2S 0.2, PENALTY | complete                      | 6, 6, 6, 6            | 191    | 0       | 2026-10-09 10:22 |
| `pos_003` | ρ1 6.408 | W1    | QS   |          | linear, N2S 0.2, PENALTY | not completed (step 4 inc 12) | 6, 6, 6, 23           | 606    | 126     | 2026-10-09 10:33 |
| `pos_044` | ρ1 8.376 | W1    | QS   |          | linear, N2S 0.2, PENALTY | open (step 1 inc 6)           | 6                     |        | 0       | 2026-10-09 10:34 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt                              | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|--------------------------------------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_002` | LOAD_16NM                            | -0.28 %  | 77.2       | 115.4          | T5 RIGHT, r 25.90, z -6.8 | 76.6       | T3_T4, r 24.83, z +0.0, Tangente 45° | -90.0      | T4_T5      | 92.2    | T4   |
| `pos_003` | LOAD_12NM                            | -0.22 %  | 64.5       | 70.3           | T5 RIGHT, r 25.90, z -6.8 | 64.3       | T3_T4, r 24.83, z -3.8, Tangente 45° | -76.2      | T4_T5      | 76.9    | T4   |
| `pos_044` | LOAD_8NM (abgebrochen bei t = 0.000) |          |            | 0.9            | T3 RIGHT, r 26.70, z -7.5 | 0.6        | T2_T3, r 24.85, z -4.5, Tangente 40° | -0.6       | T3_T4      | 0.8     | T3   |

Nicht gerechnet: 11 Dateien (`pos_045`, `pos_046`, `pos_055`, `pos_056`, `pos_064`, `pos_066` …).

## 2026-10-09 10:53 `study_20layers_bore33_60perpitch_retry_round0p05_gerechnet`

**Zweck:** Kopfkante des starren Ritzels auf 0,05 mm gerundet (fünf Facetten je Bogen, 0,014 mm) gegen das Flattern: Kontrolle pos_002 und die abgebrochene pos_003, vom Nutzer nach pos_003 gestoppt (2026-10-09). **Ergebnis:** Verschiebt das Problem, löst es nicht: die in der Studie durchgelaufene Kontrolle pos_002 bricht jetzt bei 12 Nm ab (Schrittzeit 0,752, 8 min, dieselben Knoten 7293/77943 der rechten Flanke T5, r 25,901, z ±6,75), pos_003 läuft durch (252 s, 8 Inkremente mit zwei Rückschnitten bei 12 Nm). Die Rundung von 0,05 mm ist kleiner als der Reihenabstand der Flankenknoten (0,1 mm): die Kante trifft die Knotenreihe nur 0,05 mm früher auf der Bahn. Befund aus den .msg aller drei Abbrüche (Studie pos_045, Penalty pos_003, Rundung pos_002): der Penetrationsfehler des flatternden Knotens nimmt in der letzten Attempt monoton oder mit abklingender Oszillation ab (Faktor 0,85 bis 0,95 je Iteration), die Lösung konvergiert also, nur zu langsam für die 16 Gleichgewichtsiterationen (I_C) je Inkrement; der Rückschnitt verkleinert dann das Verschiebungsinkrement und damit die Penetrationstoleranz weiter. Abhilfe zu prüfen: höhere Iterationsgrenzen (*CONTROLS, PARAMETERS=TIME INCREMENTATION, I_0/I_R/I_C) ohne Änderung von Geometrie und Kontaktbedingung. pos_044 wurde bei 16 Nm gestoppt (kein Ergebnis). (gerechnet: Vollversion; Befunde FE-14, FE-17)

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 14 Stellungsdateien (grid, 60 je Teilung)

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status                        | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|-------------------------------|-----------------------|--------|---------|------------------|
| `pos_002` | ρ1 6.359 | W1    | QS   |          | linear, N2S 0.2 | not completed (step 3 inc 11) | 6, 6, 21              | 474    | 21      | 2026-10-09 10:45 |
| `pos_003` | ρ1 6.408 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 9, 6            | 251    | 2       | 2026-10-09 10:49 |
| `pos_044` | ρ1 8.376 | W1    | QS   |          | linear, N2S 0.2 | open (step 4 inc 5)           | 6, 6, 6, 5            |        | 0       | 2026-10-09 10:53 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                                         | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_002` | LOAD_8NM  | +0.52 %  | 51.1       | 55.6           | T4 RIGHT, r 26.20, z +0.0                   | 50.9       | T3_T4, r 24.83, z -3.8, Tangente 45° | -60.8      | T4_T5      | 61.2    | T4   |
| `pos_003` | LOAD_16NM | +1.29 %  | 82.0       | 73.0           | T4 RIGHT, r 26.10, z -6.8                   | 80.9       | T3_T4, r 24.83, z +0.0, Tangente 45° | -97.4      | T4_T5      | 98.0    | T4   |
| `pos_044` | LOAD_12NM | +2.42 %  | 55.3       | 130.4          | (147 geschlossene Knoten, Ort nur mit .odb) |            |                                      |            |            |         |      |

Nicht gerechnet: 11 Dateien (`pos_045`, `pos_046`, `pos_055`, `pos_056`, `pos_064`, `pos_066` …).

## 2026-10-09 11:04 `study_20layers_bore33_60perpitch_retry_iter100`

**Zweck:** Dritte Abhilfe gegen das Flattern an der Ritzelkopfkante, ohne Änderung von Geometrie und Kontaktbedingung: Iterationsgrenzen je Inkrement I_0/I_R/I_C = 20/30/100 statt 4/8/16 (*CONTROLS, PARAMETERS=TIME INCREMENTATION), damit die langsam konvergierende Kontaktiteration (Faktor 0,85 bis 0,95 je Iteration in den .msg der Abbrüche) zu Ende läuft statt in den Rückschnitt; Stellungen 2 (Kontrolle), 3, 44, 45 der Studie (Abbrüche bei 16, 12 und 8 Nm), scharfe Kante, Lagrange (Vorlage, 2026-10-09). **Ergebnis:** Vorlage; Netz, Fläche und Decks identisch mit der Studie bis auf die vier *CONTROLS-Zeilen; gerechnet in study_20layers_bore33_60perpitch_retry_iter100_gerechnet (nach pos_003 abgebrochen).

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 4 Stellungsdateien (grid, 60 je Teilung)

Nicht gerechnet: 4 Dateien (`pos_002`, `pos_003`, `pos_044`, `pos_045`).

## 2026-10-09 11:05 `pilot_20layers_bore33_w2w4_qs_gerechnet`

**Zweck:** Erster Lauf des nichtlinearen Piloten in der Fassung V1 (W2 ohne Orientierung am Section, W4, Rate QS, NLGEOM=YES, C3D8), vom Nutzer nach pos_031_W4 gestoppt (2026-10-09). **Ergebnis:** W2 bricht in 11 s im Präprozessor ab: 'Anisotropic material properties without a local orientation system have been defined for 72320 elements' (der Hill-Potential-Block der isotropen Zeile braucht eine lokale Orientierung, Materialhandbuch Hill anisotropic yield; behoben: *ORIENTATION WHEEL_ISO = Teilerahmen am Solid Section von W2, die Fließverhältnisse der isotropen Zeile sind in den drei Normal- und drei Schubrichtungen gleich, der Rahmen ist also belanglos). W4 pos_001 (Rand −0,5 Teilung) läuft durch: 565 s (2,9 × W1), 6 Inkremente je Schritt, keine negativen Eigenwerte, Orientierungsprüfung an SEAT 0,002°, unter Last bis 0,59° Mitdrehung mit der Verformung (NLGEOM). Gegen W1 (Studie pos_001) bei 16 Nm: Ritzeldrehung 88,6 statt 77,5 µm (+14 %), Kopfverschiebung 100,2 statt 93,0 µm (+8 %), einlaufender Zahn T3 (1,48 mm vor A) trägt 67,8 statt 34,5 N, auslaufender T5 194,8 statt 199,2 N, Kantendruck 96,0 statt 125,5 MPa (−24 %), σ1 am Fuß T3_T4 61,7 statt 77,1 MPa (−20 %, Maximum bei z +4,5 statt −3,75 durch die Faserorientierung), |σ3| T4_T5 68,0 statt 89,8 MPa. Am Gitterrand tragen die Randzähne noch 10 bzw. 30 % der Zahnkraft: der Rand von 0,5 Teilung reicht für W4 nicht, Randpilot pilot_20layers_bore33_w4_qs_margin geschrieben. (gerechnet: Vollversion; Befunde FE-15, FE-17)

Netz: 82425 Knoten, 72320 Elemente (C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W2, W4, Raten QS; Momente am Rad 8, 12, 16 Nm; 10 Stellungsdateien (grid, 60 je Teilung)

**Läufe**

| Datei           | Stellung | Stufe | Rate | Variante | Löser           | Status                  | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------------|----------|-------|------|----------|-----------------|-------------------------|-----------------------|--------|---------|------------------|
| `pos_001_W2_QS` | ρ1 6.310 | W2    | QS   |          | NLGEOM, N2S 0.2 | open (odb without .sta) |                       | 11     | 0       | 2026-10-09 10:56 |
| `pos_001_W4_QS` | ρ1 6.310 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                | 6, 6, 6, 6            | 565    | 0       | 2026-10-09 11:05 |
| `pos_031_W2_QS` | A        | W2    | QS   |          | NLGEOM, N2S 0.2 | open (odb without .sta) |                       | 11     | 0       | 2026-10-09 11:06 |
| `pos_031_W4_QS` | A        | W4    | QS   |          | NLGEOM, N2S 0.2 | open (odb without .sta) |                       |        | 0       |                  |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei           | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001_W4_QS` | LOAD_16NM | -0.42 %  | 88.6       | 96.0           | T5 RIGHT, r 25.90, z -7.5 | 61.7       | T3_T4, r 24.78, z +4.5, Tangente 63° | -68.0      | T4_T5      | 100.2   | T4   |

Nicht gerechnet: 6 Dateien (`pos_066_W2_QS`, `pos_066_W4_QS`, `pos_103_W2_QS`, `pos_103_W4_QS`, `pos_133_W2_QS`, `pos_133_W4_QS`).

## 2026-10-09 11:13 `pilot_20layers_bore33_w2w4_qs_V2`

**Zweck:** Pilot der nichtlinearen Werkstoffstufen W2 (isotrop elastisch-plastisch) und W4 (Orientierungsdatei mit Plastizität), Rate QS als nachgiebigster Fall, NLGEOM=YES, C3D8, Ringkörper Bohrung 33: fünf Stellungen des 60er-Gitters (Rand −0,5 Teilung, A, C, E, Rand +0,5 Teilung), um die Verformung und die Eingriffsverlängerung gegen W1 zu messen, bevor Schrittweite und Rand des Batches festgelegt werden (Nutzer 2026-10-09: 20 je Teilung reicht für W1, für die nichtlinearen Stufen offen). V2 = Stand nach dem W2-Fix; die erste Fassung ohne Orientierung am W2-Section ist in pilot_20layers_bore33_w2w4_qs_gerechnet gerechnet (Vorlage). **Ergebnis:** Vorlage; Kontaktdurchsetzung wie in der Studie (Voreinstellung), bis die Wiederholungsläufe die Abhilfe gegen das Flattern entschieden haben; gegenüber V1 nur der W2-Section mit *ORIENTATION, die W4-Decks bis auf die Kopfzeile unverändert; gerechnet in pilot_20layers_bore33_w2w4_qs_V2_gerechnet.

Netz: 82425 Knoten, 72320 Elemente (C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W2, W4, Raten QS; Momente am Rad 8, 12, 16 Nm; 10 Stellungsdateien (grid, 60 je Teilung)

Nicht gerechnet: 10 Dateien (`pos_001_W2_QS`, `pos_001_W4_QS`, `pos_031_W2_QS`, `pos_031_W4_QS`, `pos_066_W2_QS`, `pos_066_W4_QS` …).

## 2026-10-09 11:41 `study_20layers_bore33_60perpitch_retry_iter100_gerechnet`

**Zweck:** Iterationsgrenzen I_0/I_R/I_C = 20/30/100: Kontrolle pos_002 und die abgebrochene pos_003, vom Nutzer nach pos_003 gestoppt (2026-10-09). **Ergebnis:** Hilft nur teilweise: die Inkremente 8 bis 10 des 16-Nm-Schritts, die mit 16 Iterationen zurückgeschnitten wurden, konvergieren jetzt nach 50, 51 und 40 Iterationen; Inkrement 13 (Schrittzeit 0,206, 12,8 Nm, dieselbe Stelle wie in der Studie) divergiert aber: der Penetrationsfehler des Knotens 7293 (rechte Flanke T5, r 25,901, z −6,75) wechselt je Iteration das Vorzeichen und wächst um 4 % je Iteration (2,5e-8 → 5,6e-8 mm in 20 Iterationen), bei Inkrementgrößen 1e-5 bis 1e-6 gleich; Abaqus meldet 'THE SOLUTION APPEARS TO BE DIVERGING', 20 min, 1 322 s. Also eine echte Instabilität der Newton-Iteration des harten Knoten-zu-Fläche-Kontakts an der facettierten Kopfkante, kein Iterationsbudget. Kontrolle pos_002 (186 s) ziffernidentisch mit der Studie, wie erwartet. Nächste physikneutrale Hebel: Line Search N_ls = 5 (dämpft oszillierende Newton-Korrekturen) und der Versatz der Stellung um 0,01 mm; darüber hinaus nur mit Eingriff in Kontaktgesetz (weiches Kontaktgesetz) oder Geometrie (Rundung größer als der Knotenreihenabstand 0,1 mm). (gerechnet: Vollversion; Befunde FE-14, FE-19)

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 4 Stellungsdateien (grid, 60 je Teilung)

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status                        | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|-------------------------------|-----------------------|--------|---------|------------------|
| `pos_002` | ρ1 6.359 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 186    | 0       | 2026-10-09 11:18 |
| `pos_003` | ρ1 6.408 | W1    | QS   |          | linear, N2S 0.2 | not completed (step 4 inc 13) | 6, 6, 6, 22           | 1315   | 370     | 2026-10-09 11:41 |
| `pos_044` | ρ1 8.376 | W1    | QS   |          | linear, N2S 0.2 | open (step 1 inc 2)           | 2                     |        | 0       | 2026-10-09 11:41 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_002` | LOAD_16NM | -0.26 %  | 76.9       | 116.5          | T5 RIGHT, r 25.90, z -6.8 | 76.5       | T3_T4, r 24.83, z +0.0, Tangente 45° | -89.8      | T4_T5      | 92.0    | T4   |
| `pos_003` | LOAD_12NM | -0.21 %  | 64.3       | 70.9           | T5 RIGHT, r 25.90, z -6.8 | 64.2       | T3_T4, r 24.83, z -3.8, Tangente 45° | -76.1      | T4_T5      | 76.8    | T4   |

Nicht gerechnet: 1 Dateien (`pos_045`).

## 2026-10-09 11:50 `study_20layers_bore33_60perpitch_retry_ls5_iter100`

**Zweck:** Vierte Abhilfe: Line Search N_ls = 5 (*CONTROLS, PARAMETERS=LINE SEARCH) zusammen mit den Iterationsgrenzen 20/30/100, gegen die mit 4 % je Iteration wachsende Oszillation des Flankenknotens an der Ritzelkopfkante (iter100-Lauf); Stellungen 2 (Kontrolle), 3, 44, 45, scharfe Kante, Lagrange (Vorlage, 2026-10-09). **Ergebnis:** Vorlage; Decks identisch mit der Studie bis auf die CONTROLS-Zeilen je Schritt; falls auch das nicht trägt, bleibt physikneutral nur der Versatz der Stellung (`decks --shift-mm`, 0,01 mm), sonst Kontaktgesetz oder Geometrie.

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 4 Stellungsdateien (grid, 60 je Teilung)

Nicht gerechnet: 4 Dateien (`pos_002`, `pos_003`, `pos_044`, `pos_045`).

## 2026-10-09 13:24 `pilot_20layers_bore33_w2w4_qs_V2_gerechnet`

**Zweck:** Nichtlinearer Pilot W2 und W4 (Rate QS, NLGEOM=YES, C3D8, Ringkörper Bohrung 33) an den fünf Stellungen Rand −0,5 Teilung (1), A (31), C (66), E (103), Rand +0,5 Teilung (133), gerechnet 2026-10-09 11:45 bis 13:24. **Ergebnis:** 9 von 10 durch: W2 in 212 bis 273 s (wie W1), W4 in 524 bis 652 s; pos_133_W4 bricht bei 16 Nm, Schrittzeit 0,856 (15,4 Nm) nach 37 min ab, Knoten 5742 (rechte Flanke T3, r 26,002, z −6,75): die Ritzelkopfkante 1,46 mm hinter E auf der vierten Knotenreihe, Penetrationsfehler monoton abklingend (Faktor 0,94 je Iteration), also die langsam konvergierende Art von FE-19, die die Iterationsgrenzen abfangen. Gegen W1 (Studie) bei 16 Nm: Ritzeldrehung W2/W4 +13 bis +27 % (C 84,0 → 94,8/95,5 µm, A 67,6 → 85,6/85,2, E 67,7 → 84,3/85,1), bei 8 Nm +6 bis +11 %; W2 und W4 in der Steifigkeit innerhalb 2 %. Fußspannung σ1 max bei C 16 Nm: W1 82,9, W2 48,9 (−41 %, Fließkurve bei 80 °C beginnt bei 4,3 MPa, die Spannung ist durch die Fließkurve begrenzt), W4 65,2 MPa (−21 %); mit W4 liegt das σ1-Maximum bei z +6 bis +6,75 mm statt in der Breitenmitte (Faserorientierung macht die Fußspannung über der Breite unsymmetrisch). Kantendruck des Ritzelkopfs an E: W1 159,6, W2 93,0, W4 94,0 MPa (−41 %). Lastaufteilung: der einlaufende Zahn trägt früher (pos_001 T3: 34,5 → 66/68 N), der auslaufende länger (pos_133 T3 1,46 mm hinter E: 8,3 → 54/52 N): die Ränder ±0,5 Teilung reichen für W2/W4 nicht (FE-21). Orientierungsprüfung W4 an SEAT 0,002°. (gerechnet: Vollversion; Befunde FE-03, FE-17, FE-19, FE-21)

Netz: 82425 Knoten, 72320 Elemente (C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W2, W4, Raten QS; Momente am Rad 8, 12, 16 Nm; 10 Stellungsdateien (grid, 60 je Teilung)

**Läufe**

| Datei           | Stellung  | Stufe | Rate | Variante | Löser           | Status                        | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------------|-----------|-------|------|----------|-----------------|-------------------------------|-----------------------|--------|---------|------------------|
| `pos_001_W2_QS` | ρ1 6.310  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 212    | 0       | 2026-10-09 11:48 |
| `pos_001_W4_QS` | ρ1 6.310  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 564    | 0       | 2026-10-09 11:58 |
| `pos_031_W2_QS` | A         | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 210    | 0       | 2026-10-09 12:02 |
| `pos_031_W4_QS` | A         | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 524    | 0       | 2026-10-09 12:11 |
| `pos_066_W2_QS` | C         | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 227    | 0       | 2026-10-09 12:15 |
| `pos_066_W4_QS` | C         | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 604    | 0       | 2026-10-09 12:25 |
| `pos_103_W2_QS` | E         | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 273    | 0       | 2026-10-09 12:30 |
| `pos_103_W4_QS` | E         | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 652    | 0       | 2026-10-09 12:42 |
| `pos_133_W2_QS` | ρ1 12.657 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 231    | 0       | 2026-10-09 12:46 |
| `pos_133_W4_QS` | ρ1 12.657 | W4    | QS   |          | NLGEOM, N2S 0.2 | not completed (step 4 inc 18) | 6, 6, 6, 29           | 2251   | 17      | 2026-10-09 13:24 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei           | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001_W2_QS` | LOAD_16NM | -0.36 %  | 88.1       | 93.2           | T5 RIGHT, r 25.90, z -6.0 | 48.5       | T3_T4, r 24.79, z -4.5, Tangente 58° | -56.0      | T4_T5      | 104.5   | T4   |
| `pos_001_W4_QS` | LOAD_16NM | -0.42 %  | 88.6       | 96.0           | T5 RIGHT, r 25.90, z -7.5 | 61.7       | T3_T4, r 24.78, z +4.5, Tangente 63° | -68.0      | T4_T5      | 100.2   | T4   |
| `pos_031_W2_QS` | LOAD_16NM | -0.24 %  | 85.6       | 84.7           | T4 RIGHT, r 25.70, z -6.0 | 44.6       | T3_T4, r 24.82, z -6.0, Tangente 49° | -54.5      | T4_T5      | 96.4    | T3   |
| `pos_031_W4_QS` | LOAD_16NM | -0.21 %  | 85.2       | 88.8           | T4 RIGHT, r 25.70, z +7.5 | 57.3       | T3_T4, r 24.88, z +6.8, Tangente 33° | -69.9      | T4_T5      | 94.2    | T3   |
| `pos_066_W2_QS` | LOAD_16NM | -1.21 %  | 94.8       | 73.1           | T4 RIGHT, r 26.00, z -6.0 | 48.9       | T2_T3, r 24.88, z +0.0, Tangente 33° | -55.6      | T3_T4      | 110.8   | T3   |
| `pos_066_W4_QS` | LOAD_16NM | -1.21 %  | 95.5       | 78.3           | T4 RIGHT, r 26.00, z -7.5 | 65.2       | T2_T3, r 24.78, z +6.0, Tangente 63° | -71.9      | T3_T4      | 108.2   | T3   |
| `pos_103_W2_QS` | LOAD_16NM | +0.14 %  | 84.3       | 93.0           | T3 RIGHT, r 25.70, z -6.0 | 44.7       | T1_T2, r 24.86, z -4.5, Tangente 37° | -51.2      | T3_T4      | 97.2    | T2   |
| `pos_103_W4_QS` | LOAD_16NM | +0.19 %  | 85.1       | 94.0           | T3 RIGHT, r 25.70, z +6.8 | 57.8       | T1_T2, r 24.78, z +5.2, Tangente 63° | -65.3      | T3_T4      | 96.0    | T2   |
| `pos_133_W2_QS` | LOAD_16NM | -1.60 %  | 91.5       | 63.2           | T1 RIGHT, r 26.89, z +0.0 | 51.1       | T1_T2, r 24.90, z +0.0, Tangente 30° | -58.2      | T2_T3      | 106.1   | T2   |
| `pos_133_W4_QS` | LOAD_12NM | -1.89 %  | 76.0       | 55.0           | T1 RIGHT, r 26.89, z +0.8 | 56.1       | T1_T2, r 24.79, z -6.8, Tangente 58° | -68.2      | T2_T3      | 85.0    | T2   |

## 2026-10-09 13:35 `pilot_20layers_bore33_w4_qs_margin`

**Zweck:** Randpilot W4 QS: Stellungen bei −1,0 und −0,75 Teilung vor A und +0,75 und +1,0 Teilung hinter E (Gitter 60 je Teilung mit Rand 1,0 Teilung, Indizes 1, 16, 178, 193), um den Beginn und das Ende des verlängerten Eingriffs der nachgiebigsten Stufe zu finden und daraus den Rand des Batches; mit den Iterationsgrenzen 20/30/100, weil die Kopfkante bei W4 hinter E auf weitere Knotenreihen trifft (pos_133_W4 des nichtlinearen Piloten) und dort die langsam konvergierende Art des Flatterns auftritt (Vorlage, 2026-10-09; die erste Fassung ohne Grenzen wurde nie gerechnet und ist ersetzt). **Ergebnis:** Vorlage.

Netz: 82425 Knoten, 72320 Elemente (C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W4, Raten QS; Momente am Rad 8, 12, 16 Nm; 4 Stellungsdateien (grid, 60 je Teilung)

Nicht gerechnet: 4 Dateien (`pos_001`, `pos_016`, `pos_178`, `pos_193`).

## 2026-10-09 13:35 `pilot_20layers_bore33_w4_qs_pos133_iter100`

**Zweck:** Wiederholung der abgebrochenen pos_133_W4 des nichtlinearen Piloten mit den Iterationsgrenzen 20/30/100 (eine Datei): prüft, ob die Grenzen die langsam konvergierende Art abfangen (Vorlage, 2026-10-09). **Ergebnis:** Vorlage.

Netz: 82425 Knoten, 72320 Elemente (C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W4, Raten QS; Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien (grid, 60 je Teilung)

Nicht gerechnet: 1 Dateien (`pos_133`).

