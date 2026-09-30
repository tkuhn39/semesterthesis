# Größen, Formelzeichen und Benennungen

Erzeugt aus `20_code/10_gearcore/src/gearcore/data/quantities.yaml` mit
`scripts/build_quantities.py`; nicht von Hand ändern. Die Datei ist die einzige Quelle für
Programmnamen, Formelzeichen und Benennungen (Projektregel 3b, ADR-108).

Schreibweise: Indizes nach einem Unterstrich, griechische Buchstaben ausgeschrieben. Im
Formelsatz steht das Formelzeichen kursiv, jeder Index aufrecht.
Status `pending`: Die Größe steht im Datenvertrag, ihre Benennung ist noch nicht an der
Normseite geprüft; sie darf in keiner Rechnung verwendet werden.

## Was sich gegenüber der aktuellen Norm unterscheidet

Nur die Abweichungen; alle Zuordnungen stehen in den Abschnitten weiter unten. Wo ein
Zeichen hier nicht auftaucht, schreiben die ersetzte Norm und STplus dasselbe Zeichen wie
die aktuelle Norm.

### Geänderte Formelzeichen: ersetzte und ältere Normen

| Programmname | aktuell | früher | Benennung dort | Quelle |
|---|---|---|---|---|
| `centre_distance` | a_w | a | Achsabstand eines Stirnradpaares | DIN3960:1987, §2.1, p. 2 |
| `pitch` | p | t_0 | (no designation; figure 't_0 = m·pi' and table column t_0) | DIN3972:1952, p. 1 |
| `basic_rack_dedendum` | h_fP | h_fr | Fußhöhe | DIN3972:1952, p. 1, figure (h_fr at the 'Bezugsprofil des Zahnrades') and block above the table ('bei einer Fußhöhe von h_fr'); indices f = 'bezogen auf Zahnfuß', r = 'bezogen auf Zahnrad' |
| `tool_profile_angle` | alpha_P0 | alpha_0 | Eingriffswinkel | DIN3972:1952, p. 1, figure (alpha_0 = 20°); p. 2 |
| `tool_addendum` | h_aP0 | h_kw | Kopfhöhe | DIN3972:1952, p. 1, text ('Die Kopfhöhe ist für die Bezugsprofile I, II, III und IV ... angegeben'), figure and table head; indices k = 'bezogen auf Zahnkopf', w = 'bezogen auf Werkzeug' |
| `tool_tip_radius` | rho_aP0 | rho_a0 | Kopfkanten-Rundungshalbmesser am Werkzeug | DIN3960:1987, §2.1, p. 4 |
| `tool_tip_radius` | rho_aP0 | r_1 | Rundung am Zahnkopf des Werkzeugs | DIN3972:1952, p. 1, table column r_1 (= r_2) |
| `machining_allowance` | q | p | Bearbeitungszugabe je Flanke | DIN3972:1952, p. 1 legend; p. 2 |

### Abweichende Formelzeichen in STplus 11.1F

Der Stern am Zeichen (Modulfaktor) ist keine Abweichung.

| Programmname | aktuell | STplus | Beschriftung im Listing |
|---|---|---|---|
| `centre_distance` | a_w | a | Achsabstand |
| `contact_face_width` | b_w | b_gem | Gemeinsame Breite |
| `tool_profile_angle` | alpha_P0 | alfa_n0 | Wkz-Normaleingriffswinkel |
| `gear_ratio` | u | z2/z1 | Zaehnezahlverhaeltnis |
| `generated_root_diameter` | d_fE | d_f | Fusskreisdurchmesser |
| `length_of_path_of_contact` | g_alpha | g | Eingriffsstrecke |

Nur andere Schreibweise griechischer Buchstaben: alfa_n = alpha_n, alfa_t = alpha_t, alfa_wt = alpha_wt, eps_alfa = epsilon_alpha, eps_beta = epsilon_beta, eps_gamma = epsilon_gamma.

### Abweichende Formelzeichen in anderen aktuellen Dokumenten

| Programmname | maßgebend | dort | Benennung dort | Quelle |
|---|---|---|---|---|
| `centre_distance` | a_w | a | Centre distance | ISOTR6336-30:2022, Table 2, p. 2; Table A.1, p. 43 |
| `contact_face_width` | b_w | b_eff | Contact facewidth | ISOTR6336-30:2022, Table 2, p. 2 |
| `contact_face_width` | b_w | b | Contact facewidth | ISOTR6336-30:2022, Table A.1, p. 43 |
| `basic_rack_profile_angle` | alpha_P | alpha_Pn | normal pressure angle of the basic rack for cylindrical gears | ISO6336-1:2019, Table 2, p. 10 |
| `basic_rack_dedendum` | h_fP | h_fP/m_n | Basic rack dedendum coefficient | ISOTR6336-30:2022, Table 13, p. 30 |
| `basic_rack_fillet_radius` | rho_fP | rho_fP/m_n | Basic rack fillet root radius coefficient | ISOTR6336-30:2022, Table 13, p. 30 |
| `tool_tip_radius` | rho_aP0 | r_aP0 | (lettering of Bild 35, in contrast to the equations of the same norm) | ISO21771:2014, §7.1 Bild 35, p. 63 |
| `tool_tip_radius` | rho_aP0 | rho_a0 | tool tip corner rounding | ISO6336-3:2019, Table 2, p. 7 |
| `tool_tip_radius` | rho_aP0 | rho_a0 | (Wälzfräsergeometrie) | VDI2736-2:2014, Abschnitt 4, p. 21 |
| `generated_root_diameter` | d_fE | d_f | Root diameter (based on generating profile shift coefficient, x_E) | ISOTR6336-30:2022, A.6, p. 45 |
| `generated_root_diameter` | d_fE | d_f | root diameter | ISO6336-1:2019, Table 2, p. 4 |
| `tip_relief` | C_a | C_alpha_a | Betrag der Kopfrücknahme | ISO21771:2014, §3.1 symbol list, p. 14 |
| `root_relief` | C_f | C_alpha_f | Betrag der Fußrücknahme | ISO21771:2014, §3.1 symbol list, p. 14 |
| `rotation_speed` | n | n_1 | Pinion speed | ISOTR6336-30:2022, Table A.5, p. 45 |

### Gleiches Formelzeichen, andere Benennung in der ersetzten Norm

