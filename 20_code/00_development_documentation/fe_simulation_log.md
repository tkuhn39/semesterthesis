# Simulationstagebuch (generiert)

Stand 2026-10-08 06:32; Quelle `C:/GitHub-tkuhn39/semesterthesis/80_output/fe/kst_e`; Notizen `fe_simulation_notes.yaml`; erzeugt von `build_fe_decks.py log`. Ein Abschnitt je Ordner in der Reihenfolge der letzten Bearbeitung, mit Zweck und Ergebnis aus den Notizen, Netz und Einstellungen aus `manifest.json`, dann zwei Tabellen: **Läufe** je Stellungsdatei mit Status aus `.sta` (complete, not completed mit dem letzten geschriebenen Inkrement, open = ohne Schlusszeile: läuft oder abgestürzt), Inkrementen je Schritt, Rechenzeit (Wanduhr aus `run_log.txt`, sonst aus der Zeitbilanz der `.dat`), Warnungen negativer Eigenwerte aus `.msg` und Endzeit; **Kennwerte** des letzten gedruckten Lastschritts aus `<job>_fields.json` (RM3-Abweichung gegen z_2/z_1·T_1, Drehung des Ritzels am Grundkreis in µm, größter Kontaktdruck mit Zahnhälfte und Ort, größte Fußspannung σ1 mit Fußrundung, Ort und Tangentenwinkel zur Zahnmittellinie, kleinste σ3 mit Fußrundung, größte Kopfverschiebung mit Zahn), für Läufe ohne Felddatei aus der `.dat` (Moment, Drehung, Druck ohne Ort). Löser: linear oder NLGEOM, N2S = Knoten-zu-Fläche mit SMOOTH, S2S = Fläche-zu-Fläche, DIRECT/PENALTY = Zwangsbedingung, LS = Line Search.

Läufe: 66 vollständig, 11 abgebrochen, 1 offen, 183 Dateien nicht gerechnet; 38 Ordner.

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

**Zweck:** Pilot mit der Regel je Werkstoffstufe (W1 linear C3D8I, Knoten-zu-Fläche), 20 Schichten, Bohrung 18,10 (Vorlage). **Ergebnis:** Vorlage.

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

**Zweck:** Eingefrorenes Netz des Ringkörpers (20 Schichten, Bohrung 33 mm) für das CONVERSE-Mapping; Stellung C, W1. **Ergebnis:** Mapping des Nutzers erzeugt (91_Converse/wheel_mesh_QS/DY1/DY2.cof); der Ringkörper-Pilot an C auf diesem Netz ist noch nicht gerechnet (Vergleich zum Taschenkörper).

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

**Zweck:** Auflösungsstudie der Stellungen: 133 Stellungen, 60 je Teilung, W1, 20 Schichten; Teilgitter 60/30/20/15/12/10. **Ergebnis:** läuft auf der Vollversion seit 2026-10-07 (etwa 6,5 h); liefert die Stellungen je Teilung und den Rand des Batches. **Stand:** läuft. (gerechnet: Vollversion)

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

**Zweck:** Taschenkörper an C, W1, linear, C3D8I, Knoten-zu-Fläche: erster Lauf des Radkörpers nach Zeichnung. **Ergebnis:** 215 s, alle Schritte, keine negativen Eigenwerte; Stützmoment −1,2 bis −1,0 % (Δψ, FE-15), Kopfverschiebung 77,5 / 95,9 / 114,2 µm; Vergleich zum Ringkörper mit derselben Bohrung steht aus. (gerechnet: Vollversion; Befunde FE-15, FE-18)

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

