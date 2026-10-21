# Simulationstagebuch (generiert)

Stand 2026-10-19 18:45; Quelle `C:/GitHub-tkuhn39/semesterthesis/80_output/fe/kst_e`; Notizen `fe_simulation_notes.yaml`; erzeugt von `build_fe_decks.py log`. Ein Abschnitt je Ordner in der Reihenfolge der letzten Bearbeitung, mit Zweck und Ergebnis aus den Notizen, Netz und Einstellungen aus `manifest.json`, dann zwei Tabellen: **Läufe** je Stellungsdatei mit Status aus `.sta` (complete, not completed mit dem letzten geschriebenen Inkrement, open = ohne Schlusszeile: läuft oder abgestürzt), Inkrementen je Schritt, Rechenzeit (Wanduhr aus `run_log.txt`, sonst aus der Zeitbilanz der `.dat`), Warnungen negativer Eigenwerte aus `.msg` und Endzeit; **Kennwerte** des letzten gedruckten Lastschritts aus `<job>_fields.json` (RM3-Abweichung gegen z_2/z_1·T_1, Drehung des Ritzels am Grundkreis in µm, größter Kontaktdruck mit Zahnhälfte und Ort, größte Fußspannung σ1 mit Fußrundung, Ort und Tangentenwinkel zur Zahnmittellinie, kleinste σ3 mit Fußrundung, größte Kopfverschiebung mit Zahn), für Läufe ohne Felddatei aus der `.dat` (Moment, Drehung, Druck ohne Ort). Löser: linear oder NLGEOM, N2S = Knoten-zu-Fläche mit SMOOTH, S2S = Fläche-zu-Fläche, DIRECT/PENALTY = Zwangsbedingung, LS = Line Search.

Läufe: 1254 vollständig, 32 abgebrochen, 8 offen, 3705 Dateien nicht gerechnet; 129 Ordner.

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

**Zweck:** Vierte Abhilfe: Line Search N_ls = 5 (*CONTROLS, PARAMETERS=LINE SEARCH) zusammen mit den Iterationsgrenzen 20/30/100, gegen die mit 4 % je Iteration wachsende Oszillation des Flankenknotens an der Ritzelkopfkante (iter100-Lauf); Stellungen 2 (Kontrolle), 3, 44, 45, scharfe Kante, Lagrange (Vorlage, 2026-10-09). **Ergebnis:** Vorlage; Decks identisch mit der Studie bis auf die CONTROLS-Zeilen je Schritt; gerechnet in study_20layers_bore33_60perpitch_retry_ls5_iter100_gerechnet (nach pos_003 abgebrochen).

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

**Zweck:** Wiederholung der abgebrochenen pos_133_W4 des nichtlinearen Piloten mit den Iterationsgrenzen 20/30/100 (eine Datei): prüft, ob die Grenzen die langsam konvergierende Art abfangen (Vorlage, 2026-10-09). **Ergebnis:** Vorlage; gerechnet in pilot_20layers_bore33_w4_qs_pos133_iter100_gerechnet.

Netz: 82425 Knoten, 72320 Elemente (C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W4, Raten QS; Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien (grid, 60 je Teilung)

Nicht gerechnet: 1 Dateien (`pos_133`).

## 2026-10-09 14:07 `study_20layers_bore33_60perpitch_retry_ls5_iter100_gerechnet`

**Zweck:** Line Search N_ls = 5 mit den Iterationsgrenzen 20/30/100: Kontrolle pos_002 und die abgebrochene pos_003, vom Nutzer nach pos_003 gestoppt (2026-10-09). **Ergebnis:** Hilft nicht: pos_003 bricht exakt wie im iter100-Lauf ab (gleiche Inkremente, gleiche Iterationszahlen, Schrittzeit 0,206, 23 min); der Line Search greift in den letzten Attempts gar nicht (18 zusätzliche Residuenauswertungen im ganzen Lauf, keine in den divergierenden Iterationen), die Oszillation des Knotens 7293 wächst unverändert um 4 % je Iteration. Damit sind die löserseitigen, physikneutralen Hebel erschöpft (Penalty, Iterationsgrenzen, Line Search); die Abbruchstellen der Studie liegen paarweise nebeneinander (044/045, 055/056, 106/107, 117/118), das instabile Fenster ist also 0,05 bis 0,1 mm breit auf dem Wälzweg. Nächste Versuche: Versatz der Stellung um 0,025 mm (halber Schritt des 60er-Gitters, die Nachbarn 002 und 004 liefen) und, als Geometrieoption, Rundung 0,1 mm mit 12 Facetten je Bogen. (gerechnet: Vollversion; Befunde FE-14, FE-19)

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 4 Stellungsdateien (grid, 60 je Teilung)

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser               | Status                        | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|---------------------|-------------------------------|-----------------------|--------|---------|------------------|
| `pos_002` | ρ1 6.359 | W1    | QS   |          | linear, N2S 0.2, LS | complete                      | 6, 6, 6, 6            | 193    | 0       | 2026-10-09 13:34 |
| `pos_003` | ρ1 6.408 | W1    | QS   |          | linear, N2S 0.2, LS | not completed (step 4 inc 13) | 6, 6, 6, 22           | 1403   | 369     | 2026-10-09 13:58 |
| `pos_044` | ρ1 8.376 | W1    | QS   |          | linear, N2S 0.2, LS | open (step 3 inc 11)          | 6, 6, 16              |        | 66      | 2026-10-09 14:07 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                                         | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_002` | LOAD_16NM | -0.26 %  | 76.9       | 116.5          | T5 RIGHT, r 25.90, z -6.8                   | 76.5       | T3_T4, r 24.83, z +0.0, Tangente 45° | -89.8      | T4_T5      | 92.0    | T4   |
| `pos_003` | LOAD_12NM | -0.21 %  | 64.3       | 70.9           | T5 RIGHT, r 25.90, z -6.8                   | 64.2       | T3_T4, r 24.83, z -3.8, Tangente 45° | -76.1      | T4_T5      | 76.8    | T4   |
| `pos_044` | LOAD_8NM  | +0.32 %  | 35.0       | 98.1           | (105 geschlossene Knoten, Ort nur mit .odb) |            |                                      |            |            |         |      |

Nicht gerechnet: 1 Dateien (`pos_045`).

## 2026-10-09 14:18 `study_20layers_bore33_60perpitch_retry_shift0p025_iter100`

**Zweck:** Fünfte Abhilfe, ohne Änderung von Modell oder Löser: die Stellungen 2 (Kontrolle), 3, 44, 45 um 0,025 mm auf dem Wälzweg versetzt (halber Schritt des 60er-Gitters; die Nachbarn der Abbrüche liefen durch), mit den Iterationsgrenzen 20/30/100; die Dateien behalten ihre Nummern, das Manifest trägt den Versatz und den verschobenen Wälzweg (Vorlage, 2026-10-09). **Ergebnis:** Vorlage; gerechnet in study_20layers_bore33_60perpitch_retry_shift0p025_iter100_gerechnet.

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 4 Stellungsdateien (grid, 60 je Teilung)

Nicht gerechnet: 4 Dateien (`pos_002`, `pos_003`, `pos_044`, `pos_045`).

## 2026-10-09 14:18 `study_20layers_bore33_60perpitch_retry_round0p1_f12_iter100`

**Zweck:** Geometrieoption: Kopfkante des starren Ritzels auf 0,1 mm gerundet (eine Knotenreihe der Radflanke, Reihenabstand 0,1 mm) mit mindestens 12 Facetten je Bogen (Knicke rund 5° statt 12°), Iterationsgrenzen 20/30/100, Stellungen 2, 3, 44, 45 (Vorlage, 2026-10-09; der Nutzer nimmt die Rundung nur, wenn sie zum Unterbinden des Flatterns nötig ist, FE-17). **Ergebnis:** Vorlage; gerechnet in study_20layers_bore33_60perpitch_retry_round0p1_f12_iter100_gerechnet.

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 4 Stellungsdateien (grid, 60 je Teilung)

Nicht gerechnet: 4 Dateien (`pos_002`, `pos_003`, `pos_044`, `pos_045`).

## 2026-10-09 15:31 `pilot_20layers_bore33_w4_qs_pos133_iter100_gerechnet`

**Zweck:** pos_133 W4 QS mit den Iterationsgrenzen 20/30/100 (2026-10-09, 72 min). **Ergebnis:** Bricht wieder bei Schrittzeit 0,856 (15,4 Nm) ab, nur später: die Grenzen bringen die Inkremente 12 bis 15 nach 11 bis 40 Iterationen durch (Penetrationsfehler abklingend, Faktor 0,975), Inkrement 17 divergiert dann aber an demselben Knoten 5742 (rechte Flanke T3, r 26,002, z −6,75): in den Attempts mit 100 Iterationen wächst der Fehler von 1e-7 auf 8e-6 bzw. 8e-7 mm (Faktor 1,04 bis 1,19 je Iteration), bei dt 1,1e-5 bis 1e-6 gleich. Die Einstufung 'langsam konvergierend' aus dem 16-Iterationen-Lauf galt nur für die Attempts davor; am kritischen Zustand divergiert auch W4. Damit ist für beide Werkstoffstufen belegt, dass Iterationsbudget und Line Search die Kopfkanten-Instabilität nicht beheben; es bleiben Versatz der Stellung, Rundung größer als die Knotenreihe oder ein weiches Kontaktgesetz. (gerechnet: Vollversion; Befunde FE-19, FE-21)

Netz: 82425 Knoten, 72320 Elemente (C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W4, Raten QS; Momente am Rad 8, 12, 16 Nm; 1 Stellungsdateien (grid, 60 je Teilung)

**Läufe**

| Datei     | Stellung  | Stufe | Rate | Variante | Löser           | Status                        | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|-----------|-------|------|----------|-----------------|-------------------------------|-----------------------|--------|---------|------------------|
| `pos_133` | ρ1 12.657 | W4    | QS   |          | NLGEOM, N2S 0.2 | not completed (step 4 inc 17) | 6, 6, 6, 27           | 4329   | 32      | 2026-10-09 15:31 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_133` | LOAD_12NM | -1.89 %  | 76.0       | 55.0           | T1 RIGHT, r 26.89, z +0.8 | 56.1       | T1_T2, r 24.79, z -6.8, Tangente 58° | -68.2      | T2_T3      | 85.0    | T2   |

## 2026-10-09 16:12 `study_20layers_bore33_60perpitch_retry_round0p1_f12_iter100_gerechnet`

**Zweck:** Rundung 0,1 mm mit 12 Facetten je Bogen plus Iterationsgrenzen an den Stellungen 2, 3, 44, 45 (2026-10-09, 15:58 bis 16:13). **Ergebnis:** Numerisch die erste Variante, die alle vier Stellungen durchbringt: je 6 Inkremente je Schritt ohne Rückschnitt, 0 negative Eigenwerte, 197 bis 219 s. Physikalisch aber keine kleine Änderung: gegen die scharfe Kante (Studie) bei pos_002 Ritzeldrehung +9,7 / +7,9 / +6,8 % bei 8 / 12 / 16 Nm, Kopfverschiebung +10 / +8 / +7 %, σ1 am Fuß +10 / +7 / +6 %, |σ3| +12 / +10 / +8 %; die Kraft des auslaufenden Zahns T5 am Kantenkontakt −42 / −18 / −9 %, die des Hauptzahns T4 +12 / +9 / +8 %, der Kantendruck bei 16 Nm 116,5 → 72,1 MPa (das Maximum liegt dann am Hauptkontakt). pos_003 bei 8 Nm: Drehung +12 %, σ1 +13 %, T5 trägt gar nicht mehr. Die Rundung verkürzt also den verlängerten Eingriff am Ritzelkopf, verlagert Last vom auslaufenden auf den Hauptzahn und hebt Drehung und Fußspannung um 6 bis 13 % (an diesen Stellungen; über den ganzen Eingriff liegen die Maxima innerhalb 2,5 %, die Unterschiede bleiben im Fenster von 0,3 mm um B und E, Wochenendserie 2026-10-12): eine Modelländerung, kein numerischer Eingriff. Befund für die Arbeit: Drehung und Fußspannung des Kunststoffrads hängen mit rund 10 % je 0,1 mm am Kantenradius des Stahlritzels; der wirkliche Radius der Ritzelkante (Mikroskop) ist damit ein Eingangsparameter, nicht eine Numerikfrage. (gerechnet: Vollversion; Befunde FE-17, FE-19)

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 4 Stellungsdateien (grid, 60 je Teilung)

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_002` | ρ1 6.359 | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 199    | 0       | 2026-10-09 16:01 |
| `pos_003` | ρ1 6.408 | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 197    | 0       | 2026-10-09 16:04 |
| `pos_044` | ρ1 8.376 | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 219    | 0       | 2026-10-09 16:08 |
| `pos_045` | ρ1 8.425 | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 208    | 0       | 2026-10-09 16:12 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_002` | LOAD_16NM | +0.89 %  | 82.1       | 72.1           | T4 RIGHT, r 26.10, z -6.8 | 81.2       | T3_T4, r 24.83, z +0.0, Tangente 45° | -97.1      | T4_T5      | 98.4    | T4   |
| `pos_003` | LOAD_16NM | -0.99 %  | 82.2       | 74.0           | T4 RIGHT, r 26.10, z +0.0 | 81.8       | T3_T4, r 24.83, z +0.0, Tangente 45° | -99.9      | T4_T5      | 98.2    | T4   |
| `pos_044` | LOAD_16NM | +0.62 %  | 72.2       | 180.1          | T4 RIGHT, r 25.80, z -6.8 | 63.1       | T2_T3, r 24.82, z -5.2, Tangente 49° | -77.3      | T4_T5      | 84.4    | T3   |
| `pos_045` | LOAD_16NM | +0.47 %  | 72.4       | 181.6          | T4 RIGHT, r 25.80, z -6.8 | 63.8       | T2_T3, r 24.82, z -5.2, Tangente 49° | -76.2      | T4_T5      | 84.7    | T3   |

## 2026-10-09 16:33 `study_20layers_bore33_60perpitch_retry_shift0p025_iter100_gerechnet`

**Zweck:** Stellungen 2, 3, 44, 45 um 0,025 mm versetzt, Iterationsgrenzen 20/30/100 (2026-10-09, 16:16 bis 16:33). **Ergebnis:** Alle vier 'COMPLETED', aber nur die Kontrolle pos_002 ist brauchbar (gegen die unversetzte Stellung: Drehung, Fußspannung, Kopfverschiebung innerhalb 0,5 bis 1 %, Kantendruck −4 bis −5 %, wie die Steigung der Kurven dort erwartet). pos_003 und pos_044 landen auf dem anderen Lösungsast des Knoten-zu-Fläche-Kontakts an der scharfen Kante: die Kontaktkraft ist um 8,9 / 5,5 / 3,6 ° (pos_003) und 12,9 / 8,3 / 5,8 ° (pos_044) gegen die Eingriffslinie gedreht, a_1/r_b1 nur 0,86 bis 0,97, das Stützmoment 3,2 bis 5,1 % über z_2/z_1·T_1, Summe der Zahnkräfte über der Zahnkraft: die Kantenknoten des auslaufenden Zahns liegen auf der Kopffacette der starren Fläche statt auf der Flankenfacette, die Kraft zeigt radial zum Ritzel statt entlang der Eingriffslinie. pos_045 verliert im 8-Nm-Schritt den Kontakt vollständig (0 geschlossene Knoten, RM3 = 0, Ritzel um 8,9 mrad verdreht), der Lauf 'konvergiert' mit leerem Kontakt. Der Versatz ist damit keine Rückfallebene: die Instabilität ist die Mehrdeutigkeit der Masternormalen an der scharfen Kante (Normalenkegel zwischen Flanken- und Kopffacette), und welchen Ast der Löser trifft, ist Zufall. Konsistent sind nur die Lösungen auf dem Flankenast (Kraft innerhalb 0,1 bis 3 ° der Eingriffslinie, Stützmoment innerhalb 1 %), wie in allen 122 durchgelaufenen Stellungen der Studie; die gerundete Kante (retry_round0p1_f12) hat eine stetige Normale und damit genau einen Ast. (gerechnet: Vollversion; Befunde FE-15, FE-17, FE-19)

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 4 Stellungsdateien (grid, 60 je Teilung)

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_002` | ρ1 6.384 | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 194    | 0       | 2026-10-09 16:19 |
| `pos_003` | ρ1 6.433 | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 200    | 5       | 2026-10-09 16:23 |
| `pos_044` | ρ1 8.401 | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 8, 6, 6            | 406    | 67      | 2026-10-09 16:30 |
| `pos_045` | ρ1 8.450 | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 160    | 2       | 2026-10-09 16:33 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw.  | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|-----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_002` | LOAD_16NM | -0.35 %   | 76.6       | 112.1          | T5 RIGHT, r 25.90, z -6.8 | 76.2       | T3_T4, r 24.83, z +0.0, Tangente 45° | -89.7      | T4_T5      | 91.6    | T4   |
| `pos_003` | LOAD_16NM | +0.45 %   | 82.2       | 74.1           | T4 RIGHT, r 26.10, z -6.8 | 81.3       | T3_T4, r 24.83, z +0.0, Tangente 45° | -98.8      | T4_T5      | 98.1    | T4   |
| `pos_044` | LOAD_16NM | +2.40 %   | 72.8       | 178.2          | T4 RIGHT, r 25.80, z -6.8 | 62.9       | T2_T3, r 24.82, z -5.2, Tangente 49° | -78.0      | T4_T5      | 85.0    | T3   |
| `pos_045` | LOAD_16NM | -100.00 % | 213.2      |                |                           | 0.0        | T3_T4, r 25.06, z -0.8, Tangente 12° | -0.0       | T3_T4      | 0.0     | T3   |

## 2026-10-09 17:35 `series_20layers_bore33_round0p1f12_30perpitch_margin1_qs`

**Zweck:** Wochenendserie (Nutzer 2026-10-09, ein Ordner für einen unbeaufsichtigten Lauf von rund 60 h): Ringkörper Bohrung 33, Kopfkante des starren Ritzels 0,1 mm mit 12 Facetten je Bogen (kleinste Kante, die das Netz ohne Instabilität verträgt, FE-19; die gemessene Kante kommt nächste Woche), 30 Stellungen je Teilung von 1,0 Teilung vor A bis 1,0 Teilung hinter E (99 Stellungen; der Rand zeigt selbst, wo die Randzähne kraftfrei werden, FE-21), alle vier Werkstoffstufen W1 bis W4 bei Rate QS, Iterationsgrenzen 20/30/100; 396 Dateien, erwartet rund 22 min je Stellung (W1/W2/W3 je 4 min, W4 10 min), 38 h plus Extraktion, ODBs rund 120 GB. **Ergebnis:** Vorlage; gerechnet in series_20layers_bore33_round0p1f12_30perpitch_margin1_qs_gerechnet (2026-10-09 17:45 bis 2026-10-11 22:26, 50 h Rechenzeit, 395 von 396 Jobs).

Netz: 82425 Knoten, 72320 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, W2, W3, W4, Raten QS; Momente am Rad 8, 12, 16 Nm; 396 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 396 Dateien (`pos_001_W1_QS`, `pos_001_W2_QS`, `pos_001_W3_QS`, `pos_001_W4_QS`, `pos_002_W1_QS`, `pos_002_W2_QS` …).

## 2026-10-11 22:25 `series_20layers_bore33_round0p1f12_30perpitch_margin1_qs_gerechnet`

**Zweck:** Die Wochenendserie, gerechnet auf der Vollversion (2026-10-09 17:45 bis 2026-10-11 22:26, 50,0 h; W1 3,8, W2 5,0, W3 8,7, W4 12,6 min je Stellung im Mittel; 140 GB mit ODBs, am 2026-10-12 lokal eingetroffen); Felder und Spannungstensoren mit dem neuen extract_odb.py nachgezogen (Learning-Edition-Python, 2026-10-12), Auswertung mit `build_fe_decks.py report` und `fe_series_analysis.py` (Ordner analyse/) sowie `fe_fatigue.py stommel` je Serie. **Ergebnis:** 395 von 396 Jobs vollständig; pos_073_W1_QS bricht bei 16 Nm (Schrittzeit 0,931, Stellung 3,84 mm ab A, 0,43 mm hinter E) mit dem Muster FE-19 ab (flatternde Flankenknoten 29294, 25369, 52844 bei r 25,80 mm, z −3,0 bis +2,25 mm), die Rundung 0,1 mm senkt die Abbruchrate von 11/133 (scharf, W1) auf 1/396. Verlängerter Eingriff des mittleren Zahns: 0,47 bis 0,60 Teilungen vor A, 0,35 bis 0,48 Teilungen hinter E (mit Moment und Plastizität wachsend), der Rand 1,0 Teilung reicht (FE-21 geschlossen). Werkstoffstufen bei 16 Nm gegen W1: Anisotropie W1 → W3 hebt σ1 am Fuß um 18 % und |σ3| um 14 % bei 3 % mehr Drehung; Plastizität W1 → W2 senkt σ1 um 39 %, |σ3| um 43 % und den Kantendruck um 46 % bei 17 % mehr Drehung (Fließkurve 80 °C beginnt bei 4,3 MPa); W3 → W4 entsprechend −33 / −35 / −46 % bei +13 %; W4 gegen W2 (Anisotropie plastisch) +28 / +29 % Fußspannung bei gleicher Drehung. Scharf (Studie) gegen gerundet (Serie, W1) an 68 gemeinsamen Stellungen: Unterschiede nur im Fenster von rund 0,3 mm um B und E, wo die Ritzelkopfkante trägt (Drehung +5 bis +7 %, Kantendruck −8 bis −11 %, σ1 −5 bis −9 %), an A, C, D und bei den Maxima innerhalb 2,5 % (Kraft des Nebenzahns +4 bis +5 %); die früher berichteten 6 bis 13 % waren die Stellungen 2 und 3 in diesem Fenster. Auflösung: 15 je Teilung ändert die Maxima um höchstens 2,9 % (W3, 16 Nm) und versetzt sie um höchstens 0,21 mm, 10 je Teilung bis 5,5 %, 6 je Teilung bis 15 %; die Wahl 30 je Teilung hält jedes Maximum innerhalb 1 %. Bemessung nach Stommel je Serie (99 Stellungen, Überlastungsfall F2, synthetische Wöhlerlinie, Fußrundungen des mittleren Zahns T3; Ordner stommel_<Serie>, stommel_hill_<Serie>): W1 wie veröffentlicht a_B,V 1,63 / 2,03 / 4,47 bei 8 / 12 / 16 Nm (N 3,9e3 / 0 / 0), W2 1,24 / 1,47 / 1,74 (N 3,5e5 / 2,2e4 / 1,7e3; a_stat 0,48 bis 0,73, statisch frei), W3 mit Hill 3,1 / 3,9 / 10,4 (a_stat ∞), W4 mit Hill 2,16 / 2,58 / 3,03 (a_stat 0,44 bis 0,73), W1 mit Hill 3,1 / 4,0 / 16,6. Kritischer Knoten in der Fußrundung T3_T4 (Druckseite, R < 0 durch den Nachbarzahn), bei W1 und W2 nahe der Stirnfläche (z −6,0 bis −6,75), bei W4 bei z −3,0 (Faserorientierung); die globalen Maxima liegen an Kopfknoten des Kantenkontakts (r 25,80) und unter Hill in der ersten Knotenreihe unter dieser Spur (r 25,78, in keinem Knotensatz, daher in den Tabellen mit dem Restlabel „rim“ bezeichnet, nicht die Fesselung, deren Satz am Fußkreis r 24,76 endet; geprüft 2026-10-13 an den Knotenkoordinaten), deshalb die Fußrundungen (FE-22). Der kritische Fußknoten sitzt 0,015 mm über dem Fußkreis am Übergang zur Fußfläche (r 24,775 der Zone 24,76 bis 25,08). Gegen den Laufversuch (8 Nm: Totalausfall bei 24 Mio., zweiter Lauf über 40 Mio.) unterschätzt die synthetische Linie mit W2 um rund 70×, W1 und Hill um Größenordnungen; E8 (Kalibrierung am kritischen Knoten mit der gemessenen Wöhlerlinie) ist der nächste Schritt. (gerechnet: Vollversion; Befunde FE-15, FE-17, FE-19, FE-21)

Netz: 82425 Knoten, 72320 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, W2, W3, W4, Raten QS; Momente am Rad 8, 12, 16 Nm; 396 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei           | Stellung  | Stufe | Rate | Variante | Löser           | Status                        | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------------|-----------|-------|------|----------|-----------------|-------------------------------|-----------------------|--------|---------|------------------|
| `pos_001_W1_QS` | ρ1 4.833  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 183    | 0       | 2026-10-09 17:48 |
| `pos_001_W2_QS` | ρ1 4.833  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 263    | 0       | 2026-10-09 17:53 |
| `pos_001_W3_QS` | ρ1 4.833  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 417    | 0       | 2026-10-09 18:00 |
| `pos_001_W4_QS` | ρ1 4.833  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 520    | 0       | 2026-10-09 18:09 |
| `pos_002_W1_QS` | ρ1 4.932  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 204    | 0       | 2026-10-09 18:13 |
| `pos_002_W2_QS` | ρ1 4.932  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 259    | 0       | 2026-10-09 18:17 |
| `pos_002_W3_QS` | ρ1 4.932  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 489    | 0       | 2026-10-09 18:26 |
| `pos_002_W4_QS` | ρ1 4.932  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 652    | 0       | 2026-10-09 18:37 |
| `pos_003_W1_QS` | ρ1 5.030  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 229    | 0       | 2026-10-09 18:41 |
| `pos_003_W2_QS` | ρ1 5.030  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 263    | 0       | 2026-10-09 18:46 |
| `pos_003_W3_QS` | ρ1 5.030  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 484    | 0       | 2026-10-09 18:55 |
| `pos_003_W4_QS` | ρ1 5.030  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 650    | 0       | 2026-10-09 19:06 |
| `pos_004_W1_QS` | ρ1 5.129  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 236    | 0       | 2026-10-09 19:10 |
| `pos_004_W2_QS` | ρ1 5.129  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 277    | 0       | 2026-10-09 19:15 |
| `pos_004_W3_QS` | ρ1 5.129  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 534    | 0       | 2026-10-09 19:24 |
| `pos_004_W4_QS` | ρ1 5.129  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 678    | 0       | 2026-10-09 19:36 |
| `pos_005_W1_QS` | ρ1 5.227  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 250    | 0       | 2026-10-09 19:41 |
| `pos_005_W2_QS` | ρ1 5.227  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 295    | 0       | 2026-10-09 19:46 |
| `pos_005_W3_QS` | ρ1 5.227  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 536    | 0       | 2026-10-09 19:55 |
| `pos_005_W4_QS` | ρ1 5.227  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 8            | 739    | 3       | 2026-10-09 20:08 |
| `pos_006_W1_QS` | ρ1 5.325  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 251    | 0       | 2026-10-09 20:13 |
| `pos_006_W2_QS` | ρ1 5.325  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 297    | 0       | 2026-10-09 20:18 |
| `pos_006_W3_QS` | ρ1 5.325  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 544    | 0       | 2026-10-09 20:27 |
| `pos_006_W4_QS` | ρ1 5.325  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 10           | 903    | 7       | 2026-10-09 20:43 |
| `pos_007_W1_QS` | ρ1 5.424  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 248    | 0       | 2026-10-09 20:47 |
| `pos_007_W2_QS` | ρ1 5.424  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 269    | 0       | 2026-10-09 20:52 |
| `pos_007_W3_QS` | ρ1 5.424  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 554    | 0       | 2026-10-09 21:02 |
| `pos_007_W4_QS` | ρ1 5.424  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 696    | 0       | 2026-10-09 21:14 |
| `pos_008_W1_QS` | ρ1 5.522  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 243    | 0       | 2026-10-09 21:18 |
| `pos_008_W2_QS` | ρ1 5.522  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 296    | 0       | 2026-10-09 21:24 |
| `pos_008_W3_QS` | ρ1 5.522  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 426    | 0       | 2026-10-09 21:31 |
| `pos_008_W4_QS` | ρ1 5.522  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 674    | 0       | 2026-10-09 21:43 |
| `pos_009_W1_QS` | ρ1 5.621  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 217    | 0       | 2026-10-09 21:47 |
| `pos_009_W2_QS` | ρ1 5.621  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 286    | 0       | 2026-10-09 21:52 |
| `pos_009_W3_QS` | ρ1 5.621  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 493    | 0       | 2026-10-09 22:00 |
| `pos_009_W4_QS` | ρ1 5.621  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 687    | 0       | 2026-10-09 22:12 |
| `pos_010_W1_QS` | ρ1 5.719  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 236    | 0       | 2026-10-09 22:17 |
| `pos_010_W2_QS` | ρ1 5.719  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 9            | 304    | 3       | 2026-10-09 22:22 |
| `pos_010_W3_QS` | ρ1 5.719  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 11           | 795    | 22      | 2026-10-09 22:36 |
| `pos_010_W4_QS` | ρ1 5.719  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 8, 6, 8            | 925    | 14      | 2026-10-09 22:52 |
| `pos_011_W1_QS` | ρ1 5.817  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 255    | 0       | 2026-10-09 22:56 |
| `pos_011_W2_QS` | ρ1 5.817  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 8, 9, 11           | 483    | 24      | 2026-10-09 23:05 |
| `pos_011_W3_QS` | ρ1 5.817  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 570    | 0       | 2026-10-09 23:15 |
| `pos_011_W4_QS` | ρ1 5.817  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 10, 8, 7           | 974    | 5       | 2026-10-09 23:31 |
| `pos_012_W1_QS` | ρ1 5.916  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 258    | 0       | 2026-10-09 23:36 |
| `pos_012_W2_QS` | ρ1 5.916  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 9, 8            | 393    | 8       | 2026-10-09 23:43 |
| `pos_012_W3_QS` | ρ1 5.916  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 572    | 0       | 2026-10-09 23:53 |
| `pos_012_W4_QS` | ρ1 5.916  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 10, 12          | 1173   | 6       | 2026-10-10 00:13 |
| `pos_013_W1_QS` | ρ1 6.014  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 221    | 0       | 2026-10-10 00:17 |
| `pos_013_W2_QS` | ρ1 6.014  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 313    | 0       | 2026-10-10 00:23 |
| `pos_013_W3_QS` | ρ1 6.014  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 466    | 0       | 2026-10-10 00:31 |
| `pos_013_W4_QS` | ρ1 6.014  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 737    | 0       | 2026-10-10 00:43 |
| `pos_014_W1_QS` | ρ1 6.113  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 235    | 0       | 2026-10-10 00:48 |
| `pos_014_W2_QS` | ρ1 6.113  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 281    | 0       | 2026-10-10 00:53 |
| `pos_014_W3_QS` | ρ1 6.113  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 475    | 0       | 2026-10-10 01:01 |
| `pos_014_W4_QS` | ρ1 6.113  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 736    | 0       | 2026-10-10 01:14 |
| `pos_015_W1_QS` | ρ1 6.211  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 8            | 247    | 2       | 2026-10-10 01:18 |
| `pos_015_W2_QS` | ρ1 6.211  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 8, 6            | 300    | 4       | 2026-10-10 01:24 |
| `pos_015_W3_QS` | ρ1 6.211  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 11           | 879    | 14      | 2026-10-10 01:39 |
| `pos_015_W4_QS` | ρ1 6.211  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 13, 6           | 930    | 7       | 2026-10-10 01:55 |
| `pos_016_W1_QS` | ρ1 6.310  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 266    | 0       | 2026-10-10 02:00 |
| `pos_016_W2_QS` | ρ1 6.310  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 8, 6, 6            | 319    | 4       | 2026-10-10 02:05 |
| `pos_016_W3_QS` | ρ1 6.310  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 550    | 0       | 2026-10-10 02:15 |
| `pos_016_W4_QS` | ρ1 6.310  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 701    | 0       | 2026-10-10 02:27 |
| `pos_017_W1_QS` | ρ1 6.408  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 226    | 0       | 2026-10-10 02:31 |
| `pos_017_W2_QS` | ρ1 6.408  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 271    | 0       | 2026-10-10 02:36 |
| `pos_017_W3_QS` | ρ1 6.408  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 490    | 0       | 2026-10-10 02:45 |
| `pos_017_W4_QS` | ρ1 6.408  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 678    | 0       | 2026-10-10 02:56 |
| `pos_018_W1_QS` | ρ1 6.506  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 228    | 0       | 2026-10-10 03:01 |
| `pos_018_W2_QS` | ρ1 6.506  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 271    | 0       | 2026-10-10 03:06 |
| `pos_018_W3_QS` | ρ1 6.506  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 514    | 0       | 2026-10-10 03:15 |
| `pos_018_W4_QS` | ρ1 6.506  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 661    | 0       | 2026-10-10 03:26 |
| `pos_019_W1_QS` | ρ1 6.605  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 235    | 0       | 2026-10-10 03:30 |
| `pos_019_W2_QS` | ρ1 6.605  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 8, 6, 6            | 331    | 0       | 2026-10-10 03:36 |
| `pos_019_W3_QS` | ρ1 6.605  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 484    | 0       | 2026-10-10 03:45 |
| `pos_019_W4_QS` | ρ1 6.605  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 733    | 0       | 2026-10-10 03:57 |
| `pos_020_W1_QS` | ρ1 6.703  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 227    | 0       | 2026-10-10 04:02 |
| `pos_020_W2_QS` | ρ1 6.703  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 285    | 0       | 2026-10-10 04:07 |
| `pos_020_W3_QS` | ρ1 6.703  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 483    | 0       | 2026-10-10 04:15 |
| `pos_020_W4_QS` | ρ1 6.703  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 681    | 0       | 2026-10-10 04:27 |
| `pos_021_W1_QS` | ρ1 6.802  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 225    | 0       | 2026-10-10 04:31 |
| `pos_021_W2_QS` | ρ1 6.802  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 300    | 0       | 2026-10-10 04:37 |
| `pos_021_W3_QS` | ρ1 6.802  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 495    | 0       | 2026-10-10 04:45 |
| `pos_021_W4_QS` | ρ1 6.802  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 673    | 0       | 2026-10-10 04:57 |
| `pos_022_W1_QS` | ρ1 6.900  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 227    | 0       | 2026-10-10 05:01 |
| `pos_022_W2_QS` | ρ1 6.900  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 274    | 0       | 2026-10-10 05:06 |
| `pos_022_W3_QS` | ρ1 6.900  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 491    | 0       | 2026-10-10 05:15 |
| `pos_022_W4_QS` | ρ1 6.900  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 656    | 0       | 2026-10-10 05:26 |
| `pos_023_W1_QS` | ρ1 6.998  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 212    | 0       | 2026-10-10 05:30 |
| `pos_023_W2_QS` | ρ1 6.998  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 283    | 0       | 2026-10-10 05:35 |
| `pos_023_W3_QS` | ρ1 6.998  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 496    | 0       | 2026-10-10 05:44 |
| `pos_023_W4_QS` | ρ1 6.998  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 672    | 0       | 2026-10-10 05:55 |
| `pos_024_W1_QS` | ρ1 7.097  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 228    | 0       | 2026-10-10 06:00 |
| `pos_024_W2_QS` | ρ1 7.097  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 281    | 0       | 2026-10-10 06:05 |
| `pos_024_W3_QS` | ρ1 7.097  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 536    | 0       | 2026-10-10 06:14 |
| `pos_024_W4_QS` | ρ1 7.097  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 676    | 0       | 2026-10-10 06:26 |
| `pos_025_W1_QS` | ρ1 7.195  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 230    | 0       | 2026-10-10 06:30 |
| `pos_025_W2_QS` | ρ1 7.195  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 273    | 0       | 2026-10-10 06:35 |
| `pos_025_W3_QS` | ρ1 7.195  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 492    | 0       | 2026-10-10 06:44 |
| `pos_025_W4_QS` | ρ1 7.195  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 681    | 0       | 2026-10-10 06:55 |
| `pos_026_W1_QS` | ρ1 7.294  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 216    | 0       | 2026-10-10 06:59 |
| `pos_026_W2_QS` | ρ1 7.294  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 270    | 0       | 2026-10-10 07:04 |
| `pos_026_W3_QS` | ρ1 7.294  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 488    | 0       | 2026-10-10 07:13 |
| `pos_026_W4_QS` | ρ1 7.294  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 648    | 0       | 2026-10-10 07:24 |
| `pos_027_W1_QS` | ρ1 7.392  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 215    | 0       | 2026-10-10 07:28 |
| `pos_027_W2_QS` | ρ1 7.392  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 272    | 0       | 2026-10-10 07:33 |
| `pos_027_W3_QS` | ρ1 7.392  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 464    | 0       | 2026-10-10 07:41 |
| `pos_027_W4_QS` | ρ1 7.392  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 654    | 0       | 2026-10-10 07:53 |
| `pos_028_W1_QS` | ρ1 7.490  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 222    | 0       | 2026-10-10 07:57 |
| `pos_028_W2_QS` | ρ1 7.490  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 271    | 0       | 2026-10-10 08:02 |
| `pos_028_W3_QS` | ρ1 7.490  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 508    | 0       | 2026-10-10 08:10 |
| `pos_028_W4_QS` | ρ1 7.490  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 687    | 0       | 2026-10-10 08:22 |
| `pos_029_W1_QS` | ρ1 7.589  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 221    | 0       | 2026-10-10 08:26 |
| `pos_029_W2_QS` | ρ1 7.589  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 270    | 0       | 2026-10-10 08:31 |
| `pos_029_W3_QS` | ρ1 7.589  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 448    | 0       | 2026-10-10 08:39 |
| `pos_029_W4_QS` | ρ1 7.589  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 673    | 0       | 2026-10-10 08:51 |
| `pos_030_W1_QS` | ρ1 7.687  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 229    | 0       | 2026-10-10 08:55 |
| `pos_030_W2_QS` | ρ1 7.687  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 284    | 0       | 2026-10-10 09:00 |
| `pos_030_W3_QS` | ρ1 7.687  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 506    | 0       | 2026-10-10 09:09 |
| `pos_030_W4_QS` | ρ1 7.687  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 651    | 0       | 2026-10-10 09:20 |
| `pos_031_W1_QS` | A         | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 214    | 0       | 2026-10-10 09:24 |
| `pos_031_W2_QS` | A         | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 251    | 0       | 2026-10-10 09:29 |
| `pos_031_W3_QS` | A         | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 484    | 0       | 2026-10-10 09:37 |
| `pos_031_W4_QS` | A         | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 611    | 0       | 2026-10-10 09:48 |
| `pos_032_W1_QS` | ρ1 7.884  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 212    | 0       | 2026-10-10 09:52 |
| `pos_032_W2_QS` | ρ1 7.884  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 271    | 0       | 2026-10-10 09:57 |
| `pos_032_W3_QS` | ρ1 7.884  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 504    | 0       | 2026-10-10 10:06 |
| `pos_032_W4_QS` | ρ1 7.884  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 658    | 0       | 2026-10-10 10:17 |
| `pos_033_W1_QS` | ρ1 7.982  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 222    | 0       | 2026-10-10 10:21 |
| `pos_033_W2_QS` | ρ1 7.982  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 259    | 0       | 2026-10-10 10:26 |
| `pos_033_W3_QS` | ρ1 7.982  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 464    | 0       | 2026-10-10 10:34 |
| `pos_033_W4_QS` | ρ1 7.982  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 644    | 0       | 2026-10-10 10:45 |
| `pos_034_W1_QS` | ρ1 8.081  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 234    | 0       | 2026-10-10 10:50 |
| `pos_034_W2_QS` | ρ1 8.081  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 283    | 0       | 2026-10-10 10:55 |
| `pos_034_W3_QS` | ρ1 8.081  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 548    | 0       | 2026-10-10 11:04 |
| `pos_034_W4_QS` | ρ1 8.081  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 698    | 0       | 2026-10-10 11:16 |
| `pos_035_W1_QS` | ρ1 8.179  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 257    | 0       | 2026-10-10 11:21 |
| `pos_035_W2_QS` | ρ1 8.179  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 11           | 399    | 16      | 2026-10-10 11:28 |
| `pos_035_W3_QS` | ρ1 8.179  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 532    | 0       | 2026-10-10 11:37 |
| `pos_035_W4_QS` | ρ1 8.179  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 13           | 944    | 8       | 2026-10-10 11:54 |
| `pos_036_W1_QS` | B         | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 225    | 0       | 2026-10-10 11:58 |
| `pos_036_W2_QS` | B         | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 8, 6, 6            | 323    | 6       | 2026-10-10 12:03 |
| `pos_036_W3_QS` | B         | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 514    | 0       | 2026-10-10 12:12 |
| `pos_036_W4_QS` | B         | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 12           | 952    | 9       | 2026-10-10 12:29 |
| `pos_037_W1_QS` | ρ1 8.278  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 254    | 0       | 2026-10-10 12:33 |
| `pos_037_W2_QS` | ρ1 8.278  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 305    | 5       | 2026-10-10 12:39 |
| `pos_037_W3_QS` | ρ1 8.278  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 546    | 0       | 2026-10-10 12:48 |
| `pos_037_W4_QS` | ρ1 8.278  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 14           | 958    | 5       | 2026-10-10 13:05 |
| `pos_038_W1_QS` | ρ1 8.376  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 260    | 0       | 2026-10-10 13:10 |
| `pos_038_W2_QS` | ρ1 8.376  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 280    | 0       | 2026-10-10 13:15 |
| `pos_038_W3_QS` | ρ1 8.376  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 538    | 0       | 2026-10-10 13:24 |
| `pos_038_W4_QS` | ρ1 8.376  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 701    | 0       | 2026-10-10 13:36 |
| `pos_039_W1_QS` | ρ1 8.474  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 231    | 0       | 2026-10-10 13:40 |
| `pos_039_W2_QS` | ρ1 8.474  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 283    | 0       | 2026-10-10 13:45 |
| `pos_039_W3_QS` | ρ1 8.474  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 450    | 0       | 2026-10-10 13:53 |
| `pos_039_W4_QS` | ρ1 8.474  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 675    | 0       | 2026-10-10 14:05 |
| `pos_040_W1_QS` | ρ1 8.573  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 213    | 0       | 2026-10-10 14:09 |
| `pos_040_W2_QS` | ρ1 8.573  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 287    | 0       | 2026-10-10 14:14 |
| `pos_040_W3_QS` | ρ1 8.573  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 493    | 0       | 2026-10-10 14:23 |
| `pos_040_W4_QS` | ρ1 8.573  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 652    | 0       | 2026-10-10 14:34 |
| `pos_041_W1_QS` | ρ1 8.671  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 241    | 0       | 2026-10-10 14:39 |
| `pos_041_W2_QS` | ρ1 8.671  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 7, 6, 13           | 407    | 8       | 2026-10-10 14:46 |
| `pos_041_W3_QS` | ρ1 8.671  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 9            | 819    | 18      | 2026-10-10 15:00 |
| `pos_041_W4_QS` | ρ1 8.671  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 11, 6           | 1034   | 13      | 2026-10-10 15:17 |
| `pos_042_W1_QS` | ρ1 8.770  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 11, 6, 6           | 329    | 0       | 2026-10-10 15:23 |
| `pos_042_W2_QS` | ρ1 8.770  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 8, 6, 13           | 447    | 17      | 2026-10-10 15:31 |
| `pos_042_W3_QS` | ρ1 8.770  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 8            | 741    | 0       | 2026-10-10 15:44 |
| `pos_042_W4_QS` | ρ1 8.770  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 8, 15, 12          | 1460   | 36      | 2026-10-10 16:09 |
| `pos_043_W1_QS` | ρ1 8.868  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 263    | 0       | 2026-10-10 16:14 |
| `pos_043_W2_QS` | ρ1 8.868  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 13, 12          | 546    | 21      | 2026-10-10 16:23 |
| `pos_043_W3_QS` | ρ1 8.868  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 556    | 0       | 2026-10-10 16:33 |
| `pos_043_W4_QS` | ρ1 8.868  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 10, 18          | 1351   | 12      | 2026-10-10 16:56 |
| `pos_044_W1_QS` | ρ1 8.966  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 214    | 0       | 2026-10-10 17:00 |
| `pos_044_W2_QS` | ρ1 8.966  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 301    | 0       | 2026-10-10 17:05 |
| `pos_044_W3_QS` | ρ1 8.966  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 474    | 0       | 2026-10-10 17:13 |
| `pos_044_W4_QS` | ρ1 8.966  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 697    | 0       | 2026-10-10 17:25 |
| `pos_045_W1_QS` | ρ1 9.065  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 224    | 0       | 2026-10-10 17:30 |
| `pos_045_W2_QS` | ρ1 9.065  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 279    | 0       | 2026-10-10 17:35 |
| `pos_045_W3_QS` | ρ1 9.065  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 482    | 0       | 2026-10-10 17:43 |
| `pos_045_W4_QS` | ρ1 9.065  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 715    | 0       | 2026-10-10 17:55 |
| `pos_046_W1_QS` | ρ1 9.163  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 236    | 0       | 2026-10-10 18:00 |
| `pos_046_W2_QS` | ρ1 9.163  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 10, 6           | 359    | 14      | 2026-10-10 18:06 |
| `pos_046_W3_QS` | ρ1 9.163  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 11           | 799    | 9       | 2026-10-10 18:20 |
| `pos_046_W4_QS` | ρ1 9.163  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 11, 8           | 1010   | 6       | 2026-10-10 18:37 |
| `pos_047_W1_QS` | ρ1 9.262  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 255    | 0       | 2026-10-10 18:42 |
| `pos_047_W2_QS` | ρ1 9.262  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 8, 6, 6            | 317    | 3       | 2026-10-10 18:47 |
| `pos_047_W3_QS` | ρ1 9.262  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 530    | 0       | 2026-10-10 18:57 |
| `pos_047_W4_QS` | ρ1 9.262  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 717    | 0       | 2026-10-10 19:09 |
| `pos_048_W1_QS` | ρ1 9.360  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 222    | 0       | 2026-10-10 19:13 |
| `pos_048_W2_QS` | ρ1 9.360  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 271    | 0       | 2026-10-10 19:18 |
| `pos_048_W3_QS` | ρ1 9.360  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 453    | 0       | 2026-10-10 19:26 |
| `pos_048_W4_QS` | ρ1 9.360  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 690    | 0       | 2026-10-10 19:38 |
| `pos_049_W1_QS` | C         | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 214    | 0       | 2026-10-10 19:42 |
| `pos_049_W2_QS` | C         | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 271    | 0       | 2026-10-10 19:47 |
| `pos_049_W3_QS` | C         | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 474    | 0       | 2026-10-10 19:55 |
| `pos_049_W4_QS` | C         | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 644    | 0       | 2026-10-10 20:06 |
| `pos_050_W1_QS` | ρ1 9.458  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 226    | 0       | 2026-10-10 20:11 |
| `pos_050_W2_QS` | ρ1 9.458  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 263    | 0       | 2026-10-10 20:15 |
| `pos_050_W3_QS` | ρ1 9.458  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 499    | 0       | 2026-10-10 20:24 |
| `pos_050_W4_QS` | ρ1 9.458  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 739    | 0       | 2026-10-10 20:37 |
| `pos_051_W1_QS` | ρ1 9.557  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 225    | 0       | 2026-10-10 20:41 |
| `pos_051_W2_QS` | ρ1 9.557  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 295    | 0       | 2026-10-10 20:46 |
| `pos_051_W3_QS` | ρ1 9.557  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 475    | 0       | 2026-10-10 20:55 |
| `pos_051_W4_QS` | ρ1 9.557  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 711    | 0       | 2026-10-10 21:07 |
| `pos_052_W1_QS` | ρ1 9.655  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 209    | 0       | 2026-10-10 21:11 |
| `pos_052_W2_QS` | ρ1 9.655  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 289    | 0       | 2026-10-10 21:16 |
| `pos_052_W3_QS` | ρ1 9.655  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 476    | 0       | 2026-10-10 21:24 |
| `pos_052_W4_QS` | ρ1 9.655  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 631    | 0       | 2026-10-10 21:35 |
| `pos_053_W1_QS` | ρ1 9.754  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 219    | 0       | 2026-10-10 21:39 |
| `pos_053_W2_QS` | ρ1 9.754  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 282    | 0       | 2026-10-10 21:45 |
| `pos_053_W3_QS` | ρ1 9.754  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 472    | 0       | 2026-10-10 21:53 |
| `pos_053_W4_QS` | ρ1 9.754  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 665    | 0       | 2026-10-10 22:04 |
| `pos_054_W1_QS` | ρ1 9.852  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 222    | 0       | 2026-10-10 22:08 |
| `pos_054_W2_QS` | ρ1 9.852  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 270    | 0       | 2026-10-10 22:13 |
| `pos_054_W3_QS` | ρ1 9.852  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 500    | 0       | 2026-10-10 22:22 |
| `pos_054_W4_QS` | ρ1 9.852  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 647    | 0       | 2026-10-10 22:33 |
| `pos_055_W1_QS` | ρ1 9.950  | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 211    | 0       | 2026-10-10 22:37 |
| `pos_055_W2_QS` | ρ1 9.950  | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 267    | 0       | 2026-10-10 22:42 |
| `pos_055_W3_QS` | ρ1 9.950  | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 491    | 0       | 2026-10-10 22:51 |
| `pos_055_W4_QS` | ρ1 9.950  | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 657    | 0       | 2026-10-10 23:02 |
| `pos_056_W1_QS` | ρ1 10.049 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 235    | 0       | 2026-10-10 23:06 |
| `pos_056_W2_QS` | ρ1 10.049 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 295    | 0       | 2026-10-10 23:12 |
| `pos_056_W3_QS` | ρ1 10.049 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 526    | 0       | 2026-10-10 23:21 |
| `pos_056_W4_QS` | ρ1 10.049 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 697    | 0       | 2026-10-10 23:33 |
| `pos_057_W1_QS` | ρ1 10.147 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 227    | 0       | 2026-10-10 23:37 |
| `pos_057_W2_QS` | ρ1 10.147 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 286    | 0       | 2026-10-10 23:42 |
| `pos_057_W3_QS` | ρ1 10.147 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 512    | 0       | 2026-10-10 23:51 |
| `pos_057_W4_QS` | ρ1 10.147 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 703    | 0       | 2026-10-11 00:03 |
| `pos_058_W1_QS` | ρ1 10.246 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 218    | 0       | 2026-10-11 00:07 |
| `pos_058_W2_QS` | ρ1 10.246 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 283    | 0       | 2026-10-11 00:13 |
| `pos_058_W3_QS` | ρ1 10.246 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 492    | 0       | 2026-10-11 00:21 |
| `pos_058_W4_QS` | ρ1 10.246 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 685    | 0       | 2026-10-11 00:33 |
| `pos_059_W1_QS` | ρ1 10.344 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 205    | 0       | 2026-10-11 00:37 |
| `pos_059_W2_QS` | ρ1 10.344 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 263    | 0       | 2026-10-11 00:42 |
| `pos_059_W3_QS` | ρ1 10.344 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 451    | 0       | 2026-10-11 00:50 |
| `pos_059_W4_QS` | ρ1 10.344 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 656    | 0       | 2026-10-11 01:01 |
| `pos_060_W1_QS` | ρ1 10.442 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 208    | 0       | 2026-10-11 01:05 |
| `pos_060_W2_QS` | ρ1 10.442 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 249    | 0       | 2026-10-11 01:09 |
| `pos_060_W3_QS` | ρ1 10.442 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 494    | 0       | 2026-10-11 01:18 |
| `pos_060_W4_QS` | ρ1 10.442 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 685    | 0       | 2026-10-11 01:30 |
| `pos_061_W1_QS` | ρ1 10.541 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 208    | 0       | 2026-10-11 01:34 |
| `pos_061_W2_QS` | ρ1 10.541 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 257    | 0       | 2026-10-11 01:38 |
| `pos_061_W3_QS` | ρ1 10.541 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 449    | 0       | 2026-10-11 01:46 |
| `pos_061_W4_QS` | ρ1 10.541 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 635    | 0       | 2026-10-11 01:57 |
| `pos_062_W1_QS` | ρ1 10.639 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 233    | 0       | 2026-10-11 02:02 |
| `pos_062_W2_QS` | ρ1 10.639 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 272    | 0       | 2026-10-11 02:07 |
| `pos_062_W3_QS` | ρ1 10.639 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 470    | 0       | 2026-10-11 02:15 |
| `pos_062_W4_QS` | ρ1 10.639 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 674    | 0       | 2026-10-11 02:26 |
| `pos_063_W1_QS` | D         | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 218    | 0       | 2026-10-11 02:31 |
| `pos_063_W2_QS` | D         | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 251    | 0       | 2026-10-11 02:35 |
| `pos_063_W3_QS` | D         | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 490    | 0       | 2026-10-11 02:44 |
| `pos_063_W4_QS` | D         | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 650    | 0       | 2026-10-11 02:55 |
| `pos_064_W1_QS` | ρ1 10.836 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 204    | 0       | 2026-10-11 02:59 |
| `pos_064_W2_QS` | ρ1 10.836 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 267    | 0       | 2026-10-11 03:04 |
| `pos_064_W3_QS` | ρ1 10.836 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 510    | 0       | 2026-10-11 03:13 |
| `pos_064_W4_QS` | ρ1 10.836 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 659    | 0       | 2026-10-11 03:24 |
| `pos_065_W1_QS` | ρ1 10.935 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 239    | 0       | 2026-10-11 03:28 |
| `pos_065_W2_QS` | ρ1 10.935 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 272    | 0       | 2026-10-11 03:33 |
| `pos_065_W3_QS` | ρ1 10.935 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 497    | 0       | 2026-10-11 03:42 |
| `pos_065_W4_QS` | ρ1 10.935 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 670    | 0       | 2026-10-11 03:54 |
| `pos_066_W1_QS` | ρ1 11.033 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 232    | 0       | 2026-10-11 03:58 |
| `pos_066_W2_QS` | ρ1 11.033 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 287    | 3       | 2026-10-11 04:03 |
| `pos_066_W3_QS` | ρ1 11.033 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 532    | 0       | 2026-10-11 04:12 |
| `pos_066_W4_QS` | ρ1 11.033 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 693    | 0       | 2026-10-11 04:24 |
| `pos_067_W1_QS` | ρ1 11.131 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 238    | 0       | 2026-10-11 04:29 |
| `pos_067_W2_QS` | ρ1 11.131 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 305    | 0       | 2026-10-11 04:34 |
| `pos_067_W3_QS` | ρ1 11.131 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 532    | 0       | 2026-10-11 04:44 |
| `pos_067_W4_QS` | ρ1 11.131 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 735    | 0       | 2026-10-11 04:56 |
| `pos_068_W1_QS` | E         | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 230    | 0       | 2026-10-11 05:00 |
| `pos_068_W2_QS` | E         | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 11           | 365    | 4       | 2026-10-11 05:07 |
| `pos_068_W3_QS` | E         | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 542    | 0       | 2026-10-11 05:16 |
| `pos_068_W4_QS` | E         | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 13           | 1019   | 13      | 2026-10-11 05:34 |
| `pos_069_W1_QS` | ρ1 11.230 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 241    | 0       | 2026-10-11 05:38 |
| `pos_069_W2_QS` | ρ1 11.230 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 12           | 387    | 9       | 2026-10-11 05:45 |
| `pos_069_W3_QS` | ρ1 11.230 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 539    | 0       | 2026-10-11 05:55 |
| `pos_069_W4_QS` | ρ1 11.230 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 8            | 813    | 5       | 2026-10-11 06:08 |
| `pos_070_W1_QS` | ρ1 11.328 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 231    | 0       | 2026-10-11 06:13 |
| `pos_070_W2_QS` | ρ1 11.328 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 268    | 0       | 2026-10-11 06:18 |
| `pos_070_W3_QS` | ρ1 11.328 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 522    | 0       | 2026-10-11 06:27 |
| `pos_070_W4_QS` | ρ1 11.328 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 675    | 0       | 2026-10-11 06:38 |
| `pos_071_W1_QS` | ρ1 11.427 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 224    | 0       | 2026-10-11 06:43 |
| `pos_071_W2_QS` | ρ1 11.427 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 277    | 0       | 2026-10-11 06:48 |
| `pos_071_W3_QS` | ρ1 11.427 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 447    | 0       | 2026-10-11 06:55 |
| `pos_071_W4_QS` | ρ1 11.427 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 673    | 0       | 2026-10-11 07:07 |
| `pos_072_W1_QS` | ρ1 11.525 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 212    | 0       | 2026-10-11 07:11 |
| `pos_072_W2_QS` | ρ1 11.525 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 270    | 0       | 2026-10-11 07:16 |
| `pos_072_W3_QS` | ρ1 11.525 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 512    | 0       | 2026-10-11 07:25 |
| `pos_072_W4_QS` | ρ1 11.525 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 666    | 0       | 2026-10-11 07:36 |
| `pos_073_W1_QS` | ρ1 11.623 | W1    | QS   |          | linear, N2S 0.2 | not completed (step 4 inc 23) | 6, 6, 6, 37           | 1433   | 307     | 2026-10-11 08:01 |
| `pos_073_W2_QS` | ρ1 11.623 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 7, 6, 12           | 429    | 20      | 2026-10-11 08:08 |
| `pos_073_W3_QS` | ρ1 11.623 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 9            | 662    | 6       | 2026-10-11 08:20 |
| `pos_073_W4_QS` | ρ1 11.623 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 8, 11, 8           | 1201   | 40      | 2026-10-11 08:40 |
| `pos_074_W1_QS` | ρ1 11.722 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 246    | 0       | 2026-10-11 08:45 |
| `pos_074_W2_QS` | ρ1 11.722 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 8, 14           | 447    | 10      | 2026-10-11 08:53 |
| `pos_074_W3_QS` | ρ1 11.722 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 553    | 0       | 2026-10-11 09:02 |
| `pos_074_W4_QS` | ρ1 11.722 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 8, 11, 11          | 1287   | 18      | 2026-10-11 09:24 |
| `pos_075_W1_QS` | ρ1 11.820 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 251    | 0       | 2026-10-11 09:29 |
| `pos_075_W2_QS` | ρ1 11.820 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 10           | 389    | 5       | 2026-10-11 09:36 |
| `pos_075_W3_QS` | ρ1 11.820 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 566    | 0       | 2026-10-11 09:45 |
| `pos_075_W4_QS` | ρ1 11.820 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 9, 15           | 1172   | 6       | 2026-10-11 10:05 |
| `pos_076_W1_QS` | ρ1 11.919 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 219    | 0       | 2026-10-11 10:10 |
| `pos_076_W2_QS` | ρ1 11.919 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 299    | 0       | 2026-10-11 10:15 |
| `pos_076_W3_QS` | ρ1 11.919 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 482    | 0       | 2026-10-11 10:23 |
| `pos_076_W4_QS` | ρ1 11.919 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 710    | 0       | 2026-10-11 10:36 |
| `pos_077_W1_QS` | ρ1 12.017 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 229    | 0       | 2026-10-11 10:40 |
| `pos_077_W2_QS` | ρ1 12.017 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 283    | 0       | 2026-10-11 10:45 |
| `pos_077_W3_QS` | ρ1 12.017 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 498    | 0       | 2026-10-11 10:54 |
| `pos_077_W4_QS` | ρ1 12.017 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 707    | 0       | 2026-10-11 11:06 |
| `pos_078_W1_QS` | ρ1 12.115 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 245    | 0       | 2026-10-11 11:10 |
| `pos_078_W2_QS` | ρ1 12.115 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 8, 6            | 359    | 16      | 2026-10-11 11:17 |
| `pos_078_W3_QS` | ρ1 12.115 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 12           | 890    | 11      | 2026-10-11 11:32 |
| `pos_078_W4_QS` | ρ1 12.115 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 12, 6           | 1002   | 8       | 2026-10-11 11:49 |
| `pos_079_W1_QS` | ρ1 12.214 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 264    | 0       | 2026-10-11 11:54 |
| `pos_079_W2_QS` | ρ1 12.214 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 8, 6, 6            | 306    | 3       | 2026-10-11 11:59 |
| `pos_079_W3_QS` | ρ1 12.214 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 543    | 0       | 2026-10-11 12:09 |
| `pos_079_W4_QS` | ρ1 12.214 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 8, 6, 6            | 799    | 2       | 2026-10-11 12:22 |
| `pos_080_W1_QS` | ρ1 12.312 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 227    | 0       | 2026-10-11 12:27 |
| `pos_080_W2_QS` | ρ1 12.312 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 263    | 0       | 2026-10-11 12:31 |
| `pos_080_W3_QS` | ρ1 12.312 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 476    | 0       | 2026-10-11 12:40 |
| `pos_080_W4_QS` | ρ1 12.312 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 674    | 0       | 2026-10-11 12:51 |
| `pos_081_W1_QS` | ρ1 12.411 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 226    | 0       | 2026-10-11 12:56 |
| `pos_081_W2_QS` | ρ1 12.411 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 273    | 0       | 2026-10-11 13:00 |
| `pos_081_W3_QS` | ρ1 12.411 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 514    | 0       | 2026-10-11 13:09 |
| `pos_081_W4_QS` | ρ1 12.411 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 8, 6, 6            | 767    | 0       | 2026-10-11 13:23 |
| `pos_082_W1_QS` | ρ1 12.509 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 230    | 0       | 2026-10-11 13:27 |
| `pos_082_W2_QS` | ρ1 12.509 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 313    | 0       | 2026-10-11 13:32 |
| `pos_082_W3_QS` | ρ1 12.509 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 481    | 0       | 2026-10-11 13:41 |
| `pos_082_W4_QS` | ρ1 12.509 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 731    | 0       | 2026-10-11 13:53 |
| `pos_083_W1_QS` | ρ1 12.607 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 207    | 0       | 2026-10-11 13:57 |
| `pos_083_W2_QS` | ρ1 12.607 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 272    | 0       | 2026-10-11 14:02 |
| `pos_083_W3_QS` | ρ1 12.607 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 486    | 0       | 2026-10-11 14:11 |
| `pos_083_W4_QS` | ρ1 12.607 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 664    | 0       | 2026-10-11 14:22 |
| `pos_084_W1_QS` | ρ1 12.706 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 212    | 0       | 2026-10-11 14:26 |
| `pos_084_W2_QS` | ρ1 12.706 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 275    | 0       | 2026-10-11 14:31 |
| `pos_084_W3_QS` | ρ1 12.706 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 479    | 0       | 2026-10-11 14:39 |
| `pos_084_W4_QS` | ρ1 12.706 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 650    | 0       | 2026-10-11 14:51 |
| `pos_085_W1_QS` | ρ1 12.804 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 215    | 0       | 2026-10-11 14:55 |
| `pos_085_W2_QS` | ρ1 12.804 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 264    | 0       | 2026-10-11 14:59 |
| `pos_085_W3_QS` | ρ1 12.804 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 503    | 0       | 2026-10-11 15:08 |
| `pos_085_W4_QS` | ρ1 12.804 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 645    | 0       | 2026-10-11 15:19 |
| `pos_086_W1_QS` | ρ1 12.903 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 216    | 0       | 2026-10-11 15:23 |
| `pos_086_W2_QS` | ρ1 12.903 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 271    | 0       | 2026-10-11 15:28 |
| `pos_086_W3_QS` | ρ1 12.903 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 504    | 0       | 2026-10-11 15:37 |
| `pos_086_W4_QS` | ρ1 12.903 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 664    | 0       | 2026-10-11 15:49 |
| `pos_087_W1_QS` | ρ1 13.001 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 233    | 0       | 2026-10-11 15:53 |
| `pos_087_W2_QS` | ρ1 13.001 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 287    | 0       | 2026-10-11 15:58 |
| `pos_087_W3_QS` | ρ1 13.001 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 528    | 0       | 2026-10-11 16:07 |
| `pos_087_W4_QS` | ρ1 13.001 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 693    | 0       | 2026-10-11 16:19 |
| `pos_088_W1_QS` | ρ1 13.099 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 229    | 0       | 2026-10-11 16:23 |
| `pos_088_W2_QS` | ρ1 13.099 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 283    | 0       | 2026-10-11 16:28 |
| `pos_088_W3_QS` | ρ1 13.099 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 508    | 0       | 2026-10-11 16:37 |
| `pos_088_W4_QS` | ρ1 13.099 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 689    | 0       | 2026-10-11 16:49 |
| `pos_089_W1_QS` | ρ1 13.198 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 214    | 0       | 2026-10-11 16:53 |
| `pos_089_W2_QS` | ρ1 13.198 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 269    | 0       | 2026-10-11 16:58 |
| `pos_089_W3_QS` | ρ1 13.198 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 488    | 0       | 2026-10-11 17:06 |
| `pos_089_W4_QS` | ρ1 13.198 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 656    | 0       | 2026-10-11 17:18 |
| `pos_090_W1_QS` | ρ1 13.296 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 208    | 0       | 2026-10-11 17:22 |
| `pos_090_W2_QS` | ρ1 13.296 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 263    | 0       | 2026-10-11 17:26 |
| `pos_090_W3_QS` | ρ1 13.296 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 466    | 0       | 2026-10-11 17:35 |
| `pos_090_W4_QS` | ρ1 13.296 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 661    | 0       | 2026-10-11 17:46 |
| `pos_091_W1_QS` | ρ1 13.395 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 213    | 0       | 2026-10-11 17:50 |
| `pos_091_W2_QS` | ρ1 13.395 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 259    | 0       | 2026-10-11 17:55 |
| `pos_091_W3_QS` | ρ1 13.395 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 495    | 0       | 2026-10-11 18:03 |
| `pos_091_W4_QS` | ρ1 13.395 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 658    | 0       | 2026-10-11 18:15 |
| `pos_092_W1_QS` | ρ1 13.493 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 210    | 0       | 2026-10-11 18:19 |
| `pos_092_W2_QS` | ρ1 13.493 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 265    | 0       | 2026-10-11 18:23 |
| `pos_092_W3_QS` | ρ1 13.493 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 475    | 0       | 2026-10-11 18:32 |
| `pos_092_W4_QS` | ρ1 13.493 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 644    | 0       | 2026-10-11 18:43 |
| `pos_093_W1_QS` | ρ1 13.591 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 234    | 0       | 2026-10-11 18:47 |
| `pos_093_W2_QS` | ρ1 13.591 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 275    | 0       | 2026-10-11 18:52 |
| `pos_093_W3_QS` | ρ1 13.591 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 497    | 0       | 2026-10-11 19:01 |
| `pos_093_W4_QS` | ρ1 13.591 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 665    | 0       | 2026-10-11 19:12 |
| `pos_094_W1_QS` | ρ1 13.690 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 215    | 0       | 2026-10-11 19:16 |
| `pos_094_W2_QS` | ρ1 13.690 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 252    | 0       | 2026-10-11 19:21 |
| `pos_094_W3_QS` | ρ1 13.690 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 482    | 0       | 2026-10-11 19:29 |
| `pos_094_W4_QS` | ρ1 13.690 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 628    | 0       | 2026-10-11 19:40 |
| `pos_095_W1_QS` | ρ1 13.788 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 204    | 0       | 2026-10-11 19:44 |
| `pos_095_W2_QS` | ρ1 13.788 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 254    | 0       | 2026-10-11 19:49 |
| `pos_095_W3_QS` | ρ1 13.788 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 504    | 0       | 2026-10-11 19:57 |
| `pos_095_W4_QS` | ρ1 13.788 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 649    | 0       | 2026-10-11 20:09 |
| `pos_096_W1_QS` | ρ1 13.887 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 241    | 0       | 2026-10-11 20:13 |
| `pos_096_W2_QS` | ρ1 13.887 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 269    | 0       | 2026-10-11 20:18 |
| `pos_096_W3_QS` | ρ1 13.887 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 506    | 0       | 2026-10-11 20:27 |
| `pos_096_W4_QS` | ρ1 13.887 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 656    | 0       | 2026-10-11 20:38 |
| `pos_097_W1_QS` | ρ1 13.985 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 241    | 0       | 2026-10-11 20:42 |
| `pos_097_W2_QS` | ρ1 13.985 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 9            | 351    | 9       | 2026-10-11 20:49 |
| `pos_097_W3_QS` | ρ1 13.985 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 552    | 0       | 2026-10-11 20:58 |
| `pos_097_W4_QS` | ρ1 13.985 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 698    | 0       | 2026-10-11 21:10 |
| `pos_098_W1_QS` | ρ1 14.083 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 247    | 0       | 2026-10-11 21:15 |
| `pos_098_W2_QS` | ρ1 14.083 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 11           | 378    | 4       | 2026-10-11 21:21 |
| `pos_098_W3_QS` | ρ1 14.083 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 561    | 0       | 2026-10-11 21:31 |
| `pos_098_W4_QS` | ρ1 14.083 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 10           | 996    | 11      | 2026-10-11 21:48 |
| `pos_099_W1_QS` | ρ1 14.182 | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 247    | 0       | 2026-10-11 21:53 |
| `pos_099_W2_QS` | ρ1 14.182 | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 13           | 389    | 5       | 2026-10-11 22:00 |
| `pos_099_W3_QS` | ρ1 14.182 | W3    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 536    | 0       | 2026-10-11 22:09 |
| `pos_099_W4_QS` | ρ1 14.182 | W4    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 12           | 958    | 9       | 2026-10-11 22:25 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei           | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_001_W1_QS` | LOAD_16NM | -0.34 %  | 63.3       | 126.6          | T5 RIGHT, r 25.70, z +0.0 | 68.2       | T4_T5, r 24.85, z -6.8, Tangente 40° | -49.2      | T4_T5      | 71.7    | T4   |
| `pos_001_W2_QS` | LOAD_16NM | -0.20 %  | 81.5       | 84.7           | T5 RIGHT, r 25.70, z -6.0 | 45.9       | T4_T5, r 24.82, z -6.0, Tangente 49° | -45.3      | T4_T5      | 92.2    | T4   |
| `pos_001_W3_QS` | LOAD_16NM | -0.33 %  | 66.5       | 128.4          | T5 RIGHT, r 25.70, z +7.5 | 78.9       | T4_T5, r 24.86, z +6.8, Tangente 37° | -60.2      | T4_T5      | 74.3    | T4   |
| `pos_001_W4_QS` | LOAD_16NM | -0.18 %  | 81.5       | 86.7           | T5 RIGHT, r 25.70, z +6.8 | 54.2       | T4_T5, r 24.88, z +6.8, Tangente 33° | -53.3      | T4_T5      | 90.5    | T4   |
| `pos_002_W1_QS` | LOAD_16NM | -0.27 %  | 63.0       | 136.5          | T5 RIGHT, r 25.70, z +0.0 | 67.2       | T4_T5, r 24.85, z -6.8, Tangente 40° | -50.1      | T4_T5      | 71.6    | T4   |
| `pos_002_W2_QS` | LOAD_16NM | -0.12 %  | 80.8       | 86.3           | T5 RIGHT, r 25.70, z -6.0 | 45.2       | T4_T5, r 24.82, z -6.0, Tangente 49° | -45.7      | T4_T5      | 92.0    | T4   |
| `pos_002_W3_QS` | LOAD_16NM | -0.21 %  | 66.3       | 137.1          | T5 RIGHT, r 25.70, z +7.5 | 78.0       | T4_T5, r 24.86, z +6.8, Tangente 37° | -61.1      | T4_T5      | 73.9    | T4   |
| `pos_002_W4_QS` | LOAD_16NM | -0.10 %  | 81.3       | 88.9           | T5 RIGHT, r 25.70, z +6.8 | 54.4       | T3_T4, r 24.78, z +4.5, Tangente 63° | -54.0      | T4_T5      | 90.6    | T4   |
| `pos_003_W1_QS` | LOAD_16NM | -0.10 %  | 62.8       | 144.4          | T5 RIGHT, r 25.70, z +0.0 | 66.1       | T4_T5, r 24.85, z -6.8, Tangente 40° | -50.8      | T4_T5      | 71.7    | T4   |
| `pos_003_W2_QS` | LOAD_16NM | +0.05 %  | 80.6       | 87.8           | T5 RIGHT, r 25.70, z -6.0 | 44.4       | T4_T5, r 24.82, z -6.0, Tangente 49° | -46.0      | T4_T5      | 92.3    | T4   |
| `pos_003_W3_QS` | LOAD_16NM | -0.06 %  | 66.2       | 145.0          | T5 RIGHT, r 25.70, z +7.5 | 75.9       | T4_T5, r 24.86, z +6.8, Tangente 37° | -61.8      | T4_T5      | 73.7    | T4   |
| `pos_003_W4_QS` | LOAD_16NM | +0.13 %  | 81.2       | 89.5           | T5 RIGHT, r 25.70, z +6.8 | 54.8       | T3_T4, r 24.78, z +4.5, Tangente 63° | -54.5      | T4_T5      | 90.8    | T4   |
| `pos_004_W1_QS` | LOAD_16NM | +0.68 %  | 63.2       | 145.7          | T5 RIGHT, r 25.70, z +0.0 | 61.1       | T4_T5, r 24.85, z -6.8, Tangente 40° | -51.7      | T4_T5      | 72.8    | T4   |
| `pos_004_W2_QS` | LOAD_16NM | +0.54 %  | 80.7       | 85.9           | T5 RIGHT, r 25.70, z -6.0 | 43.1       | T3_T4, r 24.79, z -4.5, Tangente 58° | -46.7      | T4_T5      | 93.3    | T4   |
| `pos_004_W3_QS` | LOAD_16NM | +0.65 %  | 66.9       | 139.2          | T5 RIGHT, r 25.70, z +7.5 | 69.5       | T4_T5, r 24.86, z +6.8, Tangente 37° | -62.4      | T4_T5      | 74.8    | T4   |
| `pos_004_W4_QS` | LOAD_16NM | +0.70 %  | 81.6       | 85.2           | T5 RIGHT, r 25.70, z +6.8 | 55.5       | T3_T4, r 24.78, z +4.5, Tangente 63° | -55.1      | T4_T5      | 91.7    | T4   |
| `pos_005_W1_QS` | LOAD_16NM | +1.54 %  | 64.9       | 127.0          | T5 RIGHT, r 25.80, z -6.8 | 56.5       | T4_T5, r 24.85, z -6.8, Tangente 40° | -53.8      | T4_T5      | 75.0    | T4   |
| `pos_005_W2_QS` | LOAD_16NM | +1.22 %  | 81.8       | 88.9           | T5 RIGHT, r 25.80, z -6.0 | 43.7       | T3_T4, r 24.79, z -4.5, Tangente 58° | -47.4      | T4_T5      | 94.8    | T4   |
| `pos_005_W3_QS` | LOAD_16NM | +1.39 %  | 68.6       | 130.2          | T5 RIGHT, r 25.80, z -7.5 | 65.0       | T3_T4, r 24.86, z +6.8, Tangente 37° | -64.7      | T4_T5      | 77.1    | T4   |
| `pos_005_W4_QS` | LOAD_16NM | +1.36 %  | 83.1       | 89.1           | T5 RIGHT, r 25.80, z -6.8 | 56.5       | T3_T4, r 24.78, z +4.5, Tangente 63° | -56.2      | T4_T5      | 93.8    | T4   |
| `pos_006_W1_QS` | LOAD_16NM | +1.52 %  | 66.4       | 152.9          | T5 RIGHT, r 25.80, z -6.8 | 57.1       | T3_T4, r 24.83, z -4.5, Tangente 45° | -57.7      | T4_T5      | 77.4    | T4   |
| `pos_006_W2_QS` | LOAD_16NM | +1.66 %  | 83.1       | 91.3           | T5 RIGHT, r 25.80, z -6.0 | 44.6       | T3_T4, r 24.79, z -4.5, Tangente 58° | -48.5      | T4_T5      | 96.9    | T4   |
| `pos_006_W3_QS` | LOAD_16NM | +1.50 %  | 70.4       | 160.9          | T5 RIGHT, r 25.80, z -7.5 | 67.9       | T3_T4, r 24.86, z +6.8, Tangente 37° | -68.9      | T4_T5      | 79.2    | T4   |
| `pos_006_W4_QS` | LOAD_16NM | +1.67 %  | 84.4       | 92.9           | T5 RIGHT, r 25.80, z -6.8 | 57.6       | T3_T4, r 24.78, z +4.5, Tangente 63° | -57.7      | T4_T5      | 95.4    | T4   |
| `pos_007_W1_QS` | LOAD_16NM | +0.89 %  | 68.2       | 177.8          | T5 RIGHT, r 25.80, z -6.8 | 60.1       | T3_T4, r 24.83, z -4.5, Tangente 45° | -62.4      | T4_T5      | 80.0    | T4   |
| `pos_007_W2_QS` | LOAD_16NM | +1.56 %  | 85.0       | 94.0           | T5 RIGHT, r 25.80, z -6.0 | 45.7       | T3_T4, r 24.79, z -4.5, Tangente 58° | -50.1      | T4_T5      | 99.8    | T4   |
| `pos_007_W3_QS` | LOAD_16NM | +0.75 %  | 71.6       | 186.8          | T5 RIGHT, r 25.80, z -7.5 | 71.2       | T3_T4, r 24.86, z +6.8, Tangente 37° | -74.9      | T4_T5      | 81.2    | T4   |
| `pos_007_W4_QS` | LOAD_16NM | +1.51 %  | 86.3       | 96.4           | T5 RIGHT, r 25.80, z -6.8 | 59.1       | T3_T4, r 24.78, z +4.5, Tangente 63° | -60.0      | T4_T5      | 98.0    | T4   |
| `pos_008_W1_QS` | LOAD_16NM | +0.52 %  | 68.7       | 183.5          | T5 RIGHT, r 25.80, z +0.0 | 61.7       | T3_T4, r 24.83, z -4.5, Tangente 45° | -65.1      | T4_T5      | 80.8    | T4   |
| `pos_008_W2_QS` | LOAD_16NM | +0.52 %  | 86.5       | 97.4           | T5 RIGHT, r 25.80, z -6.0 | 46.7       | T3_T4, r 24.79, z -4.5, Tangente 58° | -51.9      | T4_T5      | 101.8   | T4   |
| `pos_008_W3_QS` | LOAD_16NM | +0.52 %  | 72.1       | 189.0          | T5 RIGHT, r 25.80, z -7.5 | 73.0       | T3_T4, r 24.86, z +6.8, Tangente 37° | -77.4      | T4_T5      | 82.1    | T4   |
| `pos_008_W4_QS` | LOAD_16NM | +0.54 %  | 87.3       | 99.3           | T5 RIGHT, r 25.80, z -6.8 | 60.5       | T3_T4, r 24.78, z +4.5, Tangente 63° | -62.1      | T4_T5      | 99.7    | T4   |
| `pos_009_W1_QS` | LOAD_16NM | +0.58 %  | 69.3       | 184.4          | T5 RIGHT, r 25.80, z +0.0 | 63.3       | T3_T4, r 24.83, z -4.5, Tangente 45° | -67.2      | T4_T5      | 82.1    | T4   |
| `pos_009_W2_QS` | LOAD_16NM | +0.56 %  | 86.8       | 98.4           | T5 RIGHT, r 25.80, z -6.0 | 47.3       | T3_T4, r 24.79, z -4.5, Tangente 58° | -52.5      | T4_T5      | 102.6   | T4   |
| `pos_009_W3_QS` | LOAD_16NM | +0.53 %  | 72.5       | 190.1          | T5 RIGHT, r 25.80, z -7.5 | 74.3       | T3_T4, r 24.86, z +6.8, Tangente 37° | -79.3      | T4_T5      | 82.4    | T4   |
| `pos_009_W4_QS` | LOAD_16NM | +0.58 %  | 87.6       | 100.2          | T5 RIGHT, r 25.80, z -6.8 | 60.9       | T3_T4, r 24.78, z +4.5, Tangente 63° | -62.7      | T4_T5      | 99.9    | T4   |
| `pos_010_W1_QS` | LOAD_16NM | +1.04 %  | 70.0       | 184.6          | T5 RIGHT, r 25.80, z +0.0 | 64.7       | T3_T4, r 24.83, z -4.5, Tangente 45° | -69.0      | T4_T5      | 83.2    | T4   |
| `pos_010_W2_QS` | LOAD_16NM | +0.95 %  | 87.3       | 97.1           | T5 RIGHT, r 25.80, z -1.5 | 47.8       | T3_T4, r 24.79, z -4.5, Tangente 58° | -53.1      | T4_T5      | 103.7   | T4   |
| `pos_010_W3_QS` | LOAD_16NM | +1.32 %  | 73.6       | 181.7          | T5 RIGHT, r 25.80, z -7.5 | 76.1       | T3_T4, r 24.86, z +6.8, Tangente 37° | -80.8      | T4_T5      | 84.0    | T4   |
| `pos_010_W4_QS` | LOAD_16NM | +1.22 %  | 88.3       | 96.5           | T5 RIGHT, r 25.80, z -6.8 | 61.7       | T3_T4, r 24.78, z +4.5, Tangente 63° | -63.4      | T4_T5      | 100.9   | T4   |
| `pos_011_W1_QS` | LOAD_16NM | +3.01 %  | 73.3       | 151.9          | T5 RIGHT, r 25.80, z +0.0 | 68.0       | T3_T4, r 24.83, z -4.5, Tangente 45° | -72.6      | T4_T5      | 87.1    | T4   |
| `pos_011_W2_QS` | LOAD_16NM | +2.31 %  | 89.5       | 94.9           | T5 RIGHT, r 25.90, z -6.0 | 48.7       | T3_T4, r 24.79, z -4.5, Tangente 58° | -54.0      | T4_T5      | 106.1   | T4   |
| `pos_011_W3_QS` | LOAD_16NM | +3.18 %  | 77.5       | 138.0          | T5 RIGHT, r 25.80, z +0.0 | 80.6       | T3_T4, r 24.86, z +6.8, Tangente 37° | -85.9      | T4_T5      | 88.7    | T4   |
| `pos_011_W4_QS` | LOAD_16NM | +2.35 %  | 90.9       | 94.0           | T5 RIGHT, r 25.90, z -6.8 | 63.1       | T3_T4, r 24.78, z +4.5, Tangente 63° | -64.8      | T4_T5      | 104.1   | T4   |
| `pos_012_W1_QS` | LOAD_16NM | +2.59 %  | 76.5       | 144.5          | T5 RIGHT, r 25.90, z -6.8 | 72.7       | T3_T4, r 24.83, z -4.5, Tangente 45° | -79.5      | T4_T5      | 91.7    | T4   |
| `pos_012_W2_QS` | LOAD_16NM | +2.76 %  | 92.0       | 95.1           | T5 RIGHT, r 25.90, z -6.0 | 49.9       | T3_T4, r 24.79, z -4.5, Tangente 58° | -55.4      | T4_T5      | 109.5   | T4   |
| `pos_012_W3_QS` | LOAD_16NM | +2.45 %  | 80.3       | 173.1          | T5 RIGHT, r 25.90, z -7.5 | 85.2       | T3_T4, r 24.86, z +6.8, Tangente 37° | -93.5      | T4_T5      | 91.7    | T4   |
| `pos_012_W4_QS` | LOAD_16NM | +2.59 %  | 93.4       | 96.5           | T5 RIGHT, r 25.90, z -6.8 | 64.6       | T3_T4, r 24.78, z +4.5, Tangente 63° | -66.7      | T4_T5      | 106.8   | T4   |
| `pos_013_W1_QS` | LOAD_16NM | +0.56 %  | 78.5       | 168.0          | T5 RIGHT, r 25.90, z +0.0 | 76.6       | T3_T4, r 24.83, z -4.5, Tangente 45° | -86.4      | T4_T5      | 94.4    | T4   |
| `pos_013_W2_QS` | LOAD_16NM | +1.29 %  | 94.4       | 97.7           | T5 RIGHT, r 25.90, z -6.0 | 51.1       | T3_T4, r 24.79, z -4.5, Tangente 58° | -57.2      | T4_T5      | 112.8   | T4   |
| `pos_013_W3_QS` | LOAD_16NM | +0.51 %  | 81.7       | 191.1          | T5 RIGHT, r 25.90, z -7.5 | 89.2       | T3_T4, r 24.86, z +6.8, Tangente 37° | -100.5     | T4_T5      | 93.8    | T4   |
| `pos_013_W4_QS` | LOAD_16NM | +1.04 %  | 95.0       | 98.8           | T5 RIGHT, r 25.90, z +7.5 | 65.7       | T3_T4, r 24.78, z +4.5, Tangente 63° | -68.9      | T4_T5      | 108.8   | T4   |
| `pos_014_W1_QS` | LOAD_16NM | +0.44 %  | 78.9       | 156.6          | T5 RIGHT, r 25.90, z +0.0 | 77.8       | T3_T4, r 24.83, z -3.8, Tangente 45° | -88.4      | T4_T5      | 94.6    | T4   |
| `pos_014_W2_QS` | LOAD_16NM | +0.21 %  | 91.9       | 97.3           | T5 RIGHT, r 25.90, z -6.0 | 50.1       | T3_T4, r 24.79, z -4.5, Tangente 58° | -56.8      | T4_T5      | 109.3   | T4   |
| `pos_014_W3_QS` | LOAD_16NM | +0.44 %  | 82.1       | 179.8          | T5 RIGHT, r 25.90, z -7.5 | 90.8       | T3_T4, r 24.85, z +6.8, Tangente 40° | -102.6     | T4_T5      | 94.4    | T4   |
| `pos_014_W4_QS` | LOAD_16NM | +0.11 %  | 92.2       | 98.1           | T5 RIGHT, r 25.90, z -7.5 | 64.3       | T3_T4, r 24.78, z +4.5, Tangente 63° | -68.6      | T4_T5      | 105.4   | T4   |
| `pos_015_W1_QS` | LOAD_16NM | +1.48 %  | 79.6       | 152.2          | T5 RIGHT, r 25.90, z +0.0 | 78.8       | T3_T4, r 24.83, z -3.8, Tangente 45° | -90.1      | T4_T5      | 95.8    | T4   |
| `pos_015_W2_QS` | LOAD_16NM | +0.67 %  | 90.3       | 93.4           | T5 RIGHT, r 25.90, z -6.0 | 49.3       | T3_T4, r 24.79, z -4.5, Tangente 58° | -56.3      | T4_T5      | 107.0   | T4   |
| `pos_015_W3_QS` | LOAD_16NM | +1.59 %  | 82.5       | 171.0          | T5 RIGHT, r 25.90, z -7.5 | 90.8       | T3_T4, r 24.86, z +6.8, Tangente 37° | -101.9     | T4_T5      | 94.2    | T4   |
| `pos_015_W4_QS` | LOAD_16NM | +0.63 %  | 90.8       | 92.9           | T5 RIGHT, r 25.90, z +7.5 | 63.1       | T3_T4, r 24.78, z +4.5, Tangente 63° | -68.4      | T4_T5      | 103.3   | T4   |
| `pos_016_W1_QS` | LOAD_16NM | +2.11 %  | 81.7       | 101.9          | T5 RIGHT, r 25.90, z +0.0 | 80.5       | T3_T4, r 24.83, z +0.0, Tangente 45° | -94.4      | T4_T5      | 98.2    | T4   |
| `pos_016_W2_QS` | LOAD_16NM | +1.63 %  | 91.1       | 77.2           | T5 RIGHT, r 25.90, z +0.0 | 49.1       | T3_T4, r 24.79, z -4.5, Tangente 58° | -56.8      | T4_T5      | 108.1   | T4   |
| `pos_016_W3_QS` | LOAD_16NM | +1.90 %  | 83.8       | 91.1           | T5 RIGHT, r 25.90, z +0.0 | 93.1       | T3_T4, r 24.86, z +6.8, Tangente 37° | -106.1     | T4_T5      | 95.7    | T4   |
| `pos_016_W4_QS` | LOAD_16NM | +1.45 %  | 92.1       | 71.8           | T5 RIGHT, r 25.90, z -7.5 | 62.8       | T3_T4, r 24.78, z +4.5, Tangente 63° | -69.4      | T4_T5      | 104.3   | T4   |
| `pos_017_W1_QS` | LOAD_16NM | -0.99 %  | 82.2       | 74.0           | T4 RIGHT, r 26.10, z +0.0 | 81.8       | T3_T4, r 24.83, z +0.0, Tangente 45° | -99.9      | T4_T5      | 98.2    | T4   |
| `pos_017_W2_QS` | LOAD_16NM | -0.08 %  | 92.7       | 76.9           | T5 RIGHT, r 26.00, z -6.0 | 49.4       | T3_T4, r 24.79, z -6.0, Tangente 58° | -58.0      | T4_T5      | 109.6   | T4   |
| `pos_017_W3_QS` | LOAD_16NM | -0.93 %  | 84.0       | 80.4           | T5 RIGHT, r 26.00, z +7.5 | 95.1       | T3_T4, r 24.86, z +6.8, Tangente 37° | -111.7     | T4_T5      | 95.6    | T4   |
| `pos_017_W4_QS` | LOAD_16NM | -0.21 %  | 93.6       | 82.7           | T5 RIGHT, r 26.00, z +7.5 | 63.2       | T3_T4, r 24.78, z +4.5, Tangente 63° | -71.6      | T4_T5      | 105.9   | T4   |
| `pos_018_W1_QS` | LOAD_16NM | -1.23 %  | 81.5       | 75.1           | T4 RIGHT, r 26.10, z +0.0 | 81.3       | T3_T4, r 24.83, z +0.0, Tangente 45° | -100.7     | T4_T5      | 97.3    | T4   |
| `pos_018_W2_QS` | LOAD_16NM | -1.17 %  | 92.3       | 71.5           | T5 RIGHT, r 26.00, z -6.0 | 49.2       | T3_T4, r 24.80, z -6.0, Tangente 54° | -58.2      | T4_T5      | 108.5   | T4   |
| `pos_018_W3_QS` | LOAD_16NM | -1.23 %  | 83.1       | 70.6           | T4 RIGHT, r 26.10, z -7.5 | 94.6       | T3_T4, r 24.86, z +6.8, Tangente 37° | -111.5     | T4_T5      | 94.0    | T4   |
| `pos_018_W4_QS` | LOAD_16NM | -1.19 %  | 92.9       | 76.3           | T5 RIGHT, r 26.00, z +7.5 | 62.8       | T3_T4, r 24.78, z +4.5, Tangente 63° | -72.2      | T4_T5      | 104.8   | T4   |
| `pos_019_W1_QS` | LOAD_16NM | -1.29 %  | 81.1       | 74.0           | T4 RIGHT, r 26.10, z +0.0 | 81.2       | T3_T4, r 24.83, z +0.0, Tangente 45° | -101.9     | T4_T5      | 96.6    | T4   |
| `pos_019_W2_QS` | LOAD_16NM | -0.64 %  | 92.4       | 63.4           | T5 RIGHT, r 26.00, z -3.0 | 49.3       | T3_T4, r 24.80, z -6.0, Tangente 54° | -58.5      | T4_T5      | 108.8   | T4   |
| `pos_019_W3_QS` | LOAD_16NM | -1.10 %  | 82.9       | 70.8           | T4 RIGHT, r 26.00, z +7.5 | 94.9       | T3_T4, r 24.86, z +6.8, Tangente 37° | -112.2     | T4_T5      | 93.4    | T4   |
| `pos_019_W4_QS` | LOAD_16NM | -0.79 %  | 92.5       | 66.3           | T5 RIGHT, r 26.00, z +7.5 | 62.2       | T3_T4, r 24.78, z +4.5, Tangente 63° | -72.7      | T4_T5      | 103.6   | T4   |
| `pos_020_W1_QS` | LOAD_16NM | -1.98 %  | 83.2       | 77.8           | T4 RIGHT, r 26.00, z +0.0 | 83.7       | T3_T4, r 24.85, z +0.0, Tangente 40° | -107.5     | T4_T5      | 98.8    | T4   |
| `pos_020_W2_QS` | LOAD_16NM | -0.45 %  | 95.9       | 62.0           | T3 RIGHT, r 26.89, z +0.0 | 50.2       | T3_T4, r 24.80, z -6.0, Tangente 54° | -59.9      | T4_T5      | 112.7   | T4   |
| `pos_020_W3_QS` | LOAD_16NM | -1.66 %  | 85.2       | 74.5           | T4 RIGHT, r 25.90, z -7.5 | 98.6       | T3_T4, r 24.86, z +6.8, Tangente 37° | -118.2     | T4_T5      | 95.9    | T4   |
| `pos_020_W4_QS` | LOAD_16NM | -0.60 %  | 95.8       | 60.4           | T3 RIGHT, r 26.89, z -6.8 | 63.1       | T3_T4, r 24.78, z +4.5, Tangente 63° | -75.7      | T4_T5      | 107.4   | T4   |
| `pos_021_W1_QS` | LOAD_16NM | -1.92 %  | 80.9       | 77.9           | T4 RIGHT, r 26.00, z +0.0 | 81.5       | T3_T4, r 24.85, z +0.0, Tangente 40° | -104.9     | T4_T5      | 95.5    | T4   |
| `pos_021_W2_QS` | LOAD_16NM | -2.22 %  | 98.4       | 61.7           | T3 RIGHT, r 26.89, z +0.0 | 50.7       | T3_T4, r 24.80, z -6.0, Tangente 54° | -61.0      | T4_T5      | 114.9   | T4   |
| `pos_021_W3_QS` | LOAD_16NM | -1.96 %  | 83.4       | 76.7           | T4 RIGHT, r 25.90, z -7.5 | 97.1       | T3_T4, r 24.86, z +6.8, Tangente 37° | -116.3     | T4_T5      | 93.3    | T4   |
| `pos_021_W4_QS` | LOAD_16NM | -2.18 %  | 97.1       | 60.4           | T3 RIGHT, r 26.89, z +0.8 | 63.6       | T3_T4, r 24.88, z +6.8, Tangente 33° | -77.8      | T4_T5      | 108.5   | T4   |
| `pos_022_W1_QS` | LOAD_16NM | -1.77 %  | 78.4       | 75.7           | T4 RIGHT, r 26.00, z +0.0 | 79.7       | T3_T4, r 24.83, z -6.8, Tangente 45° | -102.2     | T4_T5      | 92.5    | T4   |
| `pos_022_W2_QS` | LOAD_16NM | -2.03 %  | 95.3       | 59.7           | T3 RIGHT, r 26.89, z +0.0 | 49.8       | T3_T4, r 24.80, z -6.0, Tangente 54° | -60.1      | T4_T5      | 110.9   | T4   |
| `pos_022_W3_QS` | LOAD_16NM | -1.81 %  | 81.0       | 77.9           | T4 RIGHT, r 25.90, z -7.5 | 94.7       | T3_T4, r 24.86, z +6.8, Tangente 37° | -113.0     | T4_T5      | 90.0    | T4   |
| `pos_022_W4_QS` | LOAD_16NM | -2.01 %  | 94.3       | 59.0           | T3 RIGHT, r 26.89, z +0.8 | 62.5       | T3_T4, r 24.88, z +6.8, Tangente 33° | -76.9      | T4_T5      | 104.5   | T4   |
| `pos_023_W1_QS` | LOAD_16NM | -1.64 %  | 76.3       | 75.9           | T3 RIGHT, r 26.89, z -7.5 | 78.1       | T3_T4, r 24.83, z -6.8, Tangente 45° | -99.7      | T4_T5      | 89.5    | T4   |
| `pos_023_W2_QS` | LOAD_16NM | -1.82 %  | 92.6       | 58.2           | T3 RIGHT, r 26.89, z +0.0 | 49.1       | T3_T4, r 24.80, z -6.0, Tangente 54° | -59.4      | T4_T5      | 107.4   | T4   |
| `pos_023_W3_QS` | LOAD_16NM | -1.68 %  | 78.8       | 78.5           | T4 RIGHT, r 25.90, z -7.5 | 92.6       | T3_T4, r 24.86, z +6.8, Tangente 37° | -109.9     | T4_T5      | 87.2    | T4   |
| `pos_023_W4_QS` | LOAD_16NM | -1.80 %  | 91.9       | 57.7           | T3 RIGHT, r 26.89, z +0.8 | 61.3       | T3_T4, r 24.88, z +6.8, Tangente 33° | -76.0      | T4_T5      | 100.9   | T4   |
| `pos_024_W1_QS` | LOAD_16NM | -1.51 %  | 74.4       | 77.0           | T4 RIGHT, r 25.90, z +0.0 | 76.4       | T3_T4, r 24.83, z -6.8, Tangente 45° | -97.1      | T4_T5      | 86.5    | T4   |
| `pos_024_W2_QS` | LOAD_16NM | -1.57 %  | 90.6       | 57.5           | T4 RIGHT, r 25.80, z -6.0 | 48.3       | T3_T4, r 24.80, z -6.0, Tangente 54° | -58.6      | T4_T5      | 104.4   | T4   |
| `pos_024_W3_QS` | LOAD_16NM | -1.52 %  | 76.8       | 79.3           | T4 RIGHT, r 25.90, z -7.5 | 90.7       | T3_T4, r 24.86, z +6.8, Tangente 37° | -107.0     | T4_T5      | 84.5    | T4   |
| `pos_024_W4_QS` | LOAD_16NM | -1.55 %  | 90.0       | 60.5           | T4 RIGHT, r 25.70, z +7.5 | 60.5       | T3_T4, r 24.88, z +6.8, Tangente 33° | -75.3      | T4_T5      | 98.5    | T4   |
| `pos_025_W1_QS` | LOAD_16NM | -1.34 %  | 72.7       | 76.7           | T4 RIGHT, r 25.90, z +0.0 | 75.1       | T3_T4, r 24.83, z -6.8, Tangente 45° | -95.1      | T4_T5      | 84.3    | T4   |
| `pos_025_W2_QS` | LOAD_16NM | -1.32 %  | 89.4       | 60.8           | T4 RIGHT, r 25.80, z -6.0 | 47.6       | T3_T4, r 24.80, z -6.0, Tangente 54° | -57.9      | T4_T5      | 101.9   | T4   |
| `pos_025_W3_QS` | LOAD_16NM | -1.36 %  | 75.2       | 79.8           | T4 RIGHT, r 25.90, z -7.5 | 88.8       | T3_T4, r 24.86, z +6.8, Tangente 37° | -104.2     | T4_T5      | 81.9    | T4   |
| `pos_025_W4_QS` | LOAD_16NM | -1.28 %  | 88.6       | 65.9           | T4 RIGHT, r 25.70, z +7.5 | 59.7       | T3_T4, r 24.88, z +6.8, Tangente 33° | -74.5      | T4_T5      | 96.2    | T4   |
| `pos_026_W1_QS` | LOAD_16NM | -1.17 %  | 71.3       | 78.9           | T4 RIGHT, r 25.80, z -6.8 | 73.9       | T3_T4, r 24.83, z -6.8, Tangente 45° | -93.3      | T4_T5      | 82.3    | T4   |
| `pos_026_W2_QS` | LOAD_16NM | -1.08 %  | 88.1       | 65.9           | T4 RIGHT, r 25.70, z -6.0 | 46.9       | T3_T4, r 24.82, z -6.0, Tangente 49° | -57.3      | T4_T5      | 100.2   | T4   |
| `pos_026_W3_QS` | LOAD_16NM | -1.18 %  | 73.9       | 83.5           | T4 RIGHT, r 25.70, z +7.5 | 87.6       | T3_T4, r 24.86, z +6.8, Tangente 37° | -102.2     | T4_T5      | 80.1    | T4   |
| `pos_026_W4_QS` | LOAD_16NM | -1.06 %  | 87.5       | 71.9           | T4 RIGHT, r 25.70, z +7.5 | 59.0       | T3_T4, r 24.88, z +6.8, Tangente 33° | -73.7      | T4_T5      | 94.1    | T4   |
| `pos_027_W1_QS` | LOAD_16NM | -0.99 %  | 70.2       | 83.4           | T4 RIGHT, r 25.70, z -6.8 | 72.9       | T3_T4, r 24.83, z -6.8, Tangente 45° | -91.5      | T4_T5      | 80.4    | T4   |
| `pos_027_W2_QS` | LOAD_16NM | -0.86 %  | 87.4       | 71.5           | T4 RIGHT, r 25.70, z -6.0 | 46.6       | T3_T4, r 24.82, z -6.0, Tangente 49° | -56.8      | T4_T5      | 99.3    | T4   |
| `pos_027_W3_QS` | LOAD_16NM | -0.96 %  | 72.9       | 95.1           | T4 RIGHT, r 25.70, z +7.5 | 86.7       | T3_T4, r 24.86, z +6.8, Tangente 37° | -100.3     | T4_T5      | 78.5    | T4   |
| `pos_027_W4_QS` | LOAD_16NM | -0.84 %  | 87.0       | 77.7           | T4 RIGHT, r 25.70, z +7.5 | 58.8       | T3_T4, r 24.88, z +6.8, Tangente 33° | -72.9      | T4_T5      | 93.0    | T3   |
| `pos_028_W1_QS` | LOAD_16NM | -0.82 %  | 69.4       | 95.5           | T4 RIGHT, r 25.70, z -6.8 | 72.1       | T3_T4, r 24.83, z -6.8, Tangente 45° | -90.0      | T4_T5      | 78.8    | T4   |
| `pos_028_W2_QS` | LOAD_16NM | -0.69 %  | 87.4       | 76.6           | T4 RIGHT, r 25.70, z -6.0 | 46.5       | T3_T4, r 24.82, z -6.0, Tangente 49° | -56.4      | T4_T5      | 99.1    | T4   |
| `pos_028_W3_QS` | LOAD_16NM | -0.82 %  | 71.9       | 106.2          | T4 RIGHT, r 25.70, z +7.5 | 85.4       | T3_T4, r 24.86, z +6.8, Tangente 37° | -98.2      | T4_T5      | 78.1    | T3   |
| `pos_028_W4_QS` | LOAD_16NM | -0.66 %  | 86.8       | 81.7           | T4 RIGHT, r 25.70, z +7.5 | 59.1       | T3_T4, r 24.88, z +6.8, Tangente 33° | -72.3      | T4_T5      | 94.4    | T3   |
| `pos_029_W1_QS` | LOAD_16NM | -0.66 %  | 68.5       | 105.9          | T4 RIGHT, r 25.70, z -6.8 | 71.2       | T3_T4, r 24.83, z -6.8, Tangente 45° | -88.6      | T4_T5      | 77.5    | T4   |
| `pos_029_W2_QS` | LOAD_16NM | -0.54 %  | 86.6       | 79.8           | T4 RIGHT, r 25.70, z -6.0 | 45.8       | T3_T4, r 24.82, z -6.0, Tangente 49° | -55.7      | T4_T5      | 97.3    | T4   |
| `pos_029_W3_QS` | LOAD_16NM | -0.67 %  | 71.2       | 116.9          | T4 RIGHT, r 25.70, z +7.5 | 84.2       | T3_T4, r 24.86, z +6.8, Tangente 37° | -96.5      | T4_T5      | 78.4    | T3   |
| `pos_029_W4_QS` | LOAD_16NM | -0.52 %  | 86.1       | 84.2           | T4 RIGHT, r 25.70, z +7.5 | 58.6       | T3_T4, r 24.88, z +6.8, Tangente 33° | -71.5      | T4_T5      | 94.6    | T3   |
| `pos_030_W1_QS` | LOAD_16NM | -0.49 %  | 68.0       | 116.1          | T4 RIGHT, r 25.70, z -6.8 | 70.4       | T3_T4, r 24.83, z -6.8, Tangente 45° | -87.3      | T4_T5      | 76.2    | T4   |
| `pos_030_W2_QS` | LOAD_16NM | -0.40 %  | 86.1       | 82.8           | T4 RIGHT, r 25.70, z -6.0 | 45.1       | T3_T4, r 24.82, z -6.0, Tangente 49° | -55.0      | T4_T5      | 95.9    | T3   |
| `pos_030_W3_QS` | LOAD_16NM | -0.48 %  | 70.7       | 126.5          | T4 RIGHT, r 25.70, z +7.5 | 83.5       | T3_T4, r 24.86, z +6.8, Tangente 37° | -95.3      | T4_T5      | 78.4    | T3   |
| `pos_030_W4_QS` | LOAD_16NM | -0.34 %  | 85.6       | 86.7           | T4 RIGHT, r 25.70, z +7.5 | 58.0       | T3_T4, r 24.88, z +6.8, Tangente 33° | -70.8      | T4_T5      | 94.6    | T3   |
| `pos_031_W1_QS` | LOAD_16NM | -0.37 %  | 67.6       | 126.2          | T4 RIGHT, r 25.70, z -6.8 | 69.4       | T3_T4, r 24.83, z -6.8, Tangente 45° | -85.8      | T4_T5      | 76.0    | T3   |
| `pos_031_W2_QS` | LOAD_16NM | -0.24 %  | 85.6       | 84.8           | T4 RIGHT, r 25.70, z -6.0 | 44.7       | T3_T4, r 24.82, z -6.0, Tangente 49° | -54.5      | T4_T5      | 96.4    | T3   |
| `pos_031_W3_QS` | LOAD_16NM | -0.35 %  | 70.2       | 135.6          | T4 RIGHT, r 25.70, z +7.5 | 82.5       | T3_T4, r 24.86, z +6.8, Tangente 37° | -93.7      | T4_T5      | 77.8    | T3   |
| `pos_031_W4_QS` | LOAD_16NM | -0.21 %  | 85.2       | 88.9           | T4 RIGHT, r 25.70, z +7.5 | 57.3       | T3_T4, r 24.88, z +6.8, Tangente 33° | -69.9      | T4_T5      | 94.2    | T3   |
| `pos_032_W1_QS` | LOAD_16NM | -0.30 %  | 67.2       | 135.9          | T4 RIGHT, r 25.70, z -6.8 | 68.4       | T3_T4, r 24.85, z -6.8, Tangente 40° | -84.2      | T4_T5      | 76.0    | T3   |
| `pos_032_W2_QS` | LOAD_16NM | -0.15 %  | 84.8       | 86.5           | T4 RIGHT, r 25.70, z -6.0 | 44.1       | T3_T4, r 24.83, z -6.0, Tangente 45° | -53.9      | T4_T5      | 96.2    | T3   |
| `pos_032_W3_QS` | LOAD_16NM | -0.23 %  | 70.0       | 144.9          | T4 RIGHT, r 25.70, z +7.5 | 81.7       | T3_T4, r 24.86, z +6.8, Tangente 37° | -92.3      | T4_T5      | 77.5    | T3   |
| `pos_032_W4_QS` | LOAD_16NM | -0.11 %  | 85.0       | 90.7           | T4 RIGHT, r 25.70, z +7.5 | 56.6       | T3_T4, r 24.88, z +6.8, Tangente 33° | -69.0      | T4_T5      | 94.3    | T3   |
| `pos_033_W1_QS` | LOAD_16NM | -0.10 %  | 67.0       | 143.5          | T4 RIGHT, r 25.70, z -6.8 | 67.0       | T3_T4, r 24.85, z -6.8, Tangente 40° | -83.1      | T4_T5      | 76.2    | T3   |
| `pos_033_W2_QS` | LOAD_16NM | +0.07 %  | 84.7       | 87.3           | T4 RIGHT, r 25.70, z -6.0 | 43.2       | T3_T4, r 24.83, z +0.0, Tangente 45° | -53.4      | T4_T5      | 96.6    | T3   |
| `pos_033_W3_QS` | LOAD_16NM | -0.01 %  | 69.8       | 151.4          | T4 RIGHT, r 25.70, z +7.5 | 78.1       | T3_T4, r 24.86, z +6.8, Tangente 37° | -90.6      | T4_T5      | 77.4    | T3   |
| `pos_033_W4_QS` | LOAD_16NM | +0.13 %  | 84.8       | 91.0           | T4 RIGHT, r 25.70, z +7.5 | 56.9       | T2_T3, r 24.78, z +6.0, Tangente 63° | -68.3      | T4_T5      | 94.5    | T3   |
| `pos_034_W1_QS` | LOAD_16NM | +0.64 %  | 67.6       | 141.2          | T4 RIGHT, r 25.70, z +0.0 | 62.4       | T3_T4, r 24.83, z -6.8, Tangente 45° | -82.1      | T4_T5      | 77.5    | T3   |
| `pos_034_W2_QS` | LOAD_16NM | +0.63 %  | 85.0       | 86.9           | T4 RIGHT, r 25.80, z -6.0 | 43.1       | T2_T3, r 24.80, z -4.5, Tangente 54° | -52.7      | T4_T5      | 97.8    | T3   |
| `pos_034_W3_QS` | LOAD_16NM | +0.83 %  | 70.9       | 137.5          | T4 RIGHT, r 25.70, z +7.5 | 69.8       | T3_T4, r 24.86, z +6.8, Tangente 37° | -89.7      | T4_T5      | 79.0    | T3   |
| `pos_034_W4_QS` | LOAD_16NM | +0.76 %  | 85.4       | 85.3           | T4 RIGHT, r 25.70, z +6.8 | 57.7       | T2_T3, r 24.78, z +6.0, Tangente 63° | -67.7      | T4_T5      | 95.7    | T3   |
| `pos_035_W1_QS` | LOAD_16NM | +1.43 %  | 69.3       | 129.4          | T4 RIGHT, r 25.80, z -6.8 | 58.1       | T3_T4, r 24.83, z -6.8, Tangente 45° | -81.3      | T4_T5      | 79.7    | T3   |
| `pos_035_W2_QS` | LOAD_16NM | +1.29 %  | 86.3       | 90.6           | T4 RIGHT, r 25.80, z -6.0 | 43.7       | T2_T3, r 24.80, z -4.5, Tangente 54° | -52.2      | T4_T5      | 99.5    | T3   |
| `pos_035_W3_QS` | LOAD_16NM | +1.42 %  | 72.5       | 133.5          | T4 RIGHT, r 25.80, z -7.5 | 68.5       | T2_T3, r 24.85, z +6.8, Tangente 40° | -88.3      | T4_T5      | 81.2    | T3   |
| `pos_035_W4_QS` | LOAD_16NM | +1.33 %  | 86.8       | 87.9           | T4 RIGHT, r 25.80, z +6.8 | 58.8       | T2_T3, r 24.78, z +6.0, Tangente 63° | -67.0      | T4_T5      | 97.7    | T3   |
| `pos_036_W1_QS` | LOAD_16NM | +1.49 %  | 70.3       | 145.7          | T4 RIGHT, r 25.80, z -6.8 | 59.1       | T2_T3, r 24.82, z -5.2, Tangente 49° | -80.2      | T4_T5      | 81.1    | T3   |
| `pos_036_W2_QS` | LOAD_16NM | +1.54 %  | 87.1       | 92.2           | T4 RIGHT, r 25.80, z -6.0 | 44.1       | T2_T3, r 24.79, z -4.5, Tangente 58° | -51.7      | T4_T5      | 100.6   | T3   |
| `pos_036_W3_QS` | LOAD_16NM | +1.45 %  | 73.5       | 150.8          | T4 RIGHT, r 25.80, z -7.5 | 70.3       | T2_T3, r 24.85, z +6.8, Tangente 40° | -87.2      | T4_T5      | 82.5    | T3   |
| `pos_036_W4_QS` | LOAD_16NM | +1.51 %  | 87.6       | 90.4           | T4 RIGHT, r 25.80, z +6.8 | 59.5       | T2_T3, r 24.78, z +6.0, Tangente 63° | -66.4      | T4_T5      | 98.7    | T3   |
| `pos_037_W1_QS` | LOAD_16NM | +1.46 %  | 70.9       | 157.1          | T4 RIGHT, r 25.80, z -6.8 | 60.3       | T2_T3, r 24.82, z -5.2, Tangente 49° | -79.5      | T4_T5      | 82.3    | T3   |
| `pos_037_W2_QS` | LOAD_16NM | +1.67 %  | 87.7       | 92.9           | T4 RIGHT, r 25.80, z -6.0 | 44.5       | T2_T3, r 24.79, z -4.5, Tangente 58° | -51.4      | T4_T5      | 101.7   | T3   |
| `pos_037_W3_QS` | LOAD_16NM | +1.33 %  | 74.1       | 161.2          | T4 RIGHT, r 25.80, z -7.5 | 71.5       | T2_T3, r 24.85, z +6.8, Tangente 40° | -86.4      | T4_T5      | 83.2    | T3   |
| `pos_037_W4_QS` | LOAD_16NM | +1.59 %  | 88.2       | 92.5           | T4 RIGHT, r 25.80, z +6.8 | 60.0       | T2_T3, r 24.78, z +6.0, Tangente 63° | -65.9      | T4_T5      | 99.5    | T3   |
| `pos_038_W1_QS` | LOAD_16NM | +0.62 %  | 72.2       | 180.1          | T4 RIGHT, r 25.80, z -6.8 | 63.1       | T2_T3, r 24.82, z -5.2, Tangente 49° | -77.3      | T4_T5      | 84.4    | T3   |
| `pos_038_W2_QS` | LOAD_16NM | +1.38 %  | 89.3       | 94.7           | T4 RIGHT, r 25.80, z -6.0 | 45.5       | T2_T3, r 24.79, z -4.5, Tangente 58° | -50.6      | T4_T5      | 104.3   | T3   |
| `pos_038_W3_QS` | LOAD_16NM | +0.55 %  | 75.1       | 184.4          | T4 RIGHT, r 25.80, z +7.5 | 74.9       | T2_T3, r 24.85, z +6.8, Tangente 40° | -83.7      | T4_T5      | 85.0    | T3   |
| `pos_038_W4_QS` | LOAD_16NM | +1.33 %  | 90.1       | 96.3           | T4 RIGHT, r 25.80, z +6.8 | 61.5       | T2_T3, r 24.78, z +6.0, Tangente 63° | -64.5      | T4_T5      | 102.2   | T3   |
| `pos_039_W1_QS` | LOAD_16NM | +0.48 %  | 72.5       | 182.0          | T4 RIGHT, r 25.80, z -6.8 | 64.4       | T2_T3, r 24.82, z -5.2, Tangente 49° | -75.2      | T4_T5      | 84.9    | T3   |
| `pos_039_W2_QS` | LOAD_16NM | +0.48 %  | 90.2       | 97.9           | T4 RIGHT, r 25.80, z -6.0 | 46.2       | T2_T3, r 24.79, z -4.5, Tangente 58° | -49.7      | T3_T4      | 105.4   | T3   |
| `pos_039_W3_QS` | LOAD_16NM | +0.49 %  | 75.4       | 185.4          | T4 RIGHT, r 25.80, z -7.5 | 76.4       | T2_T3, r 24.85, z +6.8, Tangente 40° | -81.8      | T4_T5      | 85.8    | T3   |
| `pos_039_W4_QS` | LOAD_16NM | +0.51 %  | 90.7       | 98.8           | T4 RIGHT, r 25.80, z +6.8 | 62.7       | T2_T3, r 24.78, z +6.0, Tangente 63° | -62.6      | T4_T5      | 103.5   | T3   |
| `pos_040_W1_QS` | LOAD_16NM | +0.54 %  | 73.0       | 183.0          | T4 RIGHT, r 25.80, z -6.8 | 66.0       | T2_T3, r 24.82, z -5.2, Tangente 49° | -73.2      | T4_T5      | 86.1    | T3   |
| `pos_040_W2_QS` | LOAD_16NM | +0.53 %  | 90.4       | 98.8           | T4 RIGHT, r 25.80, z -6.0 | 46.7       | T2_T3, r 24.79, z -4.5, Tangente 58° | -50.3      | T3_T4      | 106.3   | T3   |
| `pos_040_W3_QS` | LOAD_16NM | +0.49 %  | 75.7       | 186.5          | T4 RIGHT, r 25.80, z -7.5 | 77.7       | T2_T3, r 24.85, z +6.8, Tangente 40° | -80.4      | T3_T4      | 86.0    | T3   |
| `pos_040_W4_QS` | LOAD_16NM | +0.56 %  | 90.9       | 99.5           | T4 RIGHT, r 25.80, z +6.8 | 63.1       | T2_T3, r 24.78, z +6.0, Tangente 63° | -63.1      | T3_T4      | 103.7   | T3   |
| `pos_041_W1_QS` | LOAD_16NM | +1.11 %  | 73.8       | 181.5          | T4 RIGHT, r 25.80, z +0.0 | 67.5       | T2_T3, r 24.82, z -5.2, Tangente 49° | -71.2      | T4_T5      | 87.3    | T3   |
| `pos_041_W2_QS` | LOAD_16NM | +1.23 %  | 91.3       | 95.7           | T4 RIGHT, r 25.80, z -6.0 | 47.2       | T2_T3, r 24.79, z -4.5, Tangente 58° | -50.9      | T3_T4      | 107.7   | T3   |
| `pos_041_W3_QS` | LOAD_16NM | +1.66 %  | 77.3       | 179.3          | T4 RIGHT, r 25.80, z +7.5 | 79.9       | T2_T3, r 24.85, z +6.8, Tangente 40° | -82.2      | T3_T4      | 88.3    | T3   |
| `pos_041_W4_QS` | LOAD_16NM | +1.26 %  | 91.8       | 96.1           | T4 RIGHT, r 25.80, z +6.8 | 64.0       | T2_T3, r 24.78, z +6.0, Tangente 63° | -64.0      | T3_T4      | 105.0   | T3   |
| `pos_042_W1_QS` | LOAD_16NM | +3.24 %  | 77.9       | 141.9          | T4 RIGHT, r 25.80, z +0.0 | 71.3       | T2_T3, r 24.82, z -5.2, Tangente 49° | -73.2      | T3_T4      | 92.2    | T3   |
| `pos_042_W2_QS` | LOAD_16NM | +2.36 %  | 93.6       | 95.9           | T4 RIGHT, r 25.90, z -6.0 | 48.0       | T2_T3, r 24.79, z -4.5, Tangente 58° | -51.8      | T3_T4      | 110.2   | T3   |
| `pos_042_W3_QS` | LOAD_16NM | +3.04 %  | 81.1       | 129.1          | T4 RIGHT, r 25.90, z -7.5 | 84.5       | T2_T3, r 24.85, z +6.8, Tangente 40° | -87.1      | T3_T4      | 92.9    | T3   |
| `pos_042_W4_QS` | LOAD_16NM | +2.34 %  | 94.5       | 100.3          | T4 RIGHT, r 25.90, z -7.5 | 65.4       | T2_T3, r 24.78, z +6.0, Tangente 63° | -65.5      | T3_T4      | 108.4   | T3   |
| `pos_043_W1_QS` | LOAD_16NM | +2.35 %  | 80.5       | 149.2          | T4 RIGHT, r 25.90, z -6.8 | 75.8       | T2_T3, r 24.82, z -5.2, Tangente 49° | -80.1      | T3_T4      | 96.0    | T3   |
| `pos_043_W2_QS` | LOAD_16NM | +2.64 %  | 96.1       | 96.2           | T4 RIGHT, r 25.90, z -6.0 | 49.0       | T2_T3, r 24.79, z -4.5, Tangente 58° | -53.2      | T3_T4      | 113.7   | T3   |
| `pos_043_W3_QS` | LOAD_16NM | +2.14 %  | 83.6       | 175.6          | T4 RIGHT, r 25.90, z -7.5 | 89.1       | T2_T3, r 24.85, z +6.8, Tangente 40° | -94.4      | T3_T4      | 95.7    | T3   |
| `pos_043_W4_QS` | LOAD_16NM | +2.42 %  | 96.9       | 103.4          | T4 RIGHT, r 25.90, z -7.5 | 66.9       | T2_T3, r 24.77, z +6.0, Tangente 68° | -67.5      | T3_T4      | 111.1   | T3   |
| `pos_044_W1_QS` | LOAD_16NM | +0.51 %  | 81.8       | 165.5          | T4 RIGHT, r 25.90, z -6.8 | 79.0       | T2_T3, r 24.83, z -4.5, Tangente 45° | -86.1      | T3_T4      | 98.0    | T3   |
| `pos_044_W2_QS` | LOAD_16NM | +0.79 %  | 97.3       | 98.4           | T4 RIGHT, r 25.90, z -6.0 | 49.7       | T2_T3, r 24.79, z -4.5, Tangente 58° | -54.6      | T3_T4      | 115.4   | T3   |
| `pos_044_W3_QS` | LOAD_16NM | +0.46 %  | 84.6       | 188.7          | T4 RIGHT, r 25.90, z -7.5 | 92.7       | T2_T3, r 24.85, z +6.8, Tangente 40° | -100.4     | T3_T4      | 97.4    | T3   |
| `pos_044_W4_QS` | LOAD_16NM | +0.59 %  | 97.6       | 106.0          | T4 RIGHT, r 25.90, z -7.5 | 67.6       | T2_T3, r 24.78, z +6.0, Tangente 63° | -69.7      | T3_T4      | 112.0   | T3   |
| `pos_045_W1_QS` | LOAD_16NM | +0.39 %  | 82.1       | 154.2          | T4 RIGHT, r 25.90, z -6.8 | 80.2       | T2_T3, r 24.82, z -5.2, Tangente 49° | -88.1      | T3_T4      | 98.1    | T3   |
| `pos_045_W2_QS` | LOAD_16NM | +0.09 %  | 94.5       | 97.1           | T4 RIGHT, r 25.90, z -6.0 | 48.8       | T2_T3, r 24.79, z -4.5, Tangente 58° | -54.1      | T3_T4      | 111.6   | T3   |
| `pos_045_W3_QS` | LOAD_16NM | +0.39 %  | 84.9       | 177.1          | T4 RIGHT, r 25.90, z -7.5 | 94.2       | T2_T3, r 24.85, z +6.8, Tangente 40° | -102.4     | T3_T4      | 97.8    | T3   |
| `pos_045_W4_QS` | LOAD_16NM | +0.03 %  | 94.6       | 104.9          | T4 RIGHT, r 25.90, z -7.5 | 66.3       | T2_T3, r 24.78, z +6.0, Tangente 63° | -69.1      | T3_T4      | 108.5   | T3   |
| `pos_046_W1_QS` | LOAD_16NM | +1.30 %  | 82.5       | 145.6          | T4 RIGHT, r 25.90, z +0.0 | 80.6       | T2_T3, r 24.83, z -3.8, Tangente 45° | -89.3      | T3_T4      | 98.9    | T3   |
| `pos_046_W2_QS` | LOAD_16NM | +0.60 %  | 93.0       | 92.1           | T4 RIGHT, r 25.90, z -4.5 | 48.1       | T2_T3, r 24.80, z -4.5, Tangente 54° | -53.8      | T3_T4      | 109.6   | T3   |
| `pos_046_W3_QS` | LOAD_16NM | +1.83 %  | 85.4       | 166.6          | T4 RIGHT, r 25.90, z -7.5 | 94.2       | T2_T3, r 24.85, z +6.8, Tangente 40° | -102.0     | T3_T4      | 97.8    | T3   |
| `pos_046_W4_QS` | LOAD_16NM | +0.75 %  | 93.6       | 97.1           | T4 RIGHT, r 25.90, z -7.5 | 65.2       | T2_T3, r 24.78, z +6.0, Tangente 63° | -68.7      | T3_T4      | 106.7   | T3   |
| `pos_047_W1_QS` | LOAD_16NM | +1.94 %  | 84.8       | 89.5           | T4 RIGHT, r 25.90, z +0.0 | 82.5       | T2_T3, r 24.83, z +0.0, Tangente 45° | -94.0      | T3_T4      | 101.4   | T3   |
| `pos_047_W2_QS` | LOAD_16NM | +1.52 %  | 94.1       | 71.5           | T4 RIGHT, r 25.90, z +0.0 | 48.3       | T2_T3, r 24.88, z -3.0, Tangente 33° | -54.2      | T3_T4      | 110.9   | T3   |
| `pos_047_W3_QS` | LOAD_16NM | +1.62 %  | 86.4       | 79.9           | T4 RIGHT, r 25.90, z -7.5 | 96.3       | T2_T3, r 24.85, z +6.8, Tangente 40° | -106.3     | T3_T4      | 98.9    | T3   |
| `pos_047_W4_QS` | LOAD_16NM | +1.24 %  | 94.7       | 69.7           | T4 RIGHT, r 25.90, z -7.5 | 65.0       | T2_T3, r 24.78, z +6.0, Tangente 63° | -69.5      | T3_T4      | 107.5   | T3   |
| `pos_048_W1_QS` | LOAD_16NM | -1.09 %  | 84.5       | 74.1           | T3 RIGHT, r 26.10, z -6.8 | 83.3       | T2_T3, r 24.83, z +0.0, Tangente 45° | -98.8      | T3_T4      | 100.5   | T3   |
| `pos_048_W2_QS` | LOAD_16NM | -0.55 %  | 95.3       | 76.7           | T4 RIGHT, r 26.00, z -6.0 | 49.0       | T2_T3, r 24.88, z +0.0, Tangente 33° | -55.5      | T3_T4      | 111.8   | T3   |
| `pos_048_W3_QS` | LOAD_16NM | -1.04 %  | 86.1       | 77.3           | T4 RIGHT, r 26.00, z -7.5 | 97.7       | T2_T3, r 24.85, z +6.8, Tangente 40° | -111.2     | T3_T4      | 98.2    | T3   |
| `pos_048_W4_QS` | LOAD_16NM | -0.61 %  | 96.0       | 82.8           | T4 RIGHT, r 26.00, z -7.5 | 65.5       | T2_T3, r 24.78, z +6.0, Tangente 63° | -71.7      | T3_T4      | 109.1   | T3   |
| `pos_049_W1_QS` | LOAD_16NM | -1.25 %  | 84.0       | 74.9           | T3 RIGHT, r 26.10, z +0.0 | 82.9       | T2_T3, r 24.83, z +0.0, Tangente 45° | -99.2      | T3_T4      | 99.8    | T3   |
| `pos_049_W2_QS` | LOAD_16NM | -1.22 %  | 94.8       | 73.0           | T4 RIGHT, r 26.00, z -6.0 | 48.9       | T2_T3, r 24.88, z +0.0, Tangente 33° | -55.6      | T3_T4      | 110.8   | T3   |
| `pos_049_W3_QS` | LOAD_16NM | -1.21 %  | 85.5       | 66.3           | T4 RIGHT, r 26.00, z -7.5 | 97.4       | T2_T3, r 24.85, z +6.8, Tangente 40° | -111.1     | T3_T4      | 97.2    | T3   |
| `pos_049_W4_QS` | LOAD_16NM | -1.22 %  | 95.4       | 78.3           | T4 RIGHT, r 26.00, z -7.5 | 65.2       | T2_T3, r 24.78, z +6.0, Tangente 63° | -71.9      | T3_T4      | 108.2   | T3   |
| `pos_050_W1_QS` | LOAD_16NM | -1.33 %  | 83.7       | 75.1           | T3 RIGHT, r 26.10, z +0.0 | 82.8       | T2_T3, r 24.83, z +0.0, Tangente 45° | -99.6      | T3_T4      | 99.5    | T3   |
| `pos_050_W2_QS` | LOAD_16NM | -1.25 %  | 94.4       | 69.1           | T4 RIGHT, r 26.00, z -6.0 | 48.8       | T2_T3, r 24.88, z +0.0, Tangente 33° | -55.6      | T3_T4      | 110.3   | T3   |
| `pos_050_W3_QS` | LOAD_16NM | -1.30 %  | 85.1       | 66.5           | T3 RIGHT, r 26.10, z +6.8 | 97.1       | T2_T3, r 24.85, z +6.8, Tangente 40° | -111.0     | T3_T4      | 96.5    | T3   |
| `pos_050_W4_QS` | LOAD_16NM | -1.23 %  | 95.0       | 74.5           | T4 RIGHT, r 26.00, z -7.5 | 65.0       | T2_T3, r 24.78, z +6.0, Tangente 63° | -71.8      | T3_T4      | 107.6   | T3   |
| `pos_051_W1_QS` | LOAD_16NM | -1.30 %  | 83.3       | 74.0           | T3 RIGHT, r 26.10, z +0.0 | 82.8       | T2_T3, r 24.83, z +0.0, Tangente 45° | -101.0     | T3_T4      | 99.0    | T3   |
| `pos_051_W2_QS` | LOAD_16NM | -0.78 %  | 94.6       | 62.9           | T2 RIGHT, r 26.89, z -6.8 | 49.0       | T2_T3, r 24.90, z +0.0, Tangente 30° | -55.8      | T3_T4      | 110.6   | T3   |
| `pos_051_W3_QS` | LOAD_16NM | -1.18 %  | 84.9       | 68.4           | T3 RIGHT, r 25.90, z -7.5 | 97.5       | T2_T3, r 24.85, z +6.8, Tangente 40° | -111.9     | T3_T4      | 96.0    | T3   |
| `pos_051_W4_QS` | LOAD_16NM | -0.81 %  | 94.7       | 64.1           | T4 RIGHT, r 26.00, z +7.5 | 64.5       | T2_T3, r 24.78, z +6.0, Tangente 63° | -72.1      | T3_T4      | 106.4   | T3   |
| `pos_052_W1_QS` | LOAD_16NM | -2.06 %  | 84.8       | 77.6           | T3 RIGHT, r 26.00, z +0.0 | 84.8       | T2_T3, r 24.83, z +0.0, Tangente 45° | -105.7     | T3_T4      | 100.3   | T3   |
| `pos_052_W2_QS` | LOAD_16NM | -0.75 %  | 98.2       | 63.4           | T2 RIGHT, r 26.89, z +0.0 | 50.2       | T2_T3, r 24.90, z +0.0, Tangente 30° | -57.4      | T3_T4      | 114.6   | T3   |
| `pos_052_W3_QS` | LOAD_16NM | -1.91 %  | 87.1       | 77.5           | T3 RIGHT, r 25.90, z -7.5 | 101.2      | T2_T3, r 24.85, z +6.8, Tangente 40° | -118.2     | T3_T4      | 98.4    | T3   |
| `pos_052_W4_QS` | LOAD_16NM | -0.85 %  | 98.1       | 61.2           | T2 RIGHT, r 26.89, z +0.8 | 65.5       | T2_T3, r 24.78, z +6.0, Tangente 63° | -75.6      | T3_T4      | 110.2   | T3   |
| `pos_053_W1_QS` | LOAD_16NM | -1.94 %  | 82.3       | 77.6           | T3 RIGHT, r 26.00, z +0.0 | 82.4       | T2_T3, r 24.83, z +0.0, Tangente 45° | -102.8     | T3_T4      | 96.9    | T3   |
| `pos_053_W2_QS` | LOAD_16NM | -2.25 %  | 99.5       | 62.9           | T2 RIGHT, r 26.89, z +0.0 | 50.6       | T2_T3, r 24.90, z +0.0, Tangente 30° | -58.9      | T3_T4      | 115.4   | T3   |
| `pos_053_W3_QS` | LOAD_16NM | -1.97 %  | 84.8       | 79.1           | T3 RIGHT, r 25.90, z -7.5 | 99.0       | T2_T3, r 24.85, z +6.8, Tangente 40° | -115.2     | T3_T4      | 95.1    | T3   |
| `pos_053_W4_QS` | LOAD_16NM | -2.20 %  | 98.8       | 61.1           | T2 RIGHT, r 26.89, z +0.8 | 65.6       | T2_T3, r 24.78, z +6.0, Tangente 63° | -77.8      | T3_T4      | 110.7   | T3   |
| `pos_054_W1_QS` | LOAD_16NM | -1.78 %  | 79.8       | 75.5           | T3 RIGHT, r 26.00, z +0.0 | 80.7       | T2_T3, r 24.83, z -6.8, Tangente 45° | -100.2     | T3_T4      | 93.8    | T3   |
| `pos_054_W2_QS` | LOAD_16NM | -2.04 %  | 96.3       | 60.6           | T2 RIGHT, r 26.89, z +0.0 | 49.8       | T2_T3, r 24.90, z +0.0, Tangente 30° | -58.4      | T3_T4      | 111.5   | T3   |
| `pos_054_W3_QS` | LOAD_16NM | -1.83 %  | 82.4       | 80.1           | T3 RIGHT, r 25.90, z -7.5 | 96.6       | T2_T3, r 24.85, z +6.8, Tangente 40° | -111.9     | T3_T4      | 91.7    | T3   |
| `pos_054_W4_QS` | LOAD_16NM | -2.01 %  | 95.8       | 59.8           | T2 RIGHT, r 26.89, z +0.8 | 64.1       | T2_T3, r 24.78, z +6.0, Tangente 63° | -76.7      | T3_T4      | 106.6   | T3   |
| `pos_055_W1_QS` | LOAD_16NM | -1.65 %  | 77.7       | 76.7           | T2 RIGHT, r 26.89, z -7.5 | 79.1       | T2_T3, r 24.83, z -6.8, Tangente 45° | -97.7      | T3_T4      | 90.8    | T3   |
| `pos_055_W2_QS` | LOAD_16NM | -1.83 %  | 93.7       | 59.1           | T2 RIGHT, r 26.89, z +0.0 | 49.0       | T2_T3, r 24.90, z +0.0, Tangente 30° | -57.8      | T3_T4      | 108.0   | T3   |
| `pos_055_W3_QS` | LOAD_16NM | -1.69 %  | 80.1       | 80.5           | T3 RIGHT, r 25.90, z -7.5 | 94.5       | T2_T3, r 24.85, z +6.8, Tangente 40° | -108.8     | T3_T4      | 88.9    | T3   |
| `pos_055_W4_QS` | LOAD_16NM | -1.81 %  | 93.5       | 58.4           | T2 RIGHT, r 26.89, z +0.8 | 62.7       | T2_T3, r 24.78, z +6.0, Tangente 63° | -75.8      | T3_T4      | 103.0   | T3   |
| `pos_056_W1_QS` | LOAD_16NM | -1.52 %  | 75.7       | 76.7           | T3 RIGHT, r 25.90, z +0.0 | 77.3       | T2_T3, r 24.83, z -6.8, Tangente 45° | -95.1      | T3_T4      | 87.7    | T3   |
| `pos_056_W2_QS` | LOAD_16NM | -1.60 %  | 91.7       | 58.8           | T3 RIGHT, r 25.80, z -6.0 | 48.2       | T2_T3, r 24.90, z +0.0, Tangente 30° | -57.3      | T3_T4      | 105.0   | T3   |
| `pos_056_W3_QS` | LOAD_16NM | -1.53 %  | 78.1       | 80.9           | T3 RIGHT, r 25.90, z -7.5 | 92.5       | T2_T3, r 24.85, z +6.8, Tangente 40° | -105.9     | T3_T4      | 86.2    | T3   |
| `pos_056_W4_QS` | LOAD_16NM | -1.54 %  | 91.7       | 59.8           | T3 RIGHT, r 25.70, z +7.5 | 61.6       | T2_T3, r 24.78, z +6.0, Tangente 63° | -75.1      | T3_T4      | 100.6   | T3   |
| `pos_057_W1_QS` | LOAD_16NM | -1.35 %  | 74.0       | 76.3           | T3 RIGHT, r 25.90, z +0.0 | 76.0       | T2_T3, r 24.83, z -6.8, Tangente 45° | -93.1      | T3_T4      | 85.6    | T3   |
| `pos_057_W2_QS` | LOAD_16NM | -1.34 %  | 90.3       | 62.2           | T3 RIGHT, r 25.80, z -6.0 | 47.4       | T2_T3, r 24.88, z +0.0, Tangente 33° | -56.8      | T3_T4      | 102.4   | T3   |
| `pos_057_W3_QS` | LOAD_16NM | -1.37 %  | 76.5       | 80.9           | T3 RIGHT, r 25.90, z -7.5 | 90.6       | T2_T3, r 24.85, z +6.8, Tangente 40° | -103.2     | T3_T4      | 83.6    | T3   |
| `pos_057_W4_QS` | LOAD_16NM | -1.29 %  | 90.2       | 65.2           | T3 RIGHT, r 25.70, z +7.5 | 60.5       | T2_T3, r 24.78, z +6.0, Tangente 63° | -74.2      | T3_T4      | 98.3    | T3   |
| `pos_058_W1_QS` | LOAD_16NM | -1.18 %  | 72.6       | 78.6           | T3 RIGHT, r 25.80, z -6.8 | 74.8       | T2_T3, r 24.83, z -6.8, Tangente 45° | -91.2      | T3_T4      | 83.5    | T3   |
| `pos_058_W2_QS` | LOAD_16NM | -1.10 %  | 89.1       | 67.0           | T3 RIGHT, r 25.70, z -6.0 | 46.9       | T2_T3, r 24.88, z +0.0, Tangente 33° | -56.4      | T3_T4      | 100.9   | T3   |
| `pos_058_W3_QS` | LOAD_16NM | -1.18 %  | 75.2       | 80.7           | T3 RIGHT, r 25.70, z +7.5 | 89.4       | T2_T3, r 24.85, z +6.8, Tangente 40° | -101.3     | T3_T4      | 81.7    | T3   |
| `pos_058_W4_QS` | LOAD_16NM | -1.07 %  | 89.1       | 71.3           | T3 RIGHT, r 25.70, z +7.5 | 59.7       | T2_T3, r 24.90, z +6.8, Tangente 30° | -73.4      | T3_T4      | 96.3    | T3   |
| `pos_059_W1_QS` | LOAD_16NM | -1.00 %  | 71.5       | 83.1           | T3 RIGHT, r 25.70, z -6.8 | 73.8       | T2_T3, r 24.83, z -6.8, Tangente 45° | -89.5      | T3_T4      | 81.6    | T3   |
| `pos_059_W2_QS` | LOAD_16NM | -0.89 %  | 88.3       | 72.5           | T3 RIGHT, r 25.70, z -6.0 | 46.6       | T2_T3, r 24.88, z +0.0, Tangente 33° | -55.9      | T3_T4      | 99.9    | T3   |
| `pos_059_W3_QS` | LOAD_16NM | -0.98 %  | 74.2       | 92.3           | T3 RIGHT, r 25.70, z +7.5 | 88.4       | T2_T3, r 24.85, z +6.8, Tangente 40° | -99.6      | T3_T4      | 80.1    | T3   |
| `pos_059_W4_QS` | LOAD_16NM | -0.87 %  | 88.7       | 77.2           | T3 RIGHT, r 25.70, z +7.5 | 59.5       | T2_T3, r 24.90, z +6.8, Tangente 30° | -72.5      | T3_T4      | 95.0    | T3   |
| `pos_060_W1_QS` | LOAD_16NM | -0.83 %  | 70.6       | 95.0           | T3 RIGHT, r 25.70, z -6.8 | 72.9       | T2_T3, r 24.83, z -6.8, Tangente 45° | -88.0      | T3_T4      | 80.0    | T3   |
| `pos_060_W2_QS` | LOAD_16NM | -0.72 %  | 88.0       | 77.0           | T3 RIGHT, r 25.70, z -6.0 | 46.5       | T2_T3, r 24.88, z +0.0, Tangente 33° | -55.5      | T3_T4      | 99.1    | T3   |
| `pos_060_W3_QS` | LOAD_16NM | -0.83 %  | 73.1       | 103.2          | T3 RIGHT, r 25.70, z +7.5 | 87.1       | T2_T3, r 24.85, z +6.8, Tangente 40° | -97.5      | T3_T4      | 79.1    | T2   |
| `pos_060_W4_QS` | LOAD_16NM | -0.69 %  | 88.4       | 81.0           | T3 RIGHT, r 25.70, z +7.5 | 59.8       | T2_T3, r 24.90, z +6.8, Tangente 30° | -71.8      | T3_T4      | 95.7    | T2   |
| `pos_061_W1_QS` | LOAD_16NM | -0.68 %  | 69.7       | 105.4          | T3 RIGHT, r 25.70, z -6.8 | 72.1       | T2_T3, r 24.83, z -6.8, Tangente 45° | -86.5      | T3_T4      | 78.6    | T3   |
| `pos_061_W2_QS` | LOAD_16NM | -0.56 %  | 87.2       | 80.3           | T3 RIGHT, r 25.70, z -6.0 | 45.9       | T2_T3, r 24.88, z +0.0, Tangente 33° | -55.0      | T3_T4      | 97.2    | T3   |
| `pos_061_W3_QS` | LOAD_16NM | -0.68 %  | 72.5       | 113.8          | T3 RIGHT, r 25.70, z +7.5 | 85.8       | T2_T3, r 24.85, z +6.8, Tangente 40° | -95.7      | T3_T4      | 79.4    | T2   |
| `pos_061_W4_QS` | LOAD_16NM | -0.53 %  | 87.5       | 83.4           | T3 RIGHT, r 25.70, z +7.5 | 59.2       | T2_T3, r 24.92, z +6.8, Tangente 26° | -71.1      | T3_T4      | 95.8    | T2   |
| `pos_062_W1_QS` | LOAD_16NM | -0.51 %  | 69.2       | 115.6          | T3 RIGHT, r 25.70, z -6.8 | 71.3       | T2_T3, r 24.83, z -6.8, Tangente 45° | -85.2      | T3_T4      | 77.3    | T3   |
| `pos_062_W2_QS` | LOAD_16NM | -0.42 %  | 86.6       | 83.4           | T3 RIGHT, r 25.70, z -6.0 | 45.2       | T2_T3, r 24.88, z +0.0, Tangente 33° | -54.4      | T3_T4      | 96.2    | T2   |
| `pos_062_W3_QS` | LOAD_16NM | -0.49 %  | 71.9       | 123.3          | T3 RIGHT, r 25.70, z +7.5 | 85.0       | T2_T3, r 24.85, z +6.8, Tangente 40° | -94.4      | T3_T4      | 79.3    | T2   |
| `pos_062_W4_QS` | LOAD_16NM | -0.35 %  | 87.1       | 85.9           | T3 RIGHT, r 25.70, z +7.5 | 58.7       | T2_T3, r 24.92, z +6.8, Tangente 26° | -70.3      | T3_T4      | 95.8    | T2   |
| `pos_063_W1_QS` | LOAD_16NM | -0.39 %  | 68.7       | 125.6          | T3 RIGHT, r 25.70, z -6.8 | 70.2       | T2_T3, r 24.83, z -6.8, Tangente 45° | -83.7      | T3_T4      | 76.9    | T2   |
| `pos_063_W2_QS` | LOAD_16NM | -0.26 %  | 86.0       | 85.4           | T3 RIGHT, r 25.70, z -6.0 | 44.8       | T2_T3, r 24.88, z +0.0, Tangente 33° | -54.0      | T3_T4      | 96.6    | T2   |
| `pos_063_W3_QS` | LOAD_16NM | -0.36 %  | 71.3       | 132.4          | T3 RIGHT, r 25.70, z +7.5 | 84.0       | T2_T3, r 24.85, z +6.8, Tangente 40° | -92.9      | T3_T4      | 78.7    | T2   |
| `pos_063_W4_QS` | LOAD_16NM | -0.23 %  | 86.6       | 88.0           | T3 RIGHT, r 25.70, z +7.5 | 58.0       | T2_T3, r 24.92, z +6.8, Tangente 26° | -69.4      | T3_T4      | 95.4    | T2   |
| `pos_064_W1_QS` | LOAD_16NM | -0.31 %  | 68.4       | 135.3          | T3 RIGHT, r 25.70, z -6.8 | 69.2       | T2_T3, r 24.83, z -6.8, Tangente 45° | -82.1      | T3_T4      | 77.0    | T2   |
| `pos_064_W2_QS` | LOAD_16NM | -0.18 %  | 85.2       | 87.2           | T3 RIGHT, r 25.70, z -6.0 | 44.3       | T2_T3, r 24.88, z +0.0, Tangente 33° | -53.4      | T3_T4      | 96.3    | T2   |
| `pos_064_W3_QS` | LOAD_16NM | -0.24 %  | 71.1       | 141.6          | T3 RIGHT, r 25.70, z +7.5 | 83.1       | T2_T3, r 24.85, z +6.8, Tangente 40° | -91.4      | T3_T4      | 78.5    | T2   |
| `pos_064_W4_QS` | LOAD_16NM | -0.13 %  | 86.3       | 89.8           | T3 RIGHT, r 25.70, z +7.5 | 57.2       | T2_T3, r 24.92, z +6.8, Tangente 26° | -68.5      | T3_T4      | 95.9    | T2   |
| `pos_065_W1_QS` | LOAD_16NM | -0.10 %  | 68.1       | 142.7          | T3 RIGHT, r 25.70, z -6.8 | 67.5       | T2_T3, r 24.83, z -6.8, Tangente 45° | -81.0      | T3_T4      | 77.2    | T2   |
| `pos_065_W2_QS` | LOAD_16NM | +0.09 %  | 85.2       | 87.8           | T3 RIGHT, r 25.70, z -6.0 | 43.9       | T1_T2, r 24.86, z -4.5, Tangente 37° | -53.0      | T3_T4      | 96.9    | T2   |
| `pos_065_W3_QS` | LOAD_16NM | +0.02 %  | 71.0       | 147.5          | T3 RIGHT, r 25.70, z +7.5 | 79.6       | T2_T3, r 24.85, z +6.8, Tangente 40° | -89.7      | T3_T4      | 78.6    | T2   |
| `pos_065_W4_QS` | LOAD_16NM | +0.10 %  | 86.1       | 90.1           | T3 RIGHT, r 25.70, z +7.5 | 56.7       | T1_T2, r 24.78, z +5.2, Tangente 63° | -67.8      | T3_T4      | 96.0    | T2   |
| `pos_066_W1_QS` | LOAD_16NM | +0.65 %  | 68.8       | 138.3          | T3 RIGHT, r 25.70, z +0.0 | 62.4       | T2_T3, r 24.83, z -6.8, Tangente 45° | -79.9      | T3_T4      | 78.6    | T2   |
| `pos_066_W2_QS` | LOAD_16NM | +0.74 %  | 85.7       | 88.3           | T3 RIGHT, r 25.80, z -6.0 | 44.5       | T1_T2, r 24.86, z -4.5, Tangente 37° | -52.5      | T3_T4      | 98.2    | T2   |
| `pos_066_W3_QS` | LOAD_16NM | +0.95 %  | 72.2       | 131.8          | T3 RIGHT, r 25.70, z +7.5 | 71.8       | T2_T3, r 24.85, z +6.8, Tangente 40° | -88.8      | T3_T4      | 80.6    | T2   |
| `pos_066_W4_QS` | LOAD_16NM | +0.73 %  | 86.8       | 85.3           | T3 RIGHT, r 25.80, z -7.5 | 57.5       | T1_T2, r 24.78, z +5.2, Tangente 63° | -67.1      | T3_T4      | 97.4    | T2   |
| `pos_067_W1_QS` | LOAD_16NM | +1.37 %  | 70.5       | 130.4          | T3 RIGHT, r 25.80, z -6.8 | 60.0       | T1_T2, r 24.82, z -4.5, Tangente 49° | -78.9      | T3_T4      | 80.8    | T2   |
| `pos_067_W2_QS` | LOAD_16NM | +1.31 %  | 87.0       | 92.1           | T3 RIGHT, r 25.80, z -6.0 | 45.1       | T1_T2, r 24.86, z -4.5, Tangente 37° | -52.1      | T3_T4      | 99.9    | T2   |
| `pos_067_W3_QS` | LOAD_16NM | +1.45 %  | 73.8       | 148.9          | T3 RIGHT, r 25.80, z -7.5 | 69.6       | T1_T2, r 24.78, z -6.8, Tangente 63° | -87.2      | T3_T4      | 82.8    | T2   |
| `pos_067_W4_QS` | LOAD_16NM | +1.29 %  | 88.2       | 94.1           | T3 RIGHT, r 25.80, z -7.5 | 58.5       | T1_T2, r 24.78, z +5.2, Tangente 63° | -66.4      | T3_T4      | 99.4    | T2   |
| `pos_068_W1_QS` | LOAD_16NM | +1.40 %  | 71.4       | 146.8          | T3 RIGHT, r 25.80, z -6.8 | 61.6       | T1_T2, r 24.82, z -4.5, Tangente 49° | -77.9      | T3_T4      | 82.2    | T2   |
| `pos_068_W2_QS` | LOAD_16NM | +1.48 %  | 87.6       | 93.6           | T3 RIGHT, r 25.80, z -6.0 | 45.6       | T1_T2, r 24.86, z -4.5, Tangente 37° | -51.6      | T3_T4      | 101.0   | T2   |
| `pos_068_W3_QS` | LOAD_16NM | +1.43 %  | 74.7       | 168.2          | T3 RIGHT, r 25.80, z -7.5 | 71.3       | T1_T2, r 24.78, z -6.8, Tangente 63° | -86.0      | T3_T4      | 83.9    | T2   |
| `pos_068_W4_QS` | LOAD_16NM | +1.49 %  | 89.1       | 98.6           | T3 RIGHT, r 25.80, z -7.5 | 59.1       | T1_T2, r 24.78, z +5.2, Tangente 63° | -65.7      | T3_T4      | 100.4   | T2   |
| `pos_069_W1_QS` | LOAD_16NM | +1.36 %  | 72.0       | 158.2          | T3 RIGHT, r 25.80, z -6.8 | 62.7       | T1_T2, r 24.82, z -4.5, Tangente 49° | -77.2      | T3_T4      | 83.4    | T2   |
| `pos_069_W2_QS` | LOAD_16NM | +1.59 %  | 88.2       | 94.1           | T3 RIGHT, r 25.80, z -6.0 | 46.0       | T1_T2, r 24.86, z -4.5, Tangente 37° | -51.3      | T3_T4      | 102.1   | T2   |
| `pos_069_W3_QS` | LOAD_16NM | +1.23 %  | 75.1       | 179.0          | T3 RIGHT, r 25.80, z -7.5 | 72.3       | T1_T2, r 24.78, z -6.8, Tangente 63° | -85.2      | T3_T4      | 84.4    | T2   |
| `pos_069_W4_QS` | LOAD_16NM | +1.53 %  | 89.6       | 101.4          | T3 RIGHT, r 25.80, z -7.5 | 59.6       | T1_T2, r 24.78, z +5.2, Tangente 63° | -65.2      | T3_T4      | 101.1   | T2   |
| `pos_070_W1_QS` | LOAD_16NM | +0.48 %  | 73.1       | 180.3          | T3 RIGHT, r 25.80, z -6.8 | 65.5       | T1_T2, r 24.82, z -4.5, Tangente 49° | -75.1      | T3_T4      | 85.2    | T2   |
| `pos_070_W2_QS` | LOAD_16NM | +1.26 %  | 89.8       | 96.2           | T3 RIGHT, r 25.80, z -6.0 | 47.0       | T1_T2, r 24.88, z -4.5, Tangente 33° | -50.3      | T3_T4      | 104.6   | T2   |
| `pos_070_W3_QS` | LOAD_16NM | +0.46 %  | 75.9       | 200.7          | T3 RIGHT, r 25.80, z -7.5 | 75.3       | T1_T2, r 24.78, z -6.8, Tangente 63° | -82.9      | T3_T4      | 86.1    | T2   |
| `pos_070_W4_QS` | LOAD_16NM | +1.21 %  | 91.3       | 107.0          | T3 RIGHT, r 25.80, z -7.5 | 61.0       | T1_T2, r 24.78, z +5.2, Tangente 63° | -63.8      | T3_T4      | 103.7   | T2   |
| `pos_071_W1_QS` | LOAD_16NM | +0.45 %  | 73.3       | 181.0          | T3 RIGHT, r 25.80, z -6.8 | 66.7       | T1_T2, r 24.82, z -4.5, Tangente 49° | -73.0      | T3_T4      | 85.6    | T2   |
| `pos_071_W2_QS` | LOAD_16NM | +0.46 %  | 90.3       | 98.8           | T3 RIGHT, r 25.80, z -6.0 | 47.7       | T1_T2, r 24.88, z -4.5, Tangente 33° | -49.0      | T3_T4      | 105.3   | T2   |
| `pos_071_W3_QS` | LOAD_16NM | +0.46 %  | 76.2       | 202.5          | T3 RIGHT, r 25.80, z -7.5 | 76.8       | T1_T2, r 24.78, z -6.8, Tangente 63° | -81.9      | T2_T3      | 86.7    | T2   |
| `pos_071_W4_QS` | LOAD_16NM | +0.48 %  | 91.7       | 108.9          | T3 RIGHT, r 25.80, z -7.5 | 62.0       | T1_T2, r 24.78, z +5.2, Tangente 63° | -63.9      | T2_T3      | 104.6   | T2   |
| `pos_072_W1_QS` | LOAD_16NM | +0.52 %  | 73.8       | 182.0          | T3 RIGHT, r 25.80, z -6.8 | 68.2       | T1_T2, r 24.82, z -4.5, Tangente 49° | -71.0      | T3_T4      | 86.8    | T2   |
| `pos_072_W2_QS` | LOAD_16NM | +0.51 %  | 90.5       | 99.7           | T3 RIGHT, r 25.80, z -6.0 | 48.2       | T1_T2, r 24.88, z -4.5, Tangente 33° | -48.5      | T2_T3      | 106.2   | T2   |
| `pos_072_W3_QS` | LOAD_16NM | +0.48 %  | 76.5       | 203.7          | T3 RIGHT, r 25.80, z -7.5 | 78.2       | T1_T2, r 24.78, z -6.8, Tangente 63° | -83.7      | T2_T3      | 86.9    | T2   |
| `pos_072_W4_QS` | LOAD_16NM | +0.54 %  | 91.9       | 109.7          | T3 RIGHT, r 25.80, z -7.5 | 62.4       | T1_T2, r 24.78, z +5.2, Tangente 63° | -64.5      | T2_T3      | 104.7   | T2   |
| `pos_073_W1_QS` | LOAD_12NM | +1.08 %  | 58.4       | 148.0          | T3 RIGHT, r 25.80, z +0.0 | 53.9       | T1_T2, r 24.82, z -4.5, Tangente 49° | -53.7      | T2_T3      | 68.6    | T2   |
| `pos_073_W2_QS` | LOAD_16NM | +1.23 %  | 91.5       | 96.1           | T3 RIGHT, r 25.80, z -6.0 | 48.8       | T1_T2, r 24.88, z -4.5, Tangente 33° | -49.1      | T2_T3      | 107.7   | T2   |
| `pos_073_W3_QS` | LOAD_16NM | +1.65 %  | 78.2       | 189.1          | T3 RIGHT, r 25.80, z -7.5 | 80.6       | T1_T2, r 24.78, z -6.8, Tangente 63° | -85.6      | T2_T3      | 89.3    | T2   |
| `pos_073_W4_QS` | LOAD_16NM | +1.27 %  | 92.8       | 102.3          | T3 RIGHT, r 25.80, z -7.5 | 63.3       | T1_T2, r 24.78, z +5.2, Tangente 63° | -65.5      | T2_T3      | 106.2   | T2   |
| `pos_074_W1_QS` | LOAD_16NM | +3.23 %  | 79.0       | 134.0          | T3 RIGHT, r 25.80, z +0.0 | 73.9       | T1_T2, r 24.82, z -4.5, Tangente 49° | -73.3      | T2_T3      | 93.2    | T2   |
| `pos_074_W2_QS` | LOAD_16NM | +2.35 %  | 93.9       | 96.3           | T3 RIGHT, r 25.90, z -6.0 | 49.6       | T1_T2, r 24.88, z -4.5, Tangente 33° | -50.0      | T2_T3      | 110.4   | T2   |
| `pos_074_W3_QS` | LOAD_16NM | +2.91 %  | 82.0       | 129.2          | T3 RIGHT, r 25.90, z -7.5 | 85.3       | T1_T2, r 24.78, z -6.8, Tangente 63° | -91.0      | T2_T3      | 93.9    | T2   |
| `pos_074_W4_QS` | LOAD_16NM | +2.34 %  | 95.6       | 100.5          | T3 RIGHT, r 25.90, z -7.5 | 64.6       | T1_T2, r 24.77, z -6.8, Tangente 68° | -67.1      | T2_T3      | 109.7   | T2   |
| `pos_075_W1_QS` | LOAD_16NM | +2.16 %  | 81.2       | 149.8          | T3 RIGHT, r 25.90, z -6.8 | 78.2       | T1_T2, r 24.82, z -4.5, Tangente 49° | -80.4      | T2_T3      | 96.7    | T2   |
| `pos_075_W2_QS` | LOAD_16NM | +2.51 %  | 96.3       | 97.0           | T3 RIGHT, r 25.90, z -6.0 | 50.8       | T1_T2, r 24.88, z -4.5, Tangente 33° | -51.4      | T2_T3      | 113.8   | T2   |
| `pos_075_W3_QS` | LOAD_16NM | +1.95 %  | 84.2       | 179.2          | T3 RIGHT, r 25.90, z -7.5 | 89.7       | T1_T2, r 24.78, z -6.8, Tangente 63° | -98.7      | T2_T3      | 96.6    | T2   |
| `pos_075_W4_QS` | LOAD_16NM | +2.33 %  | 98.1       | 103.0          | T3 RIGHT, r 25.90, z -7.5 | 66.2       | T1_T2, r 24.77, z -6.8, Tangente 68° | -69.5      | T2_T3      | 112.4   | T2   |
| `pos_076_W1_QS` | LOAD_16NM | +0.48 %  | 82.3       | 163.6          | T3 RIGHT, r 25.90, z -6.8 | 81.2       | T1_T2, r 24.82, z -4.5, Tangente 49° | -86.0      | T2_T3      | 98.3    | T2   |
| `pos_076_W2_QS` | LOAD_16NM | +0.52 %  | 96.9       | 98.8           | T3 RIGHT, r 25.90, z -6.0 | 51.5       | T1_T2, r 24.90, z -3.0, Tangente 30° | -52.8      | T2_T3      | 114.7   | T2   |
| `pos_076_W3_QS` | LOAD_16NM | +0.43 %  | 85.1       | 190.7          | T3 RIGHT, r 25.90, z -7.5 | 93.1       | T1_T2, r 24.78, z -6.8, Tangente 63° | -104.5     | T2_T3      | 98.0    | T2   |
| `pos_076_W4_QS` | LOAD_16NM | +0.39 %  | 98.0       | 107.6          | T3 RIGHT, r 25.90, z -7.5 | 66.7       | T1_T2, r 24.77, z -6.8, Tangente 68° | -71.5      | T2_T3      | 112.4   | T2   |
| `pos_077_W1_QS` | LOAD_16NM | +0.36 %  | 82.5       | 152.2          | T3 RIGHT, r 25.90, z -6.8 | 82.4       | T1_T2, r 24.82, z -4.5, Tangente 49° | -87.7      | T2_T3      | 98.4    | T2   |
| `pos_077_W2_QS` | LOAD_16NM | +0.02 %  | 94.0       | 97.0           | T3 RIGHT, r 25.90, z -6.0 | 50.8       | T1_T2, r 24.88, z -3.0, Tangente 33° | -52.5      | T2_T3      | 110.8   | T2   |
| `pos_077_W3_QS` | LOAD_16NM | +0.34 %  | 85.1       | 178.2          | T3 RIGHT, r 25.90, z -7.5 | 94.3       | T1_T2, r 24.78, z -6.8, Tangente 63° | -105.9     | T2_T3      | 98.0    | T2   |
| `pos_077_W4_QS` | LOAD_16NM | -0.02 %  | 94.9       | 107.2          | T3 RIGHT, r 25.90, z -7.5 | 65.4       | T1_T2, r 24.78, z -6.8, Tangente 63° | -70.9      | T2_T3      | 108.7   | T2   |
| `pos_078_W1_QS` | LOAD_16NM | +1.45 %  | 82.9       | 145.7          | T3 RIGHT, r 25.90, z -6.8 | 82.6       | T1_T2, r 24.82, z -3.8, Tangente 49° | -88.9      | T2_T3      | 99.1    | T2   |
| `pos_078_W2_QS` | LOAD_16NM | +0.71 %  | 92.7       | 91.8           | T3 RIGHT, r 25.90, z -0.8 | 50.4       | T1_T2, r 24.88, z -3.0, Tangente 33° | -52.7      | T2_T3      | 109.1   | T2   |
| `pos_078_W3_QS` | LOAD_16NM | +1.71 %  | 85.7       | 166.2          | T3 RIGHT, r 25.90, z -7.5 | 93.4       | T1_T2, r 24.79, z -6.8, Tangente 58° | -105.4     | T2_T3      | 98.1    | T2   |
| `pos_078_W4_QS` | LOAD_16NM | +0.79 %  | 94.0       | 97.5           | T3 RIGHT, r 25.90, z -7.5 | 64.6       | T1_T2, r 24.78, z -6.8, Tangente 63° | -70.6      | T2_T3      | 107.2   | T2   |
| `pos_079_W1_QS` | LOAD_16NM | +1.71 %  | 84.8       | 82.4           | T3 RIGHT, r 25.90, z +0.0 | 84.3       | T1_T2, r 24.83, z +0.0, Tangente 45° | -93.4      | T2_T3      | 101.2   | T2   |
| `pos_079_W2_QS` | LOAD_16NM | +1.33 %  | 93.6       | 68.5           | T3 RIGHT, r 25.90, z +0.0 | 50.8       | T1_T2, r 24.90, z +0.0, Tangente 30° | -53.8      | T2_T3      | 110.2   | T2   |
| `pos_079_W3_QS` | LOAD_16NM | +1.39 %  | 86.6       | 76.6           | T3 RIGHT, r 25.90, z -7.5 | 94.7       | T1_T2, r 24.79, z -6.8, Tangente 58° | -109.3     | T2_T3      | 99.1    | T2   |
| `pos_079_W4_QS` | LOAD_16NM | +1.13 %  | 95.1       | 68.8           | T3 RIGHT, r 26.00, z -7.5 | 64.6       | T1_T2, r 24.78, z -6.8, Tangente 63° | -71.6      | T2_T3      | 107.8   | T2   |
| `pos_080_W1_QS` | LOAD_16NM | -1.17 %  | 84.1       | 74.1           | T2 RIGHT, r 26.10, z +0.0 | 85.0       | T1_T2, r 24.83, z +0.0, Tangente 45° | -97.8      | T2_T3      | 99.9    | T2   |
| `pos_080_W2_QS` | LOAD_16NM | -0.87 %  | 94.6       | 75.3           | T3 RIGHT, r 26.00, z -6.0 | 51.5       | T1_T2, r 24.90, z +0.0, Tangente 30° | -56.1      | T2_T3      | 110.8   | T2   |
| `pos_080_W3_QS` | LOAD_16NM | -1.10 %  | 86.0       | 76.6           | T2 RIGHT, r 26.10, z -7.5 | 95.6       | T1_T2, r 24.85, z +6.8, Tangente 40° | -113.4     | T2_T3      | 98.1    | T2   |
| `pos_080_W4_QS` | LOAD_16NM | -0.86 %  | 96.2       | 84.0           | T3 RIGHT, r 26.00, z -7.5 | 65.3       | T1_T2, r 24.78, z -6.8, Tangente 63° | -74.3      | T2_T3      | 109.2   | T2   |
| `pos_081_W1_QS` | LOAD_16NM | -1.41 %  | 83.3       | 75.2           | T2 RIGHT, r 26.10, z +0.0 | 84.5       | T1_T2, r 24.83, z +0.0, Tangente 45° | -98.6      | T2_T3      | 98.8    | T2   |
| `pos_081_W2_QS` | LOAD_16NM | -1.33 %  | 93.4       | 66.1           | T3 RIGHT, r 26.00, z -6.0 | 51.2       | T1_T2, r 24.90, z +0.0, Tangente 30° | -56.6      | T2_T3      | 109.0   | T2   |
| `pos_081_W3_QS` | LOAD_16NM | -1.36 %  | 85.0       | 77.4           | T2 RIGHT, r 26.10, z +7.5 | 94.9       | T1_T2, r 24.85, z +6.8, Tangente 40° | -113.3     | T2_T3      | 96.3    | T2   |
| `pos_081_W4_QS` | LOAD_16NM | -1.28 %  | 95.0       | 74.8           | T3 RIGHT, r 26.00, z -7.5 | 64.8       | T1_T2, r 24.78, z -6.8, Tangente 63° | -74.3      | T2_T3      | 107.5   | T2   |
| `pos_082_W1_QS` | LOAD_16NM | -1.41 %  | 82.9       | 74.2           | T2 RIGHT, r 26.10, z +0.0 | 84.6       | T1_T2, r 24.83, z +0.0, Tangente 45° | -100.0     | T2_T3      | 98.2    | T2   |
| `pos_082_W2_QS` | LOAD_16NM | -0.90 %  | 93.6       | 64.1           | T1 RIGHT, r 26.89, z -6.8 | 51.5       | T1_T2, r 24.90, z +0.0, Tangente 30° | -57.5      | T2_T3      | 109.4   | T2   |
| `pos_082_W3_QS` | LOAD_16NM | -1.27 %  | 84.8       | 77.5           | T2 RIGHT, r 26.00, z -7.5 | 95.4       | T1_T2, r 24.85, z +6.8, Tangente 40° | -115.1     | T2_T3      | 95.8    | T2   |
| `pos_082_W4_QS` | LOAD_16NM | -0.77 %  | 94.7       | 63.9           | T3 RIGHT, r 26.00, z +7.5 | 64.5       | T1_T2, r 24.78, z -6.8, Tangente 63° | -74.6      | T2_T3      | 106.5   | T2   |
| `pos_083_W1_QS` | LOAD_16NM | -2.08 %  | 83.7       | 77.3           | T2 RIGHT, r 26.00, z +0.0 | 86.0       | T1_T2, r 24.83, z +0.0, Tangente 45° | -103.9     | T2_T3      | 98.9    | T2   |
| `pos_083_W2_QS` | LOAD_16NM | -1.07 %  | 97.1       | 65.0           | T1 RIGHT, r 26.89, z +0.0 | 52.8       | T1_T2, r 24.90, z +0.0, Tangente 30° | -60.4      | T2_T3      | 113.1   | T2   |
| `pos_083_W3_QS` | LOAD_16NM | -2.06 %  | 86.7       | 81.4           | T2 RIGHT, r 26.00, z -7.5 | 98.9       | T1_T2, r 24.85, z +6.8, Tangente 40° | -122.5     | T2_T3      | 98.0    | T2   |
| `pos_083_W4_QS` | LOAD_16NM | -1.03 %  | 98.0       | 61.8           | T1 RIGHT, r 26.89, z +0.8 | 65.6       | T1_T2, r 24.90, z +7.5, Tangente 30° | -78.1      | T2_T3      | 110.2   | T2   |
| `pos_084_W1_QS` | LOAD_16NM | -1.95 %  | 81.2       | 77.5           | T2 RIGHT, r 26.00, z +0.0 | 83.7       | T1_T2, r 24.83, z +0.0, Tangente 45° | -100.8     | T2_T3      | 95.4    | T2   |
| `pos_084_W2_QS` | LOAD_16NM | -2.26 %  | 97.2       | 64.1           | T1 RIGHT, r 26.89, z +0.0 | 52.9       | T1_T2, r 24.90, z +0.0, Tangente 30° | -61.7      | T2_T3      | 112.6   | T2   |
| `pos_084_W3_QS` | LOAD_16NM | -1.98 %  | 84.0       | 80.7           | T2 RIGHT, r 26.00, z -7.5 | 96.3       | T1_T2, r 24.85, z +6.8, Tangente 40° | -118.9     | T2_T3      | 94.3    | T2   |
| `pos_084_W4_QS` | LOAD_16NM | -2.21 %  | 98.3       | 61.7           | T1 RIGHT, r 26.89, z +0.8 | 66.1       | T1_T2, r 24.90, z +7.5, Tangente 30° | -79.6      | T2_T3      | 110.2   | T2   |
| `pos_085_W1_QS` | LOAD_16NM | -1.80 %  | 78.7       | 75.5           | T1 RIGHT, r 26.89, z -7.5 | 81.7       | T1_T2, r 24.83, z +0.0, Tangente 45° | -98.1      | T2_T3      | 92.3    | T2   |
| `pos_085_W2_QS` | LOAD_16NM | -2.05 %  | 94.2       | 61.9           | T1 RIGHT, r 26.89, z +0.0 | 52.0       | T1_T2, r 24.90, z +0.0, Tangente 30° | -60.9      | T2_T3      | 108.9   | T2   |
| `pos_085_W3_QS` | LOAD_16NM | -1.83 %  | 81.6       | 79.1           | T2 RIGHT, r 26.00, z -7.5 | 94.0       | T1_T2, r 24.85, z +6.8, Tangente 40° | -115.8     | T2_T3      | 91.1    | T2   |
| `pos_085_W4_QS` | LOAD_16NM | -2.02 %  | 95.3       | 60.4           | T1 RIGHT, r 26.89, z +0.8 | 64.6       | T1_T2, r 24.90, z +7.5, Tangente 30° | -78.6      | T2_T3      | 106.0   | T2   |
| `pos_086_W1_QS` | LOAD_16NM | -1.66 %  | 76.5       | 77.4           | T1 RIGHT, r 26.89, z -7.5 | 79.9       | T1_T2, r 24.83, z +0.0, Tangente 45° | -95.6      | T2_T3      | 89.3    | T2   |
| `pos_086_W2_QS` | LOAD_16NM | -1.84 %  | 91.5       | 60.2           | T1 RIGHT, r 26.89, z +0.0 | 51.1       | T1_T2, r 24.90, z +0.0, Tangente 30° | -60.3      | T2_T3      | 105.4   | T2   |
| `pos_086_W3_QS` | LOAD_16NM | -1.69 %  | 79.3       | 78.1           | T2 RIGHT, r 25.90, z -7.5 | 92.0       | T1_T2, r 24.85, z +6.8, Tangente 40° | -112.8     | T2_T3      | 88.1    | T2   |
| `pos_086_W4_QS` | LOAD_16NM | -1.82 %  | 93.0       | 62.7           | T2 RIGHT, r 25.70, z +7.5 | 63.4       | T1_T2, r 24.79, z -6.8, Tangente 58° | -77.7      | T2_T3      | 102.7   | T2   |
| `pos_087_W1_QS` | LOAD_16NM | -1.54 %  | 74.5       | 76.4           | T2 RIGHT, r 25.90, z +0.0 | 78.0       | T1_T2, r 24.83, z -6.8, Tangente 45° | -92.9      | T2_T3      | 86.1    | T2   |
| `pos_087_W2_QS` | LOAD_16NM | -1.62 %  | 89.4       | 60.2           | T2 RIGHT, r 25.80, z -6.0 | 50.3       | T1_T2, r 24.90, z +0.0, Tangente 30° | -59.7      | T2_T3      | 102.3   | T2   |
| `pos_087_W3_QS` | LOAD_16NM | -1.54 %  | 77.3       | 79.1           | T2 RIGHT, r 25.90, z -7.5 | 90.1       | T1_T2, r 24.85, z +6.8, Tangente 40° | -110.1     | T2_T3      | 85.3    | T2   |
| `pos_087_W4_QS` | LOAD_16NM | -1.55 %  | 91.1       | 68.4           | T2 RIGHT, r 25.70, z +7.5 | 62.5       | T1_T2, r 24.79, z -6.8, Tangente 58° | -76.9      | T2_T3      | 100.2   | T2   |
| `pos_088_W1_QS` | LOAD_16NM | -1.36 %  | 72.7       | 76.0           | T2 RIGHT, r 25.90, z +0.0 | 76.7       | T1_T2, r 24.83, z -6.8, Tangente 45° | -90.9      | T2_T3      | 84.0    | T2   |
| `pos_088_W2_QS` | LOAD_16NM | -1.37 %  | 88.0       | 63.8           | T2 RIGHT, r 25.80, z -6.0 | 49.4       | T1_T2, r 24.90, z +0.0, Tangente 30° | -59.1      | T2_T3      | 99.8    | T2   |
| `pos_088_W3_QS` | LOAD_16NM | -1.38 %  | 75.7       | 79.3           | T2 RIGHT, r 25.90, z -7.5 | 88.3       | T1_T2, r 24.85, z +6.8, Tangente 40° | -107.5     | T2_T3      | 82.8    | T2   |
| `pos_088_W4_QS` | LOAD_16NM | -1.31 %  | 89.5       | 74.3           | T2 RIGHT, r 25.70, z +7.5 | 61.7       | T1_T2, r 24.90, z +7.5, Tangente 30° | -76.1      | T2_T3      | 97.8    | T2   |
| `pos_089_W1_QS` | LOAD_16NM | -1.19 %  | 71.3       | 77.9           | T2 RIGHT, r 25.80, z -6.8 | 75.5       | T1_T2, r 24.83, z -6.8, Tangente 45° | -89.0      | T2_T3      | 81.9    | T2   |
| `pos_089_W2_QS` | LOAD_16NM | -1.13 %  | 86.8       | 67.9           | T2 RIGHT, r 25.70, z -6.0 | 48.9       | T1_T2, r 24.90, z +0.0, Tangente 30° | -58.6      | T2_T3      | 98.3    | T2   |
| `pos_089_W3_QS` | LOAD_16NM | -1.19 %  | 74.4       | 88.9           | T2 RIGHT, r 25.70, z +7.5 | 87.2       | T1_T2, r 24.85, z +6.8, Tangente 40° | -105.6     | T2_T3      | 81.0    | T2   |
| `pos_089_W4_QS` | LOAD_16NM | -1.09 %  | 88.5       | 80.6           | T2 RIGHT, r 25.70, z +7.5 | 61.1       | T1_T2, r 24.90, z +7.5, Tangente 30° | -75.2      | T2_T3      | 95.7    | T2   |
| `pos_090_W1_QS` | LOAD_16NM | -1.01 %  | 70.2       | 82.3           | T2 RIGHT, r 25.80, z -6.8 | 74.5       | T1_T2, r 24.83, z -6.8, Tangente 45° | -87.3      | T2_T3      | 79.9    | T2   |
| `pos_090_W2_QS` | LOAD_16NM | -0.94 %  | 85.9       | 73.4           | T2 RIGHT, r 25.70, z -6.0 | 48.6       | T1_T2, r 24.90, z +0.0, Tangente 30° | -58.1      | T2_T3      | 97.2    | T2   |
| `pos_090_W3_QS` | LOAD_16NM | -0.98 %  | 73.3       | 101.7          | T2 RIGHT, r 25.70, z +7.5 | 86.2       | T1_T2, r 24.85, z +6.8, Tangente 40° | -103.8     | T2_T3      | 79.3    | T2   |
| `pos_090_W4_QS` | LOAD_16NM | -0.89 %  | 88.1       | 86.7           | T2 RIGHT, r 25.70, z +7.5 | 61.1       | T1_T2, r 24.90, z +7.5, Tangente 30° | -74.4      | T2_T3      | 95.0    | T2   |
| `pos_091_W1_QS` | LOAD_16NM | -0.85 %  | 69.3       | 93.6           | T2 RIGHT, r 25.70, z -6.8 | 73.6       | T1_T2, r 24.83, z -6.8, Tangente 45° | -85.7      | T2_T3      | 78.2    | T2   |
| `pos_091_W2_QS` | LOAD_16NM | -0.74 %  | 85.2       | 77.5           | T2 RIGHT, r 25.70, z -6.0 | 48.3       | T1_T2, r 24.90, z +0.0, Tangente 30° | -57.6      | T2_T3      | 95.8    | T2   |
| `pos_091_W3_QS` | LOAD_16NM | -0.84 %  | 72.2       | 113.8          | T2 RIGHT, r 25.70, z +7.5 | 84.9       | T1_T2, r 24.85, z +6.8, Tangente 40° | -101.7     | T2_T3      | 77.6    | T1   |
| `pos_091_W4_QS` | LOAD_16NM | -0.71 %  | 87.6       | 90.4           | T2 RIGHT, r 25.70, z +7.5 | 61.2       | T1_T2, r 24.90, z +7.5, Tangente 30° | -73.9      | T2_T3      | 94.4    | T1   |
| `pos_092_W1_QS` | LOAD_16NM | -0.69 %  | 68.4       | 103.9          | T2 RIGHT, r 25.70, z -6.8 | 72.7       | T1_T2, r 24.83, z -6.8, Tangente 45° | -84.3      | T2_T3      | 76.9    | T2   |
| `pos_092_W2_QS` | LOAD_16NM | -0.58 %  | 84.5       | 81.1           | T2 RIGHT, r 25.70, z -6.0 | 47.6       | T1_T2, r 24.90, z +0.0, Tangente 30° | -56.9      | T2_T3      | 93.9    | T2   |
| `pos_092_W3_QS` | LOAD_16NM | -0.68 %  | 71.5       | 125.4          | T2 RIGHT, r 25.70, z +7.5 | 83.7       | T1_T2, r 24.85, z +6.8, Tangente 40° | -99.8      | T2_T3      | 77.9    | T1   |
| `pos_092_W4_QS` | LOAD_16NM | -0.54 %  | 86.7       | 93.1           | T2 RIGHT, r 25.70, z +7.5 | 60.6       | T1_T2, r 24.90, z +7.5, Tangente 30° | -73.1      | T2_T3      | 94.4    | T1   |
| `pos_093_W1_QS` | LOAD_16NM | -0.52 %  | 67.8       | 114.2          | T2 RIGHT, r 25.70, z -6.8 | 71.9       | T1_T2, r 24.83, z -6.8, Tangente 45° | -83.0      | T2_T3      | 75.6    | T2   |
| `pos_093_W2_QS` | LOAD_16NM | -0.44 %  | 83.8       | 84.1           | T2 RIGHT, r 25.70, z -6.0 | 46.9       | T1_T2, r 24.88, z +0.0, Tangente 33° | -56.3      | T2_T3      | 92.9    | T1   |
| `pos_093_W3_QS` | LOAD_16NM | -0.50 %  | 70.9       | 135.8          | T2 RIGHT, r 25.70, z +7.5 | 82.9       | T1_T2, r 24.85, z +6.8, Tangente 40° | -98.4      | T2_T3      | 77.8    | T1   |
| `pos_093_W4_QS` | LOAD_16NM | -0.36 %  | 86.3       | 95.7           | T2 RIGHT, r 25.70, z +7.5 | 60.1       | T1_T2, r 24.90, z +7.5, Tangente 30° | -72.4      | T2_T3      | 94.5    | T1   |
| `pos_094_W1_QS` | LOAD_16NM | -0.40 %  | 67.3       | 124.2          | T2 RIGHT, r 25.70, z -6.8 | 70.9       | T1_T2, r 24.83, z -6.8, Tangente 45° | -81.4      | T2_T3      | 75.0    | T1   |
| `pos_094_W2_QS` | LOAD_16NM | -0.27 %  | 83.2       | 86.3           | T2 RIGHT, r 25.70, z -6.0 | 46.6       | T1_T2, r 24.88, z +0.0, Tangente 33° | -55.8      | T2_T3      | 93.3    | T1   |
| `pos_094_W3_QS` | LOAD_16NM | -0.38 %  | 70.3       | 145.7          | T2 RIGHT, r 25.70, z +7.5 | 81.9       | T1_T2, r 24.85, z +6.8, Tangente 40° | -96.8      | T2_T3      | 77.2    | T1   |
| `pos_094_W4_QS` | LOAD_16NM | -0.25 %  | 85.7       | 97.9           | T2 RIGHT, r 25.70, z +7.5 | 59.3       | T1_T2, r 24.90, z +7.5, Tangente 30° | -71.5      | T2_T3      | 94.6    | T1   |
| `pos_095_W1_QS` | LOAD_16NM | -0.32 %  | 66.9       | 133.9          | T2 RIGHT, r 25.70, z -6.8 | 69.8       | T1_T2, r 24.83, z -6.8, Tangente 45° | -79.8      | T2_T3      | 75.1    | T1   |
| `pos_095_W2_QS` | LOAD_16NM | -0.20 %  | 82.4       | 88.1           | T2 RIGHT, r 25.70, z -6.0 | 46.0       | T1_T2, r 24.88, z +0.0, Tangente 33° | -55.1      | T2_T3      | 92.9    | T1   |
| `pos_095_W3_QS` | LOAD_16NM | -0.26 %  | 70.0       | 155.8          | T2 RIGHT, r 25.70, z +7.5 | 81.0       | T1_T2, r 24.85, z +6.8, Tangente 40° | -95.2      | T2_T3      | 77.4    | T1   |
| `pos_095_W4_QS` | LOAD_16NM | -0.14 %  | 85.4       | 99.7           | T2 RIGHT, r 25.70, z +7.5 | 58.5       | T1_T2, r 24.90, z +7.5, Tangente 30° | -70.6      | T2_T3      | 95.0    | T1   |
| `pos_096_W1_QS` | LOAD_16NM | -0.09 %  | 66.6       | 141.1          | T2 RIGHT, r 25.70, z +0.0 | 67.8       | T1_T2, r 24.83, z -6.8, Tangente 45° | -78.6      | T2_T3      | 75.2    | T1   |
| `pos_096_W2_QS` | LOAD_16NM | +0.07 %  | 82.3       | 88.7           | T2 RIGHT, r 25.70, z -6.0 | 44.9       | T1_T2, r 24.88, z +0.0, Tangente 33° | -54.6      | T2_T3      | 93.5    | T1   |
| `pos_096_W3_QS` | LOAD_16NM | +0.02 %  | 69.9       | 162.1          | T2 RIGHT, r 25.70, z +7.5 | 77.6       | T1_T2, r 24.85, z +6.8, Tangente 40° | -93.4      | T2_T3      | 77.5    | T1   |
| `pos_096_W4_QS` | LOAD_16NM | +0.09 %  | 85.2       | 100.0          | T2 RIGHT, r 25.70, z +7.5 | 57.1       | T1_T2, r 24.90, z +7.5, Tangente 30° | -69.9      | T2_T3      | 95.0    | T1   |
| `pos_097_W1_QS` | LOAD_16NM | +0.70 %  | 67.4       | 135.9          | T2 RIGHT, r 25.70, z +0.0 | 62.7       | T1_T2, r 24.83, z +0.0, Tangente 45° | -77.5      | T2_T3      | 76.8    | T1   |
| `pos_097_W2_QS` | LOAD_16NM | +0.72 %  | 82.9       | 89.5           | T2 RIGHT, r 25.80, z -6.0 | 42.4       | T1_T2, r 24.88, z +0.0, Tangente 33° | -54.1      | T2_T3      | 95.0    | T1   |
| `pos_097_W3_QS` | LOAD_16NM | +0.93 %  | 71.2       | 143.8          | T2 RIGHT, r 25.70, z +7.5 | 69.9       | T1_T2, r 24.85, z +6.8, Tangente 40° | -92.3      | T2_T3      | 79.5    | T1   |
| `pos_097_W4_QS` | LOAD_16NM | +0.73 %  | 85.9       | 93.6           | T2 RIGHT, r 25.70, z +7.5 | 53.0       | T1_T2, r 24.90, z +7.5, Tangente 30° | -69.2      | T2_T3      | 96.5    | T1   |
| `pos_098_W1_QS` | LOAD_16NM | +1.32 %  | 69.0       | 130.8          | T2 RIGHT, r 25.80, z -6.8 | 59.5       | T1_T2, r 24.83, z -6.8, Tangente 45° | -76.4      | T2_T3      | 78.9    | T1   |
| `pos_098_W2_QS` | LOAD_16NM | +1.28 %  | 84.1       | 93.3           | T2 RIGHT, r 25.80, z -6.0 | 40.7       | T1_T2, r 24.86, z -6.8, Tangente 37° | -53.5      | T2_T3      | 96.6    | T1   |
| `pos_098_W3_QS` | LOAD_16NM | +1.44 %  | 72.8       | 146.3          | T2 RIGHT, r 25.80, z -7.5 | 66.0       | T1_T2, r 24.85, z +6.8, Tangente 40° | -90.6      | T2_T3      | 81.7    | T1   |
| `pos_098_W4_QS` | LOAD_16NM | +1.28 %  | 87.3       | 86.0           | T2 RIGHT, r 25.80, z +6.8 | 50.1       | T1_T2, r 24.90, z +7.5, Tangente 30° | -68.4      | T2_T3      | 98.5    | T1   |
| `pos_099_W1_QS` | LOAD_16NM | +1.26 %  | 70.4       | 157.8          | T2 RIGHT, r 25.80, z -6.8 | 59.5       | T1_T2, r 24.83, z -6.8, Tangente 45° | -74.7      | T2_T3      | 81.3    | T1   |
| `pos_099_W2_QS` | LOAD_16NM | +1.53 %  | 85.4       | 95.2           | T2 RIGHT, r 25.80, z -6.0 | 39.7       | T1_T2, r 24.88, z -6.8, Tangente 33° | -52.6      | T2_T3      | 98.9    | T1   |
| `pos_099_W3_QS` | LOAD_16NM | +1.17 %  | 74.0       | 175.6          | T2 RIGHT, r 25.80, z -7.5 | 68.3       | T1_T2, r 24.85, z +6.8, Tangente 40° | -88.2      | T2_T3      | 83.2    | T1   |
| `pos_099_W4_QS` | LOAD_16NM | +1.50 %  | 88.7       | 91.9           | T2 RIGHT, r 25.80, z -7.5 | 49.0       | T1_T2, r 24.90, z +7.5, Tangente 30° | -67.2      | T2_T3      | 100.1   | T1   |

## 2026-10-12 09:28 `pilot_20layers_bore33_round0p1f12_dy1dy2_AtoE`

**Zweck:** Ratenpilot (Vorlage, 2026-10-12): dieselbe Einstellung wie die Wochenendserie (Ringkörper Bohrung 33, Kopfkante des starren Ritzels 0,1 mm mit 12 Facetten je Bogen, Iterationsgrenzen 20/30/100, Gitter 30 je Teilung mit Rand 1,0), aber nur die Punkte A, B, C, D, E (Indizes 31, 36, 49, 63, 68 des Gitters; die Dateien behalten die Nummern der Serie) mit den dynamischen Karten des Nutzers DY1 (isotrope Zeile E = 2542,5 MPa, ν = 0,2951 bei 80 °C, Dehnrate 3 1/s) und DY2 (E = 3596,6 MPa, ν = 0,2973, 60 1/s) für alle vier Werkstoffstufen W1 bis W4; 40 Dateien, erwartet rund 4 h. Zweck: die Dehnratenabhängigkeit je Stufe gegen die Rate QS der Serie an denselben Stellungen (Drehung, Fußspannung, Kantendruck, Lastaufteilung). Radnetz, starre Fläche und Stellungsdateien sind bis auf die Werkstoffzeile und die Kopfzeile byte-identisch mit der Serie (geprüft 2026-10-12). **Ergebnis:** Vorlage.

Netz: 82425 Knoten, 72320 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, W2, W3, W4, Raten DY1, DY2; Momente am Rad 8, 12, 16 Nm; 40 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 40 Dateien (`pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_DY1`, `pos_031_W2_DY2`, `pos_031_W3_DY1`, `pos_031_W3_DY2` …).

## 2026-10-12 10:47 `series_20layers_bore33_pocket_round0p1f12_30perpitch_margin1_qs`

**Zweck:** Taschenkörper-Serie (Vorlage, 2026-10-12): das Gegenstück der Wochenendserie auf dem Radkörper nach Zeichnung (Nabe, Steg, Taschen; das Netz ist byte-identisch mit frozen_mesh_20layers_bore33_pocket, auf dem das Mapping des Nutzers liegt), Kopfkante des starren Ritzels 0,1 mm mit 12 Facetten je Bogen, 30 Stellungen je Teilung, Rand 1,0 Teilung (99 Stellungen), Iterationsgrenzen 20/30/100, alle vier Werkstoffstufen W1 bis W4 bei Rate QS; 396 Dateien, erwartet rund 45 h (der Taschenkörper rechnete an C 215 statt 177 s, also etwa 27 min je Stellung) plus Extraktion. Vorgeschichte desselben Vormittags: die ersten Taschen-Karten des Nutzers (07.10.) enthielten keine *PLASTIC- und *POTENTIAL-Blöcke, der Kartenleser lehnte W2 ab; eine Fassung mit W1 und W3 allein wurde geschrieben und ungerechnet wieder gelöscht, nachdem der Nutzer die drei Taschen-Karten mit Plastizität neu exportiert hatte (12.10. 10:34 bis 10:45). Geprüft: *ELASTIC, *EXPANSION, *DENSITY, *PLASTIC und *POTENTIAL der neuen Taschen-Karten sind Zeile für Zeile identisch mit den Ringkarten derselben Rate, die Verteilung nennt alle 72932 Elemente des Taschen-Netzes. Zweck: Körpereinfluss über den ganzen Eingriffsweg je Stufe gegen die Ringserie (Drehung, Fußspannung über der Breite, Kantendruck, Lastaufteilung), Grundlage der Stommel-Auswertung auf dem Körper nach Zeichnung. **Ergebnis:** Vorlage.

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS; Momente am Rad 8, 12, 16 Nm; 396 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 396 Dateien (`pos_001_W1_QS`, `pos_001_W2_QS`, `pos_001_W3_QS`, `pos_001_W4_QS`, `pos_002_W1_QS`, `pos_002_W2_QS` …).

## 2026-10-12 10:54 `nachtlauf_2026-10-12_pocket_pocketlevels_AtoE/pocket`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-12 10:54 `pilot_20layers_bore33_pocket_round0p1f12_qsdy1dy2_AtoE`

**Zweck:** Taschenkörper-Pilot (Vorlage, 2026-10-12, Idee des Nutzers: unter der Woche schnelle Läufe für die ersten Vergleiche der Arbeit, die 45-h-Serie am Wochenende): Taschenkörper, Kopfkante 0,1 mm mit 12 Facetten, Iterationsgrenzen 20/30/100, nur die Punkte A, B, C, D, E (Indizes 31, 36, 49, 63, 68 des 30er-Gitters mit Rand 1,0; Dateinummern wie in den Serien), alle vier Werkstoffstufen W1 bis W4 bei allen drei Raten QS, DY1, DY2 (Taschen-Karten mit Plastizität vom 12.10.); 60 Dateien, erwartet rund 6,5 h. Zusammen mit der Ringserie (QS, Wochenende) und dem Ringpiloten DY1/DY2 ergibt das an den fünf Punkten die volle Matrix zwei Körper × drei Raten × vier Stufen. Die 20 QS-Dateien sind byte-identisch mit den gleichnamigen Dateien der Taschen-Serie: ihre Ergebnisse (.sta, .dat, .msg, .odb, _fields.json, _stress.npz) können in den Serienordner kopiert werden, der Runner überspringt sie dann. **Ergebnis:** Vorlage.

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-12 11:31 `nachtlauf_2026-10-12_pocket_pocketlevels_AtoE/pocketlevels`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 82425 Knoten, 72320 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-12 11:31 `pilot_20layers_bore33_pocketlevels_round0p1f12_qsdy1dy2_AtoE`

**Zweck:** Netzeinfluss-Pilot vollständig (Vorlage, 2026-10-12 mittags): Ringkörper auf den z-Ebenen des Taschenkörpers (`decks --levels pocket`, Elementnummern wie das Ringnetz, Knotenlagen der Zähne wie das Taschen-Netz), Kopfkante 0,1 mm mit 12 Facetten, Iterationsgrenzen 20/30/100, Punkte A bis E (Indizes 31, 36, 49, 63, 68), alle vier Werkstoffstufen W1 bis W4 bei allen drei Raten QS, DY1, DY2 mit den Mappings des Nutzers auf dieses Netz (wheel-pocketlevels_mesh_<Rate>.cof); 60 Dateien, erwartet rund 6,5 h. Damit stehen an den fünf Punkten drei Netze nebeneinander: Ring 0,75 mm (Serie QS, Pilot DY1/DY2), Ring auf Taschen-Ebenen (dieser Ordner) und Tasche (pilot_20layers_bore33_pocket_round0p1f12_qsdy1dy2_AtoE); Ring 0,75 gegen Ring auf Taschen-Ebenen = Schichtteilung, Ring auf Taschen-Ebenen gegen Tasche = Körper, bei W3/W4 ohne Neuabtastung der Faserorientierung (beide Mappings tasten dieselben Punkte ab). **Ergebnis:** Vorlage.

Netz: 82425 Knoten, 72320 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-12 15:08 `pilot_20layers_bore33_round0p1f12_dy1dy2_AtoE_gerechnet`

**Zweck:** Der Ratenpilot, gerechnet auf der Vollversion am 2026-10-12 vormittags (40 Jobs, Felder und Spannungstensoren direkt vom neuen Runner); Auswertung mit report und fe_series_analysis.py gegen die QS-Serie des Wochenendes an A bis E (Abschnitt 8 der Analyse). **Ergebnis:** Alle 40 Jobs vollständig. Dehnratenabhängigkeit gegen QS an den Punkten A bis E, alle vier Stufen gleichsinnig: DY1 (E 2543 MPa) senkt die Ritzeldrehung um 5 bis 10 % und hebt σ1 am Fuß um 0 bis 10 %; DY2 (E 3597 MPa) senkt die Drehung um 23 bis 41 % und hebt σ1 um 1 bis 12 % an A, B, D und E, an C aber um 20 bis 32 % (Einzeleingriff mit verlängertem Eingriff der Nachbarzähne, der steifere Werkstoff teilt ihnen weniger Last zu) und den Kontaktdruck an C um bis zu 40 % (korrigiert 2026-10-17: die erste Fassung nannte A, die Tabellen des Abschnitts 8 zeigen C). Die Rate wirkt also stark auf Verformung und Übertragungsfehler, am Fußmaximum der Zahnmitte nur schwach, an den Kantenkontakten deutlich. Orientierungsprüfung: am SEAT exakt, unter Last bis 0,95° Mitdrehung (W4, NLGEOM, über der Toleranz 0,5°; dieselbe Erscheinung wie im nichtlinearen Piloten, kein Mapping-Fehler). (gerechnet: Vollversion; Befunde FE-15, FE-17)

Netz: 82425 Knoten, 72320 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, W2, W3, W4, Raten DY1, DY2; Momente am Rad 8, 12, 16 Nm; 40 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei            | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|------------------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031_W1_DY1` | A        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 184    | 0       | 2026-10-12 10:10 |
| `pos_031_W1_DY2` | A        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 185    | 0       | 2026-10-12 10:13 |
| `pos_031_W2_DY1` | A        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 238    | 0       | 2026-10-12 10:18 |
| `pos_031_W2_DY2` | A        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 218    | 0       | 2026-10-12 10:22 |
| `pos_031_W3_DY1` | A        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 506    | 0       | 2026-10-12 10:30 |
| `pos_031_W3_DY2` | A        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 507    | 0       | 2026-10-12 10:39 |
| `pos_031_W4_DY1` | A        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 628    | 0       | 2026-10-12 10:50 |
| `pos_031_W4_DY2` | A        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 660    | 0       | 2026-10-12 11:02 |
| `pos_036_W1_DY1` | B        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 272    | 0       | 2026-10-12 11:07 |
| `pos_036_W1_DY2` | B        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 258    | 0       | 2026-10-12 11:12 |
| `pos_036_W2_DY1` | B        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 11           | 396    | 9       | 2026-10-12 11:19 |
| `pos_036_W2_DY2` | B        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 283    | 0       | 2026-10-12 11:24 |
| `pos_036_W3_DY1` | B        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 545    | 0       | 2026-10-12 11:33 |
| `pos_036_W3_DY2` | B        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 537    | 0       | 2026-10-12 11:43 |
| `pos_036_W4_DY1` | B        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 9            | 859    | 5       | 2026-10-12 11:58 |
| `pos_036_W4_DY2` | B        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 702    | 0       | 2026-10-12 12:10 |
| `pos_049_W1_DY1` | C        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 253    | 0       | 2026-10-12 12:14 |
| `pos_049_W1_DY2` | C        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 250    | 0       | 2026-10-12 12:19 |
| `pos_049_W2_DY1` | C        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 311    | 0       | 2026-10-12 12:25 |
| `pos_049_W2_DY2` | C        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 300    | 0       | 2026-10-12 12:30 |
| `pos_049_W3_DY1` | C        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 519    | 0       | 2026-10-12 12:39 |
| `pos_049_W3_DY2` | C        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 494    | 0       | 2026-10-12 12:48 |
| `pos_049_W4_DY1` | C        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 598    | 0       | 2026-10-12 12:58 |
| `pos_049_W4_DY2` | C        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 656    | 0       | 2026-10-12 13:10 |
| `pos_063_W1_DY1` | D        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 244    | 0       | 2026-10-12 13:14 |
| `pos_063_W1_DY2` | D        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 210    | 0       | 2026-10-12 13:18 |
| `pos_063_W2_DY1` | D        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 274    | 0       | 2026-10-12 13:23 |
| `pos_063_W2_DY2` | D        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 272    | 0       | 2026-10-12 13:28 |
| `pos_063_W3_DY1` | D        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 534    | 0       | 2026-10-12 13:38 |
| `pos_063_W3_DY2` | D        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 486    | 0       | 2026-10-12 13:46 |
| `pos_063_W4_DY1` | D        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 636    | 0       | 2026-10-12 13:57 |
| `pos_063_W4_DY2` | D        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 622    | 0       | 2026-10-12 14:08 |
| `pos_068_W1_DY1` | E        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 239    | 0       | 2026-10-12 14:12 |
| `pos_068_W1_DY2` | E        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 238    | 0       | 2026-10-12 14:17 |
| `pos_068_W2_DY1` | E        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 12           | 325    | 3       | 2026-10-12 14:23 |
| `pos_068_W2_DY2` | E        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 231    | 0       | 2026-10-12 14:27 |
| `pos_068_W3_DY1` | E        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 444    | 0       | 2026-10-12 14:35 |
| `pos_068_W3_DY2` | E        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 536    | 0       | 2026-10-12 14:44 |
| `pos_068_W4_DY1` | E        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 725    | 0       | 2026-10-12 14:57 |
| `pos_068_W4_DY2` | E        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 652    | 0       | 2026-10-12 15:08 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei            | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031_W1_DY1` | LOAD_16NM | -0.34 %  | 61.1       | 126.8          | T4 RIGHT, r 25.70, z -6.8 | 69.6       | T3_T4, r 24.83, z -6.8, Tangente 45° | -86.0      | T4_T5      | 68.6    | T3   |
| `pos_031_W1_DY2` | LOAD_16NM | -0.31 %  | 43.7       | 126.0          | T4 RIGHT, r 25.70, z -6.8 | 69.9       | T3_T4, r 24.83, z -6.8, Tangente 45° | -86.2      | T4_T5      | 48.9    | T3   |
| `pos_031_W2_DY1` | LOAD_16NM | -0.22 %  | 76.9       | 89.1           | T4 RIGHT, r 25.70, z -6.0 | 46.0       | T3_T4, r 24.82, z -6.0, Tangente 49° | -55.6      | T4_T5      | 86.5    | T3   |
| `pos_031_W2_DY2` | LOAD_16NM | -0.15 %  | 50.5       | 98.4           | T4 RIGHT, r 25.70, z -6.0 | 49.1       | T3_T4, r 24.83, z -6.0, Tangente 45° | -59.4      | T4_T5      | 56.3    | T3   |
| `pos_031_W3_DY1` | LOAD_16NM | -0.32 %  | 64.6       | 138.1          | T4 RIGHT, r 25.70, z +7.5 | 85.1       | T3_T4, r 24.86, z +6.8, Tangente 37° | -95.6      | T4_T5      | 71.6    | T3   |
| `pos_031_W3_DY2` | LOAD_16NM | -0.28 %  | 45.9       | 136.8          | T4 RIGHT, r 25.70, z +7.5 | 83.4       | T3_T4, r 24.86, z +6.8, Tangente 37° | -94.4      | T4_T5      | 50.8    | T3   |
| `pos_031_W4_DY1` | LOAD_16NM | -0.18 %  | 78.1       | 96.6           | T4 RIGHT, r 25.70, z +7.5 | 60.9       | T3_T4, r 24.88, z +6.8, Tangente 33° | -73.6      | T4_T5      | 86.3    | T3   |
| `pos_031_W4_DY2` | LOAD_16NM | -0.12 %  | 51.5       | 106.1          | T4 RIGHT, r 25.70, z +7.5 | 64.3       | T3_T4, r 24.83, z +6.8, Tangente 45° | -76.7      | T4_T5      | 57.1    | T3   |
| `pos_036_W1_DY1` | LOAD_16NM | +1.57 %  | 63.7       | 149.0          | T4 RIGHT, r 25.80, z -6.8 | 59.2       | T2_T3, r 24.82, z -5.2, Tangente 49° | -80.3      | T4_T5      | 73.4    | T3   |
| `pos_036_W1_DY2` | LOAD_16NM | +1.45 %  | 46.0       | 156.8          | T4 RIGHT, r 25.80, z -6.8 | 59.6       | T2_T3, r 24.82, z -5.2, Tangente 49° | -79.9      | T4_T5      | 52.5    | T3   |
| `pos_036_W2_DY1` | LOAD_16NM | +1.56 %  | 78.8       | 98.4           | T4 RIGHT, r 25.80, z -6.0 | 45.0       | T2_T3, r 24.79, z -4.5, Tangente 58° | -52.6      | T4_T5      | 91.0    | T3   |
| `pos_036_W2_DY2` | LOAD_16NM | +1.65 %  | 52.8       | 116.5          | T4 RIGHT, r 25.80, z -6.0 | 47.7       | T2_T3, r 24.82, z -4.5, Tangente 49° | -55.9      | T4_T5      | 60.2    | T3   |
| `pos_036_W3_DY1` | LOAD_16NM | +1.41 %  | 67.8       | 153.8          | T4 RIGHT, r 25.80, z -7.5 | 73.2       | T2_T3, r 24.85, z +6.8, Tangente 40° | -88.8      | T4_T5      | 75.6    | T3   |
| `pos_036_W3_DY2` | LOAD_16NM | +1.55 %  | 48.5       | 163.6          | T4 RIGHT, r 25.80, z -7.5 | 71.7       | T2_T3, r 24.85, z +6.8, Tangente 40° | -87.6      | T4_T5      | 53.7    | T3   |
| `pos_036_W4_DY1` | LOAD_16NM | +1.56 %  | 80.5       | 97.3           | T4 RIGHT, r 25.80, z +6.8 | 63.3       | T2_T3, r 24.78, z +6.0, Tangente 63° | -69.7      | T4_T5      | 90.3    | T3   |
| `pos_036_W4_DY2` | LOAD_16NM | +1.59 %  | 54.3       | 117.8          | T4 RIGHT, r 25.80, z +6.8 | 64.5       | T2_T3, r 24.78, z +6.0, Tangente 63° | -71.5      | T4_T5      | 60.3    | T3   |
| `pos_049_W1_DY1` | LOAD_16NM | -1.29 %  | 78.7       | 80.1           | T3 RIGHT, r 26.10, z +0.0 | 86.5       | T2_T3, r 24.83, z +0.0, Tangente 45° | -104.0     | T3_T4      | 93.6    | T3   |
| `pos_049_W1_DY2` | LOAD_16NM | -1.45 %  | 65.0       | 101.8          | T3 RIGHT, r 26.10, z +0.0 | 101.8      | T2_T3, r 24.83, z +0.0, Tangente 45° | -124.2     | T3_T4      | 77.5    | T3   |
| `pos_049_W2_DY1` | LOAD_16NM | -1.22 %  | 88.7       | 68.0           | T4 RIGHT, r 26.00, z -6.0 | 50.9       | T2_T3, r 24.88, z +0.0, Tangente 33° | -58.1      | T3_T4      | 103.9   | T3   |
| `pos_049_W2_DY2` | LOAD_16NM | -1.31 %  | 70.3       | 75.2           | T3 RIGHT, r 26.10, z -6.0 | 61.0       | T2_T3, r 24.86, z +0.0, Tangente 37° | -70.4      | T3_T4      | 82.3    | T3   |
| `pos_049_W3_DY1` | LOAD_16NM | -1.20 %  | 81.0       | 69.7           | T3 RIGHT, r 26.20, z +7.5 | 103.6      | T2_T3, r 24.85, z +6.8, Tangente 40° | -117.6     | T3_T4      | 91.3    | T3   |
| `pos_049_W3_DY2` | LOAD_16NM | -1.35 %  | 66.1       | 91.0           | T3 RIGHT, r 26.20, z +7.5 | 118.0      | T2_T3, r 24.85, z +6.8, Tangente 40° | -136.9     | T3_T4      | 74.9    | T3   |
| `pos_049_W4_DY1` | LOAD_16NM | -1.21 %  | 89.8       | 75.7           | T4 RIGHT, r 26.00, z +7.5 | 71.1       | T2_T3, r 24.78, z +6.0, Tangente 63° | -78.8      | T3_T4      | 101.5   | T3   |
| `pos_049_W4_DY2` | LOAD_16NM | -1.22 %  | 70.5       | 67.4           | T3 RIGHT, r 26.10, z +0.8 | 83.1       | T2_T3, r 24.78, z +6.0, Tangente 63° | -93.8      | T3_T4      | 79.7    | T3   |
| `pos_063_W1_DY1` | LOAD_16NM | -0.35 %  | 62.2       | 126.3          | T3 RIGHT, r 25.70, z -6.8 | 70.5       | T2_T3, r 24.83, z -6.8, Tangente 45° | -83.9      | T3_T4      | 69.4    | T2   |
| `pos_063_W1_DY2` | LOAD_16NM | -0.32 %  | 44.5       | 125.5          | T3 RIGHT, r 25.70, z -6.8 | 70.8       | T2_T3, r 24.83, z -6.8, Tangente 45° | -84.2      | T3_T4      | 49.4    | T2   |
| `pos_063_W2_DY1` | LOAD_16NM | -0.23 %  | 77.3       | 89.5           | T3 RIGHT, r 25.70, z -6.0 | 45.9       | T2_T3, r 24.86, z +0.0, Tangente 37° | -55.3      | T3_T4      | 86.7    | T2   |
| `pos_063_W2_DY2` | LOAD_16NM | -0.17 %  | 50.9       | 98.4           | T3 RIGHT, r 25.70, z -6.0 | 49.2       | T2_T3, r 24.85, z +0.0, Tangente 40° | -59.1      | T3_T4      | 56.5    | T2   |
| `pos_063_W3_DY1` | LOAD_16NM | -0.34 %  | 65.7       | 134.4          | T3 RIGHT, r 25.70, z +7.5 | 86.4       | T2_T3, r 24.85, z +6.8, Tangente 40° | -95.1      | T3_T4      | 72.4    | T2   |
| `pos_063_W3_DY2` | LOAD_16NM | -0.29 %  | 46.6       | 133.1          | T3 RIGHT, r 25.70, z +7.5 | 85.0       | T2_T3, r 24.85, z +6.8, Tangente 40° | -93.8      | T3_T4      | 51.4    | T2   |
| `pos_063_W4_DY1` | LOAD_16NM | -0.19 %  | 79.3       | 95.3           | T3 RIGHT, r 25.70, z +7.5 | 61.4       | T2_T3, r 24.92, z +6.8, Tangente 26° | -73.4      | T3_T4      | 87.3    | T2   |
| `pos_063_W4_DY2` | LOAD_16NM | -0.13 %  | 52.4       | 104.6          | T3 RIGHT, r 25.70, z +7.5 | 64.5       | T2_T3, r 24.85, z +6.8, Tangente 40° | -76.5      | T3_T4      | 57.8    | T2   |
| `pos_068_W1_DY1` | LOAD_16NM | +1.47 %  | 64.7       | 150.0          | T3 RIGHT, r 25.80, z -6.8 | 61.6       | T1_T2, r 24.82, z -4.5, Tangente 49° | -78.0      | T3_T4      | 74.3    | T2   |
| `pos_068_W1_DY2` | LOAD_16NM | +1.41 %  | 46.8       | 158.6          | T3 RIGHT, r 25.80, z -6.8 | 62.1       | T1_T2, r 24.82, z -4.5, Tangente 49° | -77.6      | T3_T4      | 53.2    | T2   |
| `pos_068_W2_DY1` | LOAD_16NM | +1.58 %  | 79.4       | 99.8           | T3 RIGHT, r 25.80, z -6.0 | 46.4       | T1_T2, r 24.86, z -4.5, Tangente 37° | -52.8      | T3_T4      | 91.5    | T2   |
| `pos_068_W2_DY2` | LOAD_16NM | +1.61 %  | 53.2       | 117.5          | T3 RIGHT, r 25.80, z -6.0 | 49.1       | T1_T2, r 24.85, z -4.5, Tangente 40° | -55.8      | T3_T4      | 60.5    | T2   |
| `pos_068_W3_DY1` | LOAD_16NM | +1.37 %  | 68.8       | 174.1          | T3 RIGHT, r 25.80, z -7.5 | 74.6       | T1_T2, r 24.78, z -6.8, Tangente 63° | -88.2      | T3_T4      | 76.8    | T2   |
| `pos_068_W3_DY2` | LOAD_16NM | +1.52 %  | 49.3       | 182.8          | T3 RIGHT, r 25.80, z -7.5 | 72.4       | T1_T2, r 24.78, z -6.8, Tangente 63° | -86.6      | T3_T4      | 54.7    | T2   |
| `pos_068_W4_DY1` | LOAD_16NM | +1.50 %  | 81.7       | 108.6          | T3 RIGHT, r 25.80, z -7.5 | 62.3       | T1_T2, r 24.78, z +5.2, Tangente 63° | -69.4      | T3_T4      | 91.7    | T2   |
| `pos_068_W4_DY2` | LOAD_16NM | +1.53 %  | 55.1       | 129.6          | T3 RIGHT, r 25.80, z -7.5 | 63.8       | T1_T2, r 24.78, z +5.2, Tangente 63° | -71.0      | T3_T4      | 61.3    | T2   |

## 2026-10-13 00:49 `pilot_20layers_bore33_pocket_round0p1f12_qsdy1dy2_AtoE_gerechnet`

**Zweck:** Der Taschenkörper an A bis E (W1 bis W4, QS/DY1/DY2), gerechnet auf der Vollversion in der Nacht 2026-10-12/13 (Nachtlauf-Ordner, 60 Jobs, 17:52 bis 00:49, 6,5 h; W1 3,4, W2 4,3, W3 7,6, W4 10,7 min je Stellung); Felder und Spannungstensoren direkt vom Runner; Auswertung mit report, fe_series_analysis.py gegen die QS-Serie des Rings und fe_body_comparison.py (vergleich_koerper_AtoE). **Ergebnis:** 60 von 60 Jobs vollständig; Körpereffekt gegen den Ring auf Taschen-Schichten: Drehung +8 bis +24 %, Kopfweg +9 bis +29 %, |σ3| +2 bis +21 %, σ1 +1 bis +17 % (W1/W2) bzw. −16 bis +5 % (W3/W4), Kontaktdruck −9 bis +25 % (ADR-116 Punkt 48). (gerechnet: Vollversion; Befunde FE-23)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei            | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|------------------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031_W1_QS`  | A        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 203    | 0       | 2026-10-12 18:02 |
| `pos_031_W1_DY1` | A        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 191    | 0       | 2026-10-12 17:55 |
| `pos_031_W1_DY2` | A        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 169    | 0       | 2026-10-12 17:59 |
| `pos_031_W2_QS`  | A        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 231    | 0       | 2026-10-12 18:15 |
| `pos_031_W2_DY1` | A        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 235    | 0       | 2026-10-12 18:07 |
| `pos_031_W2_DY2` | A        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 222    | 0       | 2026-10-12 18:11 |
| `pos_031_W3_QS`  | A        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 446    | 0       | 2026-10-12 18:38 |
| `pos_031_W3_DY1` | A        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 446    | 0       | 2026-10-12 18:23 |
| `pos_031_W3_DY2` | A        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 415    | 0       | 2026-10-12 18:30 |
| `pos_031_W4_QS`  | A        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 540    | 0       | 2026-10-12 19:06 |
| `pos_031_W4_DY1` | A        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 534    | 0       | 2026-10-12 18:47 |
| `pos_031_W4_DY2` | A        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 522    | 0       | 2026-10-12 18:57 |
| `pos_036_W1_QS`  | B        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 225    | 0       | 2026-10-12 19:18 |
| `pos_036_W1_DY1` | B        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 225    | 0       | 2026-10-12 19:10 |
| `pos_036_W1_DY2` | B        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 219    | 0       | 2026-10-12 19:14 |
| `pos_036_W2_QS`  | B        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 263    | 2       | 2026-10-12 19:32 |
| `pos_036_W2_DY1` | B        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 261    | 0       | 2026-10-12 19:23 |
| `pos_036_W2_DY2` | B        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 241    | 0       | 2026-10-12 19:27 |
| `pos_036_W3_QS`  | B        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 499    | 0       | 2026-10-12 19:58 |
| `pos_036_W3_DY1` | B        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 500    | 0       | 2026-10-12 19:41 |
| `pos_036_W3_DY2` | B        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 469    | 0       | 2026-10-12 19:49 |
| `pos_036_W4_QS`  | B        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 12           | 855    | 7       | 2026-10-12 20:35 |
| `pos_036_W4_DY1` | B        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 685    | 4       | 2026-10-12 20:10 |
| `pos_036_W4_DY2` | B        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 592    | 0       | 2026-10-12 20:20 |
| `pos_049_W1_QS`  | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 200    | 0       | 2026-10-12 20:46 |
| `pos_049_W1_DY1` | C        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 204    | 0       | 2026-10-12 20:39 |
| `pos_049_W1_DY2` | C        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 196    | 0       | 2026-10-12 20:42 |
| `pos_049_W2_QS`  | C        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 8, 6, 11           | 356    | 12      | 2026-10-12 21:01 |
| `pos_049_W2_DY1` | C        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 239    | 0       | 2026-10-12 20:50 |
| `pos_049_W2_DY2` | C        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 227    | 0       | 2026-10-12 20:55 |
| `pos_049_W3_QS`  | C        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 418    | 0       | 2026-10-12 21:23 |
| `pos_049_W3_DY1` | C        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 417    | 0       | 2026-10-12 21:08 |
| `pos_049_W3_DY2` | C        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 431    | 0       | 2026-10-12 21:16 |
| `pos_049_W4_QS`  | C        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 8, 6, 11           | 823    | 6       | 2026-10-12 21:57 |
| `pos_049_W4_DY1` | C        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 566    | 0       | 2026-10-12 21:33 |
| `pos_049_W4_DY2` | C        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 568    | 0       | 2026-10-12 21:43 |
| `pos_063_W1_QS`  | D        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 202    | 0       | 2026-10-12 22:08 |
| `pos_063_W1_DY1` | D        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 204    | 0       | 2026-10-12 22:01 |
| `pos_063_W1_DY2` | D        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 174    | 0       | 2026-10-12 22:04 |
| `pos_063_W2_QS`  | D        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 12           | 319    | 6       | 2026-10-12 22:23 |
| `pos_063_W2_DY1` | D        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 248    | 0       | 2026-10-12 22:13 |
| `pos_063_W2_DY2` | D        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 226    | 0       | 2026-10-12 22:17 |
| `pos_063_W3_QS`  | D        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 465    | 0       | 2026-10-12 22:46 |
| `pos_063_W3_DY1` | D        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 455    | 0       | 2026-10-12 22:31 |
| `pos_063_W3_DY2` | D        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 412    | 0       | 2026-10-12 22:38 |
| `pos_063_W4_QS`  | D        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 11           | 751    | 4       | 2026-10-12 23:18 |
| `pos_063_W4_DY1` | D        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 546    | 0       | 2026-10-12 22:56 |
| `pos_063_W4_DY2` | D        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 538    | 0       | 2026-10-12 23:05 |
| `pos_068_W1_QS`  | E        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 226    | 0       | 2026-10-12 23:31 |
| `pos_068_W1_DY1` | E        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 237    | 0       | 2026-10-12 23:22 |
| `pos_068_W1_DY2` | E        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 225    | 0       | 2026-10-12 23:27 |
| `pos_068_W2_QS`  | E        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 307    | 5       | 2026-10-12 23:46 |
| `pos_068_W2_DY1` | E        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 256    | 0       | 2026-10-12 23:35 |
| `pos_068_W2_DY2` | E        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 253    | 0       | 2026-10-12 23:40 |
| `pos_068_W3_QS`  | E        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 510    | 0       | 2026-10-13 00:12 |
| `pos_068_W3_DY1` | E        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 492    | 0       | 2026-10-12 23:54 |
| `pos_068_W3_DY2` | E        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 499    | 0       | 2026-10-13 00:03 |
| `pos_068_W4_QS`  | E        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 12           | 886    | 6       | 2026-10-13 00:49 |
| `pos_068_W4_DY1` | E        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 647    | 2       | 2026-10-13 00:23 |
| `pos_068_W4_DY2` | E        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 614    | 0       | 2026-10-13 00:34 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei            | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031_W1_QS`  | LOAD_16NM | -0.40 %  | 80.4       | 140.2          | T4 RIGHT, r 25.70, z +0.0 | 72.3       | T3_T4, r 24.85, z +0.0, Tangente 40° | -100.5     | T4_T5      | 92.7    | T4   |
| `pos_031_W1_DY1` | LOAD_16NM | -0.38 %  | 72.6       | 140.7          | T4 RIGHT, r 25.70, z +0.0 | 72.4       | T3_T4, r 24.85, z +0.0, Tangente 40° | -100.6     | T4_T5      | 83.5    | T4   |
| `pos_031_W1_DY2` | LOAD_16NM | -0.34 %  | 51.9       | 140.6          | T4 RIGHT, r 25.70, z +0.0 | 72.6       | T3_T4, r 24.85, z +0.0, Tangente 40° | -100.8     | T4_T5      | 59.3    | T4   |
| `pos_031_W2_QS`  | LOAD_16NM | -0.28 %  | 101.2      | 86.4           | T4 RIGHT, r 25.70, z +0.0 | 45.8       | T3_T4, r 24.83, z +0.0, Tangente 45° | -58.8      | T4_T5      | 115.0   | T4   |
| `pos_031_W2_DY1` | LOAD_16NM | -0.26 %  | 91.6       | 91.9           | T4 RIGHT, r 25.70, z +0.0 | 47.2       | T3_T4, r 24.83, z +0.0, Tangente 45° | -60.8      | T4_T5      | 104.5   | T4   |
| `pos_031_W2_DY2` | LOAD_16NM | -0.20 %  | 60.0       | 102.8          | T4 RIGHT, r 25.70, z +0.0 | 50.8       | T3_T4, r 24.83, z +0.0, Tangente 45° | -66.0      | T4_T5      | 68.1    | T4   |
| `pos_031_W3_QS`  | LOAD_16NM | -0.36 %  | 80.2       | 128.8          | T4 RIGHT, r 25.70, z +7.5 | 71.3       | T3_T4, r 24.86, z -0.7, Tangente 37° | -108.3     | T4_T5      | 87.8    | T3   |
| `pos_031_W3_DY1` | LOAD_16NM | -0.35 %  | 73.3       | 132.3          | T4 RIGHT, r 25.70, z +7.5 | 71.6       | T3_T4, r 24.86, z -0.7, Tangente 37° | -109.7     | T4_T5      | 80.2    | T3   |
| `pos_031_W3_DY2` | LOAD_16NM | -0.30 %  | 52.2       | 131.1          | T4 RIGHT, r 25.70, z +7.5 | 71.7       | T3_T4, r 24.86, z -0.7, Tangente 37° | -108.9     | T4_T5      | 57.2    | T3   |
| `pos_031_W4_QS`  | LOAD_16NM | -0.23 %  | 97.1       | 85.7           | T4 RIGHT, r 25.70, z +6.7 | 56.5       | T2_T3, r 24.78, z +4.4, Tangente 63° | -76.6      | T4_T5      | 106.9   | T3   |
| `pos_031_W4_DY1` | LOAD_16NM | -0.22 %  | 88.6       | 94.2           | T4 RIGHT, r 25.70, z +7.5 | 59.2       | T2_T3, r 24.78, z +4.4, Tangente 63° | -81.5      | T4_T5      | 97.0    | T3   |
| `pos_031_W4_DY2` | LOAD_16NM | -0.16 %  | 58.6       | 104.4          | T4 RIGHT, r 25.70, z +7.5 | 59.4       | T2_T3, r 24.78, z +4.4, Tangente 63° | -86.7      | T4_T5      | 64.2    | T3   |
| `pos_036_W1_QS`  | LOAD_16NM | +0.84 %  | 84.2       | 173.1          | T4 RIGHT, r 25.80, z -5.1 | 67.1       | T2_T3, r 24.82, z +0.0, Tangente 49° | -95.4      | T4_T5      | 96.6    | T3   |
| `pos_036_W1_DY1` | LOAD_16NM | +0.92 %  | 76.3       | 176.5          | T4 RIGHT, r 25.80, z -5.9 | 67.1       | T2_T3, r 24.82, z +0.0, Tangente 49° | -95.6      | T4_T5      | 87.3    | T3   |
| `pos_036_W1_DY2` | LOAD_16NM | +1.06 %  | 55.1       | 190.1          | T4 RIGHT, r 25.80, z -6.7 | 67.5       | T2_T3, r 24.82, z +0.0, Tangente 49° | -95.8      | T4_T5      | 62.6    | T3   |
| `pos_036_W2_QS`  | LOAD_16NM | +1.02 %  | 104.5      | 95.5           | T4 RIGHT, r 25.80, z -5.9 | 47.9       | T2_T3, r 24.78, z +0.0, Tangente 63° | -56.8      | T4_T5      | 120.1   | T3   |
| `pos_036_W2_DY1` | LOAD_16NM | +1.09 %  | 95.0       | 103.1          | T4 RIGHT, r 25.80, z -5.9 | 49.0       | T2_T3, r 24.79, z +0.0, Tangente 58° | -58.6      | T4_T5      | 109.0   | T3   |
| `pos_036_W2_DY2` | LOAD_16NM | +1.32 %  | 63.9       | 124.5          | T4 RIGHT, r 25.80, z -5.9 | 52.1       | T2_T3, r 24.80, z +0.0, Tangente 54° | -63.4      | T4_T5      | 72.6    | T3   |
| `pos_036_W3_QS`  | LOAD_16NM | +0.86 %  | 84.3       | 176.5          | T4 RIGHT, r 25.80, z +7.5 | 70.4       | T2_T3, r 24.78, z +4.4, Tangente 63° | -101.9     | T4_T5      | 94.4    | T3   |
| `pos_036_W3_DY1` | LOAD_16NM | +0.92 %  | 77.4       | 182.5          | T4 RIGHT, r 25.80, z +7.5 | 72.7       | T2_T3, r 24.78, z +4.4, Tangente 63° | -103.3     | T4_T5      | 86.1    | T3   |
| `pos_036_W3_DY2` | LOAD_16NM | +1.11 %  | 55.6       | 195.2          | T4 RIGHT, r 25.80, z +7.5 | 71.3       | T2_T3, r 24.78, z +4.4, Tangente 63° | -102.9     | T4_T5      | 61.5    | T3   |
| `pos_036_W4_QS`  | LOAD_16NM | +1.12 %  | 101.6      | 95.7           | T4 RIGHT, r 25.80, z +6.7 | 60.0       | T2_T3, r 24.78, z +4.4, Tangente 63° | -73.8      | T4_T5      | 114.1   | T3   |
| `pos_036_W4_DY1` | LOAD_16NM | +1.17 %  | 92.8       | 105.3          | T4 RIGHT, r 25.80, z +7.5 | 63.4       | T2_T3, r 24.78, z +4.4, Tangente 63° | -78.5      | T4_T5      | 103.7   | T3   |
| `pos_036_W4_DY2` | LOAD_16NM | +1.38 %  | 62.5       | 127.4          | T4 RIGHT, r 25.80, z +7.5 | 64.4       | T2_T3, r 24.78, z +4.4, Tangente 63° | -83.0      | T4_T5      | 69.3    | T3   |
| `pos_049_W1_QS`  | LOAD_16NM | -0.85 %  | 96.3       | 80.6           | T4 RIGHT, r 26.00, z +0.0 | 86.2       | T2_T3, r 24.83, z +0.0, Tangente 45° | -105.9     | T3_T4      | 114.6   | T3   |
| `pos_049_W1_DY1` | LOAD_16NM | -0.95 %  | 89.8       | 81.6           | T3 RIGHT, r 26.10, z +0.0 | 89.6       | T2_T3, r 24.83, z +0.0, Tangente 45° | -110.7     | T3_T4      | 106.9   | T3   |
| `pos_049_W1_DY2` | LOAD_16NM | -1.12 %  | 73.1       | 103.1          | T3 RIGHT, r 26.10, z +0.0 | 104.8      | T2_T3, r 24.83, z +0.0, Tangente 45° | -131.2     | T3_T4      | 87.4    | T3   |
| `pos_049_W2_QS`  | LOAD_16NM | -0.82 %  | 108.9      | 86.5           | T4 RIGHT, r 26.00, z +0.0 | 50.0       | T2_T3, r 24.90, z +0.0, Tangente 30° | -57.1      | T3_T4      | 128.0   | T3   |
| `pos_049_W2_DY1` | LOAD_16NM | -0.89 %  | 101.5      | 84.2           | T4 RIGHT, r 26.00, z +0.0 | 51.9       | T2_T3, r 24.88, z +0.0, Tangente 33° | -59.8      | T3_T4      | 119.5   | T3   |
| `pos_049_W2_DY2` | LOAD_16NM | -1.06 %  | 78.4       | 74.6           | T3 RIGHT, r 26.10, z +0.0 | 61.7       | T2_T3, r 24.86, z +0.0, Tangente 37° | -71.8      | T3_T4      | 92.4    | T3   |
| `pos_049_W3_QS`  | LOAD_16NM | -0.91 %  | 95.0       | 80.7           | T4 RIGHT, r 26.00, z +7.5 | 84.6       | T2_T3, r 24.82, z +0.0, Tangente 49° | -108.0     | T3_T4      | 108.1   | T3   |
| `pos_049_W3_DY1` | LOAD_16NM | -0.95 %  | 89.2       | 75.6           | T4 RIGHT, r 26.00, z +7.5 | 87.9       | T2_T3, r 24.82, z +0.0, Tangente 49° | -114.7     | T3_T4      | 100.7   | T3   |
| `pos_049_W3_DY2` | LOAD_16NM | -1.11 %  | 72.4       | 89.4           | T3 RIGHT, r 26.20, z -7.5 | 101.9      | T2_T3, r 24.82, z +0.0, Tangente 49° | -135.4     | T3_T4      | 82.1    | T3   |
| `pos_049_W4_QS`  | LOAD_16NM | -0.85 %  | 106.2      | 87.1           | T4 RIGHT, r 26.00, z +7.5 | 59.8       | T2_T3, r 24.78, z +4.4, Tangente 63° | -76.1      | T3_T4      | 120.7   | T3   |
| `pos_049_W4_DY1` | LOAD_16NM | -1.00 %  | 99.5       | 87.2           | T4 RIGHT, r 26.00, z +7.5 | 65.2       | T2_T3, r 24.78, z +4.4, Tangente 63° | -82.7      | T3_T4      | 112.4   | T3   |
| `pos_049_W4_DY2` | LOAD_16NM | -1.04 %  | 76.8       | 67.0           | T3 RIGHT, r 26.10, z +0.7 | 75.7       | T2_T3, r 24.78, z +4.4, Tangente 63° | -97.9      | T3_T4      | 86.8    | T3   |
| `pos_063_W1_QS`  | LOAD_16NM | -0.36 %  | 84.7       | 141.9          | T3 RIGHT, r 25.70, z +0.0 | 74.8       | T2_T3, r 24.83, z +0.0, Tangente 45° | -98.8      | T3_T4      | 99.0    | T3   |
| `pos_063_W1_DY1` | LOAD_16NM | -0.38 %  | 76.3       | 142.1          | T3 RIGHT, r 25.70, z +0.0 | 74.8       | T2_T3, r 24.83, z +0.0, Tangente 45° | -98.8      | T3_T4      | 89.1    | T3   |
| `pos_063_W1_DY2` | LOAD_16NM | -0.36 %  | 54.5       | 141.9          | T3 RIGHT, r 25.70, z +0.0 | 75.1       | T2_T3, r 24.83, z +0.0, Tangente 45° | -98.8      | T3_T4      | 63.3    | T3   |
| `pos_063_W2_QS`  | LOAD_16NM | -0.21 %  | 104.9      | 87.6           | T3 RIGHT, r 25.70, z +0.0 | 47.0       | T1_T2, r 24.86, z +0.0, Tangente 37° | -61.1      | T3_T4      | 120.1   | T3   |
| `pos_063_W2_DY1` | LOAD_16NM | -0.22 %  | 94.7       | 93.0           | T3 RIGHT, r 25.70, z +0.0 | 48.0       | T2_T3, r 24.88, z +0.0, Tangente 33° | -63.0      | T3_T4      | 109.1   | T3   |
| `pos_063_W2_DY2` | LOAD_16NM | -0.23 %  | 62.1       | 103.6          | T3 RIGHT, r 25.70, z +0.0 | 51.6       | T2_T3, r 24.85, z +0.0, Tangente 40° | -67.3      | T3_T4      | 71.5    | T3   |
| `pos_063_W3_QS`  | LOAD_16NM | -0.33 %  | 84.0       | 126.2          | T3 RIGHT, r 25.70, z +0.0 | 73.6       | T2_T3, r 24.86, z -0.7, Tangente 37° | -109.5     | T3_T4      | 93.1    | T3   |
| `pos_063_W3_DY1` | LOAD_16NM | -0.34 %  | 76.6       | 126.7          | T3 RIGHT, r 25.70, z +7.5 | 73.9       | T2_T3, r 24.86, z -0.7, Tangente 37° | -111.2     | T3_T4      | 83.9    | T3   |
| `pos_063_W3_DY2` | LOAD_16NM | -0.32 %  | 54.5       | 127.8          | T3 RIGHT, r 25.70, z +7.5 | 74.0       | T2_T3, r 24.86, z -0.7, Tangente 37° | -109.9     | T3_T4      | 59.5    | T3   |
| `pos_063_W4_QS`  | LOAD_16NM | -0.19 %  | 101.4      | 81.0           | T3 RIGHT, r 25.70, z +0.7 | 56.5       | T1_T2, r 24.77, z +5.1, Tangente 68° | -80.4      | T3_T4      | 111.1   | T2   |
| `pos_063_W4_DY1` | LOAD_16NM | -0.21 %  | 92.3       | 90.2           | T3 RIGHT, r 25.70, z +7.5 | 59.1       | T1_T2, r 24.77, z +5.1, Tangente 68° | -85.5      | T3_T4      | 100.7   | T2   |
| `pos_063_W4_DY2` | LOAD_16NM | -0.19 %  | 61.1       | 103.4          | T3 RIGHT, r 25.70, z +7.5 | 59.4       | T1_T2, r 24.78, z +5.1, Tangente 63° | -89.5      | T3_T4      | 66.6    | T3   |
| `pos_068_W1_QS`  | LOAD_16NM | +0.62 %  | 87.8       | 177.3          | T3 RIGHT, r 25.80, z -3.6 | 72.0       | T1_T2, r 24.82, z +0.0, Tangente 49° | -92.6      | T3_T4      | 100.2   | T2   |
| `pos_068_W1_DY1` | LOAD_16NM | +0.69 %  | 79.5       | 179.7          | T3 RIGHT, r 25.80, z -3.6 | 72.0       | T1_T2, r 24.82, z +0.0, Tangente 49° | -92.9      | T3_T4      | 90.5    | T2   |
| `pos_068_W1_DY2` | LOAD_16NM | +0.85 %  | 57.5       | 190.7          | T3 RIGHT, r 25.80, z -5.1 | 72.4       | T1_T2, r 24.82, z +0.0, Tangente 49° | -93.2      | T3_T4      | 65.0    | T2   |
| `pos_068_W2_QS`  | LOAD_16NM | +0.83 %  | 107.4      | 96.1           | T3 RIGHT, r 25.80, z -5.9 | 49.4       | T1_T2, r 24.88, z +0.0, Tangente 33° | -58.4      | T3_T4      | 122.8   | T2   |
| `pos_068_W2_DY1` | LOAD_16NM | +0.88 %  | 97.5       | 103.7          | T3 RIGHT, r 25.80, z -5.9 | 50.5       | T1_T2, r 24.86, z +0.0, Tangente 37° | -60.0      | T3_T4      | 111.4   | T2   |
| `pos_068_W2_DY2` | LOAD_16NM | +1.12 %  | 65.9       | 125.7          | T3 RIGHT, r 25.80, z -5.9 | 54.1       | T1_T2, r 24.85, z +0.0, Tangente 40° | -63.8      | T3_T4      | 74.6    | T2   |
| `pos_068_W3_QS`  | LOAD_16NM | +0.67 %  | 87.6       | 187.7          | T3 RIGHT, r 25.80, z -7.5 | 74.8       | T1_T2, r 24.79, z -0.7, Tangente 58° | -102.0     | T3_T4      | 97.8    | T2   |
| `pos_068_W3_DY1` | LOAD_16NM | +0.73 %  | 80.3       | 196.9          | T3 RIGHT, r 25.80, z -7.5 | 76.0       | T1_T2, r 24.79, z -0.7, Tangente 58° | -104.6     | T3_T4      | 89.1    | T2   |
| `pos_068_W3_DY2` | LOAD_16NM | +0.92 %  | 57.8       | 211.1          | T3 RIGHT, r 25.80, z -7.5 | 75.5       | T1_T2, r 24.79, z -0.7, Tangente 58° | -102.9     | T3_T4      | 63.8    | T2   |
| `pos_068_W4_QS`  | LOAD_16NM | +0.90 %  | 105.3      | 100.4          | T3 RIGHT, r 25.80, z -7.5 | 60.3       | T1_T2, r 24.77, z +5.1, Tangente 68° | -76.3      | T3_T4      | 117.9   | T2   |
| `pos_068_W4_DY1` | LOAD_16NM | +0.97 %  | 96.2       | 112.5          | T3 RIGHT, r 25.80, z -7.5 | 63.4       | T1_T2, r 24.77, z +5.1, Tangente 68° | -81.2      | T3_T4      | 107.4   | T2   |
| `pos_068_W4_DY2` | LOAD_16NM | +1.20 %  | 64.9       | 136.8          | T3 RIGHT, r 25.80, z -7.5 | 64.3       | T1_T2, r 24.78, z +5.1, Tangente 63° | -84.8      | T3_T4      | 71.9    | T2   |

## 2026-10-13 07:15 `pilot_20layers_bore33_pocketlevels_round0p1f12_qsdy1dy2_AtoE_gerechnet`

**Zweck:** Der Ringkörper auf den z-Schichten des Taschenkörpers an A bis E (W1 bis W4, QS/DY1/DY2), gerechnet auf der Vollversion in der Nacht 2026-10-12/13 im selben Nachtlauf-Ordner (60 Jobs, 00:49 bis 07:15, 6,0 h; W1 3,1, W2 4,0, W3 7,0, W4 9,9 min je Stellung); Auswertung wie der Taschenkörper; Referenz des Körpervergleichs mit gleicher Abtastung der Faserorientierung. **Ergebnis:** 60 von 60 Jobs vollständig; Schichteffekt gegen den Ring mit 0,75-mm-Schichten ≤ 0,2 % bei W1/W2, bei W3/W4 bis ±7 % im Kontaktdruck und ±4 % in |σ3| (FE-23). (gerechnet: Vollversion; Befunde FE-23)

Netz: 82425 Knoten, 72320 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei            | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|------------------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031_W1_QS`  | A        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 182    | 0       | 2026-10-13 00:59 |
| `pos_031_W1_DY1` | A        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 182    | 0       | 2026-10-13 00:52 |
| `pos_031_W1_DY2` | A        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 160    | 0       | 2026-10-13 00:55 |
| `pos_031_W2_QS`  | A        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 219    | 0       | 2026-10-13 01:11 |
| `pos_031_W2_DY1` | A        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 213    | 0       | 2026-10-13 01:03 |
| `pos_031_W2_DY2` | A        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 206    | 0       | 2026-10-13 01:07 |
| `pos_031_W3_QS`  | A        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 411    | 0       | 2026-10-13 01:32 |
| `pos_031_W3_DY1` | A        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 417    | 0       | 2026-10-13 01:18 |
| `pos_031_W3_DY2` | A        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 377    | 0       | 2026-10-13 01:25 |
| `pos_031_W4_QS`  | A        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 526    | 0       | 2026-10-13 01:59 |
| `pos_031_W4_DY1` | A        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 491    | 0       | 2026-10-13 01:41 |
| `pos_031_W4_DY2` | A        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 524    | 0       | 2026-10-13 01:50 |
| `pos_036_W1_QS`  | B        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 197    | 0       | 2026-10-13 02:10 |
| `pos_036_W1_DY1` | B        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 209    | 0       | 2026-10-13 02:03 |
| `pos_036_W1_DY2` | B        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 201    | 0       | 2026-10-13 02:07 |
| `pos_036_W2_QS`  | B        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 8, 6, 10           | 383    | 12      | 2026-10-13 02:26 |
| `pos_036_W2_DY1` | B        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 260    | 3       | 2026-10-13 02:15 |
| `pos_036_W2_DY2` | B        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 222    | 0       | 2026-10-13 02:19 |
| `pos_036_W3_QS`  | B        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 445    | 0       | 2026-10-13 02:49 |
| `pos_036_W3_DY1` | B        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 434    | 0       | 2026-10-13 02:34 |
| `pos_036_W3_DY2` | B        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 440    | 0       | 2026-10-13 02:41 |
| `pos_036_W4_QS`  | B        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 9            | 702    | 5       | 2026-10-13 03:22 |
| `pos_036_W4_DY1` | B        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 638    | 0       | 2026-10-13 03:00 |
| `pos_036_W4_DY2` | B        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 566    | 0       | 2026-10-13 03:10 |
| `pos_049_W1_QS`  | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 182    | 0       | 2026-10-13 03:33 |
| `pos_049_W1_DY1` | C        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 194    | 0       | 2026-10-13 03:26 |
| `pos_049_W1_DY2` | C        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 188    | 0       | 2026-10-13 03:29 |
| `pos_049_W2_QS`  | C        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 228    | 0       | 2026-10-13 03:46 |
| `pos_049_W2_DY1` | C        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 236    | 0       | 2026-10-13 03:37 |
| `pos_049_W2_DY2` | C        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 229    | 0       | 2026-10-13 03:41 |
| `pos_049_W3_QS`  | C        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 401    | 0       | 2026-10-13 04:07 |
| `pos_049_W3_DY1` | C        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 403    | 0       | 2026-10-13 03:53 |
| `pos_049_W3_DY2` | C        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 415    | 0       | 2026-10-13 04:00 |
| `pos_049_W4_QS`  | C        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 544    | 0       | 2026-10-13 04:36 |
| `pos_049_W4_DY1` | C        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 562    | 0       | 2026-10-13 04:17 |
| `pos_049_W4_DY2` | C        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 524    | 0       | 2026-10-13 04:26 |
| `pos_063_W1_QS`  | D        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 182    | 0       | 2026-10-13 04:46 |
| `pos_063_W1_DY1` | D        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 192    | 0       | 2026-10-13 04:39 |
| `pos_063_W1_DY2` | D        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 164    | 0       | 2026-10-13 04:42 |
| `pos_063_W2_QS`  | D        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 215    | 0       | 2026-10-13 04:58 |
| `pos_063_W2_DY1` | D        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 212    | 0       | 2026-10-13 04:50 |
| `pos_063_W2_DY2` | D        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 210    | 0       | 2026-10-13 04:54 |
| `pos_063_W3_QS`  | D        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 411    | 0       | 2026-10-13 05:19 |
| `pos_063_W3_DY1` | D        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 416    | 0       | 2026-10-13 05:05 |
| `pos_063_W3_DY2` | D        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 391    | 0       | 2026-10-13 05:12 |
| `pos_063_W4_QS`  | D        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 529    | 0       | 2026-10-13 05:47 |
| `pos_063_W4_DY1` | D        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 511    | 0       | 2026-10-13 05:28 |
| `pos_063_W4_DY2` | D        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 526    | 0       | 2026-10-13 05:37 |
| `pos_068_W1_QS`  | E        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 192    | 0       | 2026-10-13 05:58 |
| `pos_068_W1_DY1` | E        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 199    | 0       | 2026-10-13 05:50 |
| `pos_068_W1_DY2` | E        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 196    | 0       | 2026-10-13 05:54 |
| `pos_068_W2_QS`  | E        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 12           | 315    | 6       | 2026-10-13 06:12 |
| `pos_068_W2_DY1` | E        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 9            | 281    | 3       | 2026-10-13 06:03 |
| `pos_068_W2_DY2` | E        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 222    | 0       | 2026-10-13 06:07 |
| `pos_068_W3_QS`  | E        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 464    | 0       | 2026-10-13 06:36 |
| `pos_068_W3_DY1` | E        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 421    | 0       | 2026-10-13 06:20 |
| `pos_068_W3_DY2` | E        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 462    | 0       | 2026-10-13 06:28 |
| `pos_068_W4_QS`  | E        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 10           | 879    | 2       | 2026-10-13 07:15 |
| `pos_068_W4_DY1` | E        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 731    | 0       | 2026-10-13 06:49 |
| `pos_068_W4_DY2` | E        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 661    | 0       | 2026-10-13 07:00 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei            | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031_W1_QS`  | LOAD_16NM | -0.37 %  | 67.6       | 126.1          | T4 RIGHT, r 25.70, z -6.7 | 69.4       | T3_T4, r 24.83, z -6.7, Tangente 45° | -85.8      | T4_T5      | 76.0    | T3   |
| `pos_031_W1_DY1` | LOAD_16NM | -0.34 %  | 61.1       | 126.8          | T4 RIGHT, r 25.70, z -6.7 | 69.6       | T3_T4, r 24.83, z -6.7, Tangente 45° | -86.0      | T4_T5      | 68.6    | T3   |
| `pos_031_W1_DY2` | LOAD_16NM | -0.31 %  | 43.7       | 125.9          | T4 RIGHT, r 25.70, z -6.7 | 69.9       | T3_T4, r 24.83, z -6.7, Tangente 45° | -86.3      | T4_T5      | 48.9    | T3   |
| `pos_031_W2_QS`  | LOAD_16NM | -0.24 %  | 85.6       | 84.8           | T4 RIGHT, r 25.70, z -5.9 | 44.6       | T3_T4, r 24.82, z -5.9, Tangente 49° | -54.5      | T4_T5      | 96.4    | T3   |
| `pos_031_W2_DY1` | LOAD_16NM | -0.22 %  | 76.9       | 89.1           | T4 RIGHT, r 25.70, z -5.9 | 45.9       | T3_T4, r 24.82, z -5.9, Tangente 49° | -55.6      | T4_T5      | 86.5    | T3   |
| `pos_031_W2_DY2` | LOAD_16NM | -0.15 %  | 50.5       | 98.3           | T4 RIGHT, r 25.70, z -5.9 | 49.1       | T3_T4, r 24.83, z -5.9, Tangente 45° | -59.4      | T4_T5      | 56.3    | T3   |
| `pos_031_W3_QS`  | LOAD_16NM | -0.35 %  | 70.1       | 135.6          | T4 RIGHT, r 25.70, z +7.5 | 82.4       | T3_T4, r 24.86, z +6.7, Tangente 37° | -93.3      | T4_T5      | 77.7    | T3   |
| `pos_031_W3_DY1` | LOAD_16NM | -0.32 %  | 64.5       | 138.1          | T4 RIGHT, r 25.70, z +7.5 | 85.0       | T3_T4, r 24.86, z +6.7, Tangente 37° | -94.7      | T4_T5      | 71.5    | T3   |
| `pos_031_W3_DY2` | LOAD_16NM | -0.28 %  | 45.8       | 136.8          | T4 RIGHT, r 25.70, z +7.5 | 83.3       | T3_T4, r 24.86, z +6.7, Tangente 37° | -94.0      | T4_T5      | 50.8    | T3   |
| `pos_031_W4_QS`  | LOAD_16NM | -0.21 %  | 85.2       | 89.2           | T4 RIGHT, r 25.70, z +7.5 | 57.5       | T3_T4, r 24.88, z +6.7, Tangente 33° | -69.0      | T4_T5      | 94.1    | T3   |
| `pos_031_W4_DY1` | LOAD_16NM | -0.18 %  | 78.0       | 96.9           | T4 RIGHT, r 25.70, z +7.5 | 61.1       | T3_T4, r 24.88, z +6.7, Tangente 33° | -72.8      | T4_T5      | 86.2    | T3   |
| `pos_031_W4_DY2` | LOAD_16NM | -0.12 %  | 51.4       | 106.4          | T4 RIGHT, r 25.70, z +7.5 | 64.4       | T3_T4, r 24.83, z +6.7, Tangente 45° | -76.3      | T4_T5      | 57.0    | T3   |
| `pos_036_W1_QS`  | LOAD_16NM | +1.49 %  | 70.3       | 145.7          | T4 RIGHT, r 25.80, z -6.7 | 59.2       | T2_T3, r 24.82, z -5.1, Tangente 49° | -80.2      | T4_T5      | 81.2    | T3   |
| `pos_036_W1_DY1` | LOAD_16NM | +1.57 %  | 63.7       | 148.9          | T4 RIGHT, r 25.80, z -6.7 | 59.2       | T2_T3, r 24.82, z -5.1, Tangente 49° | -80.3      | T4_T5      | 73.4    | T3   |
| `pos_036_W1_DY2` | LOAD_16NM | +1.45 %  | 46.0       | 156.8          | T4 RIGHT, r 25.80, z -6.7 | 59.7       | T2_T3, r 24.82, z -5.1, Tangente 49° | -79.9      | T4_T5      | 52.5    | T3   |
| `pos_036_W2_QS`  | LOAD_16NM | +1.54 %  | 87.0       | 92.1           | T4 RIGHT, r 25.80, z -5.9 | 44.1       | T2_T3, r 24.80, z -4.4, Tangente 54° | -51.7      | T4_T5      | 100.6   | T3   |
| `pos_036_W2_DY1` | LOAD_16NM | +1.58 %  | 78.8       | 98.3           | T4 RIGHT, r 25.80, z -5.9 | 45.0       | T2_T3, r 24.79, z -4.4, Tangente 58° | -52.6      | T4_T5      | 91.0    | T3   |
| `pos_036_W2_DY2` | LOAD_16NM | +1.65 %  | 52.8       | 116.4          | T4 RIGHT, r 25.80, z -5.9 | 47.7       | T2_T3, r 24.82, z -4.4, Tangente 49° | -55.8      | T4_T5      | 60.2    | T3   |
| `pos_036_W3_QS`  | LOAD_16NM | +1.45 %  | 73.4       | 150.7          | T4 RIGHT, r 25.80, z +7.5 | 70.5       | T2_T3, r 24.85, z +6.7, Tangente 40° | -86.9      | T4_T5      | 82.4    | T3   |
| `pos_036_W3_DY1` | LOAD_16NM | +1.42 %  | 67.7       | 152.6          | T4 RIGHT, r 25.80, z +7.5 | 73.4       | T2_T3, r 24.85, z +6.7, Tangente 40° | -87.8      | T4_T5      | 75.5    | T3   |
| `pos_036_W3_DY2` | LOAD_16NM | +1.55 %  | 48.4       | 161.3          | T4 RIGHT, r 25.80, z +7.5 | 71.9       | T2_T3, r 24.85, z +6.7, Tangente 40° | -87.1      | T4_T5      | 53.7    | T3   |
| `pos_036_W4_QS`  | LOAD_16NM | +1.51 %  | 87.5       | 89.9           | T4 RIGHT, r 25.80, z +6.7 | 59.8       | T2_T3, r 24.78, z +5.9, Tangente 63° | -65.5      | T4_T5      | 98.6    | T3   |
| `pos_036_W4_DY1` | LOAD_16NM | +1.57 %  | 80.4       | 96.8           | T4 RIGHT, r 25.80, z +6.7 | 63.6       | T2_T3, r 24.78, z +5.9, Tangente 63° | -69.1      | T4_T5      | 90.2    | T3   |
| `pos_036_W4_DY2` | LOAD_16NM | +1.59 %  | 54.2       | 117.3          | T4 RIGHT, r 25.80, z +6.7 | 64.8       | T2_T3, r 24.78, z +5.9, Tangente 63° | -71.2      | T4_T5      | 60.3    | T3   |
| `pos_049_W1_QS`  | LOAD_16NM | -1.25 %  | 84.0       | 74.9           | T3 RIGHT, r 26.10, z +0.0 | 82.9       | T2_T3, r 24.83, z +0.0, Tangente 45° | -99.2      | T3_T4      | 99.8    | T3   |
| `pos_049_W1_DY1` | LOAD_16NM | -1.29 %  | 78.7       | 80.1           | T3 RIGHT, r 26.10, z +0.0 | 86.5       | T2_T3, r 24.83, z +0.0, Tangente 45° | -104.0     | T3_T4      | 93.6    | T3   |
| `pos_049_W1_DY2` | LOAD_16NM | -1.45 %  | 65.0       | 101.8          | T3 RIGHT, r 26.10, z +0.0 | 101.8      | T2_T3, r 24.83, z +0.0, Tangente 45° | -124.2     | T3_T4      | 77.5    | T3   |
| `pos_049_W2_QS`  | LOAD_16NM | -1.22 %  | 94.8       | 73.0           | T4 RIGHT, r 26.00, z -5.9 | 48.9       | T2_T3, r 24.88, z +0.0, Tangente 33° | -55.6      | T3_T4      | 110.8   | T3   |
| `pos_049_W2_DY1` | LOAD_16NM | -1.22 %  | 88.7       | 68.0           | T4 RIGHT, r 26.00, z -5.9 | 50.9       | T2_T3, r 24.88, z +0.0, Tangente 33° | -58.1      | T3_T4      | 103.9   | T3   |
| `pos_049_W2_DY2` | LOAD_16NM | -1.31 %  | 70.3       | 75.2           | T3 RIGHT, r 26.10, z -5.9 | 61.0       | T2_T3, r 24.86, z +0.0, Tangente 37° | -70.4      | T3_T4      | 82.3    | T3   |
| `pos_049_W3_QS`  | LOAD_16NM | -1.20 %  | 85.4       | 68.4           | T3 RIGHT, r 26.20, z -7.5 | 97.7       | T2_T3, r 24.85, z +6.7, Tangente 40° | -111.0     | T3_T4      | 97.0    | T3   |
| `pos_049_W3_DY1` | LOAD_16NM | -1.20 %  | 80.9       | 73.9           | T3 RIGHT, r 26.20, z -7.5 | 103.9      | T2_T3, r 24.85, z +6.7, Tangente 40° | -117.7     | T3_T4      | 91.1    | T3   |
| `pos_049_W3_DY2` | LOAD_16NM | -1.35 %  | 66.0       | 96.1           | T3 RIGHT, r 26.20, z -7.5 | 118.5      | T2_T3, r 24.85, z +6.7, Tangente 40° | -137.2     | T3_T4      | 74.8    | T3   |
| `pos_049_W4_QS`  | LOAD_16NM | -1.22 %  | 95.4       | 78.5           | T4 RIGHT, r 26.00, z -7.5 | 65.4       | T2_T3, r 24.78, z +5.9, Tangente 63° | -73.3      | T3_T4      | 108.1   | T3   |
| `pos_049_W4_DY1` | LOAD_16NM | -1.21 %  | 89.7       | 75.8           | T4 RIGHT, r 26.00, z +7.5 | 71.3       | T2_T3, r 24.78, z +5.9, Tangente 63° | -79.5      | T3_T4      | 101.3   | T3   |
| `pos_049_W4_DY2` | LOAD_16NM | -1.22 %  | 70.4       | 67.8           | T3 RIGHT, r 26.20, z -7.5 | 83.3       | T2_T3, r 24.78, z +5.9, Tangente 63° | -94.6      | T3_T4      | 79.6    | T3   |
| `pos_063_W1_QS`  | LOAD_16NM | -0.39 %  | 68.7       | 125.6          | T3 RIGHT, r 25.70, z -6.7 | 70.2       | T2_T3, r 24.83, z -6.7, Tangente 45° | -83.7      | T3_T4      | 76.9    | T2   |
| `pos_063_W1_DY1` | LOAD_16NM | -0.35 %  | 62.2       | 126.2          | T3 RIGHT, r 25.70, z -6.7 | 70.4       | T2_T3, r 24.83, z -6.7, Tangente 45° | -83.9      | T3_T4      | 69.4    | T2   |
| `pos_063_W1_DY2` | LOAD_16NM | -0.32 %  | 44.5       | 125.4          | T3 RIGHT, r 25.70, z -6.7 | 70.8       | T2_T3, r 24.83, z -6.7, Tangente 45° | -84.2      | T3_T4      | 49.4    | T2   |
| `pos_063_W2_QS`  | LOAD_16NM | -0.26 %  | 86.0       | 85.3           | T3 RIGHT, r 25.70, z -5.9 | 44.8       | T2_T3, r 24.88, z +0.0, Tangente 33° | -54.0      | T3_T4      | 96.6    | T2   |
| `pos_063_W2_DY1` | LOAD_16NM | -0.23 %  | 77.3       | 89.4           | T3 RIGHT, r 25.70, z -5.9 | 45.9       | T2_T3, r 24.86, z +0.0, Tangente 37° | -55.3      | T3_T4      | 86.7    | T2   |
| `pos_063_W2_DY2` | LOAD_16NM | -0.17 %  | 50.9       | 98.3           | T3 RIGHT, r 25.70, z -5.9 | 49.2       | T2_T3, r 24.85, z +0.0, Tangente 40° | -59.1      | T3_T4      | 56.5    | T2   |
| `pos_063_W3_QS`  | LOAD_16NM | -0.36 %  | 71.2       | 135.2          | T3 RIGHT, r 25.70, z +7.5 | 84.2       | T2_T3, r 24.85, z +6.7, Tangente 40° | -93.6      | T3_T4      | 78.6    | T2   |
| `pos_063_W3_DY1` | LOAD_16NM | -0.34 %  | 65.6       | 138.0          | T3 RIGHT, r 25.70, z +7.5 | 86.7       | T2_T3, r 24.85, z +6.7, Tangente 40° | -95.6      | T3_T4      | 72.3    | T2   |
| `pos_063_W3_DY2` | LOAD_16NM | -0.29 %  | 46.6       | 136.1          | T3 RIGHT, r 25.70, z +7.5 | 85.2       | T2_T3, r 24.85, z +6.7, Tangente 40° | -94.4      | T3_T4      | 51.4    | T2   |
| `pos_063_W4_QS`  | LOAD_16NM | -0.23 %  | 86.5       | 88.9           | T3 RIGHT, r 25.70, z +7.5 | 58.4       | T2_T3, r 24.92, z +6.7, Tangente 26° | -71.7      | T3_T4      | 95.5    | T2   |
| `pos_063_W4_DY1` | LOAD_16NM | -0.20 %  | 79.3       | 96.9           | T3 RIGHT, r 25.70, z +7.5 | 61.9       | T2_T3, r 24.92, z +6.7, Tangente 26° | -76.0      | T3_T4      | 87.2    | T2   |
| `pos_063_W4_DY2` | LOAD_16NM | -0.13 %  | 52.4       | 106.5          | T3 RIGHT, r 25.70, z +7.5 | 64.7       | T2_T3, r 24.85, z +6.7, Tangente 40° | -78.6      | T3_T4      | 57.7    | T2   |
| `pos_068_W1_QS`  | LOAD_16NM | +1.40 %  | 71.4       | 146.8          | T3 RIGHT, r 25.80, z -6.7 | 61.6       | T1_T2, r 24.82, z -5.1, Tangente 49° | -77.9      | T3_T4      | 82.3    | T2   |
| `pos_068_W1_DY1` | LOAD_16NM | +1.47 %  | 64.7       | 149.9          | T3 RIGHT, r 25.80, z -6.7 | 61.6       | T1_T2, r 24.82, z -5.1, Tangente 49° | -78.0      | T3_T4      | 74.4    | T2   |
| `pos_068_W1_DY2` | LOAD_16NM | +1.41 %  | 46.8       | 158.6          | T3 RIGHT, r 25.80, z -6.7 | 62.1       | T1_T2, r 24.82, z -5.1, Tangente 49° | -77.6      | T3_T4      | 53.2    | T2   |
| `pos_068_W2_QS`  | LOAD_16NM | +1.48 %  | 87.6       | 93.5           | T3 RIGHT, r 25.80, z -5.9 | 45.6       | T1_T2, r 24.86, z -4.4, Tangente 37° | -51.6      | T3_T4      | 101.0   | T2   |
| `pos_068_W2_DY1` | LOAD_16NM | +1.58 %  | 79.4       | 99.7           | T3 RIGHT, r 25.80, z -5.9 | 46.4       | T1_T2, r 24.86, z -4.4, Tangente 37° | -52.8      | T3_T4      | 91.5    | T2   |
| `pos_068_W2_DY2` | LOAD_16NM | +1.61 %  | 53.2       | 117.4          | T3 RIGHT, r 25.80, z -5.9 | 49.1       | T1_T2, r 24.85, z -4.4, Tangente 40° | -55.8      | T3_T4      | 60.6    | T2   |
| `pos_068_W3_QS`  | LOAD_16NM | +1.43 %  | 74.6       | 166.4          | T3 RIGHT, r 25.80, z -7.5 | 71.5       | T1_T2, r 24.78, z -6.7, Tangente 63° | -87.0      | T3_T4      | 83.8    | T2   |
| `pos_068_W3_DY1` | LOAD_16NM | +1.37 %  | 68.7       | 171.7          | T3 RIGHT, r 25.80, z -7.5 | 74.8       | T1_T2, r 24.78, z -6.7, Tangente 63° | -88.4      | T3_T4      | 76.7    | T2   |
| `pos_068_W3_DY2` | LOAD_16NM | +1.53 %  | 49.2       | 180.7          | T3 RIGHT, r 25.80, z -7.5 | 72.6       | T1_T2, r 24.78, z -6.7, Tangente 63° | -87.3      | T3_T4      | 54.6    | T2   |
| `pos_068_W4_QS`  | LOAD_16NM | +1.49 %  | 89.0       | 93.3           | T3 RIGHT, r 25.80, z -7.5 | 59.4       | T1_T2, r 24.78, z +5.1, Tangente 63° | -67.8      | T3_T4      | 100.3   | T2   |
| `pos_068_W4_DY1` | LOAD_16NM | +1.50 %  | 81.6       | 102.3          | T3 RIGHT, r 25.80, z -7.5 | 62.7       | T1_T2, r 24.78, z +5.1, Tangente 63° | -71.7      | T3_T4      | 91.6    | T2   |
| `pos_068_W4_DY2` | LOAD_16NM | +1.53 %  | 55.0       | 123.4          | T3 RIGHT, r 25.80, z -7.5 | 64.1       | T1_T2, r 24.78, z +5.1, Tangente 63° | -73.1      | T3_T4      | 61.2    | T2   |

## 2026-10-13 10:40 `vollrad_52teeth_ring`

**Zweck:** Das volle Rad (52 Zähne, geschlossener Ring ohne zahnlose Segmente, Zahn 27 auf +y wie Zahn 3 des Sektors) mit dem Ringkörper in der Dichte der Wochenendserie (20 Schichten, Bohrung 33 mm, C3D8I; 846 300 Knoten, 744 640 Elemente, keine Bilder) für ein CONVERSE-Mapping des ganzen Teils: Faserorientierung aller Zähne, Angussnähe und Bindenähte, Streuung von Zahn zu Zahn (Ausblick: die Wahl der gemappten Zähne, ADR-116 Punkt 49). **Ergebnis:** Netz geschrieben 2026-10-13 (`mesh --closed`); Mapping des Nutzers vom 2026-10-13 14:17 bis 14:18 (`91_Converse/wheel-52_mesh_{QS,DY1,DY2}.cof`, 86 MB je Datei), geprüft: Labels wie das Netz, Karte je Rate, Orientierungszeilen der drei Raten identisch; gegen das Sektor-Mapping an 71 600 deckungsgleichen Elementen 97,3 % mit gleicher 1-Richtung, 2,7 % über 1° und 1,5 % über 10° (bis 90°, Achsentausch 1/2 bei fast gleichen Eigenwerten, gleichmäßig über Zähne, Radien und Umfang, an den Stirnflächen doppelt so häufig); Auswertung aller 52 Zähne in faserorientierung_vollrad/ring (ADR-119 Ergänzung): Zahn 27 gleich Zahn 3 des Sektors in jeder Zone; über den Umfang streut der AI der Fußrundungen 0,30 ± 0,10 (0,12 bis 0,53), der oberen Flanken 0,57 ± 0,13, des Kerns 0,35 ± 0,14, in Wellen von zwölf bis fünfzehn Zähnen; der Sektorzahn liegt bei Fuß und unterer Flanke nahe dem Mittel, bei oberer Flanke, Fußfläche und U darüber.

Nicht gerechnet: 1 Dateien (`wheel_mesh`).

## 2026-10-13 10:40 `vollrad_52teeth_pocket`

**Zweck:** Dasselbe volle Rad mit dem Taschenkörper nach Zeichnung (857 220 Knoten, 750 256 Elemente; Ringe Nabe/Tasche/Felge 3/3/2, Steg 6, Tasche 7 Schichten). **Ergebnis:** Netz geschrieben 2026-10-13; Mapping des Nutzers 14:25 bis 14:26 (`wheel-52-pocket_mesh_{QS,DY1,DY2}.cof`), geprüft: Labels, Karten, Raten identisch; Auswertung aller 52 Zähne in faserorientierung_vollrad/pocket: Zonenmittel innerhalb 0,02 des Ringrads, dieselben Extremzähne, Zahn 27 bis 0,05 anders (Abtastung auf den Taschenschichten).

Nicht gerechnet: 1 Dateien (`wheel-pocket_mesh`).

## 2026-10-13 11:56 `nachtlauf_2026-10-13_kopfkontakt_ctorient/ctorient`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 82425 Knoten, 72320 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 30 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 30 Dateien (`pos_031_W3_QS`, `pos_031_W3_DY1`, `pos_031_W3_DY2`, `pos_031_W4_QS`, `pos_031_W4_DY1`, `pos_031_W4_DY2` …).

## 2026-10-13 11:56 `pilot_20layers_bore33_ctorient_round0p1f12_qsdy1dy2_AtoE`

**Zweck:** W3 und W4 an A bis E (Gitterindizes 31 36 49 63 68) mit der CT-Orientierung der Zähne (orientierung_ct) statt des Mappings, Raten QS, DY1, DY2, Ringkörper, sonst wie die Wochenendserie (Rundung 0,1 mm, 12 Facetten, Iterationen 20/30/100): Vergleich der anisotropen Stufen mit dem CT-Bild einer realen Verzahnung gegen das Mapping der Spritzgusssimulation an denselben Stellungen wie Ratenpilot und Nachtlauf (ADR-119 Ergänzung); der zuerst geschriebene QS-Ordner wurde nie gerechnet und durch diesen ersetzt (Nutzer, 2026-10-13). **Ergebnis:** Vorlage (30 Jobs, rund 4,5 h).

Netz: 82425 Knoten, 72320 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 30 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 30 Dateien (`pos_031_W3_QS`, `pos_031_W3_DY1`, `pos_031_W3_DY2`, `pos_031_W4_QS`, `pos_031_W4_DY1`, `pos_031_W4_DY2` …).

## 2026-10-13 14:27 `vollrad_52teeth_pocketlevels`

**Zweck:** Das volle Rad mit dem Ringkörper auf den z-Schichten des Taschenkörpers (`mesh --closed --levels pocket`; 846 300 Knoten, 744 640 Elemente; Steg 6 × 0,667 mm, je Tasche 7 × 0,786 mm), die dritte Variante der Nachtlauf-Körper: Mapping mit derselben Abtastung wie der Taschenkörper, aber ohne Taschen (Frage des Nutzers 2026-10-13: das Vollrad mit 0,75-mm-Schichten ist nicht auf Taschen-Schichten). **Ergebnis:** Netz geschrieben 2026-10-13; Mapping des Nutzers 14:55 bis 14:57 (`wheel-52-pocketlevels_mesh_{QS,DY1,DY2}.cof`), geprüft: Labels, Karten, Raten identisch; Auswertung aller 52 Zähne in faserorientierung_vollrad/pocketlevels: wie der Taschenkörper (gleiche Abtastung), Zonenmittel innerhalb 0,02 des Ringrads.

Nicht gerechnet: 1 Dateien (`wheel_mesh`).

## 2026-10-13 17:12 `pilot_20layers_bore33_ctorient_round0p1f12_qsdy1dy2_AtoE_gerechnet`

**Zweck:** Der CT-Orientierungs-Pilot (W3 und W4 mit der Orientierung der CT-Zonen von FVA 856 I statt des Mappings, QS/DY1/DY2 an A bis E), gerechnet auf der Vollversion am 2026-10-13 nachmittags (30 Jobs, 12:23 bis 17:12, 4,8 h; W3 7,9, W4 10,5 min je Stellung, also 0,9 und 0,6 min länger als mit dem Mapping); Auswertung mit fe_series_analysis.py gegen W3 QS der Serie und mit fe_orientation_comparison.py (CT-Zonen gegen Mapping je Stufe und Rate, vergleich_orientierung_AtoE). **Ergebnis:** 30 von 30 Jobs vollständig; CT-Zonen gegen Mapping: Ritzeldrehung −5 bis −11 % (W3) und −6 bis −13 % (W4), Kopfverschiebung −3 bis −13 % (an C am wenigsten), σ1 max −8 bis +6 %, |σ3| max +2 bis +13 % (an C am meisten), Kontaktdruck an A/D/E −10 bis −16 % und an C +4 bis +20 % (W4 16 Nm an C mit Vorzeichenwechsel); DY1 größter, QS kleinster Effekt (ADR-119 Punkt 6, vergleich_orientierung_AtoE/analyse.md). (gerechnet: Vollversion; Befunde FIB-04)

Netz: 82425 Knoten, 72320 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 30 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei            | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|------------------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031_W3_QS`  | A        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 468    | 0       | 2026-10-13 12:45 |
| `pos_031_W3_DY1` | A        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 385    | 0       | 2026-10-13 12:30 |
| `pos_031_W3_DY2` | A        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 375    | 0       | 2026-10-13 12:36 |
| `pos_031_W4_QS`  | A        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 593    | 0       | 2026-10-13 13:15 |
| `pos_031_W4_DY1` | A        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 606    | 0       | 2026-10-13 12:55 |
| `pos_031_W4_DY2` | A        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 572    | 0       | 2026-10-13 13:05 |
| `pos_036_W3_QS`  | B        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 506    | 0       | 2026-10-13 13:42 |
| `pos_036_W3_DY1` | B        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 501    | 0       | 2026-10-13 13:24 |
| `pos_036_W3_DY2` | B        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 504    | 0       | 2026-10-13 13:33 |
| `pos_036_W4_QS`  | B        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 687    | 4       | 2026-10-13 14:16 |
| `pos_036_W4_DY1` | B        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 679    | 0       | 2026-10-13 13:54 |
| `pos_036_W4_DY2` | B        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 616    | 0       | 2026-10-13 14:05 |
| `pos_049_W3_QS`  | C        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 488    | 0       | 2026-10-13 14:42 |
| `pos_049_W3_DY1` | C        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 500    | 0       | 2026-10-13 14:25 |
| `pos_049_W3_DY2` | C        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 475    | 0       | 2026-10-13 14:34 |
| `pos_049_W4_QS`  | C        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 648    | 0       | 2026-10-13 15:16 |
| `pos_049_W4_DY1` | C        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 650    | 0       | 2026-10-13 14:54 |
| `pos_049_W4_DY2` | C        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 634    | 0       | 2026-10-13 15:05 |
| `pos_063_W3_QS`  | D        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 465    | 0       | 2026-10-13 15:40 |
| `pos_063_W3_DY1` | D        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 459    | 0       | 2026-10-13 15:24 |
| `pos_063_W3_DY2` | D        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 432    | 0       | 2026-10-13 15:32 |
| `pos_063_W4_QS`  | D        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 599    | 0       | 2026-10-13 16:11 |
| `pos_063_W4_DY1` | D        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 604    | 0       | 2026-10-13 15:50 |
| `pos_063_W4_DY2` | D        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 586    | 0       | 2026-10-13 16:01 |
| `pos_068_W3_QS`  | E        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 524    | 0       | 2026-10-13 16:38 |
| `pos_068_W3_DY1` | E        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 513    | 0       | 2026-10-13 16:20 |
| `pos_068_W3_DY2` | E        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 489    | 0       | 2026-10-13 16:29 |
| `pos_068_W4_QS`  | E        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 670    | 0       | 2026-10-13 17:12 |
| `pos_068_W4_DY1` | E        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 682    | 0       | 2026-10-13 16:50 |
| `pos_068_W4_DY2` | E        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 618    | 0       | 2026-10-13 17:01 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei            | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031_W3_QS`  | LOAD_16NM | -0.32 %  | 64.2       | 119.0          | T4 RIGHT, r 25.70, z -6.8 | 77.5       | T3_T4, r 24.85, z -6.8, Tangente 40° | -97.6      | T4_T5      | 71.1    | T3   |
| `pos_031_W3_DY1` | LOAD_16NM | -0.28 %  | 58.0       | 118.4          | T4 RIGHT, r 25.70, z -6.8 | 79.1       | T3_T4, r 24.85, z -6.8, Tangente 40° | -100.2     | T4_T5      | 64.1    | T3   |
| `pos_031_W3_DY2` | LOAD_16NM | -0.28 %  | 41.7       | 119.8          | T4 RIGHT, r 25.70, z -6.8 | 77.9       | T3_T4, r 24.85, z -6.8, Tangente 40° | -98.2      | T4_T5      | 46.1    | T3   |
| `pos_031_W4_QS`  | LOAD_16NM | -0.21 %  | 76.0       | 88.7           | T4 RIGHT, r 25.70, z -6.0 | 60.0       | T3_T4, r 24.88, z -0.8, Tangente 33° | -72.6      | T4_T5      | 83.8    | T3   |
| `pos_031_W4_DY1` | LOAD_16NM | -0.19 %  | 68.3       | 91.8           | T4 RIGHT, r 25.70, z -6.0 | 63.8       | T3_T4, r 24.88, z -0.8, Tangente 33° | -76.5      | T4_T5      | 75.2    | T3   |
| `pos_031_W4_DY2` | LOAD_16NM | -0.15 %  | 45.9       | 99.1           | T4 RIGHT, r 25.70, z -6.0 | 65.7       | T3_T4, r 24.86, z -0.8, Tangente 37° | -79.0      | T4_T5      | 50.7    | T3   |
| `pos_036_W3_QS`  | LOAD_16NM | +1.41 %  | 67.2       | 143.1          | T4 RIGHT, r 25.80, z +6.8 | 68.4       | T2_T3, r 24.83, z +3.8, Tangente 45° | -90.9      | T4_T5      | 75.8    | T3   |
| `pos_036_W3_DY1` | LOAD_16NM | +1.47 %  | 60.9       | 145.1          | T4 RIGHT, r 25.80, z -6.8 | 70.5       | T2_T3, r 24.83, z +3.8, Tangente 45° | -93.3      | T4_T5      | 68.3    | T3   |
| `pos_036_W3_DY2` | LOAD_16NM | +1.43 %  | 44.1       | 154.2          | T4 RIGHT, r 25.80, z +6.8 | 69.8       | T2_T3, r 24.83, z +3.8, Tangente 45° | -91.0      | T4_T5      | 49.2    | T3   |
| `pos_036_W4_QS`  | LOAD_16NM | +1.57 %  | 78.6       | 101.1          | T4 RIGHT, r 25.80, z -6.0 | 57.8       | T2_T3, r 24.86, z +3.8, Tangente 37° | -68.8      | T4_T5      | 88.4    | T3   |
| `pos_036_W4_DY1` | LOAD_16NM | +1.51 %  | 70.9       | 107.1          | T4 RIGHT, r 25.80, z -6.0 | 61.0       | T2_T3, r 24.86, z +3.8, Tangente 37° | -71.9      | T4_T5      | 79.4    | T3   |
| `pos_036_W4_DY2` | LOAD_16NM | +1.60 %  | 48.5       | 123.4          | T4 RIGHT, r 25.80, z +6.0 | 62.6       | T2_T3, r 24.85, z +3.8, Tangente 40° | -73.4      | T4_T5      | 54.0    | T3   |
| `pos_049_W3_QS`  | LOAD_16NM | -1.24 %  | 80.7       | 74.3           | T3 RIGHT, r 26.10, z +6.8 | 95.1       | T2_T3, r 24.83, z -0.8, Tangente 45° | -117.5     | T3_T4      | 93.1    | T3   |
| `pos_049_W3_DY1` | LOAD_16NM | -1.28 %  | 75.6       | 79.2           | T3 RIGHT, r 26.10, z +6.8 | 101.5      | T2_T3, r 24.83, z -0.8, Tangente 45° | -126.7     | T3_T4      | 87.0    | T3   |
| `pos_049_W3_DY2` | LOAD_16NM | -1.44 %  | 62.9       | 101.1          | T3 RIGHT, r 26.10, z +6.8 | 117.8      | T2_T3, r 24.83, z -0.8, Tangente 45° | -148.3     | T3_T4      | 72.6    | T3   |
| `pos_049_W4_QS`  | LOAD_16NM | -1.20 %  | 88.6       | 66.8           | T4 RIGHT, r 26.00, z -6.0 | 68.3       | T2_T3, r 24.86, z +1.5, Tangente 37° | -80.2      | T3_T4      | 100.1   | T3   |
| `pos_049_W4_DY1` | LOAD_16NM | -1.18 %  | 82.8       | 61.5           | T3 RIGHT, r 26.10, z +6.0 | 73.9       | T2_T3, r 24.86, z +1.5, Tangente 37° | -87.4      | T3_T4      | 93.4    | T3   |
| `pos_049_W4_DY2` | LOAD_16NM | -1.31 %  | 66.6       | 79.8           | T3 RIGHT, r 26.10, z +6.0 | 87.4       | T2_T3, r 24.86, z +1.5, Tangente 37° | -105.1     | T3_T4      | 75.3    | T3   |
| `pos_063_W3_QS`  | LOAD_16NM | -0.33 %  | 65.4       | 118.8          | T3 RIGHT, r 25.70, z -6.8 | 78.2       | T2_T3, r 24.85, z +6.8, Tangente 40° | -95.4      | T3_T4      | 71.9    | T2   |
| `pos_063_W3_DY1` | LOAD_16NM | -0.29 %  | 59.0       | 118.3          | T3 RIGHT, r 25.70, z -6.8 | 79.8       | T2_T3, r 24.85, z +6.8, Tangente 40° | -98.0      | T3_T4      | 64.9    | T2   |
| `pos_063_W3_DY2` | LOAD_16NM | -0.29 %  | 42.4       | 119.7          | T3 RIGHT, r 25.70, z -6.8 | 78.6       | T2_T3, r 24.85, z +6.8, Tangente 40° | -96.0      | T3_T4      | 46.6    | T2   |
| `pos_063_W4_QS`  | LOAD_16NM | -0.22 %  | 77.1       | 88.6           | T3 RIGHT, r 25.70, z -6.0 | 60.2       | T2_T3, r 24.88, z -0.8, Tangente 33° | -72.0      | T3_T4      | 84.7    | T2   |
| `pos_063_W4_DY1` | LOAD_16NM | -0.21 %  | 69.3       | 91.7           | T3 RIGHT, r 25.70, z -6.0 | 63.9       | T2_T3, r 24.86, z -0.8, Tangente 37° | -75.8      | T3_T4      | 75.8    | T2   |
| `pos_063_W4_DY2` | LOAD_16NM | -0.16 %  | 46.6       | 98.9           | T3 RIGHT, r 25.70, z -6.0 | 65.9       | T2_T3, r 24.86, z -0.8, Tangente 37° | -78.0      | T3_T4      | 51.2    | T2   |
| `pos_068_W3_QS`  | LOAD_16NM | +1.35 %  | 68.4       | 145.7          | T3 RIGHT, r 25.80, z +6.8 | 70.5       | T1_T2, r 24.83, z +2.2, Tangente 45° | -88.7      | T3_T4      | 76.9    | T2   |
| `pos_068_W3_DY1` | LOAD_16NM | +1.38 %  | 62.0       | 146.8          | T3 RIGHT, r 25.80, z +6.8 | 72.6       | T1_T2, r 24.83, z +2.2, Tangente 45° | -91.0      | T3_T4      | 69.3    | T2   |
| `pos_068_W3_DY2` | LOAD_16NM | +1.43 %  | 44.9       | 156.9          | T3 RIGHT, r 25.80, z +6.8 | 71.9       | T1_T2, r 24.83, z +2.2, Tangente 45° | -88.8      | T3_T4      | 49.9    | T2   |
| `pos_068_W4_QS`  | LOAD_16NM | +1.52 %  | 79.7       | 101.3          | T3 RIGHT, r 25.80, z +6.0 | 58.7       | T1_T2, r 24.86, z +3.0, Tangente 37° | -68.0      | T3_T4      | 89.3    | T2   |
| `pos_068_W4_DY1` | LOAD_16NM | +1.52 %  | 72.0       | 107.4          | T3 RIGHT, r 25.80, z +6.0 | 61.9       | T1_T2, r 24.86, z +0.0, Tangente 37° | -71.2      | T3_T4      | 80.4    | T2   |
| `pos_068_W4_DY2` | LOAD_16NM | +1.59 %  | 49.2       | 123.9          | T3 RIGHT, r 25.80, z +6.0 | 63.8       | T1_T2, r 24.85, z +0.0, Tangente 40° | -72.4      | T3_T4      | 54.7    | T2   |

## 2026-10-13 17:17 `nachtlauf_2026-10-13_kopfkontakt_ctorient/kopf_h36_r0p02`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 110775 Knoten, 97520 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 5 Dateien (`pos_031`, `pos_036`, `pos_049`, `pos_063`, `pos_068`).

## 2026-10-13 17:17 `pilot_20layers_bore33_hoehe36_round0p02f12_w1_qs_AtoE`

**Zweck:** Kopfkontakt-Pilot 2: wie Pilot 1 mit Ritzelkopfkante r 0,02 mm (Facetten rund 2,6 µm), nur W1. **Ergebnis:** Vorlage (5 Jobs). (Befunde FE-17, FE-19)

Netz: 110775 Knoten, 97520 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 5 Dateien (`pos_031`, `pos_036`, `pos_049`, `pos_063`, `pos_068`).

## 2026-10-13 17:18 `nachtlauf_2026-10-13_kopfkontakt_ctorient/kopf_h54_r0p02`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 139125 Knoten, 122720 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 5 Dateien (`pos_031`, `pos_036`, `pos_049`, `pos_063`, `pos_068`).

## 2026-10-13 17:18 `pilot_20layers_bore33_hoehe54_round0p02f12_w1_qs_AtoE`

**Zweck:** Kopfkontakt-Pilot 4: 54 Reihen, Ritzelkopfkante r 0,02 mm, nur W1. **Ergebnis:** Vorlage (5 Jobs). (Befunde FE-17, FE-19)

Netz: 139125 Knoten, 122720 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 5 Dateien (`pos_031`, `pos_036`, `pos_049`, `pos_063`, `pos_068`).

## 2026-10-13 17:44 `nachtlauf_2026-10-13_kopfkontakt_ctorient/kopf_h36_r0p05`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 110775 Knoten, 97520 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, W2, Raten QS; Momente am Rad 8, 12, 16 Nm; 10 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 10 Dateien (`pos_031_W1_QS`, `pos_031_W2_QS`, `pos_036_W1_QS`, `pos_036_W2_QS`, `pos_049_W1_QS`, `pos_049_W2_QS` …).

## 2026-10-13 17:44 `pilot_20layers_bore33_hoehe36_round0p05f12_w1w2_qs_AtoE`

**Zweck:** Kopfkontakt-Pilot 1 (Nutzerentscheidung 2026-10-12, Ordner 2026-10-13): Reihen über der Zahnhöhe verdoppelt (36 statt 18, Flankenknoten rund 0,05 mm statt 0,1 mm, 97 520 Elemente), Ritzelkopfkante r 0,05 mm mit 12 Facetten, sonst wie die Wochenendserie; W1 und W2 bei QS an A bis E, um zu prüfen, ob die feinere Flanke die kleinere Rundung trägt (FE-19), wie weit die Ergebnisse von r 0,1 mm abweichen (FE-17) und wie der elastisch-plastische Kopfkontakt auf der feineren Flanke aussieht; ersetzt den nie gerechneten W1-Ordner gleichen Namens ohne _w2. **Ergebnis:** Vorlage (10 Jobs, Nachtlauf-Ordner nachtlauf_2026-10-13_kopfkontakt_ctorient). (Befunde FE-17, FE-19)

Netz: 110775 Knoten, 97520 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, W2, Raten QS; Momente am Rad 8, 12, 16 Nm; 10 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 10 Dateien (`pos_031_W1_QS`, `pos_031_W2_QS`, `pos_036_W1_QS`, `pos_036_W2_QS`, `pos_049_W1_QS`, `pos_049_W2_QS` …).

## 2026-10-13 17:44 `nachtlauf_2026-10-13_kopfkontakt_ctorient/kopf_h54_r0p05`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 139125 Knoten, 122720 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, W2, Raten QS; Momente am Rad 8, 12, 16 Nm; 10 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 10 Dateien (`pos_031_W1_QS`, `pos_031_W2_QS`, `pos_036_W1_QS`, `pos_036_W2_QS`, `pos_049_W1_QS`, `pos_049_W2_QS` …).

## 2026-10-13 17:44 `pilot_20layers_bore33_hoehe54_round0p05f12_w1w2_qs_AtoE`

**Zweck:** Kopfkontakt-Pilot 3: Reihen über der Zahnhöhe verdreifacht (54, Flankenknoten rund 0,033 mm, 122 720 Elemente; 10 Vierecke unter dem Gütemaß 0,35, kleinster Eckensinus 0,33), Ritzelkopfkante r 0,05 mm, W1 und W2. **Ergebnis:** Vorlage (10 Jobs). (Befunde FE-17, FE-19)

Netz: 139125 Knoten, 122720 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, W2, Raten QS; Momente am Rad 8, 12, 16 Nm; 10 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 10 Dateien (`pos_031_W1_QS`, `pos_031_W2_QS`, `pos_036_W1_QS`, `pos_036_W2_QS`, `pos_049_W1_QS`, `pos_049_W2_QS` …).

## 2026-10-13 17:44 `nachtlauf_2026-10-13_kopfkontakt_ctorient/kopf_h36_r0p1`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 110775 Knoten, 97520 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 5 Dateien (`pos_031`, `pos_036`, `pos_049`, `pos_063`, `pos_068`).

## 2026-10-13 17:44 `pilot_20layers_bore33_hoehe36_round0p1f12_w1_qs_AtoE`

**Zweck:** Kontrolle zu den Kopfkontakt-Piloten: 36 Reihen mit der Rundung der Serie (r 0,1 mm), W1 QS an A bis E; trennt den Netzeffekt (Serie mit 18 Reihen gegen 36 Reihen bei gleicher Rundung) vom Rundungseffekt (36 Reihen bei 0,1 gegen 0,05 und 0,02 mm). **Ergebnis:** Vorlage (5 Jobs). (Befunde FE-17, FE-19)

Netz: 110775 Knoten, 97520 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 5 Dateien (`pos_031`, `pos_036`, `pos_049`, `pos_063`, `pos_068`).

## 2026-10-13 17:44 `nachtlauf_2026-10-13_kopfkontakt_ctorient/kopf_h54_r0p1`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 139125 Knoten, 122720 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 5 Dateien (`pos_031`, `pos_036`, `pos_049`, `pos_063`, `pos_068`).

## 2026-10-13 17:44 `pilot_20layers_bore33_hoehe54_round0p1f12_w1_qs_AtoE`

**Zweck:** Kontrolle wie oben mit 54 Reihen. **Ergebnis:** Vorlage (5 Jobs). (Befunde FE-17, FE-19)

Netz: 139125 Knoten, 122720 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 5 Dateien (`pos_031`, `pos_036`, `pos_049`, `pos_063`, `pos_068`).

## 2026-10-13 19:00 `nachtlauf_2026-10-13_kopfkontakt_ctorient/fva856tab4`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W3, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 15 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 15 Dateien (`pos_031_W3_QS`, `pos_031_W3_DY1`, `pos_031_W3_DY2`, `pos_036_W3_QS`, `pos_036_W3_DY1`, `pos_036_W3_DY2` …).

## 2026-10-13 19:00 `pilot_20layers_bore33_fva856tab4_round0p1f12_w3_qsdy1dy2_AtoE`

**Zweck:** W3 mit den neun Ingenieurkonstanten aus FVA 856 I Tabelle 4 (Randschicht, konditioniert, Zeilen 80 °C mit QS/DY1/DY2) statt des feldabhängigen Elastik-Blocks der CONVERSE-Karte, Faserkoordinatensystem des Mappings, Netz und Orientierungsstücke der Serie, Ritzelkante r 0,1 mm, A bis E; die vom Nutzer gewünschte Referenz des FE-Modells zum FVA-Bericht (Wahl B orthotrop, 2026-10-13; ADR-116 Punkt 51); nach dem Review vom Abend neu erzeugt (Kommentarzeilen des Elastik-Blocks auf 256 Zeichen umgebrochen). **Ergebnis:** Vorlage (15 Jobs, Nachtlauf-Ordner nachtlauf_2026-10-13_kopfkontakt_ctorient). (Befunde FE-24)

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W3, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 15 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 15 Dateien (`pos_031_W3_QS`, `pos_031_W3_DY1`, `pos_031_W3_DY2`, `pos_036_W3_QS`, `pos_036_W3_DY1`, `pos_036_W3_DY2` …).

## 2026-10-13 19:00 `nachtlauf_2026-10-13_kopfkontakt_ctorient/fva856tab4_ct`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W3, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 15 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 15 Dateien (`pos_031_W3_QS`, `pos_031_W3_DY1`, `pos_031_W3_DY2`, `pos_036_W3_QS`, `pos_036_W3_DY1`, `pos_036_W3_DY2` …).

## 2026-10-13 19:00 `pilot_20layers_bore33_fva856tab4_ctorient_round0p1f12_w3_qsdy1dy2_AtoE`

**Zweck:** W3 mit den Konstanten aus FVA 856 I Tabelle 4 in den Richtungen der CT-Zonen des Berichts (Orientierungsdateien aus orientierung_ct statt des Mappings), QS/DY1/DY2, A bis E: Werkstoff und Orientierung beide aus dem Bericht, nur Geometrie und Netz von hier; mit W3 der Serie, fva856tab4 und ctorient sind alle vier Kombinationen aus zwei Werkstoff- und zwei Richtungsquellen gerechnet (Nutzerwunsch 2026-10-13 abends). **Ergebnis:** Vorlage (15 Jobs, Nachtlauf-Ordner nachtlauf_2026-10-13_kopfkontakt_ctorient). (Befunde FE-24, FIB-04)

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W3, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 15 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 15 Dateien (`pos_031_W3_QS`, `pos_031_W3_DY1`, `pos_031_W3_DY2`, `pos_036_W3_QS`, `pos_036_W3_DY1`, `pos_036_W3_DY2` …).

## 2026-10-13 20:08 `pilot_20layers_bore33_hoehe36_round0p05f12_w1w2_qs_AtoE_gerechnet`

**Zweck:** Kopfkontakt: 36 Reihen über der Zahnhöhe, Ritzelkante 0,05 mm, W1 und W2 bei QS an A bis E (Nachtlauf 2026-10-13, ADR-116 Punkt 50). **Ergebnis:** W1 bricht bei 16 Nm an B und E ab (FE-19-Muster, Flankenknoten r 25,75 mm), W2 läuft überall durch; gegen die Serie: Drehung −1,4 % an C, −6 % an B/E, σ1 −1 % an C, +7 bis +8 % an B, Kontaktdruck +60 % an B/E (analyse/). (gerechnet: Vollversion; Befunde FE-17, FE-19)

Netz: 110775 Knoten, 97520 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, W2, Raten QS; Momente am Rad 8, 12, 16 Nm; 10 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei           | Stellung | Stufe | Rate | Variante | Löser           | Status                        | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------------|----------|-------|------|----------|-----------------|-------------------------------|-----------------------|--------|---------|------------------|
| `pos_031_W1_QS` | A        | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 272    | 0       | 2026-10-13 18:06 |
| `pos_031_W2_QS` | A        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 342    | 0       | 2026-10-13 18:12 |
| `pos_036_W1_QS` | B        | W1    | QS   |          | linear, N2S 0.2 | not completed (step 4 inc 17) | 6, 6, 6, 30           | 1782   | 170     | 2026-10-13 18:43 |
| `pos_036_W2_QS` | B        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 24           | 795    | 34      | 2026-10-13 18:57 |
| `pos_049_W1_QS` | C        | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 315    | 0       | 2026-10-13 19:02 |
| `pos_049_W2_QS` | C        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 8, 6, 6            | 447    | 2       | 2026-10-13 19:10 |
| `pos_063_W1_QS` | D        | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 315    | 0       | 2026-10-13 19:16 |
| `pos_063_W2_QS` | D        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 6            | 380    | 0       | 2026-10-13 19:23 |
| `pos_068_W1_QS` | E        | W1    | QS   |          | linear, N2S 0.2 | not completed (step 4 inc 16) | 6, 6, 6, 29           | 1822   | 157     | 2026-10-13 19:54 |
| `pos_068_W2_QS` | E        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 28           | 810    | 28      | 2026-10-13 20:08 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei           | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031_W1_QS` | LOAD_16NM | -0.49 %  | 66.2       | 147.5          | T4 RIGHT, r 25.65, z -6.8 | 69.1       | T3_T4, r 24.83, z -6.8, Tangente 45° | -85.1      | T4_T5      | 74.5    | T3   |
| `pos_031_W2_QS` | LOAD_16NM | -0.34 %  | 83.4       | 96.6           | T4 RIGHT, r 25.65, z -6.0 | 44.6       | T3_T4, r 24.82, z -6.0, Tangente 49° | -54.2      | T4_T5      | 94.0    | T3   |
| `pos_036_W1_QS` | LOAD_12NM | +0.28 %  | 51.2       | 184.6          | T4 RIGHT, r 25.70, z +0.0 | 48.0       | T3_T4, r 24.85, z -6.8, Tangente 40° | -59.7      | T4_T5      | 58.9    | T3   |
| `pos_036_W2_QS` | LOAD_16NM | +0.58 %  | 85.4       | 106.3          | T4 RIGHT, r 25.75, z -6.0 | 43.9       | T2_T3, r 24.80, z -4.5, Tangente 54° | -51.5      | T4_T5      | 99.0    | T3   |
| `pos_049_W1_QS` | LOAD_16NM | -0.95 %  | 81.6       | 146.5          | T4 RIGHT, r 25.95, z -6.8 | 80.7       | T2_T3, r 24.83, z +0.0, Tangente 45° | -95.1      | T3_T4      | 97.2    | T3   |
| `pos_049_W2_QS` | LOAD_16NM | -0.95 %  | 92.0       | 109.6          | T4 RIGHT, r 25.95, z -6.0 | 48.2       | T2_T3, r 24.88, z +0.0, Tangente 33° | -54.6      | T3_T4      | 107.8   | T3   |
| `pos_063_W1_QS` | LOAD_16NM | -0.49 %  | 67.4       | 146.7          | T3 RIGHT, r 25.65, z -6.8 | 69.9       | T2_T3, r 24.83, z -6.8, Tangente 45° | -83.0      | T3_T4      | 75.4    | T2   |
| `pos_063_W2_QS` | LOAD_16NM | -0.36 %  | 83.9       | 97.0           | T3 RIGHT, r 25.65, z -6.0 | 44.6       | T2_T3, r 24.88, z +0.0, Tangente 33° | -53.9      | T3_T4      | 94.2    | T2   |
| `pos_068_W1_QS` | LOAD_12NM | +0.33 %  | 52.0       | 183.3          | T3 RIGHT, r 25.70, z +0.0 | 48.2       | T2_T3, r 24.83, z -6.8, Tangente 45° | -58.0      | T3_T4      | 59.7    | T2   |
| `pos_068_W2_QS` | LOAD_16NM | +0.63 %  | 85.8       | 106.2          | T3 RIGHT, r 25.75, z -6.0 | 45.2       | T1_T2, r 24.86, z -4.5, Tangente 37° | -51.3      | T3_T4      | 99.2    | T2   |

## 2026-10-13 20:38 `pilot_20layers_bore33_hoehe36_round0p02f12_w1_qs_AtoE_gerechnet`

**Zweck:** Kopfkontakt: 36 Reihen, Ritzelkante 0,02 mm, W1 bei QS an A bis E (Nachtlauf 2026-10-13). **Ergebnis:** alle fünf Stellungen durch (0,02 mm konvergiert auf 36 Reihen); gegen die Serie: Drehung −1,4 % an C, −6 % an B/E, σ1 −1 % an C, +8 bis +9,5 % an B, +5 bis +6 % an E, Kontaktdruck +57 bis +95 %. (gerechnet: Vollversion; Befunde FE-17, FE-19)

Netz: 110775 Knoten, 97520 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031` | A        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 319    | 0       | 2026-10-13 20:14 |
| `pos_036` | B        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 323    | 0       | 2026-10-13 20:20 |
| `pos_049` | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 311    | 0       | 2026-10-13 20:26 |
| `pos_063` | D        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 318    | 0       | 2026-10-13 20:32 |
| `pos_068` | E        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 323    | 0       | 2026-10-13 20:38 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031` | LOAD_16NM | -0.49 %  | 66.2       | 147.1          | T4 RIGHT, r 25.65, z -6.8 | 69.2       | T3_T4, r 24.83, z -6.8, Tangente 45° | -85.1      | T4_T5      | 74.5    | T3   |
| `pos_036` | LOAD_16NM | +0.10 %  | 67.0       | 230.3          | T4 RIGHT, r 25.70, z -6.8 | 64.7       | T3_T4, r 24.85, z -6.8, Tangente 40° | -79.3      | T4_T5      | 77.6    | T3   |
| `pos_049` | LOAD_16NM | -0.97 %  | 81.6       | 146.1          | T4 RIGHT, r 25.95, z -6.8 | 80.7       | T2_T3, r 24.83, z +0.0, Tangente 45° | -95.1      | T3_T4      | 97.2    | T3   |
| `pos_063` | LOAD_16NM | -0.50 %  | 67.4       | 146.4          | T3 RIGHT, r 25.65, z -6.8 | 70.0       | T2_T3, r 24.83, z -6.8, Tangente 45° | -83.0      | T3_T4      | 75.4    | T2   |
| `pos_068` | LOAD_16NM | +0.08 %  | 68.0       | 229.2          | T3 RIGHT, r 25.70, z -6.8 | 65.3       | T2_T3, r 24.85, z -6.8, Tangente 40° | -77.1      | T3_T4      | 78.5    | T2   |

## 2026-10-13 21:07 `pilot_20layers_bore33_hoehe36_round0p1f12_w1_qs_AtoE_gerechnet`

**Zweck:** Kopfkontakt, Kontrolle: 36 Reihen mit der Kante 0,1 mm der Serie, W1 bei QS an A bis E (trennt Netzeffekt von Rundungseffekt). **Ergebnis:** reiner Netzeffekt: Drehung −0,5 % an C, −2,4 % an B/E, σ1 ±0,6 % an A, C, D und +2 bis +3 % an B, Kontaktdruck +30 bis +57 % (an der Kante nicht konvergiert). (gerechnet: Vollversion; Befunde FE-17, FE-19)

Netz: 110775 Knoten, 97520 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031` | A        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 325    | 0       | 2026-10-13 20:44 |
| `pos_036` | B        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 331    | 0       | 2026-10-13 20:50 |
| `pos_049` | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 323    | 0       | 2026-10-13 20:56 |
| `pos_063` | D        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 311    | 0       | 2026-10-13 21:01 |
| `pos_068` | E        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 333    | 0       | 2026-10-13 21:07 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031` | LOAD_16NM | -0.16 %  | 67.2       | 149.1          | T4 RIGHT, r 25.70, z -6.8 | 67.3       | T3_T4, r 24.83, z -6.8, Tangente 45° | -85.7      | T4_T5      | 75.6    | T3   |
| `pos_036` | LOAD_16NM | +0.83 %  | 69.0       | 216.1          | T4 RIGHT, r 25.75, z -6.8 | 60.9       | T3_T4, r 24.85, z -6.8, Tangente 40° | -79.8      | T4_T5      | 79.9    | T3   |
| `pos_049` | LOAD_16NM | +0.14 %  | 83.7       | 125.6          | T4 RIGHT, r 25.95, z +0.0 | 82.4       | T2_T3, r 24.83, z +0.0, Tangente 45° | -97.4      | T3_T4      | 99.7    | T3   |
| `pos_063` | LOAD_16NM | -0.17 %  | 68.5       | 152.1          | T3 RIGHT, r 25.70, z -6.8 | 68.3       | T2_T3, r 24.83, z -6.8, Tangente 45° | -83.6      | T3_T4      | 76.6    | T2   |
| `pos_068` | LOAD_16NM | +0.77 %  | 70.1       | 218.9          | T3 RIGHT, r 25.75, z -6.8 | 61.9       | T2_T3, r 24.85, z -6.8, Tangente 40° | -77.6      | T3_T4      | 80.9    | T2   |

## 2026-10-13 23:31 `pilot_20layers_bore33_hoehe54_round0p05f12_w1w2_qs_AtoE_gerechnet`

**Zweck:** Kopfkontakt: 54 Reihen, Ritzelkante 0,05 mm, W1 und W2 bei QS an A bis E (Nachtlauf 2026-10-13). **Ergebnis:** W1 bricht bei 16 Nm an E ab, W2 läuft durch; gegen die Serie: Drehung −2,8 % an C, −5,8 % an B/E, σ1 −2,4 % an C, +7 % an B, Kontaktdruck +98 % an B/E und +175 % an C bei 16 Nm. (gerechnet: Vollversion; Befunde FE-17, FE-19)

Netz: 139125 Knoten, 122720 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, W2, Raten QS; Momente am Rad 8, 12, 16 Nm; 10 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei           | Stellung | Stufe | Rate | Variante | Löser           | Status                        | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------------|----------|-------|------|----------|-----------------|-------------------------------|-----------------------|--------|---------|------------------|
| `pos_031_W1_QS` | A        | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 418    | 0       | 2026-10-13 21:15 |
| `pos_031_W2_QS` | A        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 8            | 574    | 2       | 2026-10-13 21:25 |
| `pos_036_W1_QS` | B        | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 11           | 661    | 17      | 2026-10-13 21:37 |
| `pos_036_W2_QS` | B        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 9            | 610    | 2       | 2026-10-13 21:48 |
| `pos_049_W1_QS` | C        | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 8            | 536    | 5       | 2026-10-13 21:57 |
| `pos_049_W2_QS` | C        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 8, 13, 17          | 1118   | 28      | 2026-10-13 22:17 |
| `pos_063_W1_QS` | D        | W1    | QS   |          | linear, N2S 0.2 | complete                      | 6, 6, 6, 6            | 413    | 0       | 2026-10-13 22:24 |
| `pos_063_W2_QS` | D        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 8            | 537    | 2       | 2026-10-13 22:34 |
| `pos_068_W1_QS` | E        | W1    | QS   |          | linear, N2S 0.2 | not completed (step 4 inc 16) | 6, 6, 6, 29           | 2475   | 170     | 2026-10-13 23:16 |
| `pos_068_W2_QS` | E        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete                      | 6, 6, 6, 15           | 867    | 15      | 2026-10-13 23:31 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei           | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031_W1_QS` | LOAD_16NM | -0.25 %  | 66.3       | 149.7          | T4 RIGHT, r 25.66, z -6.8 | 67.0       | T3_T4, r 24.83, z -6.8, Tangente 45° | -85.2      | T4_T5      | 74.5    | T3   |
| `pos_031_W2_QS` | LOAD_16NM | -0.09 %  | 83.3       | 104.7          | T4 RIGHT, r 25.66, z -6.0 | 43.8       | T3_T4, r 24.82, z -6.0, Tangente 49° | -54.3      | T4_T5      | 93.8    | T3   |
| `pos_036_W1_QS` | LOAD_16NM | +0.30 %  | 67.2       | 281.1          | T4 RIGHT, r 25.70, z +0.0 | 63.4       | T3_T4, r 24.85, z -6.8, Tangente 40° | -79.4      | T4_T5      | 77.9    | T3   |
| `pos_036_W2_QS` | LOAD_16NM | +0.45 %  | 85.5       | 117.2          | T4 RIGHT, r 25.73, z -6.0 | 43.9       | T2_T3, r 24.80, z -4.5, Tangente 54° | -51.5      | T4_T5      | 99.1    | T3   |
| `pos_049_W1_QS` | LOAD_16NM | +0.27 %  | 82.1       | 206.0          | T4 RIGHT, r 25.93, z +0.0 | 80.8       | T2_T3, r 24.83, z +0.0, Tangente 45° | -94.6      | T3_T4      | 97.8    | T3   |
| `pos_049_W2_QS` | LOAD_16NM | -0.23 %  | 92.1       | 124.6          | T4 RIGHT, r 25.97, z -6.0 | 48.1       | T2_T3, r 24.88, z +0.0, Tangente 33° | -54.5      | T3_T4      | 108.0   | T3   |
| `pos_063_W1_QS` | LOAD_16NM | -0.24 %  | 67.6       | 154.1          | T3 RIGHT, r 25.66, z -6.8 | 68.1       | T2_T3, r 24.83, z -6.8, Tangente 45° | -83.2      | T3_T4      | 75.5    | T2   |
| `pos_063_W2_QS` | LOAD_16NM | -0.07 %  | 83.9       | 107.7          | T3 RIGHT, r 25.66, z -6.0 | 43.5       | T2_T3, r 24.86, z +0.0, Tangente 37° | -54.0      | T3_T4      | 94.3    | T2   |
| `pos_068_W1_QS` | LOAD_12NM | +0.29 %  | 52.0       | 226.2          | T3 RIGHT, r 25.70, z +0.0 | 48.4       | T2_T3, r 24.83, z -6.8, Tangente 45° | -58.0      | T3_T4      | 59.7    | T2   |
| `pos_068_W2_QS` | LOAD_16NM | +0.50 %  | 85.7       | 119.2          | T3 RIGHT, r 25.73, z -6.0 | 45.2       | T1_T2, r 24.86, z -4.5, Tangente 37° | -51.2      | T3_T4      | 99.2    | T2   |

## 2026-10-14 00:10 `pilot_20layers_bore33_hoehe54_round0p02f12_w1_qs_AtoE_gerechnet`

**Zweck:** Kopfkontakt: 54 Reihen, Ritzelkante 0,02 mm, W1 bei QS an A bis E (Nachtlauf 2026-10-13). **Ergebnis:** alle fünf Stellungen durch (0,02 mm konvergiert auf 54 Reihen); gegen die Serie: Drehung −2,8 bis −3,5 % an C, −4,6 bis −5,9 % an B/E, σ1 −2,4 bis −3,3 % an C, +7,5 bis +9,4 % an B, +4,7 bis +6 % an E, Kontaktdruck +93 bis +210 %. (gerechnet: Vollversion; Befunde FE-17, FE-19)

Netz: 139125 Knoten, 122720 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031` | A        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 399    | 0       | 2026-10-13 23:39 |
| `pos_036` | B        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 460    | 0       | 2026-10-13 23:47 |
| `pos_049` | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 409    | 0       | 2026-10-13 23:55 |
| `pos_063` | D        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 401    | 0       | 2026-10-14 00:02 |
| `pos_068` | E        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 465    | 0       | 2026-10-14 00:10 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031` | LOAD_16NM | -0.53 %  | 65.8       | 166.0          | T4 RIGHT, r 25.63, z -6.8 | 69.1       | T3_T4, r 24.83, z -6.8, Tangente 45° | -84.9      | T4_T5      | 74.0    | T3   |
| `pos_036` | LOAD_16NM | +0.11 %  | 67.1       | 283.2          | T4 RIGHT, r 25.70, z -6.8 | 64.7       | T3_T4, r 24.85, z -6.8, Tangente 40° | -79.4      | T4_T5      | 77.7    | T3   |
| `pos_049` | LOAD_16NM | -0.90 %  | 81.0       | 232.5          | T4 RIGHT, r 25.93, z -6.8 | 80.1       | T2_T3, r 24.83, z +0.0, Tangente 45° | -94.0      | T3_T4      | 96.4    | T3   |
| `pos_063` | LOAD_16NM | -0.54 %  | 67.0       | 165.2          | T3 RIGHT, r 25.63, z -6.8 | 69.9       | T2_T3, r 24.83, z -6.8, Tangente 45° | -82.8      | T3_T4      | 74.9    | T2   |
| `pos_068` | LOAD_16NM | +0.09 %  | 68.1       | 281.9          | T3 RIGHT, r 25.70, z -6.8 | 65.3       | T2_T3, r 24.85, z -6.8, Tangente 40° | -77.1      | T3_T4      | 78.6    | T2   |

## 2026-10-14 00:48 `pilot_20layers_bore33_hoehe54_round0p1f12_w1_qs_AtoE_gerechnet`

**Zweck:** Kopfkontakt, Kontrolle: 54 Reihen mit der Kante 0,1 mm der Serie, W1 bei QS an A bis E. **Ergebnis:** reiner Netzeffekt: Drehung −0,2 bis −1,0 % an A, C, D, −2,3 bis −3,2 % an B/E, σ1 +0,2 % an C, +4,7 % an B, Kontaktdruck +88 bis +171 % (an der Kante nicht konvergiert). (gerechnet: Vollversion; Befunde FE-17, FE-19)

Netz: 139125 Knoten, 122720 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W1, Raten QS; Momente am Rad 8, 12, 16 Nm; 5 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei     | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|-----------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031` | A        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 393    | 0       | 2026-10-14 00:18 |
| `pos_036` | B        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 419    | 0       | 2026-10-14 00:25 |
| `pos_049` | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 431    | 0       | 2026-10-14 00:33 |
| `pos_063` | D        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 402    | 0       | 2026-10-14 00:41 |
| `pos_068` | E        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 429    | 0       | 2026-10-14 00:48 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei     | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|-----------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031` | LOAD_16NM | -0.31 %  | 66.9       | 179.4          | T4 RIGHT, r 25.66, z +0.0 | 67.9       | T3_T4, r 24.83, z -6.8, Tangente 45° | -85.5      | T4_T5      | 75.2    | T3   |
| `pos_036` | LOAD_16NM | +0.63 %  | 68.6       | 272.2          | T4 RIGHT, r 25.73, z -6.8 | 61.8       | T3_T4, r 24.85, z -6.8, Tangente 40° | -79.7      | T4_T5      | 79.5    | T3   |
| `pos_049` | LOAD_16NM | -0.68 %  | 83.2       | 202.8          | T4 RIGHT, r 25.97, z -6.8 | 82.3       | T2_T3, r 24.83, z +0.0, Tangente 45° | -97.5      | T3_T4      | 99.1    | T3   |
| `pos_063` | LOAD_16NM | -0.26 %  | 68.1       | 173.7          | T3 RIGHT, r 25.66, z +0.0 | 68.5       | T2_T3, r 24.83, z -6.8, Tangente 45° | -83.5      | T3_T4      | 76.2    | T2   |
| `pos_068` | LOAD_16NM | +0.62 %  | 69.7       | 275.3          | T3 RIGHT, r 25.73, z -6.8 | 62.7       | T2_T3, r 24.85, z -6.8, Tangente 40° | -77.5      | T3_T4      | 80.5    | T2   |

## 2026-10-14 02:16 `pilot_20layers_bore33_fva856tab4_round0p1f12_w3_qsdy1dy2_AtoE_gerechnet`

**Zweck:** W3 mit den Ingenieurkonstanten aus FVA 856 I Tabelle 4 in den Richtungen des Mappings, QS/DY1/DY2 an A bis E (Nachtlauf 2026-10-13, ADR-116 Punkt 51). **Ergebnis:** 15 von 15 Jobs; Richtungsquelle unter Tabelle 4 (gegen fva856tab4_ctorient): Drehung −4,4 bis −12 %, Kopfverschiebung −7,7 bis −14,4 %, σ1 −14 bis +4 %, |σ3| +0,6 bis +14,7 % (vergleich_orientierung_tab4_AtoE); Werkstoffquelle gegen die Karte noch zu tabellieren (FE-24). (gerechnet: Vollversion; Befunde FE-24)

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W3, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 15 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei            | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|------------------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031_W3_QS`  | A        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 308    | 0       | 2026-10-14 01:05 |
| `pos_031_W3_DY1` | A        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 305    | 0       | 2026-10-14 00:54 |
| `pos_031_W3_DY2` | A        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 285    | 0       | 2026-10-14 01:00 |
| `pos_036_W3_QS`  | B        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 365    | 0       | 2026-10-14 01:24 |
| `pos_036_W3_DY1` | B        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 327    | 0       | 2026-10-14 01:11 |
| `pos_036_W3_DY2` | B        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 332    | 0       | 2026-10-14 01:17 |
| `pos_049_W3_QS`  | C        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 315    | 0       | 2026-10-14 01:41 |
| `pos_049_W3_DY1` | C        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 309    | 0       | 2026-10-14 01:29 |
| `pos_049_W3_DY2` | C        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 323    | 0       | 2026-10-14 01:35 |
| `pos_063_W3_QS`  | D        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 306    | 0       | 2026-10-14 01:57 |
| `pos_063_W3_DY1` | D        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 312    | 0       | 2026-10-14 01:47 |
| `pos_063_W3_DY2` | D        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 293    | 0       | 2026-10-14 01:52 |
| `pos_068_W3_QS`  | E        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 373    | 0       | 2026-10-14 02:16 |
| `pos_068_W3_DY1` | E        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 337    | 0       | 2026-10-14 02:04 |
| `pos_068_W3_DY2` | E        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 341    | 0       | 2026-10-14 02:10 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei            | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031_W3_QS`  | LOAD_16NM | -0.39 %  | 81.9       | 134.2          | T4 RIGHT, r 25.70, z +7.5 | 92.9       | T3_T4, r 24.86, z +6.8, Tangente 37° | -102.0     | T4_T5      | 91.6    | T3   |
| `pos_031_W3_DY1` | LOAD_16NM | -0.35 %  | 65.7       | 133.1          | T4 RIGHT, r 25.70, z +7.5 | 90.6       | T3_T4, r 24.86, z +6.8, Tangente 37° | -100.2     | T4_T5      | 73.4    | T3   |
| `pos_031_W3_DY2` | LOAD_16NM | -0.30 %  | 44.6       | 130.8          | T4 RIGHT, r 25.70, z +7.5 | 85.9       | T3_T4, r 24.86, z +6.8, Tangente 37° | -96.9      | T4_T5      | 49.8    | T3   |
| `pos_036_W3_QS`  | LOAD_16NM | +1.48 %  | 85.4       | 146.5          | T4 RIGHT, r 25.80, z +7.5 | 75.4       | T2_T3, r 24.85, z +6.8, Tangente 40° | -95.3      | T4_T5      | 97.2    | T3   |
| `pos_036_W3_DY1` | LOAD_16NM | +1.46 %  | 68.8       | 150.4          | T4 RIGHT, r 25.80, z +7.5 | 73.4       | T2_T3, r 24.85, z +6.8, Tangente 40° | -92.9      | T4_T5      | 78.0    | T3   |
| `pos_036_W3_DY2` | LOAD_16NM | +1.53 %  | 47.0       | 158.0          | T4 RIGHT, r 25.80, z +7.5 | 69.7       | T2_T3, r 24.85, z +6.8, Tangente 40° | -89.9      | T4_T5      | 53.0    | T3   |
| `pos_049_W3_QS`  | LOAD_16NM | -1.20 %  | 95.0       | 75.5           | T4 RIGHT, r 26.00, z -7.5 | 98.5       | T2_T3, r 24.85, z +6.8, Tangente 40° | -113.6     | T3_T4      | 109.1   | T3   |
| `pos_049_W3_DY1` | LOAD_16NM | -1.21 %  | 82.2       | 68.9           | T3 RIGHT, r 26.10, z +6.8 | 104.3      | T2_T3, r 24.85, z +6.8, Tangente 40° | -121.8     | T3_T4      | 94.8    | T3   |
| `pos_049_W3_DY2` | LOAD_16NM | -1.38 %  | 65.4       | 93.0           | T3 RIGHT, r 26.10, z +6.8 | 118.1      | T2_T3, r 24.85, z +6.8, Tangente 40° | -141.7     | T3_T4      | 75.9    | T3   |
| `pos_063_W3_QS`  | LOAD_16NM | -0.41 %  | 83.6       | 133.9          | T3 RIGHT, r 25.70, z +7.5 | 90.1       | T2_T3, r 24.85, z +6.8, Tangente 40° | -103.5     | T3_T4      | 92.9    | T2   |
| `pos_063_W3_DY1` | LOAD_16NM | -0.36 %  | 67.1       | 132.7          | T3 RIGHT, r 25.70, z +7.5 | 88.4       | T2_T3, r 24.85, z +6.8, Tangente 40° | -100.8     | T3_T4      | 74.5    | T2   |
| `pos_063_W3_DY2` | LOAD_16NM | -0.31 %  | 45.5       | 130.1          | T3 RIGHT, r 25.70, z +7.5 | 84.7       | T2_T3, r 24.85, z +6.8, Tangente 40° | -96.3      | T3_T4      | 50.6    | T2   |
| `pos_068_W3_QS`  | LOAD_16NM | +1.36 %  | 87.0       | 171.3          | T3 RIGHT, r 25.80, z -7.5 | 82.5       | T1_T2, r 24.77, z -6.8, Tangente 68° | -96.8      | T3_T4      | 98.7    | T2   |
| `pos_068_W3_DY1` | LOAD_16NM | +1.42 %  | 70.2       | 171.6          | T3 RIGHT, r 25.80, z -7.5 | 79.1       | T1_T2, r 24.77, z -6.8, Tangente 68° | -94.0      | T3_T4      | 79.5    | T2   |
| `pos_068_W3_DY2` | LOAD_16NM | +1.53 %  | 48.1       | 177.5          | T3 RIGHT, r 25.80, z -7.5 | 73.0       | T1_T2, r 24.78, z -6.8, Tangente 63° | -89.2      | T3_T4      | 54.1    | T2   |

## 2026-10-14 03:39 `pilot_20layers_bore33_fva856tab4_ctorient_round0p1f12_w3_qsdy1dy2_AtoE_gerechnet`

**Zweck:** W3 mit den Ingenieurkonstanten aus FVA 856 I Tabelle 4 in den Richtungen der CT-Zonen, QS/DY1/DY2 an A bis E (Nachtlauf 2026-10-13, ADR-116 Punkt 51). **Ergebnis:** 15 von 15 Jobs; CT-Richtungen machen den Zahn unter Tabelle 4 um 4 bis 12 % steifer als die Mapping-Richtungen, σ1 bis −14 %, |σ3| bis +15 % (vergleich_orientierung_tab4_AtoE). (gerechnet: Vollversion; Befunde FE-24, FIB-04)

Netz: 82425 Knoten, 72320 Elemente (C3D8I), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W3, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 15 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei            | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|------------------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031_W3_QS`  | A        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 282    | 0       | 2026-10-14 02:32 |
| `pos_031_W3_DY1` | A        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 282    | 0       | 2026-10-14 02:22 |
| `pos_031_W3_DY2` | A        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 265    | 0       | 2026-10-14 02:27 |
| `pos_036_W3_QS`  | B        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 341    | 0       | 2026-10-14 02:50 |
| `pos_036_W3_DY1` | B        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 327    | 0       | 2026-10-14 02:38 |
| `pos_036_W3_DY2` | B        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 319    | 0       | 2026-10-14 02:43 |
| `pos_049_W3_QS`  | C        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 285    | 0       | 2026-10-14 03:06 |
| `pos_049_W3_DY1` | C        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 301    | 0       | 2026-10-14 02:55 |
| `pos_049_W3_DY2` | C        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 319    | 0       | 2026-10-14 03:01 |
| `pos_063_W3_QS`  | D        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 282    | 0       | 2026-10-14 03:21 |
| `pos_063_W3_DY1` | D        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 283    | 0       | 2026-10-14 03:11 |
| `pos_063_W3_DY2` | D        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 269    | 0       | 2026-10-14 03:16 |
| `pos_068_W3_QS`  | E        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 337    | 0       | 2026-10-14 03:39 |
| `pos_068_W3_DY1` | E        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 329    | 0       | 2026-10-14 03:27 |
| `pos_068_W3_DY2` | E        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 303    | 0       | 2026-10-14 03:33 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei            | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031_W3_QS`  | LOAD_16NM | -0.31 %  | 72.5       | 114.0          | T4 RIGHT, r 25.70, z +0.0 | 80.8       | T3_T4, r 24.88, z -0.8, Tangente 33° | -108.0     | T4_T5      | 79.0    | T3   |
| `pos_031_W3_DY1` | LOAD_16NM | -0.26 %  | 58.7       | 116.4          | T4 RIGHT, r 25.70, z +0.0 | 79.7       | T3_T4, r 24.86, z -0.8, Tangente 37° | -106.0     | T4_T5      | 64.1    | T3   |
| `pos_031_W3_DY2` | LOAD_16NM | -0.27 %  | 40.6       | 119.5          | T4 RIGHT, r 25.70, z +0.0 | 76.9       | T3_T4, r 24.86, z -0.8, Tangente 37° | -101.4     | T4_T5      | 44.5    | T3   |
| `pos_036_W3_QS`  | LOAD_16NM | +1.50 %  | 76.5       | 136.7          | T4 RIGHT, r 25.80, z -6.0 | 76.1       | T2_T3, r 24.86, z +1.5, Tangente 37° | -101.0     | T4_T5      | 83.5    | T3   |
| `pos_036_W3_DY1` | LOAD_16NM | +1.48 %  | 62.1       | 141.2          | T4 RIGHT, r 25.80, z -6.0 | 74.6       | T2_T3, r 24.86, z +1.5, Tangente 37° | -98.7      | T4_T5      | 67.7    | T3   |
| `pos_036_W3_DY2` | LOAD_16NM | +1.48 %  | 43.2       | 152.5          | T4 RIGHT, r 25.80, z -6.0 | 71.7       | T2_T3, r 24.86, z -3.8, Tangente 37° | -94.0      | T4_T5      | 47.2    | T3   |
| `pos_049_W3_QS`  | LOAD_16NM | -1.22 %  | 87.7       | 63.2           | T3 RIGHT, r 26.10, z +0.0 | 98.0       | T2_T3, r 24.86, z -0.8, Tangente 37° | -128.6     | T3_T4      | 96.2    | T3   |
| `pos_049_W3_DY1` | LOAD_16NM | -1.27 %  | 76.8       | 74.1           | T3 RIGHT, r 26.10, z +0.0 | 105.5      | T2_T3, r 24.86, z -0.8, Tangente 37° | -137.9     | T3_T4      | 84.9    | T3   |
| `pos_049_W3_DY2` | LOAD_16NM | -1.44 %  | 62.5       | 99.9           | T3 RIGHT, r 26.10, z -0.8 | 122.8      | T2_T3, r 24.86, z -0.8, Tangente 37° | -159.6     | T3_T4      | 70.1    | T3   |
| `pos_063_W3_QS`  | LOAD_16NM | -0.32 %  | 73.9       | 112.7          | T3 RIGHT, r 25.70, z +0.0 | 80.8       | T2_T3, r 24.86, z -0.8, Tangente 37° | -105.5     | T3_T4      | 80.0    | T2   |
| `pos_063_W3_DY1` | LOAD_16NM | -0.27 %  | 60.0       | 115.2          | T3 RIGHT, r 25.70, z +0.0 | 79.8       | T2_T3, r 24.86, z -0.8, Tangente 37° | -103.7     | T3_T4      | 65.0    | T2   |
| `pos_063_W3_DY2` | LOAD_16NM | -0.28 %  | 41.4       | 118.2          | T3 RIGHT, r 25.70, z +0.0 | 77.5       | T2_T3, r 24.86, z +6.8, Tangente 37° | -99.2      | T3_T4      | 45.0    | T2   |
| `pos_068_W3_QS`  | LOAD_16NM | +1.37 %  | 78.0       | 138.4          | T3 RIGHT, r 25.80, z -6.0 | 78.3       | T1_T2, r 24.86, z +0.8, Tangente 37° | -98.4      | T3_T4      | 84.8    | T2   |
| `pos_068_W3_DY1` | LOAD_16NM | +1.41 %  | 63.3       | 143.8          | T3 RIGHT, r 25.80, z -6.0 | 76.7       | T1_T2, r 24.86, z +0.8, Tangente 37° | -96.3      | T3_T4      | 68.9    | T2   |
| `pos_068_W3_DY2` | LOAD_16NM | +1.48 %  | 44.1       | 155.4          | T3 RIGHT, r 25.80, z -6.0 | 73.9       | T1_T2, r 24.85, z +0.8, Tangente 40° | -91.8      | T3_T4      | 48.0    | T2   |

## 2026-10-14 08:32 `ctorient`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 82425 Knoten, 72320 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper ring; Werkstoffstufen W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 30 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei            | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|------------------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031_W3_QS`  | A        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 472    | 0       | 2026-10-14 04:03 |
| `pos_031_W3_DY1` | A        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 461    | 0       | 2026-10-14 03:47 |
| `pos_031_W3_DY2` | A        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 434    | 0       | 2026-10-14 03:55 |
| `pos_031_W4_QS`  | A        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 598    | 0       | 2026-10-14 04:35 |
| `pos_031_W4_DY1` | A        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 615    | 0       | 2026-10-14 04:14 |
| `pos_031_W4_DY2` | A        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 586    | 0       | 2026-10-14 04:24 |
| `pos_036_W3_QS`  | B        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 510    | 0       | 2026-10-14 05:01 |
| `pos_036_W3_DY1` | B        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 496    | 0       | 2026-10-14 04:43 |
| `pos_036_W3_DY2` | B        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 502    | 0       | 2026-10-14 04:52 |
| `pos_036_W4_QS`  | B        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 702    | 4       | 2026-10-14 05:36 |
| `pos_036_W4_DY1` | B        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 689    | 0       | 2026-10-14 05:13 |
| `pos_036_W4_DY2` | B        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 630    | 0       | 2026-10-14 05:24 |
| `pos_049_W3_QS`  | C        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 481    | 0       | 2026-10-14 06:02 |
| `pos_049_W3_DY1` | C        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 494    | 0       | 2026-10-14 05:45 |
| `pos_049_W3_DY2` | C        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 477    | 0       | 2026-10-14 05:53 |
| `pos_049_W4_QS`  | C        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 656    | 0       | 2026-10-14 06:35 |
| `pos_049_W4_DY1` | C        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 642    | 0       | 2026-10-14 06:13 |
| `pos_049_W4_DY2` | C        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 632    | 0       | 2026-10-14 06:24 |
| `pos_063_W3_QS`  | D        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 468    | 0       | 2026-10-14 07:00 |
| `pos_063_W3_DY1` | D        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 461    | 0       | 2026-10-14 06:44 |
| `pos_063_W3_DY2` | D        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 431    | 0       | 2026-10-14 06:51 |
| `pos_063_W4_QS`  | D        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 595    | 0       | 2026-10-14 07:31 |
| `pos_063_W4_DY1` | D        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 609    | 0       | 2026-10-14 07:10 |
| `pos_063_W4_DY2` | D        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 588    | 0       | 2026-10-14 07:20 |
| `pos_068_W3_QS`  | E        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 528    | 0       | 2026-10-14 07:58 |
| `pos_068_W3_DY1` | E        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 512    | 0       | 2026-10-14 07:40 |
| `pos_068_W3_DY2` | E        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 488    | 0       | 2026-10-14 07:48 |
| `pos_068_W4_QS`  | E        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 670    | 0       | 2026-10-14 08:32 |
| `pos_068_W4_DY1` | E        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 681    | 0       | 2026-10-14 08:10 |
| `pos_068_W4_DY2` | E        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 616    | 0       | 2026-10-14 08:20 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei            | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031_W3_QS`  | LOAD_16NM | -0.32 %  | 64.2       | 119.0          | T4 RIGHT, r 25.70, z -6.8 | 77.5       | T3_T4, r 24.85, z -6.8, Tangente 40° | -97.6      | T4_T5      | 71.1    | T3   |
| `pos_031_W3_DY1` | LOAD_16NM | -0.28 %  | 58.0       | 118.4          | T4 RIGHT, r 25.70, z -6.8 | 79.1       | T3_T4, r 24.85, z -6.8, Tangente 40° | -100.2     | T4_T5      | 64.1    | T3   |
| `pos_031_W3_DY2` | LOAD_16NM | -0.28 %  | 41.7       | 119.8          | T4 RIGHT, r 25.70, z -6.8 | 77.9       | T3_T4, r 24.85, z -6.8, Tangente 40° | -98.2      | T4_T5      | 46.1    | T3   |
| `pos_031_W4_QS`  | LOAD_16NM | -0.21 %  | 76.0       | 88.7           | T4 RIGHT, r 25.70, z -6.0 | 60.0       | T3_T4, r 24.88, z -0.8, Tangente 33° | -72.6      | T4_T5      | 83.8    | T3   |
| `pos_031_W4_DY1` | LOAD_16NM | -0.19 %  | 68.3       | 91.8           | T4 RIGHT, r 25.70, z -6.0 | 63.8       | T3_T4, r 24.88, z -0.8, Tangente 33° | -76.5      | T4_T5      | 75.2    | T3   |
| `pos_031_W4_DY2` | LOAD_16NM | -0.15 %  | 45.9       | 99.1           | T4 RIGHT, r 25.70, z -6.0 | 65.7       | T3_T4, r 24.86, z -0.8, Tangente 37° | -79.0      | T4_T5      | 50.7    | T3   |
| `pos_036_W3_QS`  | LOAD_16NM | +1.41 %  | 67.2       | 143.1          | T4 RIGHT, r 25.80, z +6.8 | 68.4       | T2_T3, r 24.83, z +3.8, Tangente 45° | -90.9      | T4_T5      | 75.8    | T3   |
| `pos_036_W3_DY1` | LOAD_16NM | +1.47 %  | 60.9       | 145.1          | T4 RIGHT, r 25.80, z -6.8 | 70.5       | T2_T3, r 24.83, z +3.8, Tangente 45° | -93.3      | T4_T5      | 68.3    | T3   |
| `pos_036_W3_DY2` | LOAD_16NM | +1.43 %  | 44.1       | 154.2          | T4 RIGHT, r 25.80, z +6.8 | 69.8       | T2_T3, r 24.83, z +3.8, Tangente 45° | -91.0      | T4_T5      | 49.2    | T3   |
| `pos_036_W4_QS`  | LOAD_16NM | +1.57 %  | 78.6       | 101.1          | T4 RIGHT, r 25.80, z -6.0 | 57.8       | T2_T3, r 24.86, z +3.8, Tangente 37° | -68.8      | T4_T5      | 88.4    | T3   |
| `pos_036_W4_DY1` | LOAD_16NM | +1.51 %  | 70.9       | 107.1          | T4 RIGHT, r 25.80, z -6.0 | 61.0       | T2_T3, r 24.86, z +3.8, Tangente 37° | -71.9      | T4_T5      | 79.4    | T3   |
| `pos_036_W4_DY2` | LOAD_16NM | +1.60 %  | 48.5       | 123.4          | T4 RIGHT, r 25.80, z +6.0 | 62.6       | T2_T3, r 24.85, z +3.8, Tangente 40° | -73.4      | T4_T5      | 54.0    | T3   |
| `pos_049_W3_QS`  | LOAD_16NM | -1.24 %  | 80.7       | 74.3           | T3 RIGHT, r 26.10, z +6.8 | 95.1       | T2_T3, r 24.83, z -0.8, Tangente 45° | -117.5     | T3_T4      | 93.1    | T3   |
| `pos_049_W3_DY1` | LOAD_16NM | -1.28 %  | 75.6       | 79.2           | T3 RIGHT, r 26.10, z +6.8 | 101.5      | T2_T3, r 24.83, z -0.8, Tangente 45° | -126.7     | T3_T4      | 87.0    | T3   |
| `pos_049_W3_DY2` | LOAD_16NM | -1.44 %  | 62.9       | 101.1          | T3 RIGHT, r 26.10, z +6.8 | 117.8      | T2_T3, r 24.83, z -0.8, Tangente 45° | -148.3     | T3_T4      | 72.6    | T3   |
| `pos_049_W4_QS`  | LOAD_16NM | -1.20 %  | 88.6       | 66.8           | T4 RIGHT, r 26.00, z -6.0 | 68.3       | T2_T3, r 24.86, z +1.5, Tangente 37° | -80.2      | T3_T4      | 100.1   | T3   |
| `pos_049_W4_DY1` | LOAD_16NM | -1.18 %  | 82.8       | 61.5           | T3 RIGHT, r 26.10, z +6.0 | 73.9       | T2_T3, r 24.86, z +1.5, Tangente 37° | -87.4      | T3_T4      | 93.4    | T3   |
| `pos_049_W4_DY2` | LOAD_16NM | -1.31 %  | 66.6       | 79.8           | T3 RIGHT, r 26.10, z +6.0 | 87.4       | T2_T3, r 24.86, z +1.5, Tangente 37° | -105.1     | T3_T4      | 75.3    | T3   |
| `pos_063_W3_QS`  | LOAD_16NM | -0.33 %  | 65.4       | 118.8          | T3 RIGHT, r 25.70, z -6.8 | 78.2       | T2_T3, r 24.85, z +6.8, Tangente 40° | -95.4      | T3_T4      | 71.9    | T2   |
| `pos_063_W3_DY1` | LOAD_16NM | -0.29 %  | 59.0       | 118.3          | T3 RIGHT, r 25.70, z -6.8 | 79.8       | T2_T3, r 24.85, z +6.8, Tangente 40° | -98.0      | T3_T4      | 64.9    | T2   |
| `pos_063_W3_DY2` | LOAD_16NM | -0.29 %  | 42.4       | 119.7          | T3 RIGHT, r 25.70, z -6.8 | 78.6       | T2_T3, r 24.85, z +6.8, Tangente 40° | -96.0      | T3_T4      | 46.6    | T2   |
| `pos_063_W4_QS`  | LOAD_16NM | -0.22 %  | 77.1       | 88.6           | T3 RIGHT, r 25.70, z -6.0 | 60.2       | T2_T3, r 24.88, z -0.8, Tangente 33° | -72.0      | T3_T4      | 84.7    | T2   |
| `pos_063_W4_DY1` | LOAD_16NM | -0.21 %  | 69.3       | 91.7           | T3 RIGHT, r 25.70, z -6.0 | 63.9       | T2_T3, r 24.86, z -0.8, Tangente 37° | -75.8      | T3_T4      | 75.8    | T2   |
| `pos_063_W4_DY2` | LOAD_16NM | -0.16 %  | 46.6       | 98.9           | T3 RIGHT, r 25.70, z -6.0 | 65.9       | T2_T3, r 24.86, z -0.8, Tangente 37° | -78.0      | T3_T4      | 51.2    | T2   |
| `pos_068_W3_QS`  | LOAD_16NM | +1.35 %  | 68.4       | 145.7          | T3 RIGHT, r 25.80, z +6.8 | 70.5       | T1_T2, r 24.83, z +2.2, Tangente 45° | -88.7      | T3_T4      | 76.9    | T2   |
| `pos_068_W3_DY1` | LOAD_16NM | +1.38 %  | 62.0       | 146.8          | T3 RIGHT, r 25.80, z +6.8 | 72.6       | T1_T2, r 24.83, z +2.2, Tangente 45° | -91.0      | T3_T4      | 69.3    | T2   |
| `pos_068_W3_DY2` | LOAD_16NM | +1.43 %  | 44.9       | 156.9          | T3 RIGHT, r 25.80, z +6.8 | 71.9       | T1_T2, r 24.83, z +2.2, Tangente 45° | -88.8      | T3_T4      | 49.9    | T2   |
| `pos_068_W4_QS`  | LOAD_16NM | +1.52 %  | 79.7       | 101.3          | T3 RIGHT, r 25.80, z +6.0 | 58.7       | T1_T2, r 24.86, z +3.0, Tangente 37° | -68.0      | T3_T4      | 89.3    | T2   |
| `pos_068_W4_DY1` | LOAD_16NM | +1.52 %  | 72.0       | 107.4          | T3 RIGHT, r 25.80, z +6.0 | 61.9       | T1_T2, r 24.86, z +0.0, Tangente 37° | -71.2      | T3_T4      | 80.4    | T2   |
| `pos_068_W4_DY2` | LOAD_16NM | +1.59 %  | 49.2       | 123.9          | T3 RIGHT, r 25.80, z +6.0 | 63.8       | T1_T2, r 24.85, z +0.0, Tangente 40° | -72.4      | T3_T4      | 54.7    | T2   |

## 2026-10-14 13:38 `nachtlauf_2026-10-14_fussrundungen_tasche/tasche_serie_w1w4_qs`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS; Momente am Rad 8, 12, 16 Nm; 396 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 396 Dateien (`pos_001_W1_QS`, `pos_001_W2_QS`, `pos_001_W3_QS`, `pos_001_W4_QS`, `pos_002_W1_QS`, `pos_002_W2_QS` …).

## 2026-10-14 17:33 `pilot_20layers_bore33_pocket_fillet_ellipse_g30_ab3_round0p1f12_qsdy1dy2_AtoE`

**Zweck:** Fußrundungsvariante Ellipse nach Frühe (gamma 30°, a/b 3,0; Literaturwert) am Rad, Taschenkörper: W1 bis W4, QS/DY1/DY2, A bis E, Kante 0,1 mm der Serie, Orientierung aus dem CONVERSE-Mapping des Nutzers auf das Netz der Variante (ADR-116 Punkte 52 und 53). **Ergebnis:** Vorlage; Teil der Kette nachtlauf_2026-10-14_fussrundungen_tasche. (Befunde FE-05)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-14 17:33 `pilot_20layers_bore33_pocket_fillet_ellipse_g25_ab2_round0p1f12_qsdy1dy2_AtoE`

**Zweck:** Fußrundungsvariante Ellipse nach Frühe (gamma 25°, a/b 2,0; Optimum des Sweeps) am Rad, Taschenkörper: W1 bis W4, QS/DY1/DY2, A bis E, Kante 0,1 mm der Serie, Orientierung aus dem CONVERSE-Mapping des Nutzers auf das Netz der Variante (ADR-116 Punkte 52 und 53). **Ergebnis:** Vorlage; Teil der Kette nachtlauf_2026-10-14_fussrundungen_tasche. (Befunde FE-05)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-14 17:34 `nachtlauf_2026-10-14_fussrundungen_tasche/variante_ellipse_g30_ab3`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-14 17:34 `nachtlauf_2026-10-14_fussrundungen_tasche/variante_ellipse_g25_ab2`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-14 17:46 `pilot_20layers_bore33_pocket_fillet_bezier_f1_round0p1f12_qsdy1dy2_AtoE`

**Zweck:** Fußrundungsvariante Bézier nach DE 10 2013 004 861 B3 (f 1,0; Literaturwert) am Rad, Taschenkörper: W1 bis W4, QS/DY1/DY2, A bis E, Kante 0,1 mm der Serie, Orientierung aus dem CONVERSE-Mapping des Nutzers auf das Netz der Variante (ADR-116 Punkte 52 und 53). **Ergebnis:** Vorlage; Teil der Kette nachtlauf_2026-10-14_fussrundungen_tasche. (Befunde FE-05)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-14 17:46 `nachtlauf_2026-10-14_fussrundungen_tasche/variante_bezier_f1`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-14 17:47 `pilot_20layers_bore33_pocket_fillet_bezier_f2p5_round0p1f12_qsdy1dy2_AtoE`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-14 17:47 `nachtlauf_2026-10-14_fussrundungen_tasche/variante_bezier_f2p5`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-14 17:51 `pilot_20layers_bore33_pocket_fillet_bionic_phiauto_r0p3_round0p1f12_qsdy1dy2_AtoE`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-14 17:51 `nachtlauf_2026-10-14_fussrundungen_tasche/variante_bionic_phiauto_r0p3`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-14 17:55 `pilot_20layers_bore33_pocket_fillet_bionic_phi35_r0p2_round0p1f12_qsdy1dy2_AtoE`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-14 17:55 `nachtlauf_2026-10-14_fussrundungen_tasche/variante_bionic_phi35_r0p2`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-14 17:56 `series_20layers_bore33_pocket_fillet_bionic_phi35_r0.2_round0p1f12_30perpitch_margin1_qs`

**Zweck:** Vollserie der Variante mit dem größten Potenzial (bionisch phi 35°, r 0,2 S_L) auf dem Taschenkörper: W1 bis W4 bei QS, 99 Stellungen wie die Grundserie, für den Stommel-Nachweis mit Lastgeschichte gegen die Taschen-Grundserie (ADR-116 Punkt 53). **Ergebnis:** Vorlage; dritter Block der Kette nachtlauf_2026-10-14_fussrundungen_tasche. (Befunde FE-05)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS; Momente am Rad 8, 12, 16 Nm; 396 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 396 Dateien (`pos_001_W1_QS`, `pos_001_W2_QS`, `pos_001_W3_QS`, `pos_001_W4_QS`, `pos_002_W1_QS`, `pos_002_W2_QS` …).

## 2026-10-14 17:56 `nachtlauf_2026-10-14_fussrundungen_tasche/variante_bionic_phi35_r0p2_serie_w1w4_qs`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS; Momente am Rad 8, 12, 16 Nm; 396 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 396 Dateien (`pos_001_W1_QS`, `pos_001_W2_QS`, `pos_001_W3_QS`, `pos_001_W4_QS`, `pos_002_W1_QS`, `pos_002_W2_QS` …).

## 2026-10-15 02:51 `pilot_20layers_bore33_pocket_fillet_ellipse_g30_ab3_round0p1f12_qsdy1dy2_AtoE_gerechnet`

**Zweck:** Fußrundungsvariante Ellipse nach Frühe (gamma 30°, a/b 3,0; Literaturwert), Taschenkörper, W1 bis W4 × QS/DY1/DY2 an A bis E; erster Block der Kette vom 2026-10-14 (ADR-116 Punkt 53). **Ergebnis:** 60 von 60 Jobs (7,9 h, 14.10. 18:28 bis 15.10. 02:51); gegen die Trochoide an C bei 16 Nm σ1 −16 % (W1), −6 % (W2), −4 % (W3), −8 % (W4); an A, B, D und E steigt σ1 dagegen um bis zu +17 % (W1), +22 % (W2), +33 % (W3), +20 % (W4) und |σ3| um bis zu +30 % (W1, W2) und +51 % (W3), der Größtwert sitzt in der Lückenmitte am Krümmungsradius 0,083 mm (unter der Netzauflösung, FE-05); Zahn nachgiebiger: Drehung +5 bis +11 %; ebenes Modell −13 % an B, 3D an B +14 % (vergleich_fussrundung_AtoE). (gerechnet: Vollversion; Befunde FE-05, FE-25)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei            | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|------------------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031_W1_QS`  | A        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 195    | 0       | 2026-10-14 18:37 |
| `pos_031_W1_DY1` | A        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 186    | 0       | 2026-10-14 18:31 |
| `pos_031_W1_DY2` | A        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 166    | 0       | 2026-10-14 18:34 |
| `pos_031_W2_QS`  | A        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 273    | 0       | 2026-10-14 18:51 |
| `pos_031_W2_DY1` | A        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 219    | 0       | 2026-10-14 18:41 |
| `pos_031_W2_DY2` | A        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 263    | 0       | 2026-10-14 18:46 |
| `pos_031_W3_QS`  | A        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 511    | 0       | 2026-10-14 19:18 |
| `pos_031_W3_DY1` | A        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 521    | 0       | 2026-10-14 19:00 |
| `pos_031_W3_DY2` | A        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 470    | 0       | 2026-10-14 19:09 |
| `pos_031_W4_QS`  | A        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 652    | 0       | 2026-10-14 19:52 |
| `pos_031_W4_DY1` | A        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 646    | 0       | 2026-10-14 19:29 |
| `pos_031_W4_DY2` | A        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 659    | 0       | 2026-10-14 19:40 |
| `pos_036_W1_QS`  | B        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 266    | 0       | 2026-10-14 20:06 |
| `pos_036_W1_DY1` | B        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 258    | 0       | 2026-10-14 19:56 |
| `pos_036_W1_DY2` | B        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 249    | 0       | 2026-10-14 20:01 |
| `pos_036_W2_QS`  | B        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 351    | 0       | 2026-10-14 20:24 |
| `pos_036_W2_DY1` | B        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 339    | 2       | 2026-10-14 20:12 |
| `pos_036_W2_DY2` | B        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 289    | 0       | 2026-10-14 20:17 |
| `pos_036_W3_QS`  | B        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 582    | 0       | 2026-10-14 20:54 |
| `pos_036_W3_DY1` | B        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 573    | 0       | 2026-10-14 20:34 |
| `pos_036_W3_DY2` | B        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 556    | 0       | 2026-10-14 20:43 |
| `pos_036_W4_QS`  | B        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 15           | 1066   | 8       | 2026-10-14 21:38 |
| `pos_036_W4_DY1` | B        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 836    | 5       | 2026-10-14 21:08 |
| `pos_036_W4_DY2` | B        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 709    | 0       | 2026-10-14 21:20 |
| `pos_049_W1_QS`  | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 253    | 0       | 2026-10-14 21:52 |
| `pos_049_W1_DY1` | C        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 251    | 0       | 2026-10-14 21:43 |
| `pos_049_W1_DY2` | C        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 250    | 0       | 2026-10-14 21:48 |
| `pos_049_W2_QS`  | C        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 8, 6, 23           | 580    | 20      | 2026-10-14 22:14 |
| `pos_049_W2_DY1` | C        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 8, 6, 6            | 339    | 0       | 2026-10-14 21:58 |
| `pos_049_W2_DY2` | C        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 283    | 0       | 2026-10-14 22:04 |
| `pos_049_W3_QS`  | C        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 540    | 0       | 2026-10-14 22:42 |
| `pos_049_W3_DY1` | C        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 542    | 0       | 2026-10-14 22:23 |
| `pos_049_W3_DY2` | C        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 546    | 0       | 2026-10-14 22:33 |
| `pos_049_W4_QS`  | C        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 8, 6, 15           | 1113   | 10      | 2026-10-14 23:29 |
| `pos_049_W4_DY1` | C        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 8, 6, 6            | 880    | 2       | 2026-10-14 22:58 |
| `pos_049_W4_DY2` | C        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 692    | 0       | 2026-10-14 23:10 |
| `pos_063_W1_QS`  | D        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 243    | 0       | 2026-10-14 23:41 |
| `pos_063_W1_DY1` | D        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 238    | 0       | 2026-10-14 23:33 |
| `pos_063_W1_DY2` | D        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 211    | 0       | 2026-10-14 23:37 |
| `pos_063_W2_QS`  | D        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 12           | 351    | 4       | 2026-10-14 23:58 |
| `pos_063_W2_DY1` | D        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 315    | 3       | 2026-10-14 23:47 |
| `pos_063_W2_DY2` | D        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 271    | 0       | 2026-10-14 23:52 |
| `pos_063_W3_QS`  | D        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 556    | 0       | 2026-10-15 00:27 |
| `pos_063_W3_DY1` | D        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 556    | 0       | 2026-10-15 00:08 |
| `pos_063_W3_DY2` | D        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 506    | 0       | 2026-10-15 00:17 |
| `pos_063_W4_QS`  | D        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 11           | 840    | 9       | 2026-10-15 01:04 |
| `pos_063_W4_DY1` | D        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 650    | 0       | 2026-10-15 00:38 |
| `pos_063_W4_DY2` | D        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 656    | 0       | 2026-10-15 00:50 |
| `pos_068_W1_QS`  | E        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 276    | 0       | 2026-10-15 01:19 |
| `pos_068_W1_DY1` | E        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 267    | 0       | 2026-10-15 01:09 |
| `pos_068_W1_DY2` | E        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 258    | 0       | 2026-10-15 01:14 |
| `pos_068_W2_QS`  | E        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 318    | 2       | 2026-10-15 01:36 |
| `pos_068_W2_DY1` | E        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 312    | 0       | 2026-10-15 01:24 |
| `pos_068_W2_DY2` | E        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 293    | 0       | 2026-10-15 01:30 |
| `pos_068_W3_QS`  | E        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 598    | 0       | 2026-10-15 02:07 |
| `pos_068_W3_DY1` | E        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 598    | 0       | 2026-10-15 01:46 |
| `pos_068_W3_DY2` | E        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 576    | 0       | 2026-10-15 01:56 |
| `pos_068_W4_QS`  | E        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 11           | 1004   | 11      | 2026-10-15 02:51 |
| `pos_068_W4_DY1` | E        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 845    | 2       | 2026-10-15 02:21 |
| `pos_068_W4_DY2` | E        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 731    | 0       | 2026-10-15 02:34 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei            | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031_W1_QS`  | LOAD_16NM | -0.48 %  | 89.0       | 145.4          | T4 RIGHT, r 25.70, z +0.0 | 70.2       | T2_T3, r 24.48, z -2.8, Tangente 73° | -128.3     | T4_T5      | 105.4   | T4   |
| `pos_031_W1_DY1` | LOAD_16NM | -0.46 %  | 80.3       | 146.1          | T4 RIGHT, r 25.70, z +0.0 | 70.1       | T2_T3, r 24.48, z -2.8, Tangente 73° | -128.5     | T4_T5      | 95.2    | T4   |
| `pos_031_W1_DY2` | LOAD_16NM | -0.37 %  | 57.4       | 145.4          | T4 RIGHT, r 25.70, z +0.0 | 70.1       | T2_T3, r 24.48, z -3.6, Tangente 73° | -129.4     | T4_T5      | 67.8    | T4   |
| `pos_031_W2_QS`  | LOAD_16NM | -0.35 %  | 111.9      | 88.4           | T4 RIGHT, r 25.70, z +0.0 | 55.6       | T2_T3, r 24.48, z -4.4, Tangente 87° | -76.6      | T4_T5      | 130.9   | T4   |
| `pos_031_W2_DY1` | LOAD_16NM | -0.32 %  | 101.3      | 94.1           | T4 RIGHT, r 25.70, z +0.0 | 56.5       | T2_T3, r 24.48, z -4.4, Tangente 87° | -79.8      | T4_T5      | 118.9   | T4   |
| `pos_031_W2_DY2` | LOAD_16NM | -0.24 %  | 66.4       | 105.8          | T4 RIGHT, r 25.70, z +0.0 | 57.8       | T2_T3, r 24.48, z -4.4, Tangente 87° | -86.4      | T4_T5      | 77.4    | T4   |
| `pos_031_W3_QS`  | LOAD_16NM | -0.43 %  | 88.1       | 130.3          | T4 RIGHT, r 25.70, z +7.5 | 86.2       | T2_T3, r 24.48, z -3.6, Tangente 73° | -158.2     | T4_T5      | 99.8    | T4   |
| `pos_031_W3_DY1` | LOAD_16NM | -0.41 %  | 80.5       | 132.8          | T4 RIGHT, r 25.70, z +7.5 | 88.9       | T2_T3, r 24.48, z -3.6, Tangente 73° | -164.1     | T4_T5      | 90.0    | T4   |
| `pos_031_W3_DY2` | LOAD_16NM | -0.34 %  | 57.3       | 131.9          | T4 RIGHT, r 25.70, z +0.0 | 86.6       | T2_T3, r 24.48, z -3.6, Tangente 73° | -160.5     | T4_T5      | 64.0    | T4   |
| `pos_031_W4_QS`  | LOAD_16NM | -0.30 %  | 107.1      | 86.8           | T4 RIGHT, r 25.70, z +6.7 | 67.2       | T2_T3, r 24.48, z -3.6, Tangente 87° | -96.0      | T4_T5      | 120.3   | T4   |
| `pos_031_W4_DY1` | LOAD_16NM | -0.28 %  | 97.4       | 94.0           | T4 RIGHT, r 25.70, z +7.5 | 70.9       | T2_T3, r 24.48, z -3.6, Tangente 87° | -106.2     | T4_T5      | 108.9   | T4   |
| `pos_031_W4_DY2` | LOAD_16NM | -0.19 %  | 64.3       | 104.0          | T4 RIGHT, r 25.70, z +7.5 | 72.5       | T2_T3, r 24.48, z -3.6, Tangente 87° | -113.5     | T4_T5      | 71.7    | T4   |
| `pos_036_W1_QS`  | LOAD_16NM | +0.90 %  | 92.6       | 172.2          | T4 RIGHT, r 25.80, z -5.9 | 76.5       | T2_T3, r 24.48, z -2.0, Tangente 73° | -122.7     | T4_T5      | 107.4   | T3   |
| `pos_036_W1_DY1` | LOAD_16NM | +0.97 %  | 83.8       | 176.1          | T4 RIGHT, r 25.80, z -6.7 | 76.4       | T2_T3, r 24.48, z -2.0, Tangente 73° | -122.9     | T4_T5      | 97.0    | T3   |
| `pos_036_W1_DY2` | LOAD_16NM | +1.19 %  | 60.6       | 188.5          | T4 RIGHT, r 25.80, z -6.7 | 76.5       | T2_T3, r 24.48, z -2.0, Tangente 73° | -124.2     | T4_T5      | 69.6    | T3   |
| `pos_036_W2_QS`  | LOAD_16NM | +1.01 %  | 115.0      | 97.1           | T4 RIGHT, r 25.80, z -5.9 | 58.2       | T2_T3, r 24.48, z -4.4, Tangente 87° | -74.5      | T4_T5      | 133.5   | T3   |
| `pos_036_W2_DY1` | LOAD_16NM | +1.08 %  | 104.5      | 104.9          | T4 RIGHT, r 25.80, z -5.9 | 59.3       | T2_T3, r 24.48, z -4.4, Tangente 87° | -77.4      | T4_T5      | 121.1   | T3   |
| `pos_036_W2_DY2` | LOAD_16NM | +1.34 %  | 69.8       | 124.4          | T4 RIGHT, r 25.80, z -5.9 | 60.9       | T2_T3, r 24.48, z -4.4, Tangente 87° | -83.7      | T4_T5      | 80.1    | T3   |
| `pos_036_W3_QS`  | LOAD_16NM | +0.93 %  | 92.1       | 183.9          | T4 RIGHT, r 25.80, z +7.5 | 93.6       | T2_T3, r 24.48, z -3.6, Tangente 73° | -150.0     | T4_T5      | 104.5   | T3   |
| `pos_036_W3_DY1` | LOAD_16NM | +1.01 %  | 84.4       | 190.6          | T4 RIGHT, r 25.80, z +7.5 | 96.6       | T2_T3, r 24.48, z -3.6, Tangente 73° | -155.8     | T4_T5      | 95.1    | T3   |
| `pos_036_W3_DY2` | LOAD_16NM | +1.24 %  | 60.6       | 203.1          | T4 RIGHT, r 25.80, z +7.5 | 94.2       | T2_T3, r 24.48, z -3.6, Tangente 73° | -153.1     | T4_T5      | 67.8    | T3   |
| `pos_036_W4_QS`  | LOAD_16NM | +1.13 %  | 111.3      | 98.0           | T4 RIGHT, r 25.80, z +7.5 | 70.3       | T2_T3, r 24.48, z -3.6, Tangente 87° | -93.5      | T4_T5      | 126.5   | T3   |
| `pos_036_W4_DY1` | LOAD_16NM | +1.19 %  | 101.2      | 108.8          | T4 RIGHT, r 25.80, z +7.5 | 74.5       | T2_T3, r 24.48, z -3.6, Tangente 87° | -102.7     | T4_T5      | 114.5   | T3   |
| `pos_036_W4_DY2` | LOAD_16NM | +1.39 %  | 68.0       | 130.5          | T4 RIGHT, r 25.80, z +7.5 | 76.9       | T2_T3, r 24.48, z -3.6, Tangente 87° | -109.5     | T4_T5      | 76.3    | T3   |
| `pos_049_W1_QS`  | LOAD_16NM | -0.81 %  | 102.3      | 90.6           | T4 RIGHT, r 26.00, z +0.0 | 72.5       | T2_T3, r 24.49, z +0.0, Tangente 64° | -93.4      | T3_T4      | 123.0   | T3   |
| `pos_049_W1_DY1` | LOAD_16NM | -0.94 %  | 95.2       | 82.8           | T4 RIGHT, r 26.00, z +0.0 | 75.5       | T2_T3, r 24.49, z +0.0, Tangente 64° | -99.0      | T3_T4      | 114.5   | T3   |
| `pos_049_W1_DY2` | LOAD_16NM | -1.08 %  | 77.1       | 100.0          | T3 RIGHT, r 26.11, z +0.0 | 89.8       | T2_T3, r 24.48, z +0.0, Tangente 73° | -123.9     | T3_T4      | 93.1    | T3   |
| `pos_049_W2_QS`  | LOAD_16NM | -0.66 %  | 116.0      | 90.2           | T4 RIGHT, r 26.00, z +0.0 | 47.0       | T2_T3, r 24.48, z +0.0, Tangente 73° | -60.8      | T3_T4      | 138.2   | T3   |
| `pos_049_W2_DY1` | LOAD_16NM | -0.86 %  | 108.0      | 90.1           | T4 RIGHT, r 26.00, z +0.0 | 49.4       | T2_T3, r 24.48, z +0.0, Tangente 73° | -62.9      | T3_T4      | 128.8   | T3   |
| `pos_049_W2_DY2` | LOAD_16NM | -1.03 %  | 82.5       | 73.8           | T3 RIGHT, r 26.11, z +0.0 | 58.6       | T2_T3, r 24.48, z +0.0, Tangente 73° | -77.2      | T3_T4      | 98.6    | T3   |
| `pos_049_W3_QS`  | LOAD_16NM | -0.91 %  | 100.5      | 91.6           | T4 RIGHT, r 26.00, z -7.5 | 81.0       | T2_T3, r 24.48, z -2.8, Tangente 73° | -116.9     | T3_T4      | 116.4   | T3   |
| `pos_049_W3_DY1` | LOAD_16NM | -0.97 %  | 94.2       | 87.5           | T4 RIGHT, r 26.00, z -7.5 | 87.2       | T2_T3, r 24.48, z -3.6, Tangente 73° | -127.9     | T3_T4      | 108.2   | T3   |
| `pos_049_W3_DY2` | LOAD_16NM | -1.11 %  | 76.0       | 86.2           | T3 RIGHT, r 26.11, z +0.0 | 103.7      | T2_T3, r 24.48, z -3.6, Tangente 73° | -154.2     | T3_T4      | 88.0    | T3   |
| `pos_049_W4_QS`  | LOAD_16NM | -0.81 %  | 112.4      | 90.3           | T4 RIGHT, r 26.00, z +7.5 | 55.1       | T2_T3, r 24.48, z -3.6, Tangente 73° | -78.7      | T3_T4      | 129.7   | T3   |
| `pos_049_W4_DY1` | LOAD_16NM | -0.99 %  | 105.6      | 93.9           | T4 RIGHT, r 26.00, z +7.5 | 60.1       | T2_T3, r 24.48, z -3.6, Tangente 73° | -86.6      | T3_T4      | 121.3   | T3   |
| `pos_049_W4_DY2` | LOAD_16NM | -1.06 %  | 80.6       | 69.0           | T4 RIGHT, r 26.00, z -7.5 | 71.8       | T2_T3, r 24.48, z -3.6, Tangente 73° | -103.7     | T3_T4      | 92.8    | T3   |
| `pos_063_W1_QS`  | LOAD_16NM | -0.46 %  | 93.4       | 146.9          | T3 RIGHT, r 25.70, z +0.0 | 77.3       | T1_T2, r 24.48, z +0.0, Tangente 73° | -122.4     | T3_T4      | 111.5   | T3   |
| `pos_063_W1_DY1` | LOAD_16NM | -0.46 %  | 84.2       | 147.4          | T3 RIGHT, r 25.70, z +0.0 | 77.1       | T1_T2, r 24.48, z -0.7, Tangente 73° | -122.4     | T3_T4      | 100.6   | T3   |
| `pos_063_W1_DY2` | LOAD_16NM | -0.39 %  | 60.1       | 146.7          | T3 RIGHT, r 25.70, z +0.0 | 76.8       | T1_T2, r 24.48, z -2.0, Tangente 73° | -123.2     | T3_T4      | 71.8    | T3   |
| `pos_063_W2_QS`  | LOAD_16NM | -0.27 %  | 115.8      | 89.5           | T3 RIGHT, r 25.70, z +0.0 | 57.3       | T1_T2, r 24.48, z -3.6, Tangente 87° | -76.9      | T3_T4      | 136.0   | T3   |
| `pos_063_W2_DY1` | LOAD_16NM | -0.27 %  | 104.7      | 95.1           | T3 RIGHT, r 25.70, z +0.0 | 58.1       | T1_T2, r 24.48, z -3.6, Tangente 87° | -80.0      | T3_T4      | 123.4   | T3   |
| `pos_063_W2_DY2` | LOAD_16NM | -0.27 %  | 68.6       | 106.5          | T3 RIGHT, r 25.70, z +0.0 | 59.9       | T1_T2, r 24.48, z -3.6, Tangente 87° | -85.4      | T3_T4      | 80.8    | T3   |
| `pos_063_W3_QS`  | LOAD_16NM | -0.40 %  | 92.1       | 130.9          | T3 RIGHT, r 25.70, z +0.0 | 88.8       | T1_T2, r 24.48, z +3.6, Tangente 87° | -151.5     | T3_T4      | 105.3   | T3   |
| `pos_063_W3_DY1` | LOAD_16NM | -0.40 %  | 83.9       | 128.5          | T3 RIGHT, r 25.70, z +0.0 | 91.3       | T1_T2, r 24.48, z +3.6, Tangente 87° | -157.0     | T3_T4      | 95.0    | T3   |
| `pos_063_W3_DY2` | LOAD_16NM | -0.35 %  | 59.8       | 132.4          | T3 RIGHT, r 25.70, z +0.0 | 89.3       | T1_T2, r 24.48, z +3.6, Tangente 87° | -153.2     | T3_T4      | 67.6    | T3   |
| `pos_063_W4_QS`  | LOAD_16NM | -0.25 %  | 111.7      | 82.9           | T3 RIGHT, r 25.70, z -2.0 | 67.7       | T1_T2, r 24.48, z +3.6, Tangente 87° | -94.1      | T3_T4      | 126.0   | T3   |
| `pos_063_W4_DY1` | LOAD_16NM | -0.28 %  | 101.3      | 90.5           | T3 RIGHT, r 25.70, z +6.7 | 71.7       | T1_T2, r 24.48, z +3.6, Tangente 87° | -104.0     | T3_T4      | 114.1   | T3   |
| `pos_063_W4_DY2` | LOAD_16NM | -0.22 %  | 66.9       | 103.6          | T3 RIGHT, r 25.70, z +7.5 | 73.2       | T1_T2, r 24.48, z +3.6, Tangente 87° | -111.1     | T3_T4      | 75.5    | T3   |
| `pos_068_W1_QS`  | LOAD_16NM | +0.66 %  | 96.4       | 176.3          | T3 RIGHT, r 25.80, z -3.6 | 84.1       | T1_T2, r 24.48, z +0.0, Tangente 73° | -115.6     | T3_T4      | 111.0   | T2   |
| `pos_068_W1_DY1` | LOAD_16NM | +0.75 %  | 87.3       | 178.2          | T3 RIGHT, r 25.80, z -4.4 | 84.0       | T1_T2, r 24.48, z +0.0, Tangente 73° | -115.8     | T3_T4      | 100.2   | T2   |
| `pos_068_W1_DY2` | LOAD_16NM | +0.96 %  | 63.1       | 189.0          | T3 RIGHT, r 25.80, z -5.9 | 84.1       | T1_T2, r 24.48, z +0.0, Tangente 73° | -116.6     | T3_T4      | 72.0    | T2   |
| `pos_068_W2_QS`  | LOAD_16NM | +0.82 %  | 118.1      | 97.7           | T3 RIGHT, r 25.80, z -5.9 | 59.9       | T1_T2, r 24.48, z -3.6, Tangente 87° | -74.1      | T3_T4      | 136.2   | T2   |
| `pos_068_W2_DY1` | LOAD_16NM | +0.87 %  | 107.3      | 105.3          | T3 RIGHT, r 25.80, z -5.9 | 60.9       | T1_T2, r 24.48, z -3.6, Tangente 87° | -76.6      | T3_T4      | 123.5   | T2   |
| `pos_068_W2_DY2` | LOAD_16NM | +1.17 %  | 72.1       | 126.3          | T3 RIGHT, r 25.80, z +0.0 | 63.3       | T1_T2, r 24.48, z -3.6, Tangente 87° | -81.7      | T3_T4      | 82.3    | T2   |
| `pos_068_W3_QS`  | LOAD_16NM | +0.72 %  | 95.6       | 190.5          | T3 RIGHT, r 25.80, z -7.5 | 96.6       | T1_T2, r 24.48, z +3.6, Tangente 73° | -142.5     | T3_T4      | 108.1   | T2   |
| `pos_068_W3_DY1` | LOAD_16NM | +0.80 %  | 87.5       | 200.3          | T3 RIGHT, r 25.80, z -7.5 | 99.3       | T1_T2, r 24.48, z +3.6, Tangente 87° | -147.8     | T3_T4      | 98.3    | T2   |
| `pos_068_W3_DY2` | LOAD_16NM | +1.04 %  | 62.9       | 214.1          | T3 RIGHT, r 25.80, z -7.5 | 97.4       | T1_T2, r 24.48, z +3.6, Tangente 73° | -144.6     | T3_T4      | 70.2    | T2   |
| `pos_068_W4_QS`  | LOAD_16NM | +0.93 %  | 115.3      | 102.7          | T3 RIGHT, r 25.80, z -7.5 | 70.9       | T1_T2, r 24.48, z +3.6, Tangente 87° | -91.0      | T3_T4      | 130.7   | T2   |
| `pos_068_W4_DY1` | LOAD_16NM | +0.98 %  | 104.9      | 115.2          | T3 RIGHT, r 25.80, z -7.5 | 75.4       | T1_T2, r 24.48, z +3.6, Tangente 87° | -99.7      | T3_T4      | 118.3   | T2   |
| `pos_068_W4_DY2` | LOAD_16NM | +1.26 %  | 70.7       | 138.8          | T3 RIGHT, r 25.80, z -7.5 | 77.7       | T1_T2, r 24.48, z +3.6, Tangente 87° | -105.6     | T3_T4      | 79.1    | T2   |

## 2026-10-15 11:07 `pilot_20layers_bore33_pocket_fillet_ellipse_g25_ab2_round0p1f12_qsdy1dy2_AtoE_gerechnet`

**Zweck:** Fußrundungsvariante Ellipse nach Frühe (gamma 25°, a/b 2,0; Optimum der ebenen Studie), Taschenkörper, W1 bis W4 × QS/DY1/DY2 an A bis E; Kette vom 2026-10-14. **Ergebnis:** 60 von 60 Jobs (7,8 h); an C bei 16 Nm σ1 −24 % (W1), −13 % (W2), −15 % (W3), −12 % (W4); an A, B, D, E −3 bis −20 % (W1), unter W2 bis W4 aber bis +6 %, +15 % und +7 %; Drehung +4 bis +9 %; ebenes Modell −25 % an B, 3D an B −6 %, an C −24 % (vergleich_fussrundung_AtoE). (gerechnet: Vollversion; Befunde FE-05, FE-25)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei            | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|------------------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031_W1_QS`  | A        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 235    | 0       | 2026-10-15 03:03 |
| `pos_031_W1_DY1` | A        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 220    | 0       | 2026-10-15 02:55 |
| `pos_031_W1_DY2` | A        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 201    | 0       | 2026-10-15 02:59 |
| `pos_031_W2_QS`  | A        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 269    | 0       | 2026-10-15 03:18 |
| `pos_031_W2_DY1` | A        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 263    | 0       | 2026-10-15 03:08 |
| `pos_031_W2_DY2` | A        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 263    | 0       | 2026-10-15 03:13 |
| `pos_031_W3_QS`  | A        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 514    | 0       | 2026-10-15 03:45 |
| `pos_031_W3_DY1` | A        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 534    | 0       | 2026-10-15 03:27 |
| `pos_031_W3_DY2` | A        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 492    | 0       | 2026-10-15 03:36 |
| `pos_031_W4_QS`  | A        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 679    | 0       | 2026-10-15 04:19 |
| `pos_031_W4_DY1` | A        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 660    | 0       | 2026-10-15 03:56 |
| `pos_031_W4_DY2` | A        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 647    | 0       | 2026-10-15 04:08 |
| `pos_036_W1_QS`  | B        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 265    | 0       | 2026-10-15 04:34 |
| `pos_036_W1_DY1` | B        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 259    | 0       | 2026-10-15 04:24 |
| `pos_036_W1_DY2` | B        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 255    | 0       | 2026-10-15 04:29 |
| `pos_036_W2_QS`  | B        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 329    | 3       | 2026-10-15 04:51 |
| `pos_036_W2_DY1` | B        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 337    | 2       | 2026-10-15 04:40 |
| `pos_036_W2_DY2` | B        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 289    | 0       | 2026-10-15 04:45 |
| `pos_036_W3_QS`  | B        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 594    | 0       | 2026-10-15 05:21 |
| `pos_036_W3_DY1` | B        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 578    | 0       | 2026-10-15 05:01 |
| `pos_036_W3_DY2` | B        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 554    | 0       | 2026-10-15 05:11 |
| `pos_036_W4_QS`  | B        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 10           | 994    | 5       | 2026-10-15 06:05 |
| `pos_036_W4_DY1` | B        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 826    | 0       | 2026-10-15 05:36 |
| `pos_036_W4_DY2` | B        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 691    | 0       | 2026-10-15 05:48 |
| `pos_049_W1_QS`  | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 249    | 0       | 2026-10-15 06:18 |
| `pos_049_W1_DY1` | C        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 244    | 0       | 2026-10-15 06:09 |
| `pos_049_W1_DY2` | C        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 255    | 0       | 2026-10-15 06:14 |
| `pos_049_W2_QS`  | C        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 8, 6, 6            | 349    | 2       | 2026-10-15 06:37 |
| `pos_049_W2_DY1` | C        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 8, 6, 11           | 427    | 11      | 2026-10-15 06:26 |
| `pos_049_W2_DY2` | C        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 277    | 0       | 2026-10-15 06:31 |
| `pos_049_W3_QS`  | C        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 540    | 0       | 2026-10-15 07:06 |
| `pos_049_W3_DY1` | C        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 541    | 0       | 2026-10-15 06:47 |
| `pos_049_W3_DY2` | C        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 532    | 0       | 2026-10-15 06:56 |
| `pos_049_W4_QS`  | C        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 8, 6, 11           | 988    | 11      | 2026-10-15 07:49 |
| `pos_049_W4_DY1` | C        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 8, 6, 6            | 848    | 0       | 2026-10-15 07:20 |
| `pos_049_W4_DY2` | C        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 666    | 0       | 2026-10-15 07:32 |
| `pos_063_W1_QS`  | D        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 239    | 0       | 2026-10-15 08:01 |
| `pos_063_W1_DY1` | D        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 235    | 0       | 2026-10-15 07:53 |
| `pos_063_W1_DY2` | D        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 204    | 0       | 2026-10-15 07:57 |
| `pos_063_W2_QS`  | D        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 12           | 371    | 5       | 2026-10-15 08:19 |
| `pos_063_W2_DY1` | D        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 11           | 341    | 5       | 2026-10-15 08:08 |
| `pos_063_W2_DY2` | D        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 263    | 0       | 2026-10-15 08:12 |
| `pos_063_W3_QS`  | D        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 536    | 0       | 2026-10-15 08:47 |
| `pos_063_W3_DY1` | D        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 535    | 0       | 2026-10-15 08:28 |
| `pos_063_W3_DY2` | D        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 494    | 0       | 2026-10-15 08:37 |
| `pos_063_W4_QS`  | D        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 11           | 844    | 6       | 2026-10-15 09:24 |
| `pos_063_W4_DY1` | D        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 646    | 0       | 2026-10-15 08:58 |
| `pos_063_W4_DY2` | D        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 665    | 0       | 2026-10-15 09:09 |
| `pos_068_W1_QS`  | E        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 271    | 0       | 2026-10-15 09:39 |
| `pos_068_W1_DY1` | E        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 275    | 0       | 2026-10-15 09:29 |
| `pos_068_W1_DY2` | E        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 261    | 0       | 2026-10-15 09:34 |
| `pos_068_W2_QS`  | E        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 317    | 2       | 2026-10-15 09:56 |
| `pos_068_W2_DY1` | E        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 325    | 0       | 2026-10-15 09:45 |
| `pos_068_W2_DY2` | E        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 293    | 0       | 2026-10-15 09:50 |
| `pos_068_W3_QS`  | E        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 603    | 0       | 2026-10-15 10:26 |
| `pos_068_W3_DY1` | E        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 600    | 0       | 2026-10-15 10:06 |
| `pos_068_W3_DY2` | E        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 556    | 0       | 2026-10-15 10:16 |
| `pos_068_W4_QS`  | E        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 9            | 812    | 5       | 2026-10-15 11:07 |
| `pos_068_W4_DY1` | E        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 861    | 4       | 2026-10-15 10:41 |
| `pos_068_W4_DY2` | E        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 676    | 0       | 2026-10-15 10:53 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei            | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031_W1_QS`  | LOAD_16NM | -0.47 %  | 87.8       | 144.8          | T4 RIGHT, r 25.70, z +0.0 | 58.3       | T2_T3, r 24.52, z -2.8, Tangente 79° | -107.0     | T4_T5      | 103.6   | T4   |
| `pos_031_W1_DY1` | LOAD_16NM | -0.45 %  | 79.2       | 145.5          | T4 RIGHT, r 25.70, z +0.0 | 58.2       | T2_T3, r 24.52, z -3.6, Tangente 79° | -107.2     | T4_T5      | 93.6    | T4   |
| `pos_031_W1_DY2` | LOAD_16NM | -0.36 %  | 56.6       | 144.9          | T4 RIGHT, r 25.70, z +0.0 | 58.2       | T2_T3, r 24.52, z -3.6, Tangente 79° | -107.9     | T4_T5      | 66.7    | T4   |
| `pos_031_W2_QS`  | LOAD_16NM | -0.34 %  | 110.4      | 88.1           | T4 RIGHT, r 25.70, z +0.0 | 48.3       | T2_T3, r 24.52, z -4.4, Tangente 79° | -68.1      | T4_T5      | 128.8   | T4   |
| `pos_031_W2_DY1` | LOAD_16NM | -0.31 %  | 99.9       | 93.9           | T4 RIGHT, r 25.70, z +0.0 | 49.1       | T2_T3, r 24.52, z -4.4, Tangente 79° | -70.1      | T4_T5      | 117.0   | T4   |
| `pos_031_W2_DY2` | LOAD_16NM | -0.23 %  | 65.5       | 105.4          | T4 RIGHT, r 25.70, z +0.0 | 50.2       | T2_T3, r 24.52, z -4.4, Tangente 79° | -74.8      | T4_T5      | 76.2    | T4   |
| `pos_031_W3_QS`  | LOAD_16NM | -0.42 %  | 86.9       | 130.0          | T4 RIGHT, r 25.70, z +7.5 | 74.8       | T2_T3, r 24.52, z -3.6, Tangente 79° | -130.2     | T4_T5      | 97.9    | T4   |
| `pos_031_W3_DY1` | LOAD_16NM | -0.40 %  | 79.4       | 132.5          | T4 RIGHT, r 25.70, z +7.5 | 77.6       | T2_T3, r 24.52, z -3.6, Tangente 79° | -134.9     | T4_T5      | 88.2    | T4   |
| `pos_031_W3_DY2` | LOAD_16NM | -0.33 %  | 56.6       | 131.3          | T4 RIGHT, r 25.70, z +7.5 | 75.2       | T2_T3, r 24.52, z -3.6, Tangente 79° | -132.0     | T4_T5      | 62.7    | T4   |
| `pos_031_W4_QS`  | LOAD_16NM | -0.29 %  | 105.7      | 86.8           | T4 RIGHT, r 25.70, z +6.7 | 60.3       | T2_T3, r 24.52, z -3.6, Tangente 79° | -86.4      | T4_T5      | 118.0   | T4   |
| `pos_031_W4_DY1` | LOAD_16NM | -0.28 %  | 96.1       | 94.0           | T4 RIGHT, r 25.70, z +7.5 | 63.8       | T2_T3, r 24.52, z -3.6, Tangente 79° | -93.7      | T4_T5      | 106.8   | T4   |
| `pos_031_W4_DY2` | LOAD_16NM | -0.19 %  | 63.5       | 103.9          | T4 RIGHT, r 25.70, z +7.5 | 64.5       | T2_T3, r 24.52, z -3.6, Tangente 79° | -97.9      | T4_T5      | 70.4    | T4   |
| `pos_036_W1_QS`  | LOAD_16NM | +0.89 %  | 91.4       | 172.4          | T4 RIGHT, r 25.80, z -5.9 | 63.4       | T2_T3, r 24.52, z -2.8, Tangente 79° | -102.3     | T4_T5      | 105.9   | T3   |
| `pos_036_W1_DY1` | LOAD_16NM | +0.97 %  | 82.8       | 176.2          | T4 RIGHT, r 25.80, z -6.7 | 63.3       | T2_T3, r 24.52, z -2.8, Tangente 79° | -102.5     | T4_T5      | 95.7    | T3   |
| `pos_036_W1_DY2` | LOAD_16NM | +1.18 %  | 59.8       | 188.7          | T4 RIGHT, r 25.80, z -6.7 | 63.4       | T2_T3, r 24.52, z -2.8, Tangente 79° | -103.5     | T4_T5      | 68.6    | T3   |
| `pos_036_W2_QS`  | LOAD_16NM | +1.01 %  | 113.6      | 96.9           | T4 RIGHT, r 25.80, z -5.9 | 50.7       | T2_T3, r 24.52, z -3.6, Tangente 79° | -66.0      | T4_T5      | 131.7   | T3   |
| `pos_036_W2_DY1` | LOAD_16NM | +1.09 %  | 103.3      | 104.6          | T4 RIGHT, r 25.80, z -5.9 | 51.6       | T2_T3, r 24.52, z -3.6, Tangente 79° | -67.8      | T4_T5      | 119.5   | T3   |
| `pos_036_W2_DY2` | LOAD_16NM | +1.34 %  | 69.0       | 124.4          | T4 RIGHT, r 25.80, z -5.9 | 53.2       | T2_T3, r 24.52, z -2.8, Tangente 79° | -72.3      | T4_T5      | 79.1    | T3   |
| `pos_036_W3_QS`  | LOAD_16NM | +0.93 %  | 90.9       | 183.9          | T4 RIGHT, r 25.80, z +7.5 | 81.2       | T2_T3, r 24.52, z -3.6, Tangente 79° | -123.4     | T4_T5      | 103.1   | T3   |
| `pos_036_W3_DY1` | LOAD_16NM | +1.01 %  | 83.3       | 190.6          | T4 RIGHT, r 25.80, z +7.5 | 84.3       | T2_T3, r 24.52, z -3.6, Tangente 79° | -128.0     | T4_T5      | 93.8    | T3   |
| `pos_036_W3_DY2` | LOAD_16NM | +1.23 %  | 59.8       | 203.3          | T4 RIGHT, r 25.80, z +7.5 | 81.9       | T2_T3, r 24.52, z -3.6, Tangente 79° | -125.9     | T4_T5      | 66.9    | T3   |
| `pos_036_W4_QS`  | LOAD_16NM | +1.14 %  | 109.9      | 98.0           | T4 RIGHT, r 25.80, z +7.5 | 63.4       | T2_T3, r 24.52, z -3.6, Tangente 79° | -83.8      | T4_T5      | 124.7   | T3   |
| `pos_036_W4_DY1` | LOAD_16NM | +1.19 %  | 100.0      | 108.8          | T4 RIGHT, r 25.80, z +7.5 | 67.3       | T2_T3, r 24.52, z -3.6, Tangente 79° | -90.6      | T4_T5      | 113.0   | T3   |
| `pos_036_W4_DY2` | LOAD_16NM | +1.40 %  | 67.2       | 130.6          | T4 RIGHT, r 25.80, z +7.5 | 68.8       | T2_T3, r 24.52, z -3.6, Tangente 79° | -94.4      | T4_T5      | 75.3    | T3   |
| `pos_049_W1_QS`  | LOAD_16NM | -0.83 %  | 101.5      | 89.2           | T4 RIGHT, r 26.00, z +0.0 | 65.2       | T2_T3, r 24.60, z +0.0, Tangente 49° | -79.0      | T3_T4      | 121.9   | T3   |
| `pos_049_W1_DY1` | LOAD_16NM | -0.94 %  | 94.5       | 81.3           | T4 RIGHT, r 26.00, z +0.0 | 67.5       | T2_T3, r 24.60, z +0.0, Tangente 49° | -83.6      | T3_T4      | 113.6   | T3   |
| `pos_049_W1_DY2` | LOAD_16NM | -1.09 %  | 76.5       | 100.4          | T3 RIGHT, r 26.11, z +0.0 | 78.2       | T2_T3, r 24.57, z +0.0, Tangente 55° | -103.7     | T3_T4      | 92.4    | T3   |
| `pos_049_W2_QS`  | LOAD_16NM | -0.70 %  | 115.1      | 89.8           | T4 RIGHT, r 26.00, z +0.0 | 43.3       | T2_T3, r 24.90, z +0.0, Tangente 23° | -54.6      | T3_T4      | 137.0   | T3   |
| `pos_049_W2_DY1` | LOAD_16NM | -0.86 %  | 107.1      | 89.3           | T4 RIGHT, r 26.00, z +0.0 | 45.4       | T2_T3, r 24.53, z +0.0, Tangente 67° | -56.3      | T3_T4      | 127.7   | T3   |
| `pos_049_W2_DY2` | LOAD_16NM | -1.04 %  | 81.9       | 73.9           | T3 RIGHT, r 26.11, z +0.0 | 53.2       | T2_T3, r 24.53, z +0.0, Tangente 72° | -68.8      | T3_T4      | 97.8    | T3   |
| `pos_049_W3_QS`  | LOAD_16NM | -0.92 %  | 99.7       | 89.8           | T4 RIGHT, r 26.00, z -7.5 | 72.0       | T2_T3, r 24.53, z -3.6, Tangente 72° | -105.6     | T3_T4      | 115.3   | T3   |
| `pos_049_W3_DY1` | LOAD_16NM | -0.97 %  | 93.5       | 85.6           | T4 RIGHT, r 26.00, z -7.5 | 78.0       | T2_T3, r 24.53, z -3.6, Tangente 72° | -115.2     | T3_T4      | 107.2   | T3   |
| `pos_049_W3_DY2` | LOAD_16NM | -1.11 %  | 75.5       | 86.4           | T3 RIGHT, r 26.11, z +0.0 | 91.4       | T2_T3, r 24.53, z -3.6, Tangente 72° | -138.3     | T3_T4      | 87.2    | T3   |
| `pos_049_W4_QS`  | LOAD_16NM | -0.83 %  | 111.5      | 90.0           | T4 RIGHT, r 26.00, z +7.5 | 52.4       | T2_T3, r 24.53, z -3.6, Tangente 67° | -72.8      | T3_T4      | 128.5   | T3   |
| `pos_049_W4_DY1` | LOAD_16NM | -0.99 %  | 104.7      | 93.2           | T4 RIGHT, r 26.00, z +7.5 | 57.3       | T2_T3, r 24.53, z -3.6, Tangente 67° | -79.8      | T3_T4      | 120.2   | T3   |
| `pos_049_W4_DY2` | LOAD_16NM | -1.05 %  | 80.1       | 67.2           | T4 RIGHT, r 26.00, z -7.5 | 67.4       | T2_T3, r 24.53, z -3.6, Tangente 72° | -95.1      | T3_T4      | 92.1    | T3   |
| `pos_063_W1_QS`  | LOAD_16NM | -0.45 %  | 92.1       | 146.3          | T3 RIGHT, r 25.70, z +0.0 | 64.2       | T1_T2, r 24.52, z -1.3, Tangente 79° | -102.1     | T3_T4      | 109.8   | T3   |
| `pos_063_W1_DY1` | LOAD_16NM | -0.45 %  | 83.1       | 146.8          | T3 RIGHT, r 25.70, z +0.0 | 64.0       | T1_T2, r 24.52, z -2.0, Tangente 79° | -102.1     | T3_T4      | 99.1    | T3   |
| `pos_063_W1_DY2` | LOAD_16NM | -0.38 %  | 59.3       | 146.1          | T3 RIGHT, r 25.70, z +0.0 | 63.8       | T1_T2, r 24.52, z -2.0, Tangente 79° | -102.7     | T3_T4      | 70.6    | T3   |
| `pos_063_W2_QS`  | LOAD_16NM | -0.27 %  | 114.3      | 89.2           | T3 RIGHT, r 25.70, z +0.0 | 49.6       | T1_T2, r 24.52, z -3.6, Tangente 87° | -68.3      | T3_T4      | 133.9   | T3   |
| `pos_063_W2_DY1` | LOAD_16NM | -0.27 %  | 103.3      | 94.9           | T3 RIGHT, r 25.70, z +0.0 | 50.2       | T1_T2, r 24.52, z -3.6, Tangente 87° | -70.4      | T3_T4      | 121.6   | T3   |
| `pos_063_W2_DY2` | LOAD_16NM | -0.27 %  | 67.7       | 106.2          | T3 RIGHT, r 25.70, z +0.0 | 51.8       | T1_T2, r 24.52, z -2.8, Tangente 79° | -74.6      | T3_T4      | 79.6    | T3   |
| `pos_063_W3_QS`  | LOAD_16NM | -0.39 %  | 90.9       | 130.3          | T3 RIGHT, r 25.70, z +0.0 | 76.7       | T1_T2, r 24.52, z +3.6, Tangente 79° | -131.9     | T3_T4      | 103.7   | T3   |
| `pos_063_W3_DY1` | LOAD_16NM | -0.40 %  | 82.8       | 127.8          | T3 RIGHT, r 25.70, z +0.0 | 79.2       | T1_T2, r 24.52, z +3.6, Tangente 79° | -136.1     | T3_T4      | 93.4    | T3   |
| `pos_063_W3_DY2` | LOAD_16NM | -0.35 %  | 59.0       | 131.7          | T3 RIGHT, r 25.70, z +0.0 | 77.4       | T1_T2, r 24.52, z +4.4, Tangente 79° | -133.1     | T3_T4      | 66.5    | T3   |
| `pos_063_W4_QS`  | LOAD_16NM | -0.24 %  | 110.2      | 82.7           | T3 RIGHT, r 25.70, z -2.0 | 60.3       | T1_T2, r 24.52, z +3.6, Tangente 87° | -86.2      | T3_T4      | 123.9   | T3   |
| `pos_063_W4_DY1` | LOAD_16NM | -0.27 %  | 100.0      | 90.5           | T3 RIGHT, r 25.70, z +7.5 | 63.9       | T1_T2, r 24.52, z +3.6, Tangente 87° | -92.8      | T3_T4      | 112.3   | T3   |
| `pos_063_W4_DY2` | LOAD_16NM | -0.22 %  | 66.1       | 103.5          | T3 RIGHT, r 25.70, z +7.5 | 64.7       | T1_T2, r 24.52, z +3.6, Tangente 87° | -98.4      | T3_T4      | 74.3    | T3   |
| `pos_068_W1_QS`  | LOAD_16NM | +0.66 %  | 95.2       | 176.4          | T3 RIGHT, r 25.80, z -3.6 | 69.8       | T1_T2, r 24.52, z +0.0, Tangente 79° | -96.4      | T3_T4      | 109.5   | T2   |
| `pos_068_W1_DY1` | LOAD_16NM | +0.75 %  | 86.2       | 178.4          | T3 RIGHT, r 25.80, z -4.4 | 69.7       | T1_T2, r 24.52, z +0.0, Tangente 79° | -96.6      | T3_T4      | 98.9    | T2   |
| `pos_068_W1_DY2` | LOAD_16NM | +0.95 %  | 62.3       | 189.1          | T3 RIGHT, r 25.80, z -5.9 | 69.8       | T1_T2, r 24.52, z -1.3, Tangente 79° | -97.2      | T3_T4      | 71.0    | T2   |
| `pos_068_W2_QS`  | LOAD_16NM | +0.82 %  | 116.6      | 97.5           | T3 RIGHT, r 25.80, z -5.9 | 51.9       | T1_T2, r 24.52, z -3.6, Tangente 87° | -65.6      | T3_T4      | 134.4   | T2   |
| `pos_068_W2_DY1` | LOAD_16NM | +0.88 %  | 105.9      | 105.1          | T3 RIGHT, r 25.80, z -5.9 | 52.8       | T1_T2, r 24.52, z -3.6, Tangente 87° | -67.3      | T3_T4      | 121.9   | T2   |
| `pos_068_W2_DY2` | LOAD_16NM | +1.17 %  | 71.3       | 126.3          | T3 RIGHT, r 25.80, z +0.0 | 54.9       | T1_T2, r 24.52, z -2.8, Tangente 79° | -71.4      | T3_T4      | 81.3    | T2   |
| `pos_068_W3_QS`  | LOAD_16NM | +0.72 %  | 94.4       | 190.0          | T3 RIGHT, r 25.80, z -7.5 | 83.5       | T1_T2, r 24.52, z +3.6, Tangente 79° | -123.8     | T3_T4      | 106.6   | T2   |
| `pos_068_W3_DY1` | LOAD_16NM | +0.80 %  | 86.5       | 199.6          | T3 RIGHT, r 25.80, z -7.5 | 86.3       | T1_T2, r 24.52, z +3.6, Tangente 79° | -127.9     | T3_T4      | 96.9    | T2   |
| `pos_068_W3_DY2` | LOAD_16NM | +1.03 %  | 62.2       | 213.5          | T3 RIGHT, r 25.80, z -7.5 | 84.2       | T1_T2, r 24.52, z +3.6, Tangente 79° | -126.1     | T3_T4      | 69.2    | T2   |
| `pos_068_W4_QS`  | LOAD_16NM | +0.93 %  | 113.9      | 102.4          | T3 RIGHT, r 25.80, z -7.5 | 63.4       | T1_T2, r 24.52, z +3.6, Tangente 87° | -83.0      | T3_T4      | 128.9   | T2   |
| `pos_068_W4_DY1` | LOAD_16NM | +0.98 %  | 103.6      | 114.8          | T3 RIGHT, r 25.80, z -7.5 | 67.4       | T1_T2, r 24.52, z +3.6, Tangente 87° | -89.0      | T3_T4      | 116.7   | T2   |
| `pos_068_W4_DY2` | LOAD_16NM | +1.26 %  | 69.9       | 138.5          | T3 RIGHT, r 25.80, z -7.5 | 68.8       | T1_T2, r 24.52, z +3.6, Tangente 87° | -94.3      | T3_T4      | 78.0    | T2   |

## 2026-10-15 19:42 `pilot_20layers_bore33_pocket_fillet_bezier_f1_round0p1f12_qsdy1dy2_AtoE_gerechnet`

**Zweck:** Fußrundungsvariante Bézier nach DE 10 2013 004 861 B3 (f 1,0; Literaturwert), Taschenkörper, W1 bis W4 × QS/DY1/DY2 an A bis E; Kette vom 2026-10-14. **Ergebnis:** 60 von 60 Jobs (8,1 h); σ1 an allen fünf Punkten −25 bis −34 % (W1), −16 bis −27 % (W2), −25 bis −33 % (W3), −1 bis −19 % (W4), |σ3| bis −44 %; Zahn steifer: Drehung −9 bis −22 %, Kopfweg bis −26 %; Kontaktdruck an der Ritzelkante (B, E) +21 bis +29 %; ebenes Modell −32 % an B, 3D an B −31 %, an C −25 % (vergleich_fussrundung_AtoE). (gerechnet: Vollversion; Befunde FE-05, FE-25)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei            | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|------------------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031_W1_QS`  | A        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 298    | 0       | 2026-10-15 11:23 |
| `pos_031_W1_DY1` | A        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 293    | 0       | 2026-10-15 11:12 |
| `pos_031_W1_DY2` | A        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 277    | 0       | 2026-10-15 11:17 |
| `pos_031_W2_QS`  | A        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 319    | 0       | 2026-10-15 11:40 |
| `pos_031_W2_DY1` | A        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 324    | 0       | 2026-10-15 11:29 |
| `pos_031_W2_DY2` | A        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 278    | 0       | 2026-10-15 11:34 |
| `pos_031_W3_QS`  | A        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 594    | 0       | 2026-10-15 12:10 |
| `pos_031_W3_DY1` | A        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 582    | 0       | 2026-10-15 11:50 |
| `pos_031_W3_DY2` | A        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 572    | 0       | 2026-10-15 12:00 |
| `pos_031_W4_QS`  | A        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 823    | 2       | 2026-10-15 12:49 |
| `pos_031_W4_DY1` | A        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 757    | 0       | 2026-10-15 12:23 |
| `pos_031_W4_DY2` | A        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 692    | 0       | 2026-10-15 12:35 |
| `pos_036_W1_QS`  | B        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 262    | 0       | 2026-10-15 13:03 |
| `pos_036_W1_DY1` | B        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 250    | 0       | 2026-10-15 12:54 |
| `pos_036_W1_DY2` | B        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 244    | 0       | 2026-10-15 12:59 |
| `pos_036_W2_QS`  | B        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 350    | 3       | 2026-10-15 13:20 |
| `pos_036_W2_DY1` | B        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 295    | 0       | 2026-10-15 13:09 |
| `pos_036_W2_DY2` | B        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 272    | 0       | 2026-10-15 13:14 |
| `pos_036_W3_QS`  | B        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 604    | 0       | 2026-10-15 13:51 |
| `pos_036_W3_DY1` | B        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 584    | 0       | 2026-10-15 13:30 |
| `pos_036_W3_DY2` | B        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 568    | 0       | 2026-10-15 13:40 |
| `pos_036_W4_QS`  | B        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 815    | 2       | 2026-10-15 14:30 |
| `pos_036_W4_DY1` | B        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 777    | 0       | 2026-10-15 14:04 |
| `pos_036_W4_DY2` | B        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 669    | 0       | 2026-10-15 14:16 |
| `pos_049_W1_QS`  | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 238    | 0       | 2026-10-15 14:43 |
| `pos_049_W1_DY1` | C        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 243    | 0       | 2026-10-15 14:35 |
| `pos_049_W1_DY2` | C        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 241    | 0       | 2026-10-15 14:39 |
| `pos_049_W2_QS`  | C        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 317    | 0       | 2026-10-15 15:00 |
| `pos_049_W2_DY1` | C        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 337    | 4       | 2026-10-15 14:49 |
| `pos_049_W2_DY2` | C        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 285    | 0       | 2026-10-15 14:55 |
| `pos_049_W3_QS`  | C        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 598    | 0       | 2026-10-15 15:30 |
| `pos_049_W3_DY1` | C        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 550    | 0       | 2026-10-15 15:10 |
| `pos_049_W3_DY2` | C        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 560    | 0       | 2026-10-15 15:20 |
| `pos_049_W4_QS`  | C        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 793    | 0       | 2026-10-15 16:09 |
| `pos_049_W4_DY1` | C        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 755    | 0       | 2026-10-15 15:43 |
| `pos_049_W4_DY2` | C        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 702    | 0       | 2026-10-15 15:56 |
| `pos_063_W1_QS`  | D        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 265    | 0       | 2026-10-15 16:24 |
| `pos_063_W1_DY1` | D        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 259    | 0       | 2026-10-15 16:14 |
| `pos_063_W1_DY2` | D        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 263    | 0       | 2026-10-15 16:19 |
| `pos_063_W2_QS`  | D        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 315    | 0       | 2026-10-15 16:40 |
| `pos_063_W2_DY1` | D        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 307    | 0       | 2026-10-15 16:29 |
| `pos_063_W2_DY2` | D        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 291    | 0       | 2026-10-15 16:35 |
| `pos_063_W3_QS`  | D        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 594    | 0       | 2026-10-15 17:11 |
| `pos_063_W3_DY1` | D        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 590    | 0       | 2026-10-15 16:51 |
| `pos_063_W3_DY2` | D        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 566    | 0       | 2026-10-15 17:01 |
| `pos_063_W4_QS`  | D        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 835    | 3       | 2026-10-15 17:51 |
| `pos_063_W4_DY1` | D        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 753    | 0       | 2026-10-15 17:24 |
| `pos_063_W4_DY2` | D        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 721    | 0       | 2026-10-15 17:36 |
| `pos_068_W1_QS`  | E        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 12           | 458    | 0       | 2026-10-15 18:09 |
| `pos_068_W1_DY1` | E        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 269    | 0       | 2026-10-15 17:56 |
| `pos_068_W1_DY2` | E        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 269    | 0       | 2026-10-15 18:01 |
| `pos_068_W2_QS`  | E        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 11           | 383    | 3       | 2026-10-15 18:27 |
| `pos_068_W2_DY1` | E        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 327    | 0       | 2026-10-15 18:15 |
| `pos_068_W2_DY2` | E        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 295    | 0       | 2026-10-15 18:20 |
| `pos_068_W3_QS`  | E        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 714    | 0       | 2026-10-15 19:00 |
| `pos_068_W3_DY1` | E        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 614    | 0       | 2026-10-15 18:38 |
| `pos_068_W3_DY2` | E        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 580    | 0       | 2026-10-15 18:48 |
| `pos_068_W4_QS`  | E        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 11           | 946    | 5       | 2026-10-15 19:42 |
| `pos_068_W4_DY1` | E        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 773    | 0       | 2026-10-15 19:13 |
| `pos_068_W4_DY2` | E        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 701    | 0       | 2026-10-15 19:26 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei            | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031_W1_QS`  | LOAD_16NM | -0.01 %  | 64.7       | 138.4          | T4 RIGHT, r 25.68, z +0.0 | 50.4       | T3_T4, r 25.29, z +0.0, Tangente 43° | -59.0      | T4_T5      | 69.6    | T3   |
| `pos_031_W1_DY1` | LOAD_16NM | -0.05 %  | 58.2       | 138.7          | T4 RIGHT, r 25.68, z +0.0 | 50.3       | T3_T4, r 25.29, z +0.0, Tangente 43° | -58.9      | T4_T5      | 62.6    | T3   |
| `pos_031_W1_DY2` | LOAD_16NM | -0.16 %  | 41.4       | 134.9          | T4 RIGHT, r 25.68, z +0.0 | 51.0       | T3_T4, r 25.29, z +0.0, Tangente 43° | -58.8      | T4_T5      | 44.7    | T3   |
| `pos_031_W2_QS`  | LOAD_16NM | +0.12 %  | 79.4       | 85.5           | T4 RIGHT, r 25.75, z -5.9 | 35.7       | T3_T4, r 25.58, z +0.0, Tangente 17° | -44.4      | T4_T5      | 85.9    | T3   |
| `pos_031_W2_DY1` | LOAD_16NM | +0.07 %  | 71.8       | 92.4           | T4 RIGHT, r 25.68, z +0.0 | 39.5       | T3_T4, r 25.58, z -0.7, Tangente 17° | -45.2      | T4_T5      | 77.5    | T3   |
| `pos_031_W2_DY2` | LOAD_16NM | -0.06 %  | 47.3       | 105.0          | T4 RIGHT, r 25.68, z +0.0 | 39.4       | T3_T4, r 25.58, z +0.0, Tangente 17° | -47.1      | T4_T5      | 50.9    | T3   |
| `pos_031_W3_QS`  | LOAD_16NM | +0.03 %  | 66.7       | 126.0          | T4 RIGHT, r 25.68, z +0.0 | 53.5       | T3_T4, r 25.33, z -0.7, Tangente 39° | -65.9      | T4_T5      | 71.5    | T3   |
| `pos_031_W3_DY1` | LOAD_16NM | +0.00 %  | 61.2       | 124.2          | T4 RIGHT, r 25.68, z +0.0 | 55.4       | T3_T4, r 25.39, z +7.5, Tangente 32° | -69.2      | T4_T5      | 65.6    | T3   |
| `pos_031_W3_DY2` | LOAD_16NM | -0.15 %  | 43.1       | 125.8          | T4 RIGHT, r 25.68, z +0.0 | 55.8       | T3_T4, r 25.39, z +7.5, Tangente 32° | -66.5      | T4_T5      | 46.3    | T3   |
| `pos_031_W4_QS`  | LOAD_16NM | +0.15 %  | 78.9       | 83.5           | T4 RIGHT, r 25.75, z +6.7 | 55.9       | T3_T4, r 25.58, z -7.5, Tangente 17° | -53.9      | T4_T5      | 84.5    | T3   |
| `pos_031_W4_DY1` | LOAD_16NM | +0.12 %  | 72.5       | 85.5           | T4 RIGHT, r 25.75, z +6.7 | 59.2       | T3_T4, r 25.58, z -7.5, Tangente 17° | -58.1      | T4_T5      | 77.7    | T3   |
| `pos_031_W4_DY2` | LOAD_16NM | -0.02 %  | 47.9       | 97.1           | T4 RIGHT, r 25.68, z +0.0 | 58.3       | T3_T4, r 25.58, z -7.5, Tangente 17° | -59.9      | T4_T5      | 51.5    | T3   |
| `pos_036_W1_QS`  | LOAD_16NM | +0.47 %  | 66.5       | 212.0          | T4 RIGHT, r 25.75, z +0.0 | 46.4       | T3_T4, r 25.33, z +0.0, Tangente 39° | -55.1      | T4_T5      | 73.7    | T3   |
| `pos_036_W1_DY1` | LOAD_16NM | +0.42 %  | 60.1       | 217.8          | T4 RIGHT, r 25.75, z +0.0 | 46.2       | T3_T4, r 25.33, z +0.0, Tangente 39° | -55.0      | T4_T5      | 66.5    | T3   |
| `pos_036_W1_DY2` | LOAD_16NM | +0.40 %  | 43.4       | 238.3          | T4 RIGHT, r 25.75, z +0.0 | 46.0       | T3_T4, r 25.33, z +0.0, Tangente 39° | -54.7      | T4_T5      | 47.7    | T3   |
| `pos_036_W2_QS`  | LOAD_16NM | +0.53 %  | 81.6       | 97.6           | T4 RIGHT, r 25.75, z +0.0 | 35.0       | T2_T3, r 25.35, z +0.0, Tangente 36° | -41.9      | T4_T5      | 90.8    | T3   |
| `pos_036_W2_DY1` | LOAD_16NM | +0.49 %  | 74.3       | 108.7          | T4 RIGHT, r 25.75, z +0.0 | 36.0       | T2_T3, r 25.33, z +0.0, Tangente 39° | -42.7      | T4_T5      | 82.5    | T3   |
| `pos_036_W2_DY2` | LOAD_16NM | +0.45 %  | 50.0       | 129.6          | T4 RIGHT, r 25.75, z +0.0 | 38.2       | T2_T3, r 25.31, z +0.0, Tangente 41° | -44.5      | T4_T5      | 55.2    | T3   |
| `pos_036_W3_QS`  | LOAD_16NM | +0.48 %  | 68.5       | 189.2          | T4 RIGHT, r 25.75, z -7.5 | 50.0       | T3_T4, r 25.39, z -0.7, Tangente 32° | -62.0      | T4_T5      | 73.8    | T3   |
| `pos_036_W3_DY1` | LOAD_16NM | +0.44 %  | 63.2       | 203.7          | T4 RIGHT, r 25.75, z -7.5 | 55.0       | T3_T4, r 25.42, z +7.5, Tangente 30° | -64.8      | T4_T5      | 67.4    | T3   |
| `pos_036_W3_DY2` | LOAD_16NM | +0.38 %  | 45.2       | 229.5          | T4 RIGHT, r 25.75, z -7.5 | 54.5       | T3_T4, r 25.42, z +7.5, Tangente 30° | -62.4      | T4_T5      | 48.3    | T3   |
| `pos_036_W4_QS`  | LOAD_16NM | +0.55 %  | 81.5       | 94.6           | T4 RIGHT, r 25.82, z -6.7 | 55.0       | T3_T4, r 25.61, z -7.5, Tangente 16° | -51.1      | T4_T5      | 87.9    | T3   |
| `pos_036_W4_DY1` | LOAD_16NM | +0.53 %  | 75.1       | 106.7          | T4 RIGHT, r 25.75, z -7.5 | 57.5       | T3_T4, r 25.61, z -7.5, Tangente 16° | -55.1      | T4_T5      | 80.7    | T3   |
| `pos_036_W4_DY2` | LOAD_16NM | +0.46 %  | 51.0       | 136.9          | T4 RIGHT, r 25.75, z -7.5 | 60.9       | T3_T4, r 25.61, z -7.5, Tangente 16° | -56.7      | T4_T5      | 54.5    | T3   |
| `pos_049_W1_QS`  | LOAD_16NM | -0.04 %  | 85.7       | 99.6           | T4 RIGHT, r 25.97, z +0.0 | 64.5       | T2_T3, r 25.29, z +0.0, Tangente 43° | -75.5      | T3_T4      | 97.2    | T3   |
| `pos_049_W1_DY1` | LOAD_16NM | -0.23 %  | 79.5       | 88.5           | T3 RIGHT, r 26.11, z +0.0 | 66.9       | T2_T3, r 25.29, z +0.0, Tangente 43° | -78.7      | T3_T4      | 90.0    | T3   |
| `pos_049_W1_DY2` | LOAD_16NM | -0.87 %  | 63.7       | 111.8          | T3 RIGHT, r 26.11, z +0.0 | 77.9       | T2_T3, r 25.29, z +0.0, Tangente 43° | -93.1      | T3_T4      | 71.8    | T3   |
| `pos_049_W2_QS`  | LOAD_16NM | +0.04 %  | 94.1       | 88.1           | T4 RIGHT, r 25.97, z +0.0 | 42.1       | T2_T3, r 25.42, z +0.0, Tangente 30° | -47.6      | T3_T4      | 105.4   | T3   |
| `pos_049_W2_DY1` | LOAD_16NM | -0.01 %  | 89.1       | 92.8           | T4 RIGHT, r 25.97, z +0.0 | 43.8       | T2_T3, r 25.44, z +0.0, Tangente 28° | -49.7      | T3_T4      | 99.9    | T3   |
| `pos_049_W2_DY2` | LOAD_16NM | -0.53 %  | 69.2       | 76.4           | T3 RIGHT, r 26.11, z +0.0 | 51.8       | T2_T3, r 25.44, z +0.0, Tangente 28° | -59.7      | T3_T4      | 77.0    | T3   |
| `pos_049_W3_QS`  | LOAD_16NM | +0.07 %  | 86.4       | 103.4          | T4 RIGHT, r 25.97, z +0.0 | 63.5       | T2_T3, r 25.33, z -0.7, Tangente 39° | -79.4      | T3_T4      | 92.8    | T3   |
| `pos_049_W3_DY1` | LOAD_16NM | -0.00 %  | 81.3       | 94.1           | T4 RIGHT, r 25.97, z +0.0 | 65.9       | T2_T3, r 25.39, z +6.7, Tangente 32° | -86.9      | T3_T4      | 86.2    | T3   |
| `pos_049_W3_DY2` | LOAD_16NM | -0.73 %  | 64.3       | 100.2          | T3 RIGHT, r 26.25, z +7.5 | 75.4       | T2_T3, r 25.33, z -0.7, Tangente 39° | -97.9      | T3_T4      | 68.1    | T3   |
| `pos_049_W4_QS`  | LOAD_16NM | -0.01 %  | 93.5       | 78.5           | T4 RIGHT, r 25.97, z +0.0 | 49.5       | T2_T3, r 25.39, z +6.7, Tangente 32° | -64.8      | T3_T4      | 99.1    | T3   |
| `pos_049_W4_DY1` | LOAD_16NM | -0.06 %  | 88.6       | 80.9           | T4 RIGHT, r 25.97, z +0.0 | 53.6       | T2_T3, r 25.39, z +6.7, Tangente 32° | -71.6      | T3_T4      | 93.3    | T3   |
| `pos_049_W4_DY2` | LOAD_16NM | -0.51 %  | 68.8       | 75.3           | T3 RIGHT, r 25.97, z -7.5 | 61.3       | T2_T3, r 25.39, z +6.7, Tangente 32° | -83.5      | T3_T4      | 72.2    | T3   |
| `pos_063_W1_QS`  | LOAD_16NM | +0.06 %  | 68.9       | 136.5          | T3 RIGHT, r 25.68, z +0.0 | 50.7       | T2_T3, r 25.29, z +0.0, Tangente 43° | -57.1      | T3_T4      | 74.0    | T2   |
| `pos_063_W1_DY1` | LOAD_16NM | -0.01 %  | 62.0       | 138.5          | T3 RIGHT, r 25.68, z +0.0 | 51.8       | T2_T3, r 25.29, z +0.0, Tangente 43° | -56.8      | T3_T4      | 66.4    | T2   |
| `pos_063_W1_DY2` | LOAD_16NM | -0.11 %  | 44.0       | 137.5          | T3 RIGHT, r 25.68, z +0.0 | 52.5       | T2_T3, r 25.29, z +0.0, Tangente 43° | -56.6      | T3_T4      | 46.8    | T3   |
| `pos_063_W2_QS`  | LOAD_16NM | +0.12 %  | 82.6       | 88.0           | T3 RIGHT, r 25.75, z -5.9 | 35.0       | T2_T3, r 25.33, z +0.0, Tangente 39° | -45.0      | T3_T4      | 89.2    | T2   |
| `pos_063_W2_DY1` | LOAD_16NM | +0.11 %  | 74.8       | 90.9           | T3 RIGHT, r 25.75, z -5.9 | 36.0       | T2_T3, r 25.33, z +0.0, Tangente 39° | -45.9      | T3_T4      | 80.6    | T2   |
| `pos_063_W2_DY2` | LOAD_16NM | -0.03 %  | 49.4       | 103.9          | T3 RIGHT, r 25.68, z +0.0 | 38.5       | T2_T3, r 25.33, z +0.0, Tangente 39° | -47.7      | T3_T4      | 52.6    | T2   |
| `pos_063_W3_QS`  | LOAD_16NM | +0.09 %  | 70.7       | 128.9          | T3 RIGHT, r 25.75, z +7.5 | 52.4       | T2_T3, r 25.37, z +7.5, Tangente 34° | -63.7      | T3_T4      | 75.1    | T3   |
| `pos_063_W3_DY1` | LOAD_16NM | +0.06 %  | 64.8       | 124.0          | T3 RIGHT, r 25.75, z +7.5 | 56.3       | T2_T3, r 25.37, z +7.5, Tangente 34° | -65.9      | T3_T4      | 68.7    | T3   |
| `pos_063_W3_DY2` | LOAD_16NM | -0.09 %  | 45.5       | 127.0          | T3 RIGHT, r 25.68, z +0.0 | 56.5       | T2_T3, r 25.37, z +7.5, Tangente 34° | -63.8      | T3_T4      | 48.3    | T2   |
| `pos_063_W4_QS`  | LOAD_16NM | +0.16 %  | 83.1       | 88.0           | T3 RIGHT, r 25.75, z +7.5 | 51.9       | T2_T3, r 25.58, z -7.5, Tangente 17° | -55.8      | T3_T4      | 88.4    | T3   |
| `pos_063_W4_DY1` | LOAD_16NM | +0.14 %  | 76.3       | 91.1           | T3 RIGHT, r 25.75, z +7.5 | 56.5       | T2_T3, r 25.58, z -7.5, Tangente 17° | -59.7      | T3_T4      | 81.1    | T3   |
| `pos_063_W4_DY2` | LOAD_16NM | +0.01 %  | 50.5       | 95.7           | T3 RIGHT, r 25.68, z +0.0 | 54.8       | T2_T3, r 25.58, z -7.5, Tangente 17° | -58.8      | T3_T4      | 53.7    | T2   |
| `pos_068_W1_QS`  | LOAD_16NM | +0.69 %  | 70.5       | 214.5          | T3 RIGHT, r 25.75, z +0.0 | 47.5       | T2_T3, r 25.31, z +0.0, Tangente 41° | -53.1      | T3_T4      | 78.2    | T2   |
| `pos_068_W1_DY1` | LOAD_16NM | +0.53 %  | 63.4       | 219.9          | T3 RIGHT, r 25.75, z +0.0 | 47.4       | T2_T3, r 25.31, z +0.0, Tangente 41° | -52.9      | T3_T4      | 70.1    | T2   |
| `pos_068_W1_DY2` | LOAD_16NM | +0.40 %  | 45.5       | 239.4          | T3 RIGHT, r 25.75, z +0.0 | 47.1       | T2_T3, r 25.31, z +0.0, Tangente 41° | -52.5      | T3_T4      | 50.0    | T2   |
| `pos_068_W2_QS`  | LOAD_16NM | +0.61 %  | 84.5       | 99.8           | T3 RIGHT, r 25.82, z -5.9 | 36.9       | T1_T2, r 25.37, z +0.0, Tangente 34° | -42.4      | T3_T4      | 93.8    | T2   |
| `pos_068_W2_DY1` | LOAD_16NM | +0.56 %  | 76.7       | 109.1          | T3 RIGHT, r 25.75, z +0.0 | 37.8       | T1_T2, r 25.37, z +0.0, Tangente 34° | -43.3      | T3_T4      | 85.1    | T2   |
| `pos_068_W2_DY2` | LOAD_16NM | +0.44 %  | 51.7       | 129.8          | T3 RIGHT, r 25.75, z +0.0 | 39.9       | T1_T2, r 25.33, z +0.0, Tangente 39° | -44.7      | T3_T4      | 56.9    | T2   |
| `pos_068_W3_QS`  | LOAD_16NM | +0.67 %  | 72.3       | 186.6          | T3 RIGHT, r 25.75, z +0.0 | 49.9       | T2_T3, r 25.39, z -0.7, Tangente 32° | -59.7      | T3_T4      | 78.0    | T2   |
| `pos_068_W3_DY1` | LOAD_16NM | +0.58 %  | 66.4       | 186.2          | T3 RIGHT, r 25.75, z +0.0 | 52.6       | T2_T3, r 25.37, z +7.5, Tangente 34° | -62.1      | T3_T4      | 71.1    | T2   |
| `pos_068_W3_DY2` | LOAD_16NM | +0.38 %  | 47.2       | 227.8          | T3 RIGHT, r 25.75, z +7.5 | 56.3       | T2_T3, r 25.44, z +7.5, Tangente 28° | -59.6      | T3_T4      | 50.4    | T2   |
| `pos_068_W4_QS`  | LOAD_16NM | +0.62 %  | 85.3       | 98.8           | T3 RIGHT, r 25.82, z -7.5 | 48.9       | T2_T3, r 25.61, z -7.5, Tangente 16° | -52.2      | T3_T4      | 92.1    | T2   |
| `pos_068_W4_DY1` | LOAD_16NM | +0.57 %  | 78.4       | 105.3          | T3 RIGHT, r 25.82, z -7.5 | 52.0       | T2_T3, r 25.58, z +7.5, Tangente 17° | -55.9      | T3_T4      | 84.3    | T2   |
| `pos_068_W4_DY2` | LOAD_16NM | +0.46 %  | 53.1       | 138.1          | T3 RIGHT, r 25.75, z +7.5 | 55.7       | T2_T3, r 25.61, z +7.5, Tangente 16° | -55.6      | T3_T4      | 56.8    | T2   |

## 2026-10-16 04:19 `pilot_20layers_bore33_pocket_fillet_bezier_f2p5_round0p1f12_qsdy1dy2_AtoE_gerechnet`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei            | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|------------------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031_W1_QS`  | A        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 279    | 0       | 2026-10-15 19:57 |
| `pos_031_W1_DY1` | A        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 267    | 0       | 2026-10-15 19:47 |
| `pos_031_W1_DY2` | A        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 257    | 0       | 2026-10-15 19:51 |
| `pos_031_W2_QS`  | A        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 331    | 0       | 2026-10-15 20:13 |
| `pos_031_W2_DY1` | A        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 313    | 0       | 2026-10-15 20:02 |
| `pos_031_W2_DY2` | A        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 287    | 0       | 2026-10-15 20:07 |
| `pos_031_W3_QS`  | A        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 600    | 0       | 2026-10-15 20:45 |
| `pos_031_W3_DY1` | A        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 608    | 0       | 2026-10-15 20:24 |
| `pos_031_W3_DY2` | A        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 586    | 0       | 2026-10-15 20:34 |
| `pos_031_W4_QS`  | A        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 853    | 3       | 2026-10-15 21:24 |
| `pos_031_W4_DY1` | A        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 735    | 0       | 2026-10-15 20:58 |
| `pos_031_W4_DY2` | A        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 703    | 0       | 2026-10-15 21:10 |
| `pos_036_W1_QS`  | B        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 268    | 0       | 2026-10-15 21:39 |
| `pos_036_W1_DY1` | B        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 251    | 0       | 2026-10-15 21:29 |
| `pos_036_W1_DY2` | B        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 258    | 0       | 2026-10-15 21:34 |
| `pos_036_W2_QS`  | B        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 361    | 3       | 2026-10-15 21:56 |
| `pos_036_W2_DY1` | B        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 315    | 0       | 2026-10-15 21:44 |
| `pos_036_W2_DY2` | B        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 287    | 0       | 2026-10-15 21:50 |
| `pos_036_W3_QS`  | B        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 581    | 0       | 2026-10-15 22:26 |
| `pos_036_W3_DY1` | B        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 562    | 0       | 2026-10-15 22:06 |
| `pos_036_W3_DY2` | B        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 556    | 0       | 2026-10-15 22:16 |
| `pos_036_W4_QS`  | B        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 765    | 0       | 2026-10-15 23:05 |
| `pos_036_W4_DY1` | B        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 761    | 0       | 2026-10-15 22:39 |
| `pos_036_W4_DY2` | B        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 731    | 0       | 2026-10-15 22:52 |
| `pos_049_W1_QS`  | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 266    | 0       | 2026-10-15 23:19 |
| `pos_049_W1_DY1` | C        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 253    | 0       | 2026-10-15 23:10 |
| `pos_049_W1_DY2` | C        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 257    | 0       | 2026-10-15 23:14 |
| `pos_049_W2_QS`  | C        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 305    | 0       | 2026-10-15 23:35 |
| `pos_049_W2_DY1` | C        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 307    | 0       | 2026-10-15 23:25 |
| `pos_049_W2_DY2` | C        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 281    | 0       | 2026-10-15 23:30 |
| `pos_049_W3_QS`  | C        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 592    | 0       | 2026-10-16 00:06 |
| `pos_049_W3_DY1` | C        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 570    | 0       | 2026-10-15 23:45 |
| `pos_049_W3_DY2` | C        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 568    | 0       | 2026-10-15 23:55 |
| `pos_049_W4_QS`  | C        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 711    | 0       | 2026-10-16 00:43 |
| `pos_049_W4_DY1` | C        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 743    | 0       | 2026-10-16 00:19 |
| `pos_049_W4_DY2` | C        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 693    | 0       | 2026-10-16 00:31 |
| `pos_063_W1_QS`  | D        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 277    | 0       | 2026-10-16 00:58 |
| `pos_063_W1_DY1` | D        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 268    | 0       | 2026-10-16 00:48 |
| `pos_063_W1_DY2` | D        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 261    | 0       | 2026-10-16 00:53 |
| `pos_063_W2_QS`  | D        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 319    | 0       | 2026-10-16 01:14 |
| `pos_063_W2_DY1` | D        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 315    | 0       | 2026-10-16 01:03 |
| `pos_063_W2_DY2` | D        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 293    | 0       | 2026-10-16 01:09 |
| `pos_063_W3_QS`  | D        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 608    | 0       | 2026-10-16 01:46 |
| `pos_063_W3_DY1` | D        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 580    | 0       | 2026-10-16 01:25 |
| `pos_063_W3_DY2` | D        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 594    | 0       | 2026-10-16 01:35 |
| `pos_063_W4_QS`  | D        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 837    | 0       | 2026-10-16 02:26 |
| `pos_063_W4_DY1` | D        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 783    | 0       | 2026-10-16 01:59 |
| `pos_063_W4_DY2` | D        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 743    | 0       | 2026-10-16 02:12 |
| `pos_068_W1_QS`  | E        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 311    | 2       | 2026-10-16 02:42 |
| `pos_068_W1_DY1` | E        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 275    | 0       | 2026-10-16 02:31 |
| `pos_068_W1_DY2` | E        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 267    | 0       | 2026-10-16 02:36 |
| `pos_068_W2_QS`  | E        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 13           | 460    | 6       | 2026-10-16 03:01 |
| `pos_068_W2_DY1` | E        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 338    | 0       | 2026-10-16 02:48 |
| `pos_068_W2_DY2` | E        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 283    | 0       | 2026-10-16 02:53 |
| `pos_068_W3_QS`  | E        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 13           | 922    | 0       | 2026-10-16 03:38 |
| `pos_068_W3_DY1` | E        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 608    | 0       | 2026-10-16 03:12 |
| `pos_068_W3_DY2` | E        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 570    | 0       | 2026-10-16 03:22 |
| `pos_068_W4_QS`  | E        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 862    | 2       | 2026-10-16 04:19 |
| `pos_068_W4_DY1` | E        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 779    | 0       | 2026-10-16 03:51 |
| `pos_068_W4_DY2` | E        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 753    | 0       | 2026-10-16 04:04 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei            | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031_W1_QS`  | LOAD_16NM | -0.07 %  | 71.2       | 144.7          | T4 RIGHT, r 25.68, z +0.0 | 48.9       | T3_T4, r 25.03, z +0.0, Tangente 44° | -74.0      | T4_T5      | 77.4    | T3   |
| `pos_031_W1_DY1` | LOAD_16NM | -0.10 %  | 64.1       | 144.9          | T4 RIGHT, r 25.68, z +0.0 | 49.0       | T3_T4, r 25.03, z +0.0, Tangente 44° | -73.9      | T4_T5      | 69.6    | T3   |
| `pos_031_W1_DY2` | LOAD_16NM | -0.21 %  | 45.6       | 140.1          | T4 RIGHT, r 25.68, z +0.0 | 49.5       | T3_T4, r 25.03, z +0.0, Tangente 44° | -73.7      | T4_T5      | 49.6    | T3   |
| `pos_031_W2_QS`  | LOAD_16NM | +0.08 %  | 87.9       | 89.3           | T4 RIGHT, r 25.68, z -0.7 | 36.1       | T2_T3, r 24.90, z +0.0, Tangente 76° | -54.0      | T4_T5      | 96.1    | T3   |
| `pos_031_W2_DY1` | LOAD_16NM | +0.04 %  | 79.6       | 98.2           | T4 RIGHT, r 25.68, z +0.0 | 37.2       | T2_T3, r 24.90, z +0.0, Tangente 76° | -54.9      | T4_T5      | 86.8    | T3   |
| `pos_031_W2_DY2` | LOAD_16NM | -0.09 %  | 52.1       | 111.0          | T4 RIGHT, r 25.68, z +0.0 | 38.3       | T3_T4, r 25.03, z +0.0, Tangente 44° | -57.3      | T4_T5      | 56.6    | T3   |
| `pos_031_W3_QS`  | LOAD_16NM | -0.03 %  | 72.1       | 130.6          | T4 RIGHT, r 25.68, z +0.0 | 49.1       | T3_T4, r 25.11, z -0.7, Tangente 37° | -91.1      | T4_T5      | 77.9    | T3   |
| `pos_031_W3_DY1` | LOAD_16NM | -0.05 %  | 66.0       | 128.6          | T4 RIGHT, r 25.68, z +0.0 | 49.7       | T3_T4, r 25.14, z -0.7, Tangente 35° | -97.6      | T4_T5      | 71.2    | T3   |
| `pos_031_W3_DY2` | LOAD_16NM | -0.19 %  | 46.5       | 129.0          | T4 RIGHT, r 25.68, z +0.0 | 49.7       | T3_T4, r 25.14, z -0.7, Tangente 35° | -92.4      | T4_T5      | 50.3    | T3   |
| `pos_031_W4_QS`  | LOAD_16NM | +0.12 %  | 85.8       | 84.9           | T4 RIGHT, r 25.75, z +5.9 | 50.3       | T3_T4, r 25.57, z -7.5, Tangente 16° | -72.4      | T4_T5      | 92.4    | T3   |
| `pos_031_W4_DY1` | LOAD_16NM | +0.08 %  | 78.5       | 89.0           | T4 RIGHT, r 25.68, z +0.0 | 53.0       | T3_T4, r 25.57, z -7.5, Tangente 16° | -78.4      | T4_T5      | 84.6    | T3   |
| `pos_031_W4_DY2` | LOAD_16NM | -0.06 %  | 51.8       | 102.1          | T4 RIGHT, r 25.68, z +0.0 | 51.3       | T3_T4, r 25.57, z -7.5, Tangente 16° | -79.2      | T4_T5      | 56.1    | T3   |
| `pos_036_W1_QS`  | LOAD_16NM | +0.41 %  | 72.8       | 216.1          | T4 RIGHT, r 25.75, z +0.0 | 45.1       | T2_T3, r 24.95, z +0.0, Tangente 58° | -69.5      | T4_T5      | 81.7    | T3   |
| `pos_036_W1_DY1` | LOAD_16NM | +0.38 %  | 65.7       | 221.3          | T4 RIGHT, r 25.75, z +0.0 | 45.0       | T2_T3, r 24.95, z +0.0, Tangente 58° | -69.3      | T4_T5      | 73.8    | T3   |
| `pos_036_W1_DY2` | LOAD_16NM | +0.37 %  | 47.4       | 242.1          | T4 RIGHT, r 25.75, z +0.0 | 45.3       | T2_T3, r 24.95, z +0.0, Tangente 58° | -69.1      | T4_T5      | 52.9    | T3   |
| `pos_036_W2_QS`  | LOAD_16NM | +0.50 %  | 89.9       | 102.0          | T4 RIGHT, r 25.75, z +0.0 | 38.5       | T2_T3, r 24.90, z +0.0, Tangente 76° | -51.2      | T4_T5      | 101.2   | T3   |
| `pos_036_W2_DY1` | LOAD_16NM | +0.47 %  | 81.6       | 113.2          | T4 RIGHT, r 25.75, z +0.0 | 39.7       | T2_T3, r 24.90, z +0.0, Tangente 76° | -52.2      | T4_T5      | 91.8    | T3   |
| `pos_036_W2_DY2` | LOAD_16NM | +0.43 %  | 54.7       | 134.1          | T4 RIGHT, r 25.75, z +0.0 | 40.9       | T2_T3, r 24.92, z +0.0, Tangente 66° | -54.2      | T4_T5      | 61.2    | T3   |
| `pos_036_W3_QS`  | LOAD_16NM | +0.42 %  | 73.8       | 193.6          | T4 RIGHT, r 25.75, z -7.5 | 51.7       | T2_T3, r 24.90, z +4.4, Tangente 81° | -86.1      | T4_T5      | 80.8    | T3   |
| `pos_036_W3_DY1` | LOAD_16NM | +0.39 %  | 67.8       | 207.7          | T4 RIGHT, r 25.75, z -7.5 | 53.4       | T2_T3, r 24.90, z +5.1, Tangente 81° | -92.1      | T4_T5      | 73.7    | T3   |
| `pos_036_W3_DY2` | LOAD_16NM | +0.36 %  | 48.5       | 232.9          | T4 RIGHT, r 25.75, z -7.5 | 52.7       | T2_T3, r 24.90, z +5.1, Tangente 81° | -87.2      | T4_T5      | 52.6    | T3   |
| `pos_036_W4_QS`  | LOAD_16NM | +0.53 %  | 88.1       | 96.2           | T4 RIGHT, r 25.82, z -6.7 | 52.7       | T3_T4, r 25.61, z -7.5, Tangente 16° | -68.8      | T4_T5      | 96.5    | T3   |
| `pos_036_W4_DY1` | LOAD_16NM | +0.50 %  | 80.9       | 109.7          | T4 RIGHT, r 25.75, z -6.7 | 54.3       | T3_T4, r 25.61, z -7.5, Tangente 16° | -74.3      | T4_T5      | 88.2    | T3   |
| `pos_036_W4_DY2` | LOAD_16NM | +0.45 %  | 54.7       | 139.2          | T4 RIGHT, r 25.75, z -7.5 | 57.3       | T3_T4, r 25.61, z -7.5, Tangente 16° | -74.8      | T4_T5      | 59.3    | T3   |
| `pos_049_W1_QS`  | LOAD_16NM | +0.23 %  | 91.1       | 123.0          | T4 RIGHT, r 25.97, z +0.0 | 62.4       | T2_T3, r 24.99, z +0.0, Tangente 50° | -75.1      | T3_T4      | 105.4   | T3   |
| `pos_049_W1_DY1` | LOAD_16NM | +0.13 %  | 84.7       | 110.8          | T4 RIGHT, r 25.97, z +0.0 | 64.9       | T2_T3, r 24.99, z +0.0, Tangente 50° | -78.4      | T3_T4      | 98.1    | T3   |
| `pos_049_W1_DY2` | LOAD_16NM | -0.70 %  | 67.4       | 108.4          | T3 RIGHT, r 26.11, z +0.0 | 74.8       | T2_T3, r 24.99, z +0.0, Tangente 50° | -91.8      | T3_T4      | 77.8    | T3   |
| `pos_049_W2_QS`  | LOAD_16NM | +0.15 %  | 99.8       | 91.1           | T4 RIGHT, r 25.97, z +0.0 | 39.7       | T2_T3, r 24.95, z +0.0, Tangente 58° | -48.2      | T3_T4      | 114.1   | T3   |
| `pos_049_W2_DY1` | LOAD_16NM | +0.11 %  | 94.2       | 97.1           | T4 RIGHT, r 25.97, z +0.0 | 41.9       | T2_T3, r 24.94, z +0.0, Tangente 62° | -50.7      | T3_T4      | 107.9   | T3   |
| `pos_049_W2_DY2` | LOAD_16NM | -0.34 %  | 72.9       | 83.0           | T4 RIGHT, r 25.97, z +0.0 | 49.5       | T2_T3, r 24.94, z +0.0, Tangente 62° | -61.0      | T3_T4      | 83.2    | T3   |
| `pos_049_W3_QS`  | LOAD_16NM | +0.28 %  | 90.7       | 120.0          | T4 RIGHT, r 25.97, z +0.0 | 60.0       | T2_T3, r 25.01, z -1.3, Tangente 47° | -85.3      | T3_T4      | 100.0   | T3   |
| `pos_049_W3_DY1` | LOAD_16NM | +0.22 %  | 85.2       | 111.5          | T4 RIGHT, r 25.97, z +0.0 | 62.6       | T2_T3, r 24.92, z -3.6, Tangente 66° | -92.0      | T3_T4      | 92.9    | T3   |
| `pos_049_W3_DY2` | LOAD_16NM | -0.58 %  | 67.3       | 94.7           | T3 RIGHT, r 26.26, z +7.5 | 72.9       | T2_T3, r 24.92, z -3.6, Tangente 66° | -104.2     | T3_T4      | 73.3    | T3   |
| `pos_049_W4_QS`  | LOAD_16NM | +0.08 %  | 98.1       | 81.4           | T4 RIGHT, r 25.97, z +0.0 | 44.6       | T2_T3, r 25.25, z +6.7, Tangente 28° | -62.3      | T3_T4      | 107.1   | T3   |
| `pos_049_W4_DY1` | LOAD_16NM | +0.02 %  | 92.7       | 83.7           | T4 RIGHT, r 25.97, z +0.0 | 48.5       | T2_T3, r 24.92, z -3.6, Tangente 66° | -69.4      | T3_T4      | 100.5   | T3   |
| `pos_049_W4_DY2` | LOAD_16NM | -0.38 %  | 71.8       | 77.5           | T4 RIGHT, r 25.97, z +0.0 | 57.1       | T2_T3, r 24.92, z -3.6, Tangente 66° | -81.2      | T3_T4      | 77.7    | T3   |
| `pos_063_W1_QS`  | LOAD_16NM | -0.02 %  | 75.6       | 144.0          | T3 RIGHT, r 25.68, z +0.0 | 50.3       | T2_T3, r 25.03, z +0.0, Tangente 44° | -70.6      | T3_T4      | 83.2    | T3   |
| `pos_063_W1_DY1` | LOAD_16NM | -0.06 %  | 68.0       | 144.3          | T3 RIGHT, r 25.68, z +0.0 | 50.8       | T2_T3, r 25.03, z +0.0, Tangente 44° | -70.6      | T3_T4      | 74.7    | T3   |
| `pos_063_W1_DY2` | LOAD_16NM | -0.16 %  | 48.3       | 142.5          | T3 RIGHT, r 25.68, z +0.0 | 51.4       | T2_T3, r 25.03, z +0.0, Tangente 44° | -70.5      | T3_T4      | 52.6    | T3   |
| `pos_063_W2_QS`  | LOAD_16NM | +0.09 %  | 91.4       | 90.4           | T3 RIGHT, r 25.75, z -5.9 | 38.0       | T1_T2, r 24.90, z +0.0, Tangente 81° | -54.6      | T3_T4      | 99.6    | T2   |
| `pos_063_W2_DY1` | LOAD_16NM | +0.08 %  | 82.7       | 94.0           | T3 RIGHT, r 25.68, z +0.0 | 38.9       | T1_T2, r 24.90, z +0.0, Tangente 81° | -55.6      | T3_T4      | 90.0    | T3   |
| `pos_063_W2_DY2` | LOAD_16NM | -0.06 %  | 54.3       | 110.5          | T3 RIGHT, r 25.68, z +0.0 | 39.8       | T1_T2, r 24.90, z +0.0, Tangente 81° | -57.5      | T3_T4      | 58.7    | T3   |
| `pos_063_W3_QS`  | LOAD_16NM | +0.05 %  | 76.3       | 130.5          | T3 RIGHT, r 25.75, z +7.5 | 50.0       | T1_T2, r 24.90, z +5.1, Tangente 81° | -84.6      | T3_T4      | 81.3    | T2   |
| `pos_063_W3_DY1` | LOAD_16NM | -0.01 %  | 69.6       | 127.9          | T3 RIGHT, r 25.68, z +0.0 | 51.3       | T1_T2, r 24.90, z +5.1, Tangente 81° | -87.7      | T3_T4      | 74.3    | T2   |
| `pos_063_W3_DY2` | LOAD_16NM | -0.13 %  | 49.0       | 130.8          | T3 RIGHT, r 25.68, z +0.0 | 50.4       | T1_T2, r 24.90, z +5.1, Tangente 81° | -85.2      | T3_T4      | 52.4    | T2   |
| `pos_063_W4_QS`  | LOAD_16NM | +0.13 %  | 90.1       | 90.3           | T3 RIGHT, r 25.75, z +7.5 | 46.5       | T2_T3, r 25.57, z -7.5, Tangente 16° | -67.5      | T3_T4      | 96.6    | T2   |
| `pos_063_W4_DY1` | LOAD_16NM | +0.11 %  | 82.5       | 92.8           | T3 RIGHT, r 25.75, z +7.5 | 50.8       | T2_T3, r 25.57, z -7.5, Tangente 16° | -73.1      | T3_T4      | 88.1    | T2   |
| `pos_063_W4_DY2` | LOAD_16NM | -0.02 %  | 54.4       | 100.4          | T3 RIGHT, r 25.68, z +0.0 | 48.7       | T2_T3, r 25.57, z -7.5, Tangente 16° | -74.4      | T3_T4      | 58.3    | T2   |
| `pos_068_W1_QS`  | LOAD_16NM | +0.64 %  | 77.0       | 218.8          | T3 RIGHT, r 25.75, z +0.0 | 49.5       | T1_T2, r 24.94, z +0.0, Tangente 62° | -66.7      | T3_T4      | 86.2    | T2   |
| `pos_068_W1_DY1` | LOAD_16NM | +0.48 %  | 69.2       | 223.2          | T3 RIGHT, r 25.75, z +0.0 | 49.2       | T1_T2, r 24.94, z +0.0, Tangente 62° | -66.3      | T3_T4      | 77.3    | T2   |
| `pos_068_W1_DY2` | LOAD_16NM | +0.37 %  | 49.7       | 243.3          | T3 RIGHT, r 25.75, z +0.0 | 49.2       | T1_T2, r 24.94, z +0.0, Tangente 62° | -65.8      | T3_T4      | 55.1    | T2   |
| `pos_068_W2_QS`  | LOAD_16NM | +0.59 %  | 93.0       | 102.0          | T3 RIGHT, r 25.75, z +0.0 | 40.1       | T1_T2, r 24.90, z +0.0, Tangente 81° | -51.7      | T3_T4      | 104.4   | T2   |
| `pos_068_W2_DY1` | LOAD_16NM | +0.54 %  | 84.2       | 113.2          | T3 RIGHT, r 25.75, z +0.0 | 41.0       | T1_T2, r 24.90, z +0.0, Tangente 81° | -52.7      | T3_T4      | 94.5    | T2   |
| `pos_068_W2_DY2` | LOAD_16NM | +0.42 %  | 56.5       | 134.2          | T3 RIGHT, r 25.75, z +0.0 | 42.6       | T1_T2, r 24.90, z +0.0, Tangente 81° | -54.1      | T3_T4      | 63.0    | T2   |
| `pos_068_W3_QS`  | LOAD_16NM | +0.62 %  | 77.7       | 189.3          | T3 RIGHT, r 25.75, z +0.0 | 54.4       | T1_T2, r 24.90, z +5.1, Tangente 81° | -80.0      | T3_T4      | 85.0    | T2   |
| `pos_068_W3_DY1` | LOAD_16NM | +0.52 %  | 71.1       | 188.7          | T3 RIGHT, r 25.75, z +0.0 | 56.1       | T1_T2, r 24.90, z +5.1, Tangente 81° | -83.2      | T3_T4      | 77.2    | T2   |
| `pos_068_W3_DY2` | LOAD_16NM | +0.36 %  | 50.6       | 230.7          | T3 RIGHT, r 25.75, z +7.5 | 55.8       | T1_T2, r 24.90, z +5.1, Tangente 81° | -79.8      | T3_T4      | 54.8    | T2   |
| `pos_068_W4_QS`  | LOAD_16NM | +0.60 %  | 92.1       | 102.3          | T3 RIGHT, r 25.82, z -7.5 | 48.0       | T1_T2, r 24.90, z +5.1, Tangente 81° | -64.3      | T3_T4      | 101.0   | T2   |
| `pos_068_W4_DY1` | LOAD_16NM | +0.55 %  | 84.3       | 109.1          | T3 RIGHT, r 25.82, z -7.5 | 51.0       | T1_T2, r 24.90, z +5.1, Tangente 81° | -69.4      | T3_T4      | 92.0    | T2   |
| `pos_068_W4_DY2` | LOAD_16NM | +0.44 %  | 57.0       | 140.5          | T3 RIGHT, r 25.75, z +7.5 | 52.1       | T1_T2, r 24.90, z +5.1, Tangente 81° | -70.3      | T3_T4      | 61.8    | T2   |

## 2026-10-16 13:42 `pilot_20layers_bore33_pocket_fillet_bionic_phiauto_r0p3_round0p1f12_qsdy1dy2_AtoE_gerechnet`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei            | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|------------------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031_W1_QS`  | A        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 263    | 0       | 2026-10-16 04:34 |
| `pos_031_W1_DY1` | A        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 261    | 0       | 2026-10-16 04:24 |
| `pos_031_W1_DY2` | A        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 259    | 0       | 2026-10-16 04:29 |
| `pos_031_W2_QS`  | A        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 325    | 0       | 2026-10-16 04:50 |
| `pos_031_W2_DY1` | A        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 303    | 0       | 2026-10-16 04:39 |
| `pos_031_W2_DY2` | A        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 285    | 0       | 2026-10-16 04:44 |
| `pos_031_W3_QS`  | A        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 600    | 0       | 2026-10-16 05:20 |
| `pos_031_W3_DY1` | A        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 575    | 0       | 2026-10-16 05:00 |
| `pos_031_W3_DY2` | A        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 562    | 0       | 2026-10-16 05:10 |
| `pos_031_W4_QS`  | A        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 839    | 2       | 2026-10-16 06:00 |
| `pos_031_W4_DY1` | A        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 747    | 0       | 2026-10-16 05:33 |
| `pos_031_W4_DY2` | A        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 693    | 0       | 2026-10-16 05:45 |
| `pos_036_W1_QS`  | B        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 255    | 0       | 2026-10-16 06:14 |
| `pos_036_W1_DY1` | B        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 254    | 0       | 2026-10-16 06:05 |
| `pos_036_W1_DY2` | B        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 249    | 0       | 2026-10-16 06:09 |
| `pos_036_W2_QS`  | B        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 327    | 2       | 2026-10-16 06:30 |
| `pos_036_W2_DY1` | B        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 299    | 0       | 2026-10-16 06:19 |
| `pos_036_W2_DY2` | B        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 279    | 0       | 2026-10-16 06:24 |
| `pos_036_W3_QS`  | B        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 606    | 0       | 2026-10-16 07:01 |
| `pos_036_W3_DY1` | B        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 580    | 0       | 2026-10-16 06:40 |
| `pos_036_W3_DY2` | B        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 570    | 0       | 2026-10-16 06:50 |
| `pos_036_W4_QS`  | B        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 821    | 2       | 2026-10-16 07:40 |
| `pos_036_W4_DY1` | B        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 759    | 0       | 2026-10-16 07:14 |
| `pos_036_W4_DY2` | B        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 683    | 0       | 2026-10-16 07:26 |
| `pos_049_W1_QS`  | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 256    | 0       | 2026-10-16 07:54 |
| `pos_049_W1_DY1` | C        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 246    | 0       | 2026-10-16 07:45 |
| `pos_049_W1_DY2` | C        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 250    | 0       | 2026-10-16 07:49 |
| `pos_049_W2_QS`  | C        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 317    | 0       | 2026-10-16 08:12 |
| `pos_049_W2_DY1` | C        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 359    | 6       | 2026-10-16 08:01 |
| `pos_049_W2_DY2` | C        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 289    | 0       | 2026-10-16 08:06 |
| `pos_049_W3_QS`  | C        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 600    | 0       | 2026-10-16 08:42 |
| `pos_049_W3_DY1` | C        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 578    | 0       | 2026-10-16 08:22 |
| `pos_049_W3_DY2` | C        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 570    | 0       | 2026-10-16 08:32 |
| `pos_049_W4_QS`  | C        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 786    | 0       | 2026-10-16 09:21 |
| `pos_049_W4_DY1` | C        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 745    | 0       | 2026-10-16 08:55 |
| `pos_049_W4_DY2` | C        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 723    | 0       | 2026-10-16 09:08 |
| `pos_063_W1_QS`  | D        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 275    | 0       | 2026-10-16 09:36 |
| `pos_063_W1_DY1` | D        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 269    | 0       | 2026-10-16 09:26 |
| `pos_063_W1_DY2` | D        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 275    | 0       | 2026-10-16 09:31 |
| `pos_063_W2_QS`  | D        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 317    | 0       | 2026-10-16 09:53 |
| `pos_063_W2_DY1` | D        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 317    | 0       | 2026-10-16 09:42 |
| `pos_063_W2_DY2` | D        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 292    | 0       | 2026-10-16 09:47 |
| `pos_063_W3_QS`  | D        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 584    | 0       | 2026-10-16 10:24 |
| `pos_063_W3_DY1` | D        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 592    | 0       | 2026-10-16 10:03 |
| `pos_063_W3_DY2` | D        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 586    | 0       | 2026-10-16 10:14 |
| `pos_063_W4_QS`  | D        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 1127   | 0       | 2026-10-16 11:09 |
| `pos_063_W4_DY1` | D        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 768    | 0       | 2026-10-16 10:37 |
| `pos_063_W4_DY2` | D        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 713    | 0       | 2026-10-16 10:49 |
| `pos_068_W1_QS`  | E        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 12           | 1620   | 0       | 2026-10-16 12:06 |
| `pos_068_W1_DY1` | E        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 1499   | 0       | 2026-10-16 11:34 |
| `pos_068_W1_DY2` | E        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 270    | 0       | 2026-10-16 11:39 |
| `pos_068_W2_QS`  | E        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 357    | 4       | 2026-10-16 12:24 |
| `pos_068_W2_DY1` | E        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 325    | 0       | 2026-10-16 12:12 |
| `pos_068_W2_DY2` | E        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 288    | 0       | 2026-10-16 12:18 |
| `pos_068_W3_QS`  | E        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 9            | 853    | 0       | 2026-10-16 13:00 |
| `pos_068_W3_DY1` | E        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 604    | 0       | 2026-10-16 12:35 |
| `pos_068_W3_DY2` | E        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 592    | 0       | 2026-10-16 12:45 |
| `pos_068_W4_QS`  | E        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 945    | 4       | 2026-10-16 13:42 |
| `pos_068_W4_DY1` | E        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 796    | 0       | 2026-10-16 13:13 |
| `pos_068_W4_DY2` | E        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 705    | 0       | 2026-10-16 13:26 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei            | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031_W1_QS`  | LOAD_16NM | -0.02 %  | 65.5       | 139.0          | T4 RIGHT, r 25.68, z +0.0 | 49.4       | T3_T4, r 25.32, z +0.0, Tangente 39° | -66.5      | T4_T5      | 70.5    | T3   |
| `pos_031_W1_DY1` | LOAD_16NM | -0.06 %  | 59.0       | 139.2          | T4 RIGHT, r 25.68, z +0.0 | 49.3       | T3_T4, r 25.32, z +0.0, Tangente 39° | -66.4      | T4_T5      | 63.5    | T3   |
| `pos_031_W1_DY2` | LOAD_16NM | -0.16 %  | 42.0       | 135.3          | T4 RIGHT, r 25.68, z +0.0 | 50.1       | T3_T4, r 25.32, z +0.0, Tangente 39° | -66.2      | T4_T5      | 45.3    | T3   |
| `pos_031_W2_QS`  | LOAD_16NM | +0.12 %  | 80.5       | 85.7           | T4 RIGHT, r 25.75, z -5.9 | 35.2       | T3_T4, r 25.58, z +0.0, Tangente 17° | -50.2      | T4_T5      | 87.1    | T3   |
| `pos_031_W2_DY1` | LOAD_16NM | +0.07 %  | 72.8       | 93.1           | T4 RIGHT, r 25.68, z +0.0 | 39.0       | T3_T4, r 25.58, z -0.7, Tangente 17° | -51.0      | T4_T5      | 78.6    | T3   |
| `pos_031_W2_DY2` | LOAD_16NM | -0.07 %  | 47.9       | 105.8          | T4 RIGHT, r 25.68, z +0.0 | 39.0       | T3_T4, r 25.58, z +0.0, Tangente 17° | -53.1      | T4_T5      | 51.6    | T3   |
| `pos_031_W3_QS`  | LOAD_16NM | +0.02 %  | 67.4       | 126.4          | T4 RIGHT, r 25.68, z +0.0 | 53.1       | T3_T4, r 25.34, z -0.7, Tangente 37° | -75.3      | T4_T5      | 72.2    | T3   |
| `pos_031_W3_DY1` | LOAD_16NM | -0.00 %  | 61.8       | 124.6          | T4 RIGHT, r 25.68, z +0.0 | 55.3       | T3_T4, r 25.38, z +7.5, Tangente 32° | -79.4      | T4_T5      | 66.3    | T3   |
| `pos_031_W3_DY2` | LOAD_16NM | -0.15 %  | 43.5       | 126.0          | T4 RIGHT, r 25.68, z +0.0 | 55.9       | T3_T4, r 25.38, z +7.5, Tangente 32° | -76.0      | T4_T5      | 46.8    | T3   |
| `pos_031_W4_QS`  | LOAD_16NM | +0.15 %  | 79.7       | 83.4           | T4 RIGHT, r 25.75, z +5.9 | 54.9       | T3_T4, r 25.58, z -7.5, Tangente 17° | -61.2      | T4_T5      | 85.4    | T3   |
| `pos_031_W4_DY1` | LOAD_16NM | +0.12 %  | 73.2       | 85.5           | T4 RIGHT, r 25.75, z +5.9 | 58.1       | T3_T4, r 25.58, z -7.5, Tangente 17° | -65.7      | T4_T5      | 78.5    | T3   |
| `pos_031_W4_DY2` | LOAD_16NM | -0.02 %  | 48.4       | 97.8           | T4 RIGHT, r 25.68, z +0.0 | 57.0       | T3_T4, r 25.58, z -7.5, Tangente 17° | -66.9      | T4_T5      | 52.1    | T3   |
| `pos_036_W1_QS`  | LOAD_16NM | +0.46 %  | 67.3       | 212.4          | T4 RIGHT, r 25.75, z +0.0 | 46.3       | T3_T4, r 25.34, z +0.0, Tangente 37° | -62.3      | T4_T5      | 74.7    | T3   |
| `pos_036_W1_DY1` | LOAD_16NM | +0.42 %  | 60.8       | 218.1          | T4 RIGHT, r 25.75, z +0.0 | 46.1       | T3_T4, r 25.34, z +0.0, Tangente 37° | -62.1      | T4_T5      | 67.4    | T3   |
| `pos_036_W1_DY2` | LOAD_16NM | +0.40 %  | 43.9       | 238.6          | T4 RIGHT, r 25.75, z +0.0 | 45.9       | T3_T4, r 25.34, z +0.0, Tangente 37° | -61.9      | T4_T5      | 48.4    | T3   |
| `pos_036_W2_QS`  | LOAD_16NM | +0.53 %  | 82.6       | 98.2           | T4 RIGHT, r 25.75, z +0.0 | 35.6       | T2_T3, r 25.07, z +0.0, Tangente 77° | -47.5      | T4_T5      | 92.0    | T3   |
| `pos_036_W2_DY1` | LOAD_16NM | +0.49 %  | 75.2       | 109.4          | T4 RIGHT, r 25.75, z +0.0 | 36.9       | T2_T3, r 25.07, z +0.0, Tangente 77° | -48.4      | T4_T5      | 83.6    | T3   |
| `pos_036_W2_DY2` | LOAD_16NM | +0.45 %  | 50.6       | 130.2          | T4 RIGHT, r 25.75, z +0.0 | 38.0       | T2_T3, r 25.07, z +0.0, Tangente 77° | -50.0      | T4_T5      | 55.9    | T3   |
| `pos_036_W3_QS`  | LOAD_16NM | +0.46 %  | 69.2       | 189.9          | T4 RIGHT, r 25.75, z -7.5 | 50.2       | T3_T4, r 25.38, z -0.7, Tangente 32° | -71.0      | T4_T5      | 74.6    | T3   |
| `pos_036_W3_DY1` | LOAD_16NM | +0.43 %  | 63.7       | 204.5          | T4 RIGHT, r 25.75, z -7.5 | 55.7       | T3_T4, r 25.41, z +7.5, Tangente 30° | -74.7      | T4_T5      | 68.2    | T3   |
| `pos_036_W3_DY2` | LOAD_16NM | +0.38 %  | 45.6       | 230.1          | T4 RIGHT, r 25.75, z -7.5 | 55.2       | T3_T4, r 25.41, z +7.5, Tangente 30° | -71.6      | T4_T5      | 48.8    | T3   |
| `pos_036_W4_QS`  | LOAD_16NM | +0.54 %  | 82.3       | 94.9           | T4 RIGHT, r 25.82, z -6.7 | 54.5       | T3_T4, r 25.61, z -7.5, Tangente 16° | -57.9      | T4_T5      | 88.9    | T3   |
| `pos_036_W4_DY1` | LOAD_16NM | +0.52 %  | 75.8       | 107.1          | T4 RIGHT, r 25.75, z -7.5 | 56.9       | T3_T4, r 25.61, z -7.5, Tangente 16° | -62.2      | T4_T5      | 81.6    | T3   |
| `pos_036_W4_DY2` | LOAD_16NM | +0.46 %  | 51.4       | 137.2          | T4 RIGHT, r 25.75, z -7.5 | 60.2       | T3_T4, r 25.61, z -7.5, Tangente 16° | -63.4      | T4_T5      | 55.0    | T3   |
| `pos_049_W1_QS`  | LOAD_16NM | +0.00 %  | 86.4       | 102.9          | T4 RIGHT, r 25.97, z +0.0 | 62.6       | T2_T3, r 25.32, z +0.0, Tangente 39° | -72.7      | T3_T4      | 98.2    | T3   |
| `pos_049_W1_DY1` | LOAD_16NM | -0.18 %  | 80.2       | 88.3           | T4 RIGHT, r 25.97, z +0.0 | 65.0       | T2_T3, r 25.32, z +0.0, Tangente 39° | -75.9      | T3_T4      | 91.0    | T3   |
| `pos_049_W1_DY2` | LOAD_16NM | -0.86 %  | 64.2       | 111.4          | T3 RIGHT, r 26.11, z +0.0 | 75.7       | T2_T3, r 25.32, z +0.0, Tangente 39° | -89.5      | T3_T4      | 72.5    | T3   |
| `pos_049_W2_QS`  | LOAD_16NM | +0.05 %  | 94.8       | 88.5           | T4 RIGHT, r 25.97, z +0.0 | 42.1       | T2_T3, r 25.41, z +0.0, Tangente 30° | -47.6      | T3_T4      | 106.4   | T3   |
| `pos_049_W2_DY1` | LOAD_16NM | +0.01 %  | 89.7       | 93.4           | T4 RIGHT, r 25.97, z +0.0 | 43.8       | T2_T3, r 25.43, z +0.0, Tangente 28° | -49.7      | T3_T4      | 100.9   | T3   |
| `pos_049_W2_DY2` | LOAD_16NM | -0.51 %  | 69.6       | 76.3           | T3 RIGHT, r 26.11, z +0.0 | 51.7       | T2_T3, r 25.43, z +0.0, Tangente 28° | -59.6      | T3_T4      | 77.8    | T3   |
| `pos_049_W3_QS`  | LOAD_16NM | +0.10 %  | 87.0       | 105.5          | T4 RIGHT, r 25.97, z +0.0 | 62.5       | T2_T3, r 25.34, z -0.7, Tangente 37° | -77.8      | T3_T4      | 93.6    | T3   |
| `pos_049_W3_DY1` | LOAD_16NM | +0.03 %  | 81.8       | 96.3           | T4 RIGHT, r 25.97, z +0.0 | 65.0       | T2_T3, r 25.38, z -0.7, Tangente 32° | -85.6      | T3_T4      | 87.0    | T3   |
| `pos_049_W3_DY2` | LOAD_16NM | -0.71 %  | 64.7       | 98.9           | T3 RIGHT, r 26.25, z +7.5 | 74.1       | T2_T3, r 25.38, z -0.7, Tangente 32° | -96.1      | T3_T4      | 68.7    | T3   |
| `pos_049_W4_QS`  | LOAD_16NM | -0.00 %  | 94.0       | 78.8           | T4 RIGHT, r 25.97, z +0.0 | 48.5       | T2_T3, r 25.38, z +6.7, Tangente 32° | -63.6      | T3_T4      | 99.9    | T3   |
| `pos_049_W4_DY1` | LOAD_16NM | -0.06 %  | 89.1       | 81.4           | T4 RIGHT, r 25.97, z +0.0 | 52.2       | T2_T3, r 25.38, z +6.7, Tangente 32° | -70.3      | T3_T4      | 94.1    | T3   |
| `pos_049_W4_DY2` | LOAD_16NM | -0.50 %  | 69.2       | 75.1           | T3 RIGHT, r 25.97, z -7.5 | 60.0       | T2_T3, r 25.38, z +6.7, Tangente 32° | -82.0      | T3_T4      | 72.7    | T3   |
| `pos_063_W1_QS`  | LOAD_16NM | +0.05 %  | 69.8       | 137.3          | T3 RIGHT, r 25.68, z +0.0 | 49.3       | T2_T3, r 25.30, z +0.0, Tangente 42° | -63.6      | T3_T4      | 75.0    | T2   |
| `pos_063_W1_DY1` | LOAD_16NM | -0.02 %  | 62.8       | 139.0          | T3 RIGHT, r 25.68, z +0.0 | 50.5       | T2_T3, r 25.30, z +0.0, Tangente 42° | -63.4      | T3_T4      | 67.3    | T2   |
| `pos_063_W1_DY2` | LOAD_16NM | -0.12 %  | 44.5       | 137.9          | T3 RIGHT, r 25.68, z +0.0 | 51.2       | T2_T3, r 25.32, z +0.0, Tangente 39° | -63.4      | T3_T4      | 47.5    | T2   |
| `pos_063_W2_QS`  | LOAD_16NM | +0.12 %  | 83.7       | 88.2           | T3 RIGHT, r 25.75, z -5.9 | 35.2       | T1_T2, r 25.06, z +0.0, Tangente 82° | -50.6      | T3_T4      | 90.5    | T2   |
| `pos_063_W2_DY1` | LOAD_16NM | +0.11 %  | 75.8       | 91.1           | T3 RIGHT, r 25.75, z -5.9 | 36.2       | T1_T2, r 25.06, z +0.0, Tangente 82° | -51.6      | T3_T4      | 81.7    | T2   |
| `pos_063_W2_DY2` | LOAD_16NM | -0.04 %  | 50.0       | 104.7          | T3 RIGHT, r 25.68, z +0.0 | 38.4       | T2_T3, r 25.34, z +0.0, Tangente 37° | -53.0      | T3_T4      | 53.3    | T2   |
| `pos_063_W3_QS`  | LOAD_16NM | +0.09 %  | 71.4       | 128.9          | T3 RIGHT, r 25.75, z +7.5 | 52.1       | T2_T3, r 25.43, z +7.5, Tangente 28° | -73.3      | T3_T4      | 75.7    | T3   |
| `pos_063_W3_DY1` | LOAD_16NM | +0.05 %  | 65.4       | 124.1          | T3 RIGHT, r 25.68, z +0.0 | 55.8       | T2_T3, r 25.43, z +7.5, Tangente 28° | -77.3      | T3_T4      | 69.3    | T2   |
| `pos_063_W3_DY2` | LOAD_16NM | -0.10 %  | 46.0       | 127.3          | T3 RIGHT, r 25.68, z +0.0 | 56.1       | T2_T3, r 25.36, z +7.5, Tangente 34° | -74.2      | T3_T4      | 48.8    | T2   |
| `pos_063_W4_QS`  | LOAD_16NM | +0.16 %  | 83.9       | 88.3           | T3 RIGHT, r 25.75, z +7.5 | 51.1       | T2_T3, r 25.58, z -7.5, Tangente 17° | -61.0      | T3_T4      | 89.1    | T3   |
| `pos_063_W4_DY1` | LOAD_16NM | +0.14 %  | 77.0       | 91.3           | T3 RIGHT, r 25.75, z +7.5 | 55.7       | T2_T3, r 25.58, z -7.5, Tangente 17° | -65.6      | T3_T4      | 81.8    | T2   |
| `pos_063_W4_DY2` | LOAD_16NM | +0.00 %  | 50.9       | 96.2           | T3 RIGHT, r 25.68, z +0.0 | 53.9       | T2_T3, r 25.58, z +7.5, Tangente 17° | -66.5      | T3_T4      | 54.3    | T2   |
| `pos_068_W1_QS`  | LOAD_16NM | +0.68 %  | 71.4       | 214.8          | T3 RIGHT, r 25.75, z +0.0 | 47.2       | T2_T3, r 25.34, z +0.0, Tangente 37° | -59.8      | T3_T4      | 79.2    | T2   |
| `pos_068_W1_DY1` | LOAD_16NM | +0.52 %  | 64.1       | 220.2          | T3 RIGHT, r 25.75, z +0.0 | 47.1       | T2_T3, r 25.34, z +0.0, Tangente 37° | -59.5      | T3_T4      | 70.9    | T2   |
| `pos_068_W1_DY2` | LOAD_16NM | +0.39 %  | 46.1       | 239.7          | T3 RIGHT, r 25.75, z +0.0 | 46.7       | T2_T3, r 25.34, z +0.0, Tangente 37° | -59.0      | T3_T4      | 50.6    | T2   |
| `pos_068_W2_QS`  | LOAD_16NM | +0.60 %  | 85.5       | 99.9           | T3 RIGHT, r 25.82, z -5.9 | 37.4       | T1_T2, r 25.06, z +0.0, Tangente 82° | -47.7      | T3_T4      | 95.1    | T2   |
| `pos_068_W2_DY1` | LOAD_16NM | +0.56 %  | 77.7       | 109.6          | T3 RIGHT, r 25.75, z +0.0 | 38.6       | T1_T2, r 25.06, z +0.0, Tangente 82° | -48.7      | T3_T4      | 86.3    | T2   |
| `pos_068_W2_DY2` | LOAD_16NM | +0.44 %  | 52.3       | 130.4          | T3 RIGHT, r 25.75, z +0.0 | 40.0       | T1_T2, r 25.07, z +0.0, Tangente 77° | -49.7      | T3_T4      | 57.7    | T2   |
| `pos_068_W3_QS`  | LOAD_16NM | +0.66 %  | 73.0       | 186.7          | T3 RIGHT, r 25.75, z +0.0 | 50.0       | T2_T3, r 25.38, z -0.7, Tangente 32° | -69.5      | T3_T4      | 78.9    | T2   |
| `pos_068_W3_DY1` | LOAD_16NM | +0.57 %  | 66.9       | 186.3          | T3 RIGHT, r 25.75, z +0.0 | 53.2       | T2_T3, r 25.43, z +7.5, Tangente 28° | -73.1      | T3_T4      | 71.8    | T2   |
| `pos_068_W3_DY2` | LOAD_16NM | +0.38 %  | 47.6       | 228.3          | T3 RIGHT, r 25.75, z +7.5 | 57.0       | T2_T3, r 25.43, z +7.5, Tangente 28° | -69.7      | T3_T4      | 50.9    | T2   |
| `pos_068_W4_QS`  | LOAD_16NM | +0.61 %  | 86.1       | 99.3           | T3 RIGHT, r 25.82, z -7.5 | 48.3       | T2_T3, r 25.61, z -7.5, Tangente 16° | -57.9      | T3_T4      | 93.2    | T2   |
| `pos_068_W4_DY1` | LOAD_16NM | +0.57 %  | 79.1       | 106.0          | T3 RIGHT, r 25.82, z -7.5 | 51.2       | T2_T3, r 25.58, z +7.5, Tangente 17° | -62.2      | T3_T4      | 85.2    | T2   |
| `pos_068_W4_DY2` | LOAD_16NM | +0.45 %  | 53.6       | 138.4          | T3 RIGHT, r 25.75, z +7.5 | 54.9       | T2_T3, r 25.61, z +7.5, Tangente 16° | -62.8      | T3_T4      | 57.4    | T2   |

## 2026-10-16 22:32 `pilot_20layers_bore33_pocket_fillet_bionic_phi35_r0p2_round0p1f12_qsdy1dy2_AtoE_gerechnet`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

**Läufe**

| Datei            | Stellung | Stufe | Rate | Variante | Löser           | Status   | Inkremente je Schritt | Wand s | neg. EW | Ende             |
|------------------|----------|-------|------|----------|-----------------|----------|-----------------------|--------|---------|------------------|
| `pos_031_W1_QS`  | A        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 273    | 0       | 2026-10-16 13:57 |
| `pos_031_W1_DY1` | A        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 269    | 0       | 2026-10-16 13:47 |
| `pos_031_W1_DY2` | A        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 259    | 0       | 2026-10-16 13:52 |
| `pos_031_W2_QS`  | A        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 319    | 0       | 2026-10-16 14:13 |
| `pos_031_W2_DY1` | A        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 314    | 0       | 2026-10-16 14:02 |
| `pos_031_W2_DY2` | A        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 283    | 0       | 2026-10-16 14:07 |
| `pos_031_W3_QS`  | A        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 600    | 0       | 2026-10-16 14:44 |
| `pos_031_W3_DY1` | A        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 596    | 0       | 2026-10-16 14:24 |
| `pos_031_W3_DY2` | A        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 594    | 0       | 2026-10-16 14:34 |
| `pos_031_W4_QS`  | A        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 763    | 0       | 2026-10-16 15:23 |
| `pos_031_W4_DY1` | A        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 759    | 0       | 2026-10-16 14:58 |
| `pos_031_W4_DY2` | A        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 686    | 0       | 2026-10-16 15:10 |
| `pos_036_W1_QS`  | B        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 267    | 0       | 2026-10-16 15:37 |
| `pos_036_W1_DY1` | B        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 252    | 0       | 2026-10-16 15:27 |
| `pos_036_W1_DY2` | B        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 261    | 0       | 2026-10-16 15:32 |
| `pos_036_W2_QS`  | B        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 11           | 391    | 5       | 2026-10-16 15:55 |
| `pos_036_W2_DY1` | B        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 305    | 0       | 2026-10-16 15:43 |
| `pos_036_W2_DY2` | B        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 283    | 0       | 2026-10-16 15:48 |
| `pos_036_W3_QS`  | B        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 565    | 0       | 2026-10-16 16:24 |
| `pos_036_W3_DY1` | B        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 581    | 0       | 2026-10-16 16:05 |
| `pos_036_W3_DY2` | B        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 542    | 0       | 2026-10-16 16:14 |
| `pos_036_W4_QS`  | B        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 861    | 2       | 2026-10-16 17:04 |
| `pos_036_W4_DY1` | B        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 674    | 0       | 2026-10-16 16:36 |
| `pos_036_W4_DY2` | B        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 769    | 0       | 2026-10-16 16:49 |
| `pos_049_W1_QS`  | C        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 310    | 0       | 2026-10-16 17:20 |
| `pos_049_W1_DY1` | C        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 288    | 0       | 2026-10-16 17:09 |
| `pos_049_W1_DY2` | C        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 285    | 0       | 2026-10-16 17:15 |
| `pos_049_W2_QS`  | C        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 348    | 0       | 2026-10-16 17:39 |
| `pos_049_W2_DY1` | C        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 381    | 3       | 2026-10-16 17:27 |
| `pos_049_W2_DY2` | C        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 313    | 0       | 2026-10-16 17:33 |
| `pos_049_W3_QS`  | C        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 634    | 0       | 2026-10-16 18:12 |
| `pos_049_W3_DY1` | C        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 636    | 0       | 2026-10-16 17:50 |
| `pos_049_W3_DY2` | C        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 640    | 0       | 2026-10-16 18:01 |
| `pos_049_W4_QS`  | C        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 771    | 0       | 2026-10-16 18:52 |
| `pos_049_W4_DY1` | C        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 781    | 0       | 2026-10-16 18:26 |
| `pos_049_W4_DY2` | C        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 770    | 0       | 2026-10-16 18:39 |
| `pos_063_W1_QS`  | D        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 281    | 0       | 2026-10-16 19:07 |
| `pos_063_W1_DY1` | D        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 269    | 0       | 2026-10-16 18:57 |
| `pos_063_W1_DY2` | D        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 262    | 0       | 2026-10-16 19:02 |
| `pos_063_W2_QS`  | D        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 329    | 0       | 2026-10-16 19:24 |
| `pos_063_W2_DY1` | D        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 317    | 0       | 2026-10-16 19:13 |
| `pos_063_W2_DY2` | D        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 293    | 0       | 2026-10-16 19:18 |
| `pos_063_W3_QS`  | D        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 606    | 0       | 2026-10-16 19:56 |
| `pos_063_W3_DY1` | D        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 610    | 0       | 2026-10-16 19:35 |
| `pos_063_W3_DY2` | D        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 578    | 0       | 2026-10-16 19:45 |
| `pos_063_W4_QS`  | D        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 838    | 0       | 2026-10-16 20:37 |
| `pos_063_W4_DY1` | D        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 802    | 0       | 2026-10-16 20:10 |
| `pos_063_W4_DY2` | D        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 727    | 0       | 2026-10-16 20:22 |
| `pos_068_W1_QS`  | E        | W1    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 8            | 359    | 8       | 2026-10-16 20:53 |
| `pos_068_W1_DY1` | E        | W1    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 271    | 0       | 2026-10-16 20:42 |
| `pos_068_W1_DY2` | E        | W1    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 276    | 0       | 2026-10-16 20:47 |
| `pos_068_W2_QS`  | E        | W2    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 13           | 459    | 5       | 2026-10-16 21:13 |
| `pos_068_W2_DY1` | E        | W2    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 340    | 0       | 2026-10-16 20:59 |
| `pos_068_W2_DY2` | E        | W2    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 291    | 0       | 2026-10-16 21:04 |
| `pos_068_W3_QS`  | E        | W3    | QS   |          | linear, N2S 0.2 | complete | 6, 6, 6, 9            | 797    | 0       | 2026-10-16 21:47 |
| `pos_068_W3_DY1` | E        | W3    | DY1  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 614    | 0       | 2026-10-16 21:23 |
| `pos_068_W3_DY2` | E        | W3    | DY2  |          | linear, N2S 0.2 | complete | 6, 6, 6, 6            | 572    | 0       | 2026-10-16 21:33 |
| `pos_068_W4_QS`  | E        | W4    | QS   |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 9            | 957    | 3       | 2026-10-16 22:32 |
| `pos_068_W4_DY1` | E        | W4    | DY1  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 8            | 883    | 0       | 2026-10-16 22:02 |
| `pos_068_W4_DY2` | E        | W4    | DY2  |          | NLGEOM, N2S 0.2 | complete | 6, 6, 6, 6            | 740    | 0       | 2026-10-16 22:15 |

**Kennwerte des letzten gedruckten Lastschritts**

| Datei            | Schritt   | RM3 Abw. | Drehung µm | CPRESS max MPa | Ort                       | σ1 max MPa | Fußrundung, Ort, Tangente            | σ3 min MPa | Fußrundung | Kopf µm | Zahn |
|------------------|-----------|----------|------------|----------------|---------------------------|------------|--------------------------------------|------------|------------|---------|------|
| `pos_031_W1_QS`  | LOAD_16NM | -0.06 %  | 70.0       | 143.0          | T4 RIGHT, r 25.68, z +0.0 | 46.8       | T2_T3, r 24.91, z +0.0, Tangente 79° | -85.7      | T4_T5      | 76.0    | T3   |
| `pos_031_W1_DY1` | LOAD_16NM | -0.09 %  | 63.1       | 143.1          | T4 RIGHT, r 25.68, z +0.0 | 46.5       | T2_T3, r 24.91, z +0.0, Tangente 79° | -85.6      | T4_T5      | 68.3    | T3   |
| `pos_031_W1_DY2` | LOAD_16NM | -0.20 %  | 44.8       | 138.6          | T4 RIGHT, r 25.68, z +0.0 | 46.3       | T2_T3, r 24.91, z +0.0, Tangente 79° | -85.4      | T4_T5      | 48.7    | T3   |
| `pos_031_W2_QS`  | LOAD_16NM | +0.09 %  | 86.3       | 87.4           | T4 RIGHT, r 25.68, z -0.7 | 40.2       | T2_T3, r 24.91, z -1.3, Tangente 79° | -59.3      | T4_T5      | 94.1    | T3   |
| `pos_031_W2_DY1` | LOAD_16NM | +0.05 %  | 78.1       | 97.0           | T4 RIGHT, r 25.68, z +0.0 | 41.5       | T2_T3, r 24.91, z +0.0, Tangente 79° | -60.5      | T4_T5      | 85.0    | T3   |
| `pos_031_W2_DY2` | LOAD_16NM | -0.09 %  | 51.2       | 109.8          | T4 RIGHT, r 25.68, z +0.0 | 42.0       | T2_T3, r 24.91, z -1.3, Tangente 79° | -63.2      | T4_T5      | 55.5    | T3   |
| `pos_031_W3_QS`  | LOAD_16NM | -0.02 %  | 71.8       | 129.2          | T4 RIGHT, r 25.68, z +0.0 | 53.4       | T2_T3, r 24.91, z -4.4, Tangente 79° | -98.4      | T4_T5      | 77.5    | T3   |
| `pos_031_W3_DY1` | LOAD_16NM | -0.04 %  | 65.8       | 127.3          | T4 RIGHT, r 25.68, z -0.7 | 54.6       | T2_T3, r 24.91, z -4.4, Tangente 79° | -102.2     | T4_T5      | 71.0    | T3   |
| `pos_031_W3_DY2` | LOAD_16NM | -0.18 %  | 46.3       | 128.2          | T4 RIGHT, r 25.68, z -0.7 | 53.7       | T2_T3, r 24.91, z -4.4, Tangente 79° | -98.7      | T4_T5      | 50.1    | T3   |
| `pos_031_W4_QS`  | LOAD_16NM | +0.12 %  | 85.1       | 84.5           | T4 RIGHT, r 25.75, z +5.9 | 51.1       | T3_T4, r 25.58, z -7.5, Tangente 16° | -75.4      | T4_T5      | 91.7    | T3   |
| `pos_031_W4_DY1` | LOAD_16NM | +0.09 %  | 78.1       | 87.0           | T4 RIGHT, r 25.68, z -0.7 | 53.1       | T3_T4, r 25.58, z -7.5, Tangente 16° | -80.9      | T4_T5      | 84.2    | T3   |
| `pos_031_W4_DY2` | LOAD_16NM | -0.05 %  | 51.5       | 101.2          | T4 RIGHT, r 25.68, z +0.0 | 52.2       | T3_T4, r 25.58, z -7.5, Tangente 16° | -82.6      | T4_T5      | 55.7    | T3   |
| `pos_036_W1_QS`  | LOAD_16NM | +0.42 %  | 71.6       | 215.0          | T4 RIGHT, r 25.75, z +0.0 | 51.2       | T2_T3, r 24.91, z +0.0, Tangente 79° | -80.4      | T4_T5      | 80.2    | T3   |
| `pos_036_W1_DY1` | LOAD_16NM | +0.39 %  | 64.7       | 220.2          | T4 RIGHT, r 25.75, z +0.0 | 51.0       | T2_T3, r 24.91, z +0.0, Tangente 79° | -80.2      | T4_T5      | 72.4    | T3   |
| `pos_036_W1_DY2` | LOAD_16NM | +0.38 %  | 46.7       | 241.0          | T4 RIGHT, r 25.75, z +0.0 | 51.2       | T2_T3, r 24.91, z +0.0, Tangente 79° | -79.9      | T4_T5      | 51.9    | T3   |
| `pos_036_W2_QS`  | LOAD_16NM | +0.50 %  | 88.2       | 101.2          | T4 RIGHT, r 25.75, z +0.0 | 42.7       | T2_T3, r 24.91, z -1.3, Tangente 79° | -56.3      | T4_T5      | 99.1    | T3   |
| `pos_036_W2_DY1` | LOAD_16NM | +0.48 %  | 80.2       | 112.3          | T4 RIGHT, r 25.75, z +0.0 | 44.0       | T2_T3, r 24.91, z -1.3, Tangente 79° | -57.5      | T4_T5      | 90.0    | T3   |
| `pos_036_W2_DY2` | LOAD_16NM | +0.43 %  | 53.8       | 133.2          | T4 RIGHT, r 25.75, z +0.0 | 45.5       | T2_T3, r 24.91, z -1.3, Tangente 79° | -59.5      | T4_T5      | 60.0    | T3   |
| `pos_036_W3_QS`  | LOAD_16NM | +0.43 %  | 73.5       | 191.6          | T4 RIGHT, r 25.75, z -7.5 | 58.7       | T2_T3, r 24.91, z -4.4, Tangente 79° | -92.5      | T4_T5      | 80.2    | T3   |
| `pos_036_W3_DY1` | LOAD_16NM | +0.40 %  | 67.6       | 206.0          | T4 RIGHT, r 25.75, z -7.5 | 60.3       | T2_T3, r 24.91, z -4.4, Tangente 79° | -96.3      | T4_T5      | 73.2    | T3   |
| `pos_036_W3_DY2` | LOAD_16NM | +0.36 %  | 48.3       | 231.6          | T4 RIGHT, r 25.75, z -7.5 | 59.7       | T2_T3, r 24.91, z -4.4, Tangente 79° | -92.7      | T4_T5      | 52.2    | T3   |
| `pos_036_W4_QS`  | LOAD_16NM | +0.54 %  | 87.4       | 95.3           | T4 RIGHT, r 25.75, z -7.5 | 52.9       | T3_T4, r 25.61, z -7.5, Tangente 16° | -71.8      | T4_T5      | 95.5    | T3   |
| `pos_036_W4_DY1` | LOAD_16NM | +0.51 %  | 80.5       | 108.7          | T4 RIGHT, r 25.75, z -7.5 | 54.6       | T3_T4, r 25.61, z -7.5, Tangente 16° | -76.8      | T4_T5      | 87.5    | T3   |
| `pos_036_W4_DY2` | LOAD_16NM | +0.45 %  | 54.5       | 139.3          | T4 RIGHT, r 25.75, z -7.5 | 57.6       | T3_T4, r 25.61, z -7.5, Tangente 16° | -78.2      | T4_T5      | 58.8    | T3   |
| `pos_049_W1_QS`  | LOAD_16NM | +0.19 %  | 90.1       | 119.2          | T4 RIGHT, r 25.97, z +0.0 | 64.3       | T2_T3, r 24.93, z +0.0, Tangente 64° | -81.6      | T3_T4      | 103.7   | T3   |
| `pos_049_W1_DY1` | LOAD_16NM | +0.08 %  | 83.8       | 106.8          | T4 RIGHT, r 25.97, z +0.0 | 67.1       | T2_T3, r 24.93, z +0.0, Tangente 64° | -86.3      | T3_T4      | 96.5    | T3   |
| `pos_049_W1_DY2` | LOAD_16NM | -0.73 %  | 66.7       | 109.0          | T3 RIGHT, r 26.11, z +0.0 | 78.7       | T2_T3, r 24.93, z +0.0, Tangente 64° | -102.1     | T3_T4      | 76.6    | T3   |
| `pos_049_W2_QS`  | LOAD_16NM | +0.13 %  | 98.7       | 90.7           | T4 RIGHT, r 25.97, z +0.0 | 42.1       | T2_T3, r 24.91, z +0.0, Tangente 71° | -53.3      | T3_T4      | 112.3   | T3   |
| `pos_049_W2_DY1` | LOAD_16NM | +0.09 %  | 93.3       | 96.3           | T4 RIGHT, r 25.97, z +0.0 | 44.5       | T2_T3, r 24.91, z +0.0, Tangente 71° | -56.2      | T3_T4      | 106.2   | T3   |
| `pos_049_W2_DY2` | LOAD_16NM | -0.38 %  | 72.1       | 79.5           | T4 RIGHT, r 25.97, z +0.0 | 53.1       | T2_T3, r 24.91, z +0.0, Tangente 71° | -68.2      | T3_T4      | 81.8    | T3   |
| `pos_049_W3_QS`  | LOAD_16NM | +0.25 %  | 90.5       | 118.4          | T4 RIGHT, r 25.97, z +0.0 | 65.5       | T2_T3, r 24.91, z -3.6, Tangente 71° | -96.0      | T3_T4      | 99.0    | T3   |
| `pos_049_W3_DY1` | LOAD_16NM | +0.20 %  | 85.1       | 110.0          | T4 RIGHT, r 25.97, z +0.0 | 69.9       | T2_T3, r 24.91, z -3.6, Tangente 71° | -105.4     | T3_T4      | 92.1    | T3   |
| `pos_049_W3_DY2` | LOAD_16NM | -0.59 %  | 67.1       | 96.3           | T3 RIGHT, r 26.26, z +7.5 | 83.0       | T2_T3, r 24.91, z -3.6, Tangente 71° | -119.0     | T3_T4      | 72.6    | T3   |
| `pos_049_W4_QS`  | LOAD_16NM | +0.07 %  | 97.8       | 80.9           | T4 RIGHT, r 25.97, z +0.0 | 47.1       | T2_T3, r 24.91, z -3.6, Tangente 71° | -69.1      | T3_T4      | 105.9   | T3   |
| `pos_049_W4_DY1` | LOAD_16NM | +0.01 %  | 92.5       | 83.2           | T4 RIGHT, r 25.97, z +0.0 | 51.8       | T2_T3, r 24.91, z -3.6, Tangente 71° | -76.7      | T3_T4      | 99.5    | T3   |
| `pos_049_W4_DY2` | LOAD_16NM | -0.39 %  | 71.6       | 76.0           | T4 RIGHT, r 25.97, z +0.0 | 62.1       | T2_T3, r 24.91, z -3.6, Tangente 71° | -90.3      | T3_T4      | 76.9    | T3   |
| `pos_063_W1_QS`  | LOAD_16NM | +0.00 %  | 74.4       | 142.1          | T3 RIGHT, r 25.68, z +0.0 | 52.7       | T1_T2, r 24.91, z +0.0, Tangente 79° | -81.9      | T3_T4      | 81.3    | T3   |
| `pos_063_W1_DY1` | LOAD_16NM | -0.05 %  | 66.9       | 142.6          | T3 RIGHT, r 25.68, z +0.0 | 52.4       | T1_T2, r 24.91, z +0.0, Tangente 79° | -81.8      | T3_T4      | 72.9    | T3   |
| `pos_063_W1_DY2` | LOAD_16NM | -0.15 %  | 47.5       | 141.1          | T3 RIGHT, r 25.68, z +0.0 | 52.1       | T1_T2, r 24.91, z +0.0, Tangente 79° | -81.7      | T3_T4      | 51.3    | T3   |
| `pos_063_W2_QS`  | LOAD_16NM | +0.10 %  | 89.7       | 89.8           | T3 RIGHT, r 25.75, z -5.9 | 42.0       | T1_T2, r 24.91, z +0.0, Tangente 79° | -59.5      | T3_T4      | 97.5    | T2   |
| `pos_063_W2_DY1` | LOAD_16NM | +0.09 %  | 81.2       | 92.8           | T3 RIGHT, r 25.75, z -5.9 | 42.9       | T1_T2, r 24.91, z +0.0, Tangente 79° | -60.8      | T3_T4      | 88.1    | T2   |
| `pos_063_W2_DY2` | LOAD_16NM | -0.05 %  | 53.4       | 109.1          | T3 RIGHT, r 25.68, z +0.0 | 44.4       | T1_T2, r 24.91, z +0.0, Tangente 79° | -63.3      | T3_T4      | 57.4    | T2   |
| `pos_063_W3_QS`  | LOAD_16NM | +0.06 %  | 76.0       | 130.5          | T3 RIGHT, r 25.75, z +7.5 | 55.5       | T1_T2, r 24.91, z -4.4, Tangente 79° | -96.8      | T3_T4      | 80.9    | T2   |
| `pos_063_W3_DY1` | LOAD_16NM | +0.01 %  | 69.5       | 126.6          | T3 RIGHT, r 25.68, z -0.7 | 56.4       | T1_T2, r 24.91, z -4.4, Tangente 79° | -99.9      | T3_T4      | 74.0    | T2   |
| `pos_063_W3_DY2` | LOAD_16NM | -0.12 %  | 48.9       | 129.9          | T3 RIGHT, r 25.68, z -0.7 | 55.6       | T1_T2, r 24.91, z -4.4, Tangente 79° | -97.3      | T3_T4      | 52.2    | T2   |
| `pos_063_W4_QS`  | LOAD_16NM | +0.13 %  | 89.5       | 90.1           | T3 RIGHT, r 25.75, z +7.5 | 48.0       | T1_T2, r 24.91, z +5.1, Tangente 87° | -74.8      | T3_T4      | 95.7    | T2   |
| `pos_063_W4_DY1` | LOAD_16NM | +0.12 %  | 82.0       | 92.9           | T3 RIGHT, r 25.75, z +7.5 | 51.8       | T2_T3, r 25.58, z -7.5, Tangente 16° | -80.9      | T3_T4      | 87.6    | T2   |
| `pos_063_W4_DY2` | LOAD_16NM | -0.02 %  | 54.1       | 99.4           | T3 RIGHT, r 25.68, z +0.0 | 50.7       | T1_T2, r 24.91, z +5.1, Tangente 79° | -82.7      | T3_T4      | 58.0    | T2   |
| `pos_068_W1_QS`  | LOAD_16NM | +0.65 %  | 75.9       | 217.6          | T3 RIGHT, r 25.75, z +0.0 | 57.3       | T1_T2, r 24.91, z +0.0, Tangente 79° | -77.2      | T3_T4      | 84.7    | T2   |
| `pos_068_W1_DY1` | LOAD_16NM | +0.49 %  | 68.2       | 222.2          | T3 RIGHT, r 25.75, z +0.0 | 56.9       | T1_T2, r 24.91, z +0.0, Tangente 79° | -76.7      | T3_T4      | 75.9    | T2   |
| `pos_068_W1_DY2` | LOAD_16NM | +0.37 %  | 48.9       | 242.1          | T3 RIGHT, r 25.75, z +0.0 | 56.9       | T1_T2, r 24.91, z +0.0, Tangente 79° | -76.1      | T3_T4      | 54.2    | T2   |
| `pos_068_W2_QS`  | LOAD_16NM | +0.59 %  | 91.3       | 101.2          | T3 RIGHT, r 25.75, z +0.0 | 44.3       | T1_T2, r 24.91, z +0.0, Tangente 79° | -56.7      | T3_T4      | 102.3   | T2   |
| `pos_068_W2_DY1` | LOAD_16NM | +0.55 %  | 82.8       | 112.4          | T3 RIGHT, r 25.75, z +0.0 | 45.3       | T1_T2, r 24.91, z +0.0, Tangente 79° | -57.8      | T3_T4      | 92.6    | T2   |
| `pos_068_W2_DY2` | LOAD_16NM | +0.43 %  | 55.6       | 133.4          | T3 RIGHT, r 25.75, z +0.0 | 47.5       | T1_T2, r 24.91, z +0.0, Tangente 79° | -59.6      | T3_T4      | 61.8    | T2   |
| `pos_068_W3_QS`  | LOAD_16NM | +0.63 %  | 77.4       | 189.3          | T3 RIGHT, r 25.75, z -0.7 | 60.4       | T1_T2, r 24.91, z -4.4, Tangente 79° | -91.5      | T3_T4      | 84.4    | T2   |
| `pos_068_W3_DY1` | LOAD_16NM | +0.54 %  | 70.9       | 189.0          | T3 RIGHT, r 25.75, z -0.7 | 61.7       | T1_T2, r 24.91, z -4.4, Tangente 79° | -94.8      | T3_T4      | 76.8    | T2   |
| `pos_068_W3_DY2` | LOAD_16NM | +0.36 %  | 50.4       | 229.2          | T3 RIGHT, r 25.75, z +7.5 | 61.5       | T1_T2, r 24.91, z -4.4, Tangente 79° | -91.2      | T3_T4      | 54.4    | T2   |
| `pos_068_W4_QS`  | LOAD_16NM | +0.61 %  | 91.4       | 102.7          | T3 RIGHT, r 25.82, z -7.5 | 51.2       | T1_T2, r 24.91, z +5.1, Tangente 87° | -71.5      | T3_T4      | 99.9    | T2   |
| `pos_068_W4_DY1` | LOAD_16NM | +0.56 %  | 83.9       | 109.4          | T3 RIGHT, r 25.82, z -7.5 | 54.0       | T1_T2, r 24.91, z +5.1, Tangente 87° | -77.0      | T3_T4      | 91.3    | T2   |
| `pos_068_W4_DY2` | LOAD_16NM | +0.44 %  | 56.7       | 140.1          | T3 RIGHT, r 25.75, z +7.5 | 55.5       | T1_T2, r 24.91, z +5.1, Tangente 79° | -78.3      | T3_T4      | 61.3    | T2   |

## 2026-10-19 18:26 `pilot_20layers_bore33_pocket_gemessen_stahl_round0p1f12_qsdy1dy2_AtoE`

**Zweck:** Gemessene Geometrie, Variante stahl (ADR-116 Punkt 54): Stahlritzel wie gefertigt (Median der Prüfstandsserie 95911 bis 95920, letzte GINA-Runde: Zahnweite 16,797, Kopfkreis 52,879, Fußkreis 48,321 mm, lineare Kopfrücknahme 23,6 µm ab d 51,946 bis zum Kopfkreis), Kunststoffrad nach dem STplus-Fall; Taschenkörper, Netz der Taschenserie (titelgleich bis auf die Zeile 1), Ritzelkante 0,1 mm, W1 bis W4 × QS/DY1/DY2 an A bis E (pos_031/036/049/063/068), 60 Jobs. **Ergebnis:** Vorlage; erster Unterordner der Kette nachtlauf_2026-10-19_messvarianten. (Befunde FE-19)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-19 18:27 `pilot_20layers_bore33_pocket_gemessen_kunststoff_round0p1f12_qsdy1dy2_AtoE`

**Zweck:** Gemessene Geometrie, Variante kunststoff (ADR-116 Punkt 54): Stahlritzel nach dem STplus-Fall, Kunststoffrad wie gefertigt (Median der Kerngruppe: Zahnweite 16,972, Kopfkreis 54,0515, Fußkreis 49,5055 mm, Profil-Winkelabweichung +10,25 µm ab d_Cf 50,3 mit Nullpunkt am Messkreis d_M 51,728, Kopfkantenrundung r_K 0,21 mm statt der 45°-Fase); Taschenkörper auf dem gemessenen Zahn, drei Elementreihen auf dem Bogen (86 800 Knoten, 75 732 C3D8I), Ritzelkante 0,1 mm, A bis E (pos_031/036/049/063/068); W1 und W2 × QS/DY1/DY2 (30 Jobs), W3/W4 nach dem CONVERSE-Mapping des Nutzers auf wheel-pocket_mesh.inp. **Ergebnis:** Vorlage; zweiter Unterordner der Kette nachtlauf_2026-10-19_messvarianten. (Befunde FE-19, FE-26)

Netz: 86800 Knoten, 75732 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 30 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 30 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-19 18:28 `pilot_20layers_bore33_pocket_gemessen_beide_round0p1f12_qsdy1dy2_AtoE`

**Zweck:** Gemessene Geometrie, Variante beide (ADR-116 Punkt 54): Stahlritzel und Kunststoffrad wie gefertigt (die Zahlen der beiden Einzelvarianten); Radnetz byteidentisch mit der Variante kunststoff, Ritzelfläche byteidentisch mit der Variante stahl; A bis E (pos_031/036/049/063/068); W1 und W2 × QS/DY1/DY2 (30 Jobs), W3/W4 nach dem Mapping. **Ergebnis:** Vorlage; dritter Unterordner der Kette nachtlauf_2026-10-19_messvarianten. (Befunde FE-19, FE-26)

Netz: 86800 Knoten, 75732 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 30 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 30 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-19 18:35 `nachtlauf_2026-10-19_messvarianten/variante_stahl_gemessen`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 83650 Knoten, 72932 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, W3, W4, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 60 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 60 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-19 18:35 `nachtlauf_2026-10-19_messvarianten/variante_kunststoff_gemessen`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 86800 Knoten, 75732 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 30 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 30 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).

## 2026-10-19 18:35 `nachtlauf_2026-10-19_messvarianten/variante_beide_gemessen`

(keine Notiz in fe_simulation_notes.yaml)

Netz: 86800 Knoten, 75732 Elemente (C3D8I, C3D8), 20 Schichten, Bohrung r 16.500 mm, Körper pocket; Werkstoffstufen W1, W2, Raten QS, DY1, DY2; Momente am Rad 8, 12, 16 Nm; 30 Stellungsdateien (grid, 30 je Teilung)

Nicht gerechnet: 30 Dateien (`pos_031_W1_QS`, `pos_031_W1_DY1`, `pos_031_W1_DY2`, `pos_031_W2_QS`, `pos_031_W2_DY1`, `pos_031_W2_DY2` …).


## 2026-10-21 `tasche_serie_w1w4_qs_gerechnet` ausgewertet (Serie, Nachweis), `vergleich_fussrundung_AtoE_V2`

**Zweck:** Die Taschenserie (99 Stellungen × W1 bis W4 × QS, vom Nutzer am 2026-10-21 abgelegt) wird der Hauptfall der Kapitel 5.2, 5.3 und 7 (Entscheidung des Nutzers, ADR-118 Amendment 2026-10-21). `fe_series_analysis.py --folder tasche_serie_w1w4_qs_gerechnet` (387 von 396 vollständig; neun Abbrüche im Schritt 16 Nm: W1 Stellungen 010, 040, 045, 072, 077; W3 040, 045, 072, 077; flatternde Kontaktknoten auf r 25,800 und 25,901 mm, Muster FE-19). `fe_fatigue.py stommel` auf W1_QS und W2_QS (von Mises, Klasse verstärkt) sowie W1_QS, W3_QS, W4_QS unter Hill (`--equivalent hill --cof 91_Converse/wheel-pocket_mesh_QS.cof --reduction-class semi_crystalline_unreinforced`); die Datei `wheel-52-pocket_mesh_QS.cof` gehört zum feineren 750 256-Elemente-Netz und wird vom Skript als fremd erkannt (Prüfung der Elementnummern).

**Ergebnis (Fußrundungen des Zahns T3):** W2 kritischer Knoten Fuß T3/T4 bei z = −5,93 mm auf der Zugseite (h 0,49), a_B,V 1,30 / 1,64 / 1,96, N_pred 1,65e5 / 4,33e3 / 0; W1 in der Zahnmitte, 1,72 / 2,69 / 10,4, a_stat > 1 an 0 / 176 / 944 Fußknoten. Hill: W3 Fuß T3/T4 z −0,67 / 1,33 mm, a_B,V 3,25 / 4,67 / 55,1, a_stat ∞ (54 / 614 / 1116 Fußknoten jenseits der Isotherme); W4 Fuß T2/T3 z 2,79 mm, h 0,46, a_B,V 2,45 / 3,01 / 3,55, a_stat 0,45 / 0,66 / ∞ (0 / 0 / 9); W1 Hill Fuß z 0,67 / 2,00 mm, 3,29 / 5,68 / (16 Nm siehe bericht). Auf dem Ring lag der kritische Knoten von W2 auf der Druckseite (R ≈ −0,4); der Steg des Taschenkörpers verschiebt die Lastgeschichte.

**Fußrundungsvarianten V2:** `fe_fillet_comparison.py` mit dem bionischen Optimum (φ 35°, r 0,2 S_L) als sechster Variante und dem neuen Ratenbild `fusseffekt_raten_LOAD_16NM`; bionisch φ35 an C: W1 −25,4 %, W2 −15,8 %, W3 −22,6 %, W4 −21,2 %; eben −38,1 % gegen 3D −23,8 % an B; CPRESS an B/E bis +47,8 %.

**Dehnrate im Betrieb (E4, k_slopes.py im Scratchpad):** Eingriffslinie 7,7 m/s bei 3000 1/min, Teilung 0,385 ms, Anstieg über ≈ 3,2 mm = 0,42 ms; W1 QS 2,6 bis 3,8 % → 62 bis 91 1/s (DY2-Modul 44 bis 70; 2250 1/min × 0,75). Neigungen k der Bruchlinie über der Spannung je Verfahren (Taschen-Pilot A bis E): W1 8,0 / W2 11,8 / W3 7,7 / W4 10,0 (QS), DY1 8,0 / 13,2 / 8,0 / 10,4, DY2 6,4 / 12,0 / 6,6 / 10,6; VDI 2736 4,30; RIKOR 5,75.