| Programmname | Zeichen | Benennung aktuell | Benennung früher | Quelle |
|---|---|---|---|---|
| `tip_chamfer_radial` | h_K | Radiale Höhe des Kopfkantenbruchs oder der Kopfkantenrundung | Radialbetrag des Kopfkantenbruchs oder der Kopfkantenrundung | DIN3960:1987, §2.1, p. 2 |
| `number_of_teeth_spanned` | k | Anzahl der Zähne, Lücken oder Teilungen in einem Bereich (z. B. Messzähnezahl) | Anzahl der Zähne oder Teilungen in einem Bereich | DIN3960:1987, §2.1, p. 3 |
| `number_of_teeth_spanned` | k | Anzahl der Zähne, Lücken oder Teilungen in einem Bereich (z. B. Messzähnezahl) | Meßzähnezahl (Meßlückenzahl) bei der Zahnweitenmessung | DIN3960:1987, §2.1, p. 3 |
| `transverse_tooth_thickness` | s_t | Zahndicke auf dem Teilzylinder im Stirnschnitt | Stirnzahndicke | DIN3960:1987, §3.5.8.1, Eq. (3.5.24), p. 12; §2.1, p. 3 lists s 'Zahndicke auf dem Teilzylinder' |
| `normal_tooth_thickness` | s_n | Zahndicke auf dem Teilzylinder im Normalschnitt | Normalzahndicken | DIN3960:1987, §3.5.8.5 (heading 'Normalzahndicken s_n, s_yn, s_vn und s_bn'), Eq. (3.5.44), p. 13 |
| `transverse_space_width` | e_t | Lückenweite auf dem Teilzylinder | Lückenweite | DIN3960:1987, §3.5.8.3, Eq. (3.5.33), p. 13; §2.1, p. 2 lists e 'Lückenweite auf dem Teilzylinder' |
| `normal_space_width` | e_n | Normallückenweite | Normallückenweiten | DIN3960:1987, §3.5.8.6 (heading 'Normallückenweiten e_n, e_yn, e_vn und e_bn'), p. 13 |
| `base_tooth_thickness_half_angle` | psi_b | Zahndicken-Halbwinkel am Grundkreis | Grunddicken-Halbwinkel | DIN3960:1987, §2.1, p. 5 |
| `base_space_width_half_angle` | eta_b | Zahnlücken-Halbwinkel am Grundkreis | Grundlücken-Halbwinkel | DIN3960:1987, §2.1, p. 4 |
| `transverse_profile_angle_at_y` | alpha_yt | Stirnprofilwinkel am Y-Zylinder | Stirnprofilwinkel | DIN3960:1987, §3.3.3, Eq. (3.3.02), p. 8; §2.1, p. 4 lists alpha_y 'Profilwinkel am Y-Zylinder' |
| `normal_profile_angle_at_y` | alpha_yn | Normalprofilwinkel am Y-Zylinder | Normalprofilwinkel | DIN3960:1987, §3.3.4, p. 8 |
| `involute_function` | inv | Involute- (Evolventen-)Funktion | Evolventenfunktion | DIN3960:1987, §2.1, p. 3 |
| `transverse_tooth_thickness_at_y` | s_yt | Zahndicke auf dem Y-Zylinder im Stirnschnitt | Stirnzahndicke | DIN3960:1987, §3.5.8.1, Eq. (3.5.25), p. 12; §2.1, p. 3 lists s_y 'Zahndicke auf dem Y-Zylinder' |
| `normal_tooth_thickness_at_y` | s_yn | Zahndicke auf dem Y-Zylinder im Normalschnitt | Normalzahndicken | DIN3960:1987, §3.5.8.5 (heading), Eq. (3.5.45), p. 13 |
| `transverse_space_width_at_y` | e_yt | Lückenweite auf dem Y-Zylinder | Lückenweite | DIN3960:1987, §3.5.8.3, Eq. (3.5.35), p. 13; §2.1, p. 2 lists e_y 'Lückenweite auf dem Y-Zylinder' |
| `normal_space_width_at_y` | e_yn | Normallückenweite | Normallückenweiten | DIN3960:1987, §3.5.8.6 (heading), p. 13 |
| `module` | m | Module | Modul (Durchmesserteilung) | DIN3960:1987, §2.1, p. 3 |
| `pitch` | p | Teilung, Teilung auf dem Teilzylinder | Teilung auf dem Teilzylinder | DIN3960:1987, §2.1, p. 3 |
| `basic_rack_profile_angle` | alpha_P | Profilwinkel des Bezugsprofils | Profilwinkel des Stirnrad-Bezugsprofils | DIN3960:1987, §2.1, p. 4 |
| `basic_rack_addendum` | h_aP | Kopfhöhe des Bezugsprofils | Kopfhöhe des Stirnrad-Bezugsprofils | DIN3960:1987, §2.1, p. 2 |
| `basic_rack_dedendum` | h_fP | Fußhöhe des Bezugsprofils | Fußhöhe des Stirnrad-Bezugsprofils | DIN3960:1987, §2.1, p. 2 |
| `basic_rack_fillet_radius` | rho_fP | Zahnfußradius am Bezugsprofil | Zahnfußradius am Stirnrad-Bezugsprofil | DIN3960:1987, §2.1, p. 4 |
| `basic_rack_root_form_height` | h_FfP | Fuß-Formhöhe des Bezugsprofils | Fuß-Formhöhe des Stirnrad-Bezugsprofils | DIN3960:1987, §2.1, p. 2 |
| `machining_allowance` | q | Bearbeitungszugabe auf der Zahnflanke | Bearbeitungszugabe auf den Stirnrad-Zahnflanken | DIN3960:1987, §2.1, p. 3 |
| `transverse_working_pressure_angle` | alpha_wt | Betriebseingriffswinkel des Radpaares | Betriebseingriffswinkel | DIN3960:1987, §2.1, p. 4 |
| `transverse_pitch` | p_t | Stirnteilung | Stirnteilung, Teilkreisteilung | DIN3960:1987, §2.1, p. 3 |
| `transverse_base_pitch` | p_bt | Teilung auf dem Grundzylinder im Stirnschnitt | Grundkreisteilung | DIN3960:1987, §3.4.5.1, Eq. (3.4.10), p. 10; §2.1, p. 3 lists p_b 'Teilung auf dem Grundzylinder' |
| `transverse_contact_pitch` | p_et | Eingriffsteilung im Stirnschnitt | Stirneingriffsteilung | DIN3960:1987, §3.4.6.1, p. 10; §2.1, p. 3 lists p_e 'Eingriffsteilung' |
| `length_of_path_of_contact` | g_alpha | Länge der Eingriffsstrecke | Länge der Eingriffsstrecke (gesamte) | DIN3960:1987, §2.1, p. 2 |
| `sap_diameter` | d_Nf | Fuß-Nutzkreisdurchmesser (SAP Durchmesser, nutzbarer Fußdurchmesser) | Fuß-Nutzkreisdurchmesser | DIN3960:1987, §2.1, p. 2 |

Noch nicht an der Normseite geprüft (`pending`), daher oben nicht aufgeführt: `tool_edge_break_angle`: alpha_K (DIN3960:1987) statt alpha_KP; `tool_protuberance_angle`: alfa_pr0 (STplus 11.1F) statt alpha_pr; `tooth_thickness_allowance`: E_sns (ISO21771:2014) statt E_sns/E_sni; `tooth_thickness_allowance`: E_sni (ISO21771:2014) statt E_sns/E_sni; `span_allowance`: A_We (STplus 11.1F) statt A_We/A_Wi; `quality_grade`: A (ISOTR6336-30:2022) statt Q; `min_tip_clearance`: c (ISO21771:2014) statt c_min.

## Aktuelle Norm

| Programmname | Zeichen | Einheit | Benennung der Norm | Quelle | Englische Benennung | seit | Status |
|---|---|---|---|---|---|---|---|
| `number_of_teeth` | z | - | Zähnezahl | ISO21771:2014, §3.1 symbol list, p. 14 | number of teeth (ISO6336-1:2019, Table 2, p. 10) | Inkrement 0 | verified |
| `normal_module` | m_n | mm | Normalmodul | ISO21771:2014, §3.1 symbol list, p. 12 | normal module (ISO6336-1:2019, Table 2, p. 8) | Inkrement 0 | verified |
| `normal_pressure_angle` | alpha_n | deg | Normaleingriffswinkel | ISO21771:2014, §3.1 symbol list, p. 15 | Normal pressure angle (ISOTR6336-30:2022, Table 2, p. 5) | Inkrement 0 | verified |
| `helix_angle` | beta | deg | Schrägungswinkel | ISO21771:2014, §3.1 symbol list, p. 16 | helix angle (without subscript, at reference cylinder) (ISO6336-1:2019, Table 2, p. 10) | Inkrement 0 | verified |
| `centre_distance` | a_w | mm | Achsabstand eines Zylinderradpaares | ISO21771:2014, §3.1 symbol list, p. 11 | Centre distance (ISOTR6336-30:2022, Table 2, p. 2) | Inkrement 0 | verified |
| `profile_shift_coefficient` | x | - | Profilverschiebungsfaktor | ISO21771:2014, §3.1 symbol list, p. 13 | profile shift coefficient (ISO6336-1:2019, Table 2, p. 9) | Inkrement 0 | verified |
| `face_width` | b | mm | Zahnbreite | ISO21771:2014, §3.1 symbol list, p. 11 | face width (ISO6336-1:2019, Table 2, p. 3) | Inkrement 0 | verified |
| `contact_face_width` | b_w | mm | wirksame Zahnbreite (genutzte Zahnbreite) | ISO21771:2014, §3.1 symbol list, p. 11 | Contact facewidth (ISOTR6336-30:2022, Table 2, p. 2) | Inkrement 1 | verified |
| `tip_diameter` | d_a | mm | Kopfkreisdurchmesser | ISO21771:2014, §3.1 symbol list, p. 11 | tip diameter (ISO6336-1:2019, Table 2, p. 4) | Inkrement 0 | verified |
| `tip_chamfer_radial` | h_K | mm | Radiale Höhe des Kopfkantenbruchs oder der Kopfkantenrundung | ISO21771:2014, §3.1 symbol list, p. 12 | Tip chamfer (ISOTR6336-30:2022, Table 2, p. 3) | Inkrement 0 | verified |
| `span_measurement` | W_k | mm | Zahnweite über k Messzähne oder Messlücken | ISO21771:2014, §3.1 symbol list, p. 15 | Span measurement (ISOTR6336-30:2022, Table 2, p. 4) | Inkrement 0 | verified |
| `number_of_teeth_spanned` | k | - | Anzahl der Zähne, Lücken oder Teilungen in einem Bereich (z. B. Messzähnezahl) | ISO21771:2014, §3.1 symbol list, p. 12 | Number of teeth spanned (ISOTR6336-30:2022, Table 2, p. 3) | Inkrement 0 | verified |
| `hand_of_helix` | – | - | Hand of helix | ISOTR6336-30:2022, Table A.1, p. 43 | Hand of helix (ISOTR6336-30:2022, Table A.1, p. 43) | Inkrement 1 | verified |
| `transverse_module` | m_t | mm | Stirnmodul | ISO21771:2014, §3.1 symbol list, p. 12 | Transverse module (ISOTR6336-30:2022, A.6, p. 45) | Inkrement 1 | verified |
| `transverse_pressure_angle` | alpha_t | deg | Stirneingriffswinkel | ISO21771:2014, §3.1 symbol list, p. 15 | transverse pressure angle (ISO6336-1:2019, Table 2, p. 10) | Inkrement 1 | verified |
| `base_helix_angle` | beta_b | deg | Grundschrägungswinkel | ISO21771:2014, §3.1 symbol list, p. 16 | base helix angle (ISO6336-1:2019, Table 2, p. 10) | Inkrement 1 | verified |
| `reference_diameter` | d | mm | Teilkreisdurchmesser | ISO21771:2014, §3.1 symbol list, p. 11 | diameter (without subscript, reference diameter) (ISO6336-1:2019, Table 2, p. 4) | Inkrement 1 | verified |
| `base_diameter` | d_b | mm | Grundkreisdurchmesser | ISO21771:2014, §3.1 symbol list, p. 11 | base diameter (ISO6336-1:2019, Table 2, p. 4) | Inkrement 1 | verified |
| `transverse_tooth_thickness` | s_t | mm | Zahndicke auf dem Teilzylinder im Stirnschnitt | ISO21771:2014, §3.1 symbol list, p. 13 | – | Inkrement 1 | verified |
| `normal_tooth_thickness` | s_n | mm | Zahndicke auf dem Teilzylinder im Normalschnitt | ISO21771:2014, §3.1 symbol list, p. 13 | – | Inkrement 1 | verified |
| `transverse_space_width` | e_t | mm | Lückenweite auf dem Teilzylinder | ISO21771:2014, §3.1 symbol list, p. 11 | – | Inkrement 1 | verified |
| `normal_space_width` | e_n | mm | Normallückenweite | ISO21771:2014, §4.7.6 (heading), Eq. (51) for the reference cylinder, p. 37 | – | Inkrement 1 | verified |
| `tooth_thickness_half_angle` | psi | deg | Zahndicken-Halbwinkel am Teilkreis | ISO21771:2014, §3.1 symbol list, p. 16 | – | Inkrement 1 | verified |
| `space_width_half_angle` | eta | deg | Zahnlücken-Halbwinkel am Teilkreis | ISO21771:2014, §3.1 symbol list, p. 16 | – | Inkrement 1 | verified |
| `base_tooth_thickness_half_angle` | psi_b | deg | Zahndicken-Halbwinkel am Grundkreis | ISO21771:2014, §3.1 symbol list, p. 16 | – | Inkrement 1 | verified |
| `base_space_width_half_angle` | eta_b | deg | Zahnlücken-Halbwinkel am Grundkreis | ISO21771:2014, §3.1 symbol list, p. 16 | – | Inkrement 1 | verified |
| `y_diameter` | d_y | mm | Y-Kreis-Durchmesser | ISO21771:2014, §3.1 symbol list, p. 11 | – | Inkrement 1 | verified |
| `helix_angle_at_y` | beta_y | deg | Schrägungswinkel auf dem Y-Zylinder | ISO21771:2014, §3.1 symbol list, p. 16 | – | Inkrement 1 | verified |
| `transverse_profile_angle_at_y` | alpha_yt | deg | Stirnprofilwinkel am Y-Zylinder | ISO21771:2014, §3.1 symbol list, p. 15 | – | Inkrement 1 | verified |
| `normal_profile_angle_at_y` | alpha_yn | deg | Normalprofilwinkel am Y-Zylinder | ISO21771:2014, §3.1 symbol list, p. 15 | – | Inkrement 1 | verified |
| `roll_angle` | xi_y | rad | Wälzwinkel der Evolvente im Punkt Y | ISO21771:2014, §3.1 symbol list, p. 16 | – | Inkrement 1 | verified |
| `radius_of_curvature` | rho_y | mm | Krümmungshalbmesser der Evolvente im Punkt Y | ISO21771:2014, §3.1 symbol list, p. 16 | – | Inkrement 1 | verified |
| `involute_function` | inv | rad | Involute- (Evolventen-)Funktion | ISO21771:2014, §3.1 symbol list, p. 12 | – | Inkrement 1 | verified |
| `tooth_thickness_half_angle_at_y` | psi_y | deg | Zahndicken-Halbwinkel am Y-Kreis | ISO21771:2014, §3.1 symbol list, p. 16 | – | Inkrement 1 | verified |
| `space_width_half_angle_at_y` | eta_y | deg | Zahnlücken-Halbwinkel am Y-Kreis | ISO21771:2014, §3.1 symbol list, p. 16 | – | Inkrement 1 | verified |
| `transverse_tooth_thickness_at_y` | s_yt | mm | Zahndicke auf dem Y-Zylinder im Stirnschnitt | ISO21771:2014, §3.1 symbol list, p. 13 | – | Inkrement 1 | verified |
| `normal_tooth_thickness_at_y` | s_yn | mm | Zahndicke auf dem Y-Zylinder im Normalschnitt | ISO21771:2014, §3.1 symbol list, p. 13 | – | Inkrement 1 | verified |
| `transverse_space_width_at_y` | e_yt | mm | Lückenweite auf dem Y-Zylinder | ISO21771:2014, §3.1 symbol list, p. 12 | – | Inkrement 1 | verified |
| `normal_space_width_at_y` | e_yn | mm | Normallückenweite | ISO21771:2014, §4.7.6 (heading), Eq. (50) for any cylinder, p. 37 | – | Inkrement 1 | verified |
| `module` | m | mm | Module | ISO53:1998, Table 1, p. 2 | Module (ISO53:1998, Table 1, p. 2) | Inkrement 1 | verified |
| `pitch` | p | mm | Teilung, Teilung auf dem Teilzylinder | ISO21771:2014, §3.1 symbol list, p. 13; Bild 4, p. 22 | Pitch (ISO53:1998, Table 1, p. 2) | Inkrement 1 | verified |
| `basic_rack_profile_angle` | alpha_P | deg | Profilwinkel des Bezugsprofils | ISO21771:2014, §3.1 symbol list, p. 15 | Pressure angle (ISO53:1998, Table 1, p. 2) | Inkrement 1 | verified |
| `basic_rack_addendum` | h_aP | mm | Kopfhöhe des Bezugsprofils | ISO21771:2014, §3.1 symbol list, p. 12; Bild 4, p. 22 | Addendum of standard basic rack tooth (ISO53:1998, Table 1, p. 2) | Inkrement 1 | verified |
| `basic_rack_dedendum` | h_fP | mm | Fußhöhe des Bezugsprofils | ISO21771:2014, §3.1 symbol list, p. 12; Bild 4, p. 22 | Dedendum of standard basic rack tooth (ISO53:1998, Table 1, p. 2) | Inkrement 1 | verified |
| `basic_rack_bottom_clearance` | c_P | mm | Kopfspiel zwischen Bezugsprofil und Gegenprofil | DIN867:1986, §2 table, p. 1; §4.3 and §4.4, p. 2 | Bottom clearance between standard basic rack tooth and mating standard basic rack tooth (ISO53:1998, Table 1, p. 2) | Inkrement 1 | verified |
| `basic_rack_fillet_radius` | rho_fP | mm | Zahnfußradius am Bezugsprofil | ISO21771:2014, §3.1 symbol list, p. 16; Bild 4, p. 22 | Fillet radius of the basic rack (ISO53:1998, Table 1, p. 2) | Inkrement 1 | verified |
| `basic_rack_root_form_height` | h_FfP | mm | Fuß-Formhöhe des Bezugsprofils | ISO21771:2014, §3.1 symbol list, p. 12; Bild 4, p. 22 | Straight portion of the standard basic rack tooth dedendum (ISO53:1998, Table 1, p. 2) | Inkrement 1 | verified |
| `tool_profile_angle` | alpha_P0 | deg | Profilwinkel des Bezugserzeugungsprofils | ISO21771:2014, §3.1 symbol list, p. 15 | – | Inkrement 0 | verified |
| `tool_addendum` | h_aP0 | mm | Kopfhöhe des Werkzeug-Bezugsprofils | ISO21771:2014, §3.1 symbol list, p. 12; §7.5 Eq. (125), p. 68 | addendum of tool (ISO6336-3:2019, Table 2, p. 3) | Inkrement 0 | verified |
| `tool_tip_radius` | rho_aP0 | mm | Kopfkantenrundungsradius des Werkzeug-Bezugsprofils | DIN867:1986, §2 table, p. 1; §4.4 and §4.5 Anmerkung, p. 2 | tool tip corner rounding (ISO6336-3:2019, Table 2, p. 7) | Inkrement 0 | verified |
| `tool_dedendum` | h_fP0 | mm | Fußhöhe des Werkzeug-Bezugsprofils | ISO21771:2014, §3.1 symbol list, p. 12 | – | Inkrement 0 | verified |
| `machining_allowance` | q | mm | Bearbeitungszugabe auf der Zahnflanke | ISO21771:2014, §3.1 symbol list, p. 13; §7.1 Bild 36 b), p. 64 | Material allowance for finishing (ISOTR6336-30:2022, Table 2, p. 4; Table A.1, p. 43) | Inkrement 0 | verified |
| `tool_normal_module` | m_n0 | mm | – | – | – | Inkrement 0 | pending |
| `tool_root_form_height` | h_FfP0 | mm | – | – | – | Inkrement 0 | pending |
| `tool_edge_break_angle` | alpha_KP | deg | – | – | – | Inkrement 0 | pending |
| `tool_protuberance` | pr | mm | – | – | – | Inkrement 0 | pending |
| `tool_protuberance_angle` | alpha_pr | deg | – | – | – | Inkrement 0 | pending |
| `gear_ratio` | u | - | Zähnezahlverhältnis | ISO21771:2014, §3.1 symbol list, p. 13 | gear ratio (z_2 / z_1) ≥ 1 (ISO6336-1:2019, Table 2, p. 9) | Inkrement 1 | verified |
| `transverse_working_pressure_angle` | alpha_wt | deg | Betriebseingriffswinkel des Radpaares | ISO21771:2014, §3.1 symbol list, p. 15 | Transverse working pressure angle (ISOTR6336-30:2022, Table 2, p. 5; A.6, p. 45) | Inkrement 1 | verified |
| `generating_profile_shift_coefficient` | x_E | - | Erzeugungs-Profilverschiebungsfaktor | ISO21771:2014, §3.1 symbol list, p. 13 | Generating profile shift coefficient (ISOTR6336-30:2022, Table 2, p. 4; A.6, p. 45) | Inkrement 1 | verified |
| `generated_root_diameter` | d_fE | mm | Erzeugter Fußkreisdurchmesser | ISO21771:2014, §3.1 symbol list, p. 11; §7.5 Eq. (125), p. 68 | Root diameter (based on x_E) (ISOTR6336-30:2022, Table 2, p. 2) | Inkrement 1 | verified |
| `root_form_diameter` | d_Ff | mm | Fuß-Formkreisdurchmesser | ISO21771:2014, §3.1 symbol list, p. 11; Eq. (128) in Anhang NB, p. 6 | Root form diameter (based on x_E) (ISOTR6336-30:2022, Table 2, p. 2) | Inkrement 1 | verified |
| `residual_fillet_undercut` | s_pr | mm | Residual fillet undercut, s_pr = pr - q | ISOTR6336-30:2022, Table 2, p. 4 | Residual fillet undercut, s_pr = pr - q (ISOTR6336-30:2022, Table 2, p. 4) | Inkrement 1 | verified |
| `tip_relief` | C_a | µm | Tip relief | ISOTR6336-30:2022, Table 2, p. 2 | tip relief (ISO6336-1:2019, Table 2, p. 4) | Inkrement 1 | verified |
| `root_relief` | C_f | µm | Root relief | ISOTR6336-30:2022, Table 2, p. 2 | root relief (ISO6336-1:2019, Table 2, p. 4) | Inkrement 1 | verified |
| `profile_modification_compensates_deflections` | – | - | Profile modification compensate for the deflections | ISOTR6336-30:2022, Table A.1, p. 43 | Profile modification compensate for the deflections (ISOTR6336-30:2022, Table A.1, p. 43) | Inkrement 1 | verified |
| `working_pitch_diameter` | d_w | mm | Wälzkreisdurchmesser | ISO21771:2014, §3.1 symbol list, p. 11 | Working pitch diameter (ISOTR6336-30:2022, Table 2, p. 2; A.6, p. 46) | Inkrement 1 | verified |
| `normal_pitch` | p_n | mm | Normalteilung | ISO21771:2014, §3.1 symbol list, p. 13 | Normal pitch (ISOTR6336-30:2022, A.6, p. 46) | Inkrement 1 | verified |
| `transverse_pitch` | p_t | mm | Stirnteilung | ISO21771:2014, §3.1 symbol list, p. 13 | Transverse pitch (ISOTR6336-30:2022, A.6, p. 46) | Inkrement 1 | verified |
| `transverse_base_pitch` | p_bt | mm | Teilung auf dem Grundzylinder im Stirnschnitt | ISO21771:2014, §3.1 symbol list, p. 13 | transverse pitch on the base cylinder (ISO6336-1:2019, Table 2, p. 8) | Inkrement 1 | verified |
| `transverse_contact_pitch` | p_et | mm | Eingriffsteilung im Stirnschnitt | ISO21771:2014, §3.1 symbol list, p. 13 | Transverse base pitch on the path of contact (ISOTR6336-30:2022, A.6, p. 46) | Inkrement 1 | verified |
| `length_of_path_of_contact` | g_alpha | mm | Länge der Eingriffsstrecke | ISO21771:2014, §3.1 symbol list, p. 12 | length of path of contact (ISO6336-1:2019, Table 2, p. 6) | Inkrement 1 | verified |
| `sap_diameter` | d_Nf | mm | Fuß-Nutzkreisdurchmesser (SAP Durchmesser, nutzbarer Fußdurchmesser) | ISO21771:2014, §3.1 symbol list, p. 11 | SAP diameter (ISOTR6336-30:2022, A.6, p. 46) | Inkrement 1 | verified |
| `transverse_contact_ratio` | epsilon_alpha | - | Profilüberdeckung | ISO21771:2014, §3.1 symbol list, p. 16 | transverse contact ratio (ISO6336-1:2019, Table 2, p. 11) | Inkrement 1 | verified |
| `overlap_ratio` | epsilon_beta | - | Sprungüberdeckung | ISO21771:2014, §3.1 symbol list, p. 16 | overlap ratio (ISO6336-1:2019, Table 2, p. 11) | Inkrement 1 | verified |
| `total_contact_ratio` | epsilon_gamma | - | Gesamtüberdeckung | ISO21771:2014, §3.1 symbol list, p. 16 | total contact ratio, epsilon_gamma = epsilon_alpha + epsilon_beta (ISO6336-1:2019, Table 2, p. 11) | Inkrement 1 | verified |
| `transverse_base_pitch_deviation` | f_pb | µm | Transverse base pitch deviation (the values of f_pT may be used for calculations in accordance with the ISO 6336 series, using tolerances according to ISO 1328-1:2013) | ISOTR6336-30:2022, Table 2, p. 3 | Transverse base pitch deviation (ISOTR6336-30:2022, A.6, p. 46) | Inkrement 1 | verified |
| `pitch_line_velocity` | v_w | m/s | Pitch line velocity | ISOTR6336-30:2022, Table 2, p. 4 | Pitch line velocity (ISOTR6336-30:2022, Table 2, p. 4; A.6, p. 46) | Inkrement 1 | verified |
| `circumferential_velocity` | v | m/s | Circumferential velocity at the reference cylinder | ISOTR6336-30:2022, Table 2, p. 4 | Circumferential velocity at the reference cylinder (ISOTR6336-30:2022, Table 2, p. 4) | Inkrement 1 | verified |
| `single_pitch_tolerance` | f_pT | µm | Single pitch tolerance (see ISO 1328-1:2013, ISO 6336 refers to f_pT as f_pt) | ISOTR6336-30:2022, Table 2, p. 3 | Single pitch tolerance (ISOTR6336-30:2022, Table A.2, p. 43) | Inkrement 1 | verified |
| `rotation_speed` | n | 1/min | Rotation speed of pinion (or wheel) | ISOTR6336-30:2022, Table 2, p. 4 | rotation speed of pinion (or wheel) (ISO6336-1:2019, Table 2, p. 8) | Inkrement 1 | verified |
| `tooth_thickness_allowance` | E_sns/E_sni | µm | – | – | – | Inkrement 0 | pending |
| `span_allowance` | A_We/A_Wi | µm | – | – | – | Inkrement 0 | pending |
| `quality_grade` | Q | - | – | – | – | Inkrement 0 | pending |
| `min_tip_clearance` | c_min | mm | – | – | – | Inkrement 0 | pending |

## STplus 11.1F

| Programmname | Zeichen der Norm | Zeichen im Listing | Beschriftung im Listing | Eingabe (.ste) | Schnittstelle (.sts) |
|---|---|---|---|---|---|
| `number_of_teeth` | z | z | Zaehnezahl | ZAEHNEZAHL | ZAEHNEZAHL |
| `normal_module` | m_n | m_n | Normalmodul | NORMALMODUL | NORMALMODUL |
| `normal_pressure_angle` | alpha_n | alfa_n | Normaleingriffswinkel | EINGRIFFSWINKEL | NORMALEINGRIFFSWINKEL |
| `helix_angle` | beta | beta | Schraegungswinkel am Teilkreis | SCHRAEGUNGSWINKEL | SCHRAEGUNGSWINKEL_TEILK |
| `centre_distance` | a_w | a | Achsabstand | ACHSABSTAND | ACHSABSTAND |
| `profile_shift_coefficient` | x | x | Profilverschiebungsfaktor (Nennw.) | PROFILVERSCHIEBUNG_N | PROFILVERSCHIEBFAKTOR |
| `face_width` | b | b | Zahnbreite (eine Pfeilhaelfte bei DSV) | ZAHNBREITE | ZAHNBREITE |
| `contact_face_width` | b_w | b_gem | Gemeinsame Breite | – | GEMEINSAME_BREITE |
| `tip_diameter` | d_a | d_a | Kopfkreisdurchmesser | KOPFKREISDM | KOPFKREISDURCHM |
| `tip_chamfer_radial` | h_K | h_K | Kopfkantenbruch (Radialbetrag) | KOPFKANTENBRUCH | KOPFKANTENBRUCH |
| `span_measurement` | W_k | W_k | Zahnweite (Nennmass) | ZAHNWEITE | ZAHNWEITE |
| `number_of_teeth_spanned` | k | k | Messzaehnezahl | MESSZAEHNEZAHL | MESSZAEHNEZAHL |
| `transverse_module` | m_t | m_t | Stirnmodul | – | STIRNMODUL |
| `transverse_pressure_angle` | alpha_t | alfa_t | Stirneingriffswinkel | – | STIRNEINGRIFFSWINKEL |
| `base_helix_angle` | beta_b | beta_b | Schraegungswinkel am Grundkreis | – | SCHRAEGUNGSWINKEL_GRUND |
| `reference_diameter` | d | d | Teilkreisdurchmesser | – | TEILKREISDURCHM |
| `base_diameter` | d_b | d_b | Grundkreisdurchmesser | – | GRUNDKREISDURCHM |
| `transverse_tooth_thickness` | s_t | s_t | Zahndicke (Nennmass, Stirnschn.) | – | ZAHNDICKE_STIRNSCHNITT |
| `normal_tooth_thickness` | s_n | s_n | Zahndicke (Nennmass, Normalschn.) | – | ZAHNDICKE_NORMAL |
| `normal_space_width` | e_n | e_n | Zahnlueckenweite (Normalschnitt) | – | ZAHNLUECKE_NORMAL |
| `basic_rack_addendum` | h_aP | h_aP* | Bezugspr.-Kopfhoehenfaktor (Istw.) | – | BEZPR_KOPFHOEHENFAKTOR |
| `tool_profile_angle` | alpha_P0 | alfa_n0 | Wkz-Normaleingriffswinkel | WKZ_EINGRIFFSWINKEL | WKZ_NORMALEINGRWINKEL |
| `tool_addendum` | h_aP0 | h_aP0* | Kopfhoehenfaktor (Wkz_Bezugspr.) | KOPFHOEHENFAKTOR | WKZ_KOPFHOEHENFAKTOR |
| `tool_tip_radius` | rho_aP0 | rho_aP0* | Wkz-Kopfabrundungsfaktor | KOPFABRUNDUNGSFAKTOR | WKZ_KOPFABRUNDUNGSF |
| `tool_dedendum` | h_fP0 | h_fP0* | Fuss-Hoehenfaktor (Wkz-Bezugspr.) | FUSSHOEHENFAKTOR | WKZ_FUSSHOEHENF |
| `machining_allowance` | q | q | Gesamt-Bearbeitungszugabe | BEARB_ZUGABE_WKZ | BEARBEITUNGSZUGABE |
| `tool_normal_module` | m_n0 | m_n0 | Wkz-Normalmodul | WKZ_NORMALMODUL | WKZ_NORMALMODUL |
| `tool_root_form_height` | h_FfP0 | h_FfP0* | Fussform-Hoehenf.(Wkz-Bezugspr.) | FUSSFORMHOEHENFAKTOR | WKZ_FUSSFORMHOEHENF |
| `tool_edge_break_angle` | alpha_KP | – | – | KANTENBRECHWINKEL | – |
| `tool_protuberance` | pr | – | – | PROTUBERANZBETRAG | PROTUBERANZBETRAG |
| `tool_protuberance_angle` | alpha_pr | alfa_pr0 | Protuberanzwinkel | PROTUBERANZWINKEL | PROTUBERANZWINKEL |
| `gear_ratio` | u | z2/z1 | Zaehnezahlverhaeltnis | ZAEHNEZAHLVERHAELTNIS | ZAEHNEZAHLVERHAELTNIS |
| `transverse_working_pressure_angle` | alpha_wt | alfa_wt | Betriebseingriffswinkel | – | BETRIEBSEINGRIFFSWINKEL |
| `generating_profile_shift_coefficient` | x_E | x_E | Erz.-Profilversch.faktor | – | ERZ_PROFILVERSCHFAKTOR |
| `generated_root_diameter` | d_fE | d_f | Fusskreisdurchmesser | – | FUSSKREISDURCHM |
| `root_form_diameter` | d_Ff | d_Ff | Fuss-Formkreisdurchmesser | – | FUSSFORMKREISDURCHM |
| `working_pitch_diameter` | d_w | d_w | Waelzkreisdurchmesser | – | WAELZKREISDURCHM |
| `normal_pitch` | p_n | p_n | Normalteilung | – | NORMALTEILUNG |
| `transverse_pitch` | p_t | p_t | Stirnteilung | – | STIRNTEILUNG |
| `transverse_contact_pitch` | p_et | p_et | Stirneingriffsteilung | – | STIRNEINGRTEILUNG |
| `length_of_path_of_contact` | g_alpha | g | Eingriffsstrecke | – | EINGRIFFSSTRECKE |
| `sap_diameter` | d_Nf | d_Nf | Nutzkreisdurchmesser am Fuss | – | NUTZKREISDURCHM_FUSS |
| `transverse_contact_ratio` | epsilon_alpha | eps_alfa | Profilueberdeckung | – | PROFILUEBERDECKUNG |
| `overlap_ratio` | epsilon_beta | eps_beta | Sprungueberdeckung | – | SPRUNGUEBERDECKUNG |
| `total_contact_ratio` | epsilon_gamma | eps_gamma | Gesamtueberdeckung | – | GESAMTUEBERDECKUNG |
| `span_allowance` | A_We/A_Wi | A_We | – | OBERES_ZAHNW_ABMASS | OBERES_ZAHNWEITENABM |
| `quality_grade` | Q | – | – | DIN_QUALITAET | – |

## Ersetzte und ältere Normen

| Programmname | Zeichen der Norm | Zeichen dort | Benennung dort | Quelle |
|---|---|---|---|---|
| `number_of_teeth` | z | z | Zähnezahl | DIN3960:1987, §2.1, p. 3 |
| `normal_module` | m_n | m_n | Normalmodul | DIN3960:1987, §2.1, p. 3 |
| `normal_pressure_angle` | alpha_n | alpha_n | Normaleingriffswinkel | DIN3960:1987, §2.1, p. 4 |
| `helix_angle` | beta | beta | Schrägungswinkel | DIN3960:1987, §2.1, p. 4 |
| `centre_distance` | a_w | a | Achsabstand eines Stirnradpaares | DIN3960:1987, §2.1, p. 2 |
| `profile_shift_coefficient` | x | x | Profilverschiebungsfaktor | DIN3960:1987, §2.1, p. 3 |
| `face_width` | b | b | Zahnbreite | DIN3960:1987, §2.1, p. 2 |
| `tip_diameter` | d_a | d_a | Kopfkreisdurchmesser | DIN3960:1987, §2.1, p. 2 |
| `tip_chamfer_radial` | h_K | h_K | Radialbetrag des Kopfkantenbruchs oder der Kopfkantenrundung | DIN3960:1987, §2.1, p. 2 |
| `span_measurement` | W_k | W_k | Zahnweite über k Meßzähne oder Meßlücken | DIN3960:1987, §2.1, p. 4 |
| `number_of_teeth_spanned` | k | k | Anzahl der Zähne oder Teilungen in einem Bereich | DIN3960:1987, §2.1, p. 3 |
| `number_of_teeth_spanned` | k | k | Meßzähnezahl (Meßlückenzahl) bei der Zahnweitenmessung | DIN3960:1987, §2.1, p. 3 |
| `transverse_module` | m_t | m_t | Stirnmodul | DIN3960:1987, §2.1, p. 3 |
| `transverse_pressure_angle` | alpha_t | alpha_t | Stirneingriffswinkel | DIN3960:1987, §2.1, p. 4 |
| `base_helix_angle` | beta_b | beta_b | Grundschrägungswinkel | DIN3960:1987, §2.1, p. 4 |
| `reference_diameter` | d | d | Teilkreisdurchmesser | DIN3960:1987, §2.1, p. 2 |
| `base_diameter` | d_b | d_b | Grundkreisdurchmesser | DIN3960:1987, §2.1, p. 2 |
| `transverse_tooth_thickness` | s_t | s_t | Stirnzahndicke | DIN3960:1987, §3.5.8.1, Eq. (3.5.24), p. 12; §2.1, p. 3 lists s 'Zahndicke auf dem Teilzylinder' |
| `normal_tooth_thickness` | s_n | s_n | Normalzahndicken | DIN3960:1987, §3.5.8.5 (heading 'Normalzahndicken s_n, s_yn, s_vn und s_bn'), Eq. (3.5.44), p. 13 |
| `transverse_space_width` | e_t | e_t | Lückenweite | DIN3960:1987, §3.5.8.3, Eq. (3.5.33), p. 13; §2.1, p. 2 lists e 'Lückenweite auf dem Teilzylinder' |
| `normal_space_width` | e_n | e_n | Normallückenweiten | DIN3960:1987, §3.5.8.6 (heading 'Normallückenweiten e_n, e_yn, e_vn und e_bn'), p. 13 |
| `tooth_thickness_half_angle` | psi | psi | Zahndicken-Halbwinkel am Teilkreis | DIN3960:1987, §2.1, p. 5 |
| `space_width_half_angle` | eta | eta | Zahnlücken-Halbwinkel am Teilkreis | DIN3960:1987, §2.1, p. 4 |
| `base_tooth_thickness_half_angle` | psi_b | psi_b | Grunddicken-Halbwinkel | DIN3960:1987, §2.1, p. 5 |
| `base_space_width_half_angle` | eta_b | eta_b | Grundlücken-Halbwinkel | DIN3960:1987, §2.1, p. 4 |
| `y_diameter` | d_y | d_y | Y-Kreis-Durchmesser | DIN3960:1987, §2.1, p. 2 |
| `helix_angle_at_y` | beta_y | beta_y | Schrägungswinkel auf dem Y-Zylinder | DIN3960:1987, §2.1, p. 4 |
| `transverse_profile_angle_at_y` | alpha_yt | alpha_yt | Stirnprofilwinkel | DIN3960:1987, §3.3.3, Eq. (3.3.02), p. 8; §2.1, p. 4 lists alpha_y 'Profilwinkel am Y-Zylinder' |
| `normal_profile_angle_at_y` | alpha_yn | alpha_yn | Normalprofilwinkel | DIN3960:1987, §3.3.4, p. 8 |
| `roll_angle` | xi_y | xi_y | Wälzwinkel der Evolvente im Punkt Y | DIN3960:1987, §2.1, p. 4 |
| `radius_of_curvature` | rho_y | rho_y | Krümmungshalbmesser der Evolvente im Punkt Y | DIN3960:1987, §2.1, p. 4 |
| `involute_function` | inv | inv | Evolventenfunktion | DIN3960:1987, §2.1, p. 3 |
| `tooth_thickness_half_angle_at_y` | psi_y | psi_y | Zahndicken-Halbwinkel am Y-Kreis | DIN3960:1987, §2.1, p. 5 |
| `space_width_half_angle_at_y` | eta_y | eta_y | Zahnlücken-Halbwinkel am Y-Kreis | DIN3960:1987, §2.1, p. 4 |
| `transverse_tooth_thickness_at_y` | s_yt | s_yt | Stirnzahndicke | DIN3960:1987, §3.5.8.1, Eq. (3.5.25), p. 12; §2.1, p. 3 lists s_y 'Zahndicke auf dem Y-Zylinder' |
| `normal_tooth_thickness_at_y` | s_yn | s_yn | Normalzahndicken | DIN3960:1987, §3.5.8.5 (heading), Eq. (3.5.45), p. 13 |
| `transverse_space_width_at_y` | e_yt | e_yt | Lückenweite | DIN3960:1987, §3.5.8.3, Eq. (3.5.35), p. 13; §2.1, p. 2 lists e_y 'Lückenweite auf dem Y-Zylinder' |
| `normal_space_width_at_y` | e_yn | e_yn | Normallückenweiten | DIN3960:1987, §3.5.8.6 (heading), p. 13 |
| `module` | m | m | Modul (Durchmesserteilung) | DIN3960:1987, §2.1, p. 3 |
| `pitch` | p | p | Teilung auf dem Teilzylinder | DIN3960:1987, §2.1, p. 3 |
| `pitch` | p | t_0 | (no designation; figure 't_0 = m·pi' and table column t_0) | DIN3972:1952, p. 1 |
| `basic_rack_profile_angle` | alpha_P | alpha_P | Profilwinkel des Stirnrad-Bezugsprofils | DIN3960:1987, §2.1, p. 4 |
| `basic_rack_addendum` | h_aP | h_aP | Kopfhöhe des Stirnrad-Bezugsprofils | DIN3960:1987, §2.1, p. 2 |
| `basic_rack_dedendum` | h_fP | h_fP | Fußhöhe des Stirnrad-Bezugsprofils | DIN3960:1987, §2.1, p. 2 |
| `basic_rack_dedendum` | h_fP | h_fr | Fußhöhe | DIN3972:1952, p. 1, figure (h_fr at the 'Bezugsprofil des Zahnrades') and block above the table ('bei einer Fußhöhe von h_fr'); indices f = 'bezogen auf Zahnfuß', r = 'bezogen auf Zahnrad' |
| `basic_rack_bottom_clearance` | c_P | c_P | Kopfspiel zwischen Bezugsprofil und Gegenprofil | DIN3960:1987, §2.1, p. 2 |
| `basic_rack_fillet_radius` | rho_fP | rho_fP | Zahnfußradius am Stirnrad-Bezugsprofil | DIN3960:1987, §2.1, p. 4 |
| `basic_rack_root_form_height` | h_FfP | h_FfP | Fuß-Formhöhe des Stirnrad-Bezugsprofils | DIN3960:1987, §2.1, p. 2 |
| `tool_profile_angle` | alpha_P0 | alpha_0 | Eingriffswinkel | DIN3972:1952, p. 1, figure (alpha_0 = 20°); p. 2 |
| `tool_addendum` | h_aP0 | h_aP0 | Kopfhöhe des Werkzeug-Bezugsprofils | DIN3960:1987, §2.1, p. 2 |
| `tool_addendum` | h_aP0 | h_kw | Kopfhöhe | DIN3972:1952, p. 1, text ('Die Kopfhöhe ist für die Bezugsprofile I, II, III und IV ... angegeben'), figure and table head; indices k = 'bezogen auf Zahnkopf', w = 'bezogen auf Werkzeug' |
| `tool_tip_radius` | rho_aP0 | rho_a0 | Kopfkanten-Rundungshalbmesser am Werkzeug | DIN3960:1987, §2.1, p. 4 |
| `tool_tip_radius` | rho_aP0 | r_1 | Rundung am Zahnkopf des Werkzeugs | DIN3972:1952, p. 1, table column r_1 (= r_2) |
| `tool_dedendum` | h_fP0 | h_fP0 | Fußhöhe des Werkzeug-Bezugsprofils | DIN3960:1987, §2.1, p. 2 |
| `machining_allowance` | q | q | Bearbeitungszugabe auf den Stirnrad-Zahnflanken | DIN3960:1987, §2.1, p. 3 |
| `machining_allowance` | q | p | Bearbeitungszugabe je Flanke | DIN3972:1952, p. 1 legend; p. 2 |
| `tool_root_form_height` | h_FfP0 | h_FfP0 | Fuß-Formhöhe des Werkzeug-Bezugsprofils | DIN3960:1987, §2.1, p. 2 |
| `tool_edge_break_angle` | alpha_KP | alpha_K | Profilwinkel der Kantenbruchflanke | DIN3960:1987, §2.1, p. 4 |
| `tool_protuberance` | pr | pr | Protuberanzbetrag | DIN3960:1987, §2.1, p. 3 |
| `tool_protuberance_angle` | alpha_pr | alpha_pr | Protuberanz-Profilwinkel | DIN3960:1987, §2.1, p. 4 |
| `gear_ratio` | u | u | Zähnezahlverhältnis | DIN3960:1987, §2.1, p. 3 |
| `transverse_working_pressure_angle` | alpha_wt | alpha_wt | Betriebseingriffswinkel | DIN3960:1987, §2.1, p. 4 |
| `generating_profile_shift_coefficient` | x_E | x_E | Erzeugungs-Profilverschiebungsfaktor | DIN3960:1987, §2.1, p. 3 |
| `generated_root_diameter` | d_fE | d_fE | Erzeugter Fußkreisdurchmesser | DIN3960:1987, §2.1, p. 2 |
| `root_form_diameter` | d_Ff | d_Ff | Fuß-Formkreisdurchmesser | DIN3960:1987, §2.1, p. 2 |
| `working_pitch_diameter` | d_w | d_w | Wälzkreisdurchmesser | DIN3960:1987, §2.1, p. 2 |
| `normal_pitch` | p_n | p_n | Normalteilung | DIN3960:1987, §2.1, p. 3 |
| `transverse_pitch` | p_t | p_t | Stirnteilung, Teilkreisteilung | DIN3960:1987, §2.1, p. 3 |
| `transverse_base_pitch` | p_bt | p_bt | Grundkreisteilung | DIN3960:1987, §3.4.5.1, Eq. (3.4.10), p. 10; §2.1, p. 3 lists p_b 'Teilung auf dem Grundzylinder' |
| `transverse_contact_pitch` | p_et | p_et | Stirneingriffsteilung | DIN3960:1987, §3.4.6.1, p. 10; §2.1, p. 3 lists p_e 'Eingriffsteilung' |
| `length_of_path_of_contact` | g_alpha | g_alpha | Länge der Eingriffsstrecke (gesamte) | DIN3960:1987, §2.1, p. 2 |
| `sap_diameter` | d_Nf | d_Nf | Fuß-Nutzkreisdurchmesser | DIN3960:1987, §2.1, p. 2 |
| `transverse_contact_ratio` | epsilon_alpha | epsilon_alpha | Profilüberdeckung | DIN3960:1987, §2.1, p. 4 |
| `overlap_ratio` | epsilon_beta | epsilon_beta | Sprungüberdeckung | DIN3960:1987, §2.1, p. 4 |
| `total_contact_ratio` | epsilon_gamma | epsilon_gamma | Gesamtüberdeckung | DIN3960:1987, §2.1, p. 4 |

## Andere aktuelle Dokumente

| Programmname | Zeichen der Norm | Zeichen dort | Benennung dort | Quelle |
|---|---|---|---|---|
| `centre_distance` | a_w | a | Centre distance | ISOTR6336-30:2022, Table 2, p. 2; Table A.1, p. 43 |
| `profile_shift_coefficient` | x | x | Nominal profile shift coefficient | ISOTR6336-30:2022, Table 2, p. 4 |
| `profile_shift_coefficient` | x | x | Nominal addendum correction factor | ISOTR6336-30:2022, Table A.1, p. 43 |
| `face_width` | b | b | Facewidth (total facewidth if double helical) | ISOTR6336-30:2022, Table 2, p. 2 |
| `contact_face_width` | b_w | b_eff | Contact facewidth | ISOTR6336-30:2022, Table 2, p. 2 |
| `contact_face_width` | b_w | b | Contact facewidth | ISOTR6336-30:2022, Table A.1, p. 43 |
| `contact_face_width` | b_w | b_w | gemeinsame Zahnbreite | VDI2736-2:2014, Abschnitt 4 (Ausgangsdaten), p. 21 |
| `reference_diameter` | d | d | Reference diameter | ISOTR6336-30:2022, Table 2, p. 2 |
| `base_diameter` | d_b | d_b | Base circle diameter | ISOTR6336-30:2022, Table 2, p. 2 |
| `involute_function` | inv | inv alpha_n | Involute normal pressure angle | ISOTR6336-30:2022, A.6, p. 45 |
| `involute_function` | inv | inv alpha_t | Transverse pressure angle | ISOTR6336-30:2022, A.6, p. 45, second formula of the row |
| `module` | m | m | Modul | DIN867:1986, §2 table, p. 1 |
| `pitch` | p | p | Teilung | DIN867:1986, §2 table, p. 1 |
| `basic_rack_profile_angle` | alpha_P | alpha_Pn | normal pressure angle of the basic rack for cylindrical gears | ISO6336-1:2019, Table 2, p. 10 |
| `basic_rack_addendum` | h_aP | h_aP | addendum of basic rack of cylindrical gears | ISO6336-3:2019, Table 2, p. 3 |
| `basic_rack_dedendum` | h_fP | h_fP | Basic rack dedendum | ISOTR6336-30:2022, Table 2, p. 3; Table A.1, p. 43 |
| `basic_rack_dedendum` | h_fP | h_fP | dedendum of basic rack of cylindrical gears (ISO 53:1998 shall apply) | ISO6336-3:2019, Table 2, p. 3 |
| `basic_rack_dedendum` | h_fP | h_fP/m_n | Basic rack dedendum coefficient | ISOTR6336-30:2022, Table 13, p. 30 |
| `basic_rack_fillet_radius` | rho_fP | rho_fP | Fußrundungsradius des Bezugsprofils | DIN867:1986, §2 table, p. 1; §4.5, p. 2 |
| `basic_rack_fillet_radius` | rho_fP | rho_fP | tooth root fillet radius of the basic rack for cylindrical gears | ISO6336-3:2019, Table 2, p. 7 |
| `basic_rack_fillet_radius` | rho_fP | rho_fP | Root fillet radius of the basic rack for cylindrical gears | ISOTR6336-30:2022, Table 2, p. 5 |
| `basic_rack_fillet_radius` | rho_fP | rho_fP | Basic rack fillet root radius | ISOTR6336-30:2022, Table A.1, p. 43 |
| `basic_rack_fillet_radius` | rho_fP | rho_fP/m_n | Basic rack fillet root radius coefficient | ISOTR6336-30:2022, Table 13, p. 30 |
| `tool_tip_radius` | rho_aP0 | rho_aP0 | (used in Eq. (128) of the normative Anhang NB and in Eq. (130), without designation) | ISO21771:2014, Anhang NB, p. 6; §7.6, p. 69 |
| `tool_tip_radius` | rho_aP0 | r_aP0 | (lettering of Bild 35, in contrast to the equations of the same norm) | ISO21771:2014, §7.1 Bild 35, p. 63 |
| `tool_tip_radius` | rho_aP0 | rho_aP0 | (used as a length in the formula of d_Ff, without designation) | ISOTR6336-30:2022, A.6, p. 45 |
| `tool_tip_radius` | rho_aP0 | rho_a0 | tool tip corner rounding | ISO6336-3:2019, Table 2, p. 7 |
| `tool_tip_radius` | rho_aP0 | rho_a0 | (Wälzfräsergeometrie) | VDI2736-2:2014, Abschnitt 4, p. 21 |
| `machining_allowance` | q | q | material allowance for finish machining per flank | ISO6336-3:2019, Table 2, p. 4 |
| `tool_root_form_height` | h_FfP0 | h_FfP0 | (lettering of Bild 36 a), without designation) | ISO21771:2014, §7.1 Bild 36 a), p. 64 |
| `tool_edge_break_angle` | alpha_KP | alpha_KP | (lettering of Bild 36 a), without designation) | ISO21771:2014, §7.1 Bild 36 a), p. 64 |
| `tool_protuberance` | pr | pr | As cut basic rack undercut | ISOTR6336-30:2022, Table 2, p. 4 |
| `gear_ratio` | u | u | Gear ratio | ISOTR6336-30:2022, A.6, p. 45 |
| `transverse_working_pressure_angle` | alpha_wt | alpha_wt | working transverse pressure angle at the pitch cylinder | ISO6336-1:2019, Table 2, p. 10 |
| `generated_root_diameter` | d_fE | d_f | Root diameter (based on generating profile shift coefficient, x_E) | ISOTR6336-30:2022, A.6, p. 45 |
| `generated_root_diameter` | d_fE | d_f | root diameter | ISO6336-1:2019, Table 2, p. 4 |
| `residual_fillet_undercut` | s_pr | s_pr | residual fillet undercut, s_pr = pr - q | ISO6336-3:2019, Table 2, p. 4 |
| `tip_relief` | C_a | C_alpha_a | Betrag der Kopfrücknahme | ISO21771:2014, §3.1 symbol list, p. 14 |
| `root_relief` | C_f | C_alpha_f | Betrag der Fußrücknahme | ISO21771:2014, §3.1 symbol list, p. 14 |
| `working_pitch_diameter` | d_w | d_w | pitch diameter | ISO6336-1:2019, Table 2, p. 5 |
| `transverse_base_pitch` | p_bt | p_bt | Transverse base pitch | ISOTR6336-30:2022, A.6, p. 46 |
| `transverse_contact_pitch` | p_et | p_et | transverse base pitch on the path of conctact | ISO6336-1:2019, Table 2, p. 8 (spelling as printed) |
| `length_of_path_of_contact` | g_alpha | g_alpha | Length of line of contact | ISOTR6336-30:2022, A.6, p. 46 |
| `sap_diameter` | d_Nf | d_Nf | Start of active profile diameter | ISOTR6336-30:2022, Table 2, p. 2 |
| `transverse_base_pitch_deviation` | f_pb | f_pb | transverse base pitch deviation (the values of f_pt may be used for calculations in accordance with the ISO 6336 series, using tolerances complying with ISO 1328-1:2013) | ISO6336-1:2019, Table 2, p. 6 |
| `circumferential_velocity` | v | v | Circumferential velocity at the reference circle (see ISO 6336-1:2019, 4.2.2) | ISOTR6336-30:2022, A.6, p. 46 |
| `circumferential_velocity` | v | v | circumferential velocity (without subscript at the reference circle) | ISO6336-1:2019, Table 2, p. 9 |
| `rotation_speed` | n | n_1 | Pinion speed | ISOTR6336-30:2022, Table A.5, p. 45 |
| `rotation_speed` | n | n | rotational speed | ISO6336-1:2019, Table 2, p. 8 |
| `tooth_thickness_allowance` | E_sns/E_sni | E_sns | oberes Zahndickengrenzabmaß | ISO21771:2014, §3.1 symbol list, p. 14 |
| `tooth_thickness_allowance` | E_sns/E_sni | E_sni | unteres Zahndickengrenzabmaß | ISO21771:2014, §3.1 symbol list, p. 14 |
| `quality_grade` | Q | A | Flank tolerance class | ISOTR6336-30:2022, Table 2, p. 2; Table A.2, p. 43 |
| `min_tip_clearance` | c_min | c | Kopfspiel | ISO21771:2014, §3.1 symbol list, p. 11; §5.2.7, p. 41 |

## Hinweise

- `helix_angle` (beta): STplus sign: positive = pinion right-hand; the interface file prints the hand of each gear as a sign.
- `centre_distance` (a_w): Symbol changed from a (DIN 3960, STplus) to a_w. ISO/TR 6336-30:2022 prints a in its tables and in the formulas of d_Nf (A.6, p. 46), a_w in the formulas of alpha_wt (A.6, p. 45) and g_alpha (p. 46). A given centre distance is fixed (ADR-107).
- `profile_shift_coefficient` (x): ISO/TR 6336-30:2022 names the same quantity differently in Table 2 and in Table A.1. Table A.1 prints x_1 in parentheses; clause 4.2.18 (p. 9): 'Values in the input table (e.g. nominal profile shift coefficient x) are put in parenthesis when they are calculated and for reference only.' x_2 = 0 and the centre distance are given, x_1 follows from them (ADR-107).
- `contact_face_width` (b_w): ISO/TR 6336-30:2022 lists b_eff in Table 2 and prints b in Table A.1. Used from increment 2 on.
- `tip_chamfer_radial` (h_K): The program name keeps 'radial' of the German designation; ISO/TR 6336-30 says 'Tip chamfer' only.
- `span_measurement` (W_k): Inspection dimensions are governed by DIN 21773:2014-08 (increment 4); the entry is reviewed there.
- `number_of_teeth_spanned` (k): STplus has a second key MESSZAEHNEZAHL_K for the span used as a check dimension.
- `hand_of_helix` (–): No symbol. gearcore carries the hand in the sign of beta; it enters with the pair geometry (increment 2).
- `base_helix_angle` (beta_b): The listing prints the magnitude, the interface file the sign of each gear.
- `transverse_tooth_thickness` (s_t): Signed value of Eq. (39); see BasicGearGeometry. Same symbol as in DIN 3960, which writes s for a spur gear.
- `normal_tooth_thickness` (s_n): Signed value of Eq. (49). Same symbol as in DIN 3960.
- `transverse_space_width` (e_t): Signed value of Eq. (44). STplus prints the normal space width only. Same symbol as in DIN 3960, which writes e for a spur gear.
- `normal_space_width` (e_n): Not in the symbol list §3.1 of DIN ISO 21771; the designation is taken from §4.7.6.
- `base_space_width_half_angle` (eta_b): Signed (Eq. (47)). Negative when the two involutes that bound a tooth space meet above the base circle; for x = 0, alpha_n = 20°, beta = 0 from z = 106 on. The root circle of such a gear lies above that point.
- `transverse_profile_angle_at_y` (alpha_yt): DIN ISO 21771 distinguishes the pressure angle (Eingriffswinkel, at the reference cylinder) from the profile angle (Profilwinkel, at any cylinder).
- `involute_function` (inv): ISO/TR 6336-30 names inv alpha_n and lists inv alpha_t in the row 'Transverse pressure angle'.
- `normal_space_width_at_y` (e_yn): Not in the symbol list §3.1 of DIN ISO 21771; the designation is taken from §4.7.6.
- `module` (m): Module of the basic rack; DIN ISO 21771 lists m_n, m_t and m_x only.
- `basic_rack_profile_angle` (alpha_P): ISO 53 says 'pressure angle'; the program name follows 'Profilwinkel' of DIN ISO 21771.
- `basic_rack_addendum` (h_aP): The STplus row is an actual value ('Istw.'), not an input of the basic rack: it equals (d_a - d) / (2 m_n) - x and contains the tip alteration (kst_c_rerun prints 0.88761 and 0.75096, neg_shift_z17_xm08 1.00000 and 0.26148).
- `basic_rack_dedendum` (h_fP): DIN 3972 p. 2 uses h_fr also for the dedendum a gear gets by a larger infeed ('Zahnfußhöhe h_fr, die größer als 1,25 · m ist'), which is a dedendum of the gear, not of the basic rack.
- `basic_rack_bottom_clearance` (c_P): Not in the symbol list of DIN ISO 21771 (which lists c, the tip clearance of a gear pair).
- `tool_profile_angle` (alpha_P0): None in the contract = profile angle of the gear.
- `tool_addendum` (h_aP0): The contract holds the module factor h_aP0* (Anhang NB of DIN ISO 21771, p. 6: * marks a module factor). STplus manual Bild 4.174 (p. 185): 'Kopfhöhenfaktor d. Wkz-Bez-profils h_aP0*'.
- `tool_tip_radius` (rho_aP0): DIN ISO 21771 uses rho_aP0 in its equations but names it nowhere; the designation comes from DIN 867. ISO 6336-3:2019 lists the quantity as rho_a0. ISO/TR 6336-30:2022 uses the symbol in two senses: as this length in the formula of d_Ff (A.6, p. 45) and as the dimensionless 'Pinion cutter tip radius coefficient' (Table 2, p. 5; input of example 6, Table 13, p. 30). The program name translates the German designation. The STplus manual writes ro_aP0* (Bild 4.174, p. 185), the listing rho_aP0*.
- `tool_dedendum` (h_fP0): STplus manual Bild 4.174 (p. 185): 'Fußhöhenfaktor d. Wkz-Bez.profils h_fP0*'.
- `machining_allowance` (q): The program name translates 'Bearbeitungszugabe'; ISO/TR 6336-30 words it differently. STplus has two inputs: BEARBEITUNGSZUGABE ('Bearbeitungzugabe q', geometry data, manual Bild 4.8, p. 20), applied in addition to the allowance contained in the tool (p. 184), and BEARB_ZUGABE_WKZ ('Werkzeuginterne Bearbeitungszugabe', tool data, Bild 4.174, p. 185); the listing prints the total. The contract field of the tool reads BEARB_ZUGABE_WKZ; BEARBEITUNGSZUGABE is reported as unmapped key until the generation (increment 3) implements q. No fixture contains either key, the listed total is 0 in all 15 listings.
- `tool_normal_module` (m_n0): Symbol as STplus prints it; no symbol of a current norm verified yet. None in the contract = normal module of the gear.
- `tool_root_form_height` (h_FfP0): Designation of the current norm to be verified with the generation (increment 3).
- `tool_edge_break_angle` (alpha_KP): STplus manual Bild 4.174 (p. 185): 'Kantenbrechwinkel d. Wkz-Bez.profils alfa_Kn0'. To be verified with the generation (increment 3).
- `tool_protuberance` (pr): Extension point (protuberance flank). STplus manual Bild 4.174 (p. 185): 'Protuberanzbetrag pr_n0'.
- `tool_protuberance_angle` (alpha_pr): Extension point (protuberance flank); symbol of DIN 3960 until a current norm is verified.
- `gear_ratio` (u): Implemented in increment 2. The input key is documented in the STplus manual (Bild 4.3, p. 15; Bild 4.12, p. 25) and occurs in no fixture.
- `transverse_working_pressure_angle` (alpha_wt): Implemented in increment 2.
- `generating_profile_shift_coefficient` (x_E): Implemented in increment 3.
- `generated_root_diameter` (d_fE): DIN ISO 21771 separates d_f (Fußkreisdurchmesser, Nennmaß) from d_fE (generated with x_E). ISO/TR 6336-30 and STplus print d_f for the generated value; ISO 6336-1:2019 lists d_f 'root diameter' without saying which of the two it is. Implemented in increment 3.
- `root_form_diameter` (d_Ff): Implemented in increment 3.
- `residual_fillet_undercut` (s_pr): Quantity of the load capacity norms (ISO 6336-3); DIN ISO 21771 does not list it. Table A.1 prints the label in lower case.
- `tip_relief` (C_a): Flank modification, used by the load capacity (stage 2). DIN ISO 21771 writes C with the indices alpha and a.
- `root_relief` (C_f): Flank modification, used by the load capacity (stage 2).
- `profile_modification_compensates_deflections` (–): Yes/no statement of the worked example, used by the load capacity (stage 2).
- `working_pitch_diameter` (d_w): Implemented in increment 2.
- `normal_pitch` (p_n): Implemented in increment 2.
- `transverse_pitch` (p_t): Implemented in increment 2.
- `transverse_base_pitch` (p_bt): Implemented in increment 2.
- `transverse_contact_pitch` (p_et): The English designation has eight words; the program name shortens it. Implemented in increment 2.
- `length_of_path_of_contact` (g_alpha): ISO/TR 6336-30 says 'line of contact' where ISO 6336-1 says 'path of contact'. Implemented in increment 2.
- `sap_diameter` (d_Nf): Implemented in increment 2.
- `transverse_contact_ratio` (epsilon_alpha): Implemented in increment 2.
- `overlap_ratio` (epsilon_beta): Implemented in increment 2.
- `total_contact_ratio` (epsilon_gamma): Implemented in increment 2.
- `transverse_base_pitch_deviation` (f_pb): Quantity of the load capacity (stage 2).
- `pitch_line_velocity` (v_w): Quantity of the load capacity (stage 2).
- `circumferential_velocity` (v): Quantity of the load capacity (stage 2).
- `single_pitch_tolerance` (f_pT): Quantity of the tolerances (increment 5) and of the load capacity (stage 2).
- `rotation_speed` (n): Quantity of the load capacity (stage 2); Table 2 of both documents prints the symbol as n_1,2; the registry writes a symbol without the index of the gear. ISO 6336-1:2019 has a second row n 'rotational speed'. The documents print the unit as min^-1.
- `tooth_thickness_allowance` (E_sns/E_sni): Pair of upper and lower allowance; governed by DIN 3967:1978-08 and DIN 21773:2014-08, verified in increment 5.
- `span_allowance` (A_We/A_Wi): Symbols as STplus prints them (DIN 3967 notation); the current symbols are verified in increment 5.
- `quality_grade` (Q): Verified in increment 5 (DIN ISO 1328-1:2018-03).
- `min_tip_clearance` (c_min): Input of a tip diameter check (STplus MINDESTKOPFSPIEL); verified in increment 2.
