# Normenlandkarte Stirnräder (gerad- und schrägverzahnt, Außenverzahnung)

Stand 2026-09-30, verifiziert aus den Norm-PDFs in `00_literatur/05_normen_und_richtlinien/`.
Pflege: bei jeder Änderung der Berechnungsbasis (ADR) aktualisieren. Gleichungsebene der Unterschiede:
`data/stplus/expected_differences.yaml`; die Darstellung `norm_differences.md` wird daraus mit
Inkrement 6 erzeugt.

## Zuordnung STplus (DIN 3960-Kette) → aktuelle Normen

| Thema | STplus 11.1F verwendet | Status | Berechnungsbasis in `gearcore` | Rechenbeispiel als Referenz |
|---|---|---|---|---|
| Begriffe/Geometrie | DIN 3960:1987-03 | zurückgezogen (Nachfolger laut Normkopf) | **DIN ISO 21771:2014-08** (ISO 21771:2007): §4 Einzelräder, §5 Zylinderradpaare, §7 Geometrische Grenzen (7.1 Werkzeug-Bezugsprofil, 7.2 Bearbeitungszugabe, 7.3 Zahndickenabmaße, 7.4 x_E, 7.5 d_f, 7.6 Formkreise, 7.7 Unterschnitt, 7.9 Mindestkopfdicke). Nationales Vorwort verwirft Anhang A; Anhang NB korrigiert Gl. (56), (57), (128) | keins → STplus-Orakel, ISO/TR 6336-30-Geometriewerte |
| Abweichungsdefinitionen | DIN 3960 §6–8 | zurückgezogen | DIN 21772:2012-07 → ersetzt durch **DIN ISO 1328-1:2018-03** | – |
| Prüfmaße | DIN 3960 §3.8 | zurückgezogen | **DIN 21773:2014-08**: §5 Sehne, §6 konstante Sehne, §7 Zahnweite (7.2 Messzähnezahl), §8–11 Kugel/Rolle, §12 Zweiflankenwälz-Achsabstand, §14 Abmaße | keins → STplus-Orakel |
| Bezugsprofil / Werkzeug | Werkzeugfaktoren (h_aP0*, ρ_aP0*, h_FfP0*, pr₀, α_K0) | gültig | **DIN 867:1986-02**, **ISO 53:1998**, **DIN 3972:1952-02** (Profile I–IV), Modulreihe ISO 54:1996 | – |
| Zahndickenabmaße / Flankenspiel | DIN 3967:1978-08 (Reihen z. B. C25) | gültig | DIN 3967:1978-08 | Text-/Anhangsbeispiele; kst-B C25 |
| Achsabstandsabmaße | DIN 3964:1980-11 (js5…js11) | gültig | DIN 3964:1980-11 | Tabellen; STplus-qualidefs als Gegenprobe |
| Verzahnungsqualität | DIN 3961/62/63:1978 (Tabellen, in STplus als XML) | zurückgezogen | **DIN ISO 1328-1:2018-03** (Formeln, Stufensprung √2), **DIN ISO 1328-2:2021-09** | 1328-2 Anhang E |
| Tragfähigkeit Flanke/Fuß | DIN 3990-1…-5:1987; ISO 6336:1996/2006/2019 | DIN gültig; international ISO | ISO 6336-1/-2/-3/-6:2019, -5:2016, ISO/TS 6336-4:2019 (Etappe 2) | ISO/TR 6336-30:2022 (8 Beispiele), ISO 6336-6 Anhang C, DIN 3990-11/-21 Anhang B |
| Fressen | DIN 3990-4:1987; ISO/TR 13989:2000 | TR zurückgezogen | ISO/TS 6336-20/-21:2022 (Etappe 2) | 6336-21 Anhang A |
| Graufleckigkeit | ISO/TR 15144-1:2010 | zurückgezogen | ISO/TS 6336-22:2018-08 (Etappe 2) | – |
| Kunststoff | nicht in STplus | – | VDI 2736 Bl. 1–4 (2014/2016), Bl. 2 Tab. 1/2/5/6 (Etappe 2) | Bl. 2 Anhang A |
| Ohne aktuelle Norm | Lewis-Parabel, K*/U-Faktor, FVA-166-Verluste, CCS 1996 | – | bewusst weggelassen (ADR-105) | – |

## Unterschiede in den Berechnungsansätzen (Planebene)

- **Struktur:** DIN 3960 bündelt Begriffe, Erzeugung (§3.6, Anhang A), Prüfmaße (§3.8) und Abweichungen
  (§6–8). ISO 21771 enthält nur Begriffe/Bestimmungsgrößen und Erzeugung (§7); Prüfmaße → DIN 21773,
  Abweichungen → DIN ISO 1328-1. Symbolwechsel: Abmaß A → E, Zahndickensehne s̄_n → s_cn,
  Flankenspiel j_t/j_n → j_wt/j_bn.
- **Nenn- vs. erzeugte Verzahnung:** STplus meldet die real vom Werkzeug erzeugte Verzahnung
  (d_f = d + 2·m_n·(x_E − h_aP0*), Formkreise, Kopfkantenbruch); DIN 3960/ISO 21771 formulieren Teile nur
  für die Nennverzahnung.
- **Toleranzen:** DIN 3962 tabelliert (1978), DIN ISO 1328-1 formelbasiert mit Stufensprung √2.
- **Fußausrundung:** keine Norm gibt die Trochoide geschlossen an; Hüllkurve der Werkzeug-Kopfrundung aus
  der Wälzkinematik (Linke 2010; FVA 604 I). Die geschlossene d_Ff-Form (ISO 21771 Gl. (128) NB /
  DIN 3960 Gl. 3.6.08) gilt nicht bei Unterschnitt.
- **Kein Kunststoff in STplus:** VDI 2736 ist eine eigene, nicht in STplus abgebildete Kette.
- **Alte Symbolik in DIN 3972:1952:** Die Norm schreibt h_kw (Kopfhöhe des Werkzeugs), h_fr (Fußhöhe des
  Zahnrades), h_w (Zahnhöhe des Werkzeugs), r₁ (Rundung am Zahnkopf des Werkzeugs) und r₂. In heutiger
  Schreibweise (DIN ISO 21771:2014-08 §7.1, Bild 35) entspricht h_kw der Kopfhöhe des
  Werkzeug-Bezugsprofils h_aP0 und r₁ dem Kopfrundungsradius des Werkzeug-Bezugsprofils. Die Rundung ist
  **tabelliert** (Spalte „r₂ ≈ 0,2 m“: 0,08 bei m = 1 bis 0,2·m ab etwa m = 2,5) und r₁ wird gleich r₂
  ausgeführt; „0,2·m“ ist also nur ein Näherungswert und darf nicht als Formel implementiert werden.

## Befunde aus Inkrement 1 (2026-09-29)

- **Fußrundungsradius des Bezugsprofils:** DIN 867:1986-02 Gl. (7)/(8) und ISO 53:1998 Gl. (2)/(3)
  geben dieselben beiden Obergrenzen für ρ_fP an (Kopfspiel-Bedingung und Vollrundung); `gearcore`
  führt sie als eine Funktion mit beiden Quellenangaben. Bei α_P = 20° wechselt die maßgebende
  Grenze bei c_P = 0,295·m. ISO 53 gibt Gl. (3) für 0,295·m < c_P ≤ 0,396·m an; DIN 867 Gl. (8) hat
  keine obere Grenze und deckt auch ISO 53 Typ D (c_P = 0,4·m) ab.
- **Gedruckte Fußrundungsradien:** Die Normen drucken zwei Nachkommastellen. Zwei gedruckte
  Wertepaare überschreiten dadurch die Grenze: c_P = 0,25·m mit ρ_fP = 0,38·m (Grenze 0,37995·m;
  ISO 53 Typ A, DIN 867) und c_P = 0,3·m mit ρ_fP = 0,45·m (Grenze 0,44592·m; DIN 867,
  Erläuterungen S. 3). `gearcore` prüft die Grenze ohne Toleranz und lässt genau diese beiden Paare
  zu. Ein weiterer Wert der Tabelle von DIN 867 weicht von der Formel ab: für c_P = 0,17·m ist
  0,25·m gedruckt, Gl. (7) ergibt 0,2584·m.
- **Kopfspiel:** DIN 867:1986-02 §4.4 nennt 0,1·m bis 0,4·m als üblich („im allgemeinen“), nicht als
  Grenze; Bild 2 reicht bis 0,5·m. `gearcore` meldet ein Kopfspiel außerhalb des üblichen Bereichs
  als Hinweis.
- **Formelzeichen der Werkzeug-Kopfrundung:** `gearcore` verwendet ρ_aP0. Übersicht der aktuellen
  Normen (gerenderte Seiten, 2026-09-29):

  | Norm | Zeichen | Fundstelle |
  |---|---|---|
  | DIN ISO 21771:2014-08 | ρ_aP0 | Gl. (128) im normativen Anhang NB (S. 6), Gl. (128) und (130) (S. 69) |
  | DIN ISO 21771:2014-08 | r_aP0 | nur Beschriftung in Bild 35 (S. 63); in der Symbolliste §3.1 fehlt das Zeichen |
  | ISO/TR 6336-30:2022 | ρ_aP0 | A.6 (S. 45, Länge in der Gleichung für d_Ff); Table 2 (S. 5) benennt dasselbe Zeichen als dimensionslosen „Pinion cutter tip radius coefficient“ |
  | DIN 867:1986-02 | ρ_aP0 | §2, §4.4, §4.5 („Kopfkantenrundungsradius des Werkzeug-Bezugsprofils“) |
  | ISO 6336-3:2019 | ρ_a0 | Table 2 (S. 7, „tool tip corner rounding“) |
  | VDI 2736 Blatt 2:2014-06 | ρ_a0 | Abschnitt 4 (S. 21, Wälzfräsergeometrie) |
  | STplus 11.1F | ro_aP0 | Programmanleitung Bild 4.174 (S. 185), Eingabe `KOPFABRUNDUNGSFAKTOR` |

  Maßgebend ist die neueste Geometrienorm (DIN ISO 21771:2014-08 mit Anhang NB). α_P0 heißt dort
  „Profilwinkel des Bezugserzeugungsprofils“ (§3.1, S. 15).
- **Übersetzung STplus → aktuelle Norm:** Die Formelzeichen des STplus-Listings und der
  Werkzeugeingabe sind je Größe in der Registry `data/quantities.yaml` zugeordnet, Tabelle in `quantities.md`
  (α_t, β_b, m_t, d, d_b, s_t, s_n, e_n, x, h_aP0*, ρ_aP0*). Die Zeichen stimmen überein; STplus
  schreibt griechische Buchstaben aus (alfa_t, ro_aP0). e_n steht in DIN ISO 21771 nur in §4.7.6,
  nicht in der Symbolliste.
- **Formelzeichen DIN 3960 → DIN ISO 21771:** Für die Größen im Stirn- und Normalschnitt sind die
  Zeichen gleich geblieben (s_t, s_n, e_t, e_n, s_yt, s_yn, e_yt, e_yn, p_bt, p_et, α_yt, α_yn;
  DIN 3960 §3.3.3, §3.3.4, §3.4.5, §3.4.6, §3.5.8). Die Liste §2.1 der DIN 3960 führt sie ohne
  Schnittindex (s, e, p_b, p_e, α_y); die Abschnitte nennen diese Kurzform für Geradstirnräder.
  Geändert haben sich a → a_w und ϱ_a0 → ρ_aP0 (α_K → α_KP ist noch nicht verifiziert).
- **Bearbeitungszugabe in STplus:** zwei Eingaben, `BEARBEITUNGSZUGABE` (q, Geometriedaten,
  Anleitung Bild 4.8, S. 20) zusätzlich zur werkzeuginternen `BEARB_ZUGABE_WKZ` (Bild 4.174,
  S. 185); das Listing druckt die Summe als „Gesamt-Bearbeitungszugabe“. Der „Bezugspr.-
  Kopfhoehenfaktor (Istw.)“ des Listings ist ein Istwert, (d_a − d) / (2·m_n) − x, und enthält die
  Kopfhöhenänderung.
- **Modulreihe:** ISO 54:1996 Tabelle 1 beginnt bei Modul 1 mm. Kleinere Moduln (Kunststoff-Feinwerk­technik,
  z. B. m_n = 0,5) liegen außerhalb der Reihe und werden als Hinweis gemeldet, nicht abgelehnt.
- **Tabelle und Formeln in DIN 3972:1952-02:** Von den 152 Tabellenwerten für h_kw I–IV, p III und
  p IV entsprechen 146 dem korrekt gerundeten Wert der Formel derselben Norm (S. 1 und 2). Sechs
  Werte weichen um mehr als eine halbe Einheit der letzten Stelle ab:

  | Modul | Spalte | gedruckt | Formelwert |
  |---|---|---|---|
  | 1,5 | p IV | 0,24 | 0,2349 |
  | 2 | h_kw III | 2,82 | 2,8150 |
  | 3,5 | h_kw IV | 5,28 | 5,2860 |
  | 3,75 | h_kw IV | 5,63 | 5,6197 |
  | 4,5 | h_kw IV | 6,60 | 6,6156 |
  | 5,5 | h_kw IV | 7,92 | 7,9341 |

  Größte Abweichung 0,016 mm (Modul 4,5). `gearcore` rechnet mit den Formeln; die sechs
  Abweichungen sind im Test `test_din3972_formulas_reproduce_the_table` einzeln festgehalten, alle
  anderen Werte werden auf halbe Einheit der letzten Stelle geprüft.
- **Rechengenauigkeit von STplus:** STplus rechnet mit einfacher Genauigkeit (32 Bit, etwa sieben
  signifikante Stellen), `gearcore` durchgängig mit doppelter Genauigkeit (64 Bit). Das Listing druckt
  Längen mit drei Nachkommastellen, dort ist das unsichtbar; in der Schnittstellendatei mit fünf
  Nachkommastellen weichen einzelne Werte der schrägverzahnten Läufe um eine Einheit der letzten
  Stelle ab (größte Abweichung 0,014 µm bei d = 345,86 mm). Das ist kein Normunterschied, sondern
  eine Eigenschaft des Zahlenformats; Nachweis und Vergleichsregel in ADR-106.
- **Vorzeichen der Zahndicke am Teilzylinder:** DIN ISO 21771 Gl. (39), (41), (44), (46), (49), (51)
  liefern für |x| > π / (4·tan α_n) eine negative Zahndicke oder Lückenweite am Teilzylinder
  (ab α_n = 21,4° innerhalb von |x| ≤ 2). Das Rad kann trotzdem herstellbar sein, der Teilzylinder
  liegt dann außerhalb der Verzahnung. `gearcore` gibt den Formelwert mit Vorzeichen zurück und
  meldet den Fall als Hinweis.
- **Werkzeugprofil im Stirnschnitt:** Die Umrechnung des Werkzeug-Bezugsprofils vom Normal- in den
  Stirnschnitt (Kopfrundung wird zur Ellipse) gehört zur Erzeugung; umgesetzt in Inkrement 3
  (`trochoid.py`, Befunde unten).

## Befunde aus Inkrement 2 (2026-09-30)

- **Gemeinsame Zahnhöhe (bewusste Abweichung von der Norm, ADR-112):** DIN ISO 21771:2014-08 §5.2.6
  Gl. (59), S. 41, und DIN 3960:1987-03 §4.2.6 Gl. (4.2.08), S. 31, definieren
  h_w = (d_a1 + d_a2) / 2 − a mit den Kopfkreisen. STplus setzt in dieselbe Formel die
  Kopf-Formkreise ein, (d_Fa1 + d_Fa2) / 2 − a (kst-B: 2,918 mm statt 3,205 mm; mit eingegebenem
  Kantenbruch an beiden Rädern, Referenzfall `chamfer_hk_z20_34`: 3,522 mm statt 4,022 mm); das
  Handbuch sagt es nicht, der Vergleich hat es gezeigt. Beide Normen sagen dasselbe, der Unterschied
  ist eine Eigenschaft des Programms. Nach Entscheidung des Nutzers (2026-09-30) rechnet `gearcore`
  ebenfalls mit den Kopf-Formkreisen: Auf dem Kopfkantenbruch trägt der Zahn nicht (vgl. DIN ISO
  21771 §6.1.2, S. 55: Kopfkantenbruch und Kopfkantenrundung schränken den nutzbaren Bereich der
  Zahnflanke ein). Wo beide Werte verschieden sind, nennt das Ergebnis den Wert nach dem Wortlaut
  der Norm als Hinweis; der Eintrag steht in `data/stplus/expected_differences.yaml` unter
  `deviations_from_the_norm`.
- **Gleichungsnummern:** Die Nummer (61) kommt in DIN ISO 21771:2014-08 nicht vor; unter (60) stehen
  zwei Formeln (Kopfspiel c_1 und c_2), darauf folgt (62).
- **Zahnbreite in der Sprungüberdeckung:** Gl. (93) schreibt b, der Sprung-Überdeckungswinkel in
  Gl. (91) ist mit der genutzten Zahnbreite b_w definiert. `gearcore` rechnet mit b_w und setzt ohne
  Angabe eines Mittenversatzes b_w = min(b_1, b_2).
- **Gleitfaktoren je Rad:** Die Norm gibt K_ga (Gl. (113), Punkt E) und K_gf (Gl. (112), Punkt A) für
  das treibende Ritzel an. STplus druckt beide als „Gleitfaktor am Zahnkopf“ je Rad; der Wert des
  Rades ist das K_gf der Norm. `gearcore` führt die Größen ebenfalls je Rad und nennt die Gleichung.
- **Formelzeichen der Kopfeingriffsstrecke:** DIN 3960:1987-03 schreibt im Abschnitt selbst g_a
  (Gl. (4.4.13), S. 35), wie DIN ISO 21771; g_αa steht nur in der Zeichenliste §2.1 und im
  STplus-Listing. Das Zeichen hat sich also nicht geändert (Korrektur nach dem Gate).
- **Kopfhöhenänderungsfaktor:** DIN 3960:1987-03 schreibt k* für den Faktor und k für die
  Kopfhöhenänderung als Länge (§4.3.6 Gl. (4.3.07), (4.3.08), S. 32); DIN ISO 21771 schreibt k für
  den Faktor (§4.5.2, S. 34).
- **Formübermaß:** STplus druckt c_F (Gl. (76)) im Listing unter dem Zeichen c_n.
- **Korrektur im Anhang NB:** Anhang NB (S. 6) korrigiert die erste Form von Gl. (56) und (57). Der
  mittlere Term der korrigierten Gleichungen ist dort als cos α_t / cos α_wt ohne den Faktor d_1
  bzw. d_2 gedruckt. `gearcore` verwendet die letzte Form d_w = d_b / cos α_wt.
- **Zahnweite und Profilverschiebung (offen):** Zahnweite und Profilverschiebungsfaktor bestimmen
  einander: DIN 21773:2014-08 §7.2 Gl. (14), S. 13, W_k = m_n·cos α_n·[π·(k − 0,5) + z·inv α_t] +
  2·x·m_n·sin α_n, mit dem Profilverschiebungsfaktor bzw. dem Erzeugungs-Profilverschiebungsfaktor.
  Eine Zahnweite mit Zahndickenabmaß entspricht x_E (DIN ISO 21771:2014-08 §7.4 Gl. (123), (124),
  S. 67). ISO/TR 6336-30:2022 Anhang A Beispiel 1 berechnet aus W_k1 = 38,196 mm (Tabelle A.1,
  S. 43) x_E1 = 0,117 79 (S. 45); der Nennwert desselben Rades ist x_1 = (0,145 22). Wie eine
  eingegebene Zahnweite zu behandeln ist und wie STplus das handhabt, wird mit den Prüfmaßen und
  Abmaßen (Inkremente 4 und 5) geklärt und vom Nutzer bestätigt; bis dahin wertet `gearcore` keine
  Zahnweite aus (ADR-107, PAIR-06).
- **Beginn der aktiven Flanke auf dem Grundkreis:** Das spezifische Gleiten nach Gl. (116), (117)
  ist dort unbeschränkt; `gearcore` bricht mit einer Meldung ab, wenn d_Nf ≤ d_b·(1 + 10⁻¹²) ist
  (ADR-110).
- **Überbestimmte Eingabe:** STplus behält bei gegebenem a, x_1 und x_2 den Wert x_1 und leitet x_2
  ab, ohne es zu melden. `gearcore` lässt nur zwei der drei Werte zu (ADR-107). Sind a und nur x_2
  gegeben, leitet STplus x_1 ab wie `gearcore` (Referenzfall `a_x2_only_z18_45`).
- **Rechenbeispiel:** ISO/TR 6336-30:2022 Anhang A Beispiel 1 gibt a und x_2 = 0 an; das in Klammern
  gedruckte x_1 = 0,145 22 (Abschnitt 4.2.18, S. 9: berechnet, nur zur Information) wird von
  `gearcore` aus a und x_2 reproduziert (0,145 222 1).

## Befunde aus Inkrement 3 (2026-09-30)

- **Gl. (130) gegen Anhang NB:** Anhang NB (S. 6) korrigiert Gl. (128) auf (1 − sin α_n) in der
  Klammer, Gl. (130) (S. 69) druckt (1 − sin α_t) und wird nicht korrigiert. Für Geradverzahnung sind
  beide gleich; für das schrägverzahnte Beispiel 1 der ISO/TR 6336-30:2022 (β = 15,8°, x_E1 = 0,117 79)
  liefert Gl. (128) NB den gedruckten Wert d_Ff1 = 132,248 mm (S. 45), Gl. (130) wie gedruckt
  132,243 mm. Die Höhe des Übergangs von der Werkzeug-Kopfrundung zur geraden Flanke ist eine Höhe im
  Normalschnitt und bleibt im Stirnschnitt gleich (FVA 604 I, S. 29). `gearcore` rechnet nach Anhang
  NB; Gl. (130) ist als Gegenprobe implementiert (`root_form_diameter_by_roll_angle`).
- **Kopf-Formkreis bei Kantenbrechflanke:** DIN ISO 21771 nennt in §7.6 nur d_Fa = d_a − 2 h_K
  (Gl. (127)); die Erzeugung des Kantenbruchs durch die Kantenbrechflanke des Werkzeugs (Bild 36 a),
  α_kP ab h_FfP0) steht in DIN 3960:1987-03 Anhang A.3.1, Gl. (A.3.03), (A.3.05), (A.3.06), S. 52.
  `gearcore` zitiert die zurückgezogene Norm für diese Lücke (Regel 3, gekennzeichnet). Bild 36 a)
  schreibt den Winkel mit kleinem k (α_kP, 600 dpi geprüft); DIN 3960 schreibt α_K (§2.1) und α_KP0
  (Anhang A).
- **Zahndickenabmaß bei STplus:** STplus druckt A_ste/A_sti („oberes/unteres Zahndickenabmass“,
  OBERES/UNTERES_ZAHNDICKENABM) als **Stirnschnittwert** E_sns / cos β (DIN 3967 Anhang A, S. 7, nennt
  A_ste so), obwohl DIN 3967 das Passsystem im Normalschnitt festlegt (§1, S. 1): helix30_z25_40
  druckt −0,098 mm, wo die Reihe c25 für d = 86,6 mm −0,085 mm nennt (fzg_c, gleiche Reihe und
  Durchmesserstufe: −0,085). Mit dem Normalschnittwert reproduziert Gl. (123) das von STplus gedruckte
  x_E genau; der Vergleich rechnet die gedruckten Werte um.
- **Fuß-Formkreis bei STplus:** STplus wertet Gl. (128) nicht aus. Sein d_Ff ist der numerische
  Übergang seiner Fußkurve in seine Evolvente: in allen 14 eigenen Konturexporten ist d_Ff / 2 der
  Radius eines eigens gesetzten, doppelten Konturpunkts (Abstand ≤ 4·10⁻⁵ mm), während die Kurven
  selbst mit `gearcore` auf 0,6 µm übereinstimmen. Gegen Gl. (128) NB bzw. den exakten Schnittpunkt
  (Unterschnitt) weicht der gedruckte Wert um bis zu 6,4 µm ab (fzg_c Ritzel; Schnittwinkel 4,1°:
  0,23 µm Normalabstand der Kurven werden zu 6 µm im Durchmesser). Der Vergleich räumt dem
  STplus-Wert 0,007 mm ein (`parity.FORM_CIRCLE_ACCURACY_MM`, halb für c_F und h_K); die gemessenen
  Maxima sind gepinnt (`test_stplus_root_form_diameter_is_a_numerical_junction`). Ursache ist die
  Iterationsgrenze von STplus (Bogendifferenz m_n / 10 000, S. 227): Mit 20 000 und 50 000 rückt
  sein d_Ff des fzg_c-Ritzels von 6,4 µm auf 2,6 µm und 0,7 µm an den Schnittpunkt heran, den
  `gearcore` berechnet (Probeläufe `form_circle_limit_*`).
- **Ellipse der Kopfrundung:** FVA 604 I (S. 29) nähert die Stirnschnitt-Ellipse der Werkzeug-
  Kopfrundung durch einen Kreis mit ρ_aP0 / cos β. Gegen die STplus-Konturen liegt die Näherung bei
  β = 30° um 176 µm (β = 20°: 96 µm, β = 15°: 26,5 µm) daneben, die exakte Ellipse um höchstens
  0,6 µm (`scripts/circle_approximation_fva604.py`, konstanter Radius um den Rundungsmittelpunkt,
  der Fußkreis rückt um ρ_aP0 (1/cos β − 1) zur Radmitte hin). STplus rechnet also
  mit der exakten Stirnschnitt-Kinematik; `gearcore` ebenso.
- **Unterschnitt:** Unterhalb der Grenze x_Emin (Gl. (135)) liefert Gl. (128) mit negativer Klammer
  den Punkt des gespiegelten Evolventenastes jenseits von T, auf dem die Fußkurve endet; der
  Fuß-Formkreis ist der Schnittpunkt der Fußkurve mit der Evolvente (§7.6, S. 70), den `gearcore`
  numerisch bestimmt (`trochoid.root_form_diameter_by_intersection`). Vier Räder der Fixtures sind
  unterschnitten (fzg_c-Ritzel mit h_aP0* = 1,39, undercut_z12_x0, neg_shift_z17_xm08, small_z8_x05).
- **Werkzeug-Fußhöhe (berichtigt 2026-10-03, ADR-114):** §7 der Norm verwendet h_fP0 nicht. STplus
  belegt Fußformhöhe und Fußhöhe des Werkzeugs je mit 1,3 vor und setzt eine Fußhöhe unter der
  Fußformhöhe dieser gleich (kst-E: Eingabe nur h_fP0* = 1,0, Listing 1,300 / 1,300). Die frühere
  Lesart, STplus hebe eine Fußhöhe an, deren Fußlinie unter dem Kopfkreis läge, war falsch: Liegt
  der Kopfkreis über der Fußlinie des Werkzeugs, schneidet das Werkzeug ihn auf
  d_a = d + 2 m_n (x_E + h_fP0*) ab („Kopfkreis … von Wkz mit Fusshoehenfaktor geschnitten“).
  `gearcore` schneidet ebenso ab und meldet `tip_circle_cut_by_tool` (Nutzerentscheidung
  2026-10-03).
- **Kantenbrechflanke des Werkzeugs (berichtigt 2026-10-03, ADR-114):** Liegt die Fußhöhe über der
  Fußformhöhe, hat das Werkzeug zwischen beiden eine Kantenbrechflanke; STplus ersetzt eine
  Fußausrundung des Werkzeugs durch diese Flanke und belegt ihren Winkel mit α_n0 + 10° vor
  (Anleitung S. 186; Beispiel 1 druckt „alfa_K0 = 30.00 grd“). Ein Werkzeug mit
  FUSSFORMHOEHENFAKTOR ohne Winkel und ohne Fußhöhe (kst-B/-C-Ritzel, 1,75) hat in STplus die
  Fußhöhe 1,75 und damit keine Flanke; mit einer größeren Fußhöhe bricht es die Kopfkante unter
  30° (Probeläufe `tool_root_form_height_only`, `tool_root_both_heights`). Der `.ste`-Import setzt
  Fußhöhe und Winkel so und vermerkt es; der Rechenkern meldet für einen Datenvertrag mit
  Fußformhöhe unter der Fußhöhe ohne Winkel weiterhin `NotSupportedError` (Fußausrundung des
  Werkzeugs, GEN-10) und für einen Winkel ohne Flanke `edge_break_angle_without_flank`.
- **Zahnhöhen und Kopfzahndicke:** STplus druckt Zahnhöhe und Fußhöhe mit dem erzeugten Fußkreis
  d_fE (erste Form der Gl. (35)–(37)); „Zahndicke am Kopfkreis fuer A_We“ (s_an, ZAHNDICKE_KOPF) ist
  Gl. (38) am Kopfkreis mit x_E, in den Normalschnitt nach Gl. (48) mit β_a umgerechnet;
  RESTDICKE ist ohne Kantenbruch dieselbe Größe, mit Kantenbruch durch das Werkzeug s_aK nach
  DIN 3960 (A.3.05) und mit eingegebenem h_K der Wert s_an − 2 · 0,7 h_K im Normalschnitt,
  mindestens 0,2 s_an (Vorbelegung des Tangentialbetrags, Handbuch S. 19; der Normalschnitt und
  die Untergrenze sind aus Probeläufen bei β = 0° und 25° belegt). Der `.ste`-Import wendet die
  Regel an und vermerkt es (ADR-114, `stplus_program.stplus_residual_tip_thickness`); der
  Datenvertrag des Rechenkerns verlangt weiterhin h_K und s_aK (DIN ISO 21771 §6.1.2).
- **Zahndickenabmaße im Vergleich:** kst-E (Listing 11.0F) druckt x_E2 = 0,0117 zu x_2 = 0,314 33
  und A_ste2 = −0,220; Gl. (123) gibt 0,0121. Die Differenz ist die Rundung des gedruckten Abmaßes
  (−0,2203 mm erklärt 0,0117); der Vergleich führt sie als Eingaberundung.

## Befunde aus Inkrement 4 (2026-10-04)

**Norm.**

- **DIN 21773 Gl. (10) und die zweiten Formen von Gl. (12), (13)** (S. 12) sind, wie gedruckt,
  innerhalb von INT um 0,5 kleiner als Gl. (9) und die ersten Formen: sie enthalten s_bn / p_bn und
  damit die halbe Teilung. Die ersten Formen sind die geometrisch richtigen (Berührung der Meßflächen
  am genannten Zylinder); `gearcore` implementiert sie. Beispiel kst-B, Ritzel: Gl. (9) ergibt k = 5
  (wie STplus), Gl. (10) wie gedruckt k = 4.
- **Grenzmaße.** §4 (S. 8) rechnet die Grenzmaße mit x_Es, x_Em, x_Ei in den Gleichungen des
  Nennmaßes; §14 gibt Abmaßfaktoren (Ableitungen). Für die Zahnweite ist beides gleich, für das
  Kugelmaß bis auf die zweite Ordnung (kst-B, Ritzel, T_sn = 40 µm: 0,07 µm). `gearcore` rechnet
  nach §4 und gibt die Faktoren des §14 zusätzlich aus.
- **Kopfüberschnitt.** DIN 21773 §13 Gl. (40), S. 23, d_aM = d + 2 x_Es m_n + 2 h_fP0, ist die
  Normgleichung für den vom Werkzeug überschnittenen Kopfzylinder (ADR-114); die Aussage aus
  Inkrement 3, die Norm kenne dafür keine Gleichung, galt nur für DIN ISO 21771 §7.
- **DIN 3977 Bild 2** (S. 4) nennt für z = 22, β = 30°, x = +0,5, m_n = 3,5 mm die Meßstücke 6 bis
  8 mm als verwendbar; die eigene Grenze der Norm (1,73 m_n = 6,055 mm) schließt 6 mm aus.
  `gearcore` hält sich an die Grenzen des Abschnitts 6 und meldet 6 mm
  (`measuring_circle_outside_din3977_range`, Meßkreis 0,113 m_n unter dem V-Zylinder).
- **DIN 3977:1981-02** ist weiterhin gültig (Nutzer, 2026-10-04); DIN 21773 verweist für den
  Meßstückdurchmesser nicht mehr auf sie, nennt aber nur den idealen Durchmesser (Gl. (26), (27)).

**STplus 11.1F** (Regeln des Programms, `gearcore.stplus_program`, nie stillschweigend angewendet):

| Gegenstand | Norm / gearcore | STplus | Beleg |
|---|---|---|---|
| Prüfmaß einer Eingabe | sagt, welches Maß es ist (DIN 21773 §4) | immer Maß der Fertigverzahnung beim oberen Abmaß (x_E) | Proben `span_*`, kst-A/B/C |
| Aufteilung bei a_w + zwei Prüfmaßen | Kern verlangt vierte Angabe | Rad 1 behält das vorbelegte Abmaß (c25), Rad 2 den Rest; Überbestimmung wird ohne Meldung aufgelöst | Proben `span_with_upper_allowance_*` |
| Meßzähnezahl k | Gl. (9): Berührung am V-Zylinder, im Bereich Gl. (12), (13) | k = min(INT((k_min + k_max)/2) + 1, k_max) | `inspection_choices.json` (540 Räder), 18 Listings |
| Meßstückdurchmesser D_M | nächstgrößerer Wert DIN 3977 Tabelle 1 über dem idealen (V-Zylinder) | eigene Tabelle 1 … 110 mm (ohne Werte < 1 mm, 1,4, 3,25, 3,75, 4,25, 5,25, 30, 35; mit 32, 36, 60 … 110); max(kleinste Kugel über dem Kopf, zwei Tabellenwerte unter der Kugel für die Mitte der Formkreise nach der Form von DIN 3960 Gl. (3.8.24)–(3.8.27)) | wie oben; Umschaltpunkte auf 0,0005 mm |
| Zylinder der Zahndickensehne | dem Anwender überlassen (§5) | (d_Ff + d_Fa) / 2 | 76 Räder innerhalb 0,0005 mm |
| „Abmassfaktor A_Md/A_sn“ | Ableitung, Gl. (60) (kst-B Ritzel 2,309) | Verhältnis A_Mde / A_sne (gedruckt 2,287) | kst_b_rerun |
| Abmaß der Zahndickensehne | Gl. (48)–(53) | druckt das Zahndickenabmaß selbst | Listings |
| Paar ohne Flankenspiel bei den oberen Abmaßen | Hinweis `no_backlash_at_upper_allowances` | Abbruch („eingegebener Achsabstand a < spielfreier Achsabstand“) | Probe `spans_too_thick_for_the_centre_distance` |

Auf den 36 Rädern der 18 Vergleichsfälle wählt die Normregel bei 20 dasselbe k (bei 6 davon nennt
die Eingabe k) und bei 18 dasselbe D_M wie STplus; auf den 540 Zufallsrädern des Belegs liegt der
Meßkreis der STplus-Kugel bei 416 von 538 im Bereich der DIN 3977 Abschnitt 6, der der Normregel
bei 537 von 538. Für Schrägverzahnung ist die Kugel, die STplus für die Flankenmitte ansetzt, nicht
die dort berührende (z = 40, β = 30°: 6,0 mm statt 4,69 mm).

## Tabellenwerte und Vorbelegungen (Stand 2026-10-03)

Werte, die nicht eingegeben werden müssen, stammen aus zwei verschiedenen Quellen: aus
**Normtabellen** (der Wert folgt aus Modul, Durchmesser, Qualität …) und aus **Vorbelegungen des
Programms** (STplus setzt einen Wert, wenn die Eingabe fehlt). Beides wird je Inkrement inventarisiert:
Was belegt STplus vor (Programmanleitung), was tabelliert die aktuelle, nicht zurückgezogene Norm,
weichen die Werte ab. `gearcore` kennt keine stillen Vorbelegungen: Ein nicht eingegebener Wert ist
entweder ein benannter Wert einer Normtabelle (Funktion mit Quellenangabe) oder er fehlt, und die
Rechnung, die ihn braucht, meldet das. Das gilt auch für die Null eines fehlenden Merkmals:
Schrägungswinkel, Kopfkantenbruch, Protuberanz und Bearbeitungszugabe sind Pflichteingaben; der
`.ste`-Import setzt die Null nur zusammen mit einem Hinweis (Nutzerentscheidung 2026-09-30,
ADR-111).

Seit 2026-10-03 (Nutzerentscheidung, ADR-114) liest der `.ste`-Import eine Datei so, **wie STplus
sie rechnet**: Er wendet die Vorbelegungen und Korrekturen des Programms an und vermerkt jede in
`SteImport.notes`. Der Rechenkern bleibt ausdrücklich; wer ihn ohne Importer benutzt, gibt jeden
Wert selbst an. Grundlage ist die vollständige Lektüre der Programmanleitung (Kap. 1 bis 3, 4.1,
4.2, 4.14 bis 4.17, 5 bis 8, 10) und 70 aufbewahrte Probeläufe mit unvollständigen und
widersprüchlichen Eingaben (`data/stplus_program/probes`).

| Wert | STplus 11.1F | aktuelle Norm | Stand in `gearcore` | Inkrement |
|---|---|---|---|---|
| Normaleingriffswinkel | 20° vorbelegt (Anleitung S. 15), aber nur in der Benutzeroberfläche: eine Eingabedatei ohne `EINGRIFFSWINKEL` wird abgelehnt (Probelauf) | DIN 867:1986-02, ISO 53:1998: α_P = 20° | keine Vorbelegung: Pflichteingabe im Datenvertrag und im Import (seit Inkrement 2) | 2 ✓ |
| Kopfkantenbruch, Protuberanz, Bearbeitungszugabe des Werkzeugs | fehlt die Eingabe, gilt 0 (kein Merkmal) | – | Pflichteingaben im Datenvertrag; der Import setzt 0 mit Hinweis (ADR-111) | 2 ✓ |
| Schrägungswinkel ohne Eingabe | wird aus Achsabstand und Profilverschiebungssumme berechnet (S. 16, Unterprogramm GE12; Rad 1 rechtssteigend); ohne Achsabstand wird die Eingabe abgelehnt (Probeläufe `helix_angle_from_centre_distance`: 12,1313°, `no_helix_angle_no_centre_distance`) | DIN ISO 21771:2014-08 Gl. (55) und Achsabstand, nach β aufgelöst | Pflichteingabe im Datenvertrag; der Import löst die Gleichung (`stplus_helix_angle_deg`, 12,1322°; die Iteration von STplus endet, sobald der Achsabstand auf etwa 0,5 µm getroffen ist, sein Winkel ist deshalb bis zu 0,002° zu klein und der Rest steckt in x_2; ohne Profilverschiebung druckt es 16,25980° für arccos(60 / 62,5) = 16,26020°, Probelauf `helix_angle_without_profile_shift`) und vermerkt es, ohne Achsabstand `ParseError`. Berichtigt 2026-10-03: zuvor setzte der Import 0 | 3 ✓ |
| Bezugsprofil des Rades (h_aP, h_fP, c_P, ρ_fP) | über Werkzeugfaktoren | DIN 867:1986-02; ISO 53:1998 Typ A–D | Funktionen `din867_basic_rack`, `iso53_basic_rack`; Grenzen des Fußrundungsradius beider Normen verglichen (gleich) | 1 ✓ |
| Werkzeug-Bezugsprofile I–IV (Kopfhöhe, Kopfrundung, Bearbeitungszugabe) | fest im Programm; ohne Werkzeugeingabe „geeignetes Wälzwerkzeug“ (S. 22) | DIN 3972:1952-02 (gültig) | `din3972_tool`; alle 152 Tabellenwerte gegen die Formeln geprüft, 6 Abweichungen dokumentiert. Kein stilles Standardwerkzeug: das Werkzeug ist Pflichteingabe | 1 ✓ |
| Modulreihe | – | ISO 54:1996 | `check_module` (Hinweis, keine Ablehnung) | 1 ✓ |
| Werkzeugdatenbank | `wkz.dat` (12 Werkzeuge) und `WKZ_GLOB.DAT` (2 Werkzeuge), keine Normtabelle | – | unverändert übernommen, gekennzeichnet „STplus 11.1F (Freigabe 01.12.2025)“ (`gearcore.stplus_program.tool_database`, ADR-109). Seit ADR-114 so gelesen, wie STplus mit den Datensätzen rechnet (Faktor vor Absolutwert, Vorbelegungen, Grenzen): 10 sind für sich Werkzeug-Datenverträge, die 2 der globalen Datenbank nennen keinen Profilwinkel und werden mit dem des Rades vervollständigt (`stplus_tool(name, normal_pressure_angle_deg=…)`), 2 (α_n0 = 16°) überschreiten nach der Begrenzung die Schranke 2,5 des Datenvertrags | 1 ✓, 3 ✓ |
| Standardwerkzeug ohne Werkzeugeingabe | Wälzfräser mit h_aP0* = 1,25; ρ_aP0* = 0,25; h_fP0* = h_FfP0* = 1,3 (Probelauf; die Anleitung nennt keine Zahlen, S. 22) | DIN 3972:1952-02 Profil II hat dieselbe Kopfhöhe 1,25·m, die Kopfrundung ist dort je Modul tabelliert | `stplus_default_tool()`; der Import setzt es für ein Rad ohne Werkzeug mit Hinweis (ADR-114), auch wenn nur das andere Rad ein Werkzeug nennt; ab α_n = 26,8° greifen die Grenzen (28°: ρ_aP0* 0,201; 30°: 0,110 und 1,265 / 1,265). Der Datenvertrag verlangt das Werkzeug | 1 ✓, 3 ✓ |
| Fehlende Werkzeugfaktoren | h_aP0* 1,25; ρ_aP0* 0,25; h_FfP0* 1,3; h_fP0* 1,3 (Probeläufe; S. 224 nennt für h_Ff0* 1,1, siehe unten). Eine Fußhöhe unter der Fußformhöhe wird ihr gleichgesetzt: die Fußhöhe wirkt nur zusammen mit einer kleineren Fußformhöhe | – | `stplus_tool_factors`; der Import vervollständigt das Werkzeug so und vermerkt jeden Wert. Die Faktoren der 60 Probeläufe, die der Import liest, und der 18 Vergleichsfälle stimmen in drei Nachkommastellen mit den Listings | 3 ✓ |
| Grenzen der Werkzeughöhen | Kopfhöhe ≤ (π/2 − 0,120) / (2 tan α_n); Kopfrundung ≤ Vollrundung; Fußformhöhe ≤ (π/2 − 0,110) / (2 tan α_n); Fußhöhe ≤ h_FfP0* + (π/2 − (2 h_FfP0* + 0,06) tan α_n) / (2 tan α_K). Die Anleitung druckt keine Formeln, nennt aber die Steuergrößen dahinter (S. 224: s_a0*, e_Ff0*, e_f0*); 0,120 und 0,110 sind deren Vorbelegungen im Programm, 0,06 tan α_n entspricht e_f0* = 0,03 (durch Variation der Steuergrößen belegt, α_n = 15° bis 30°); die Grenzen gelten auch für Vorbelegungen (28°, 30°). Kantenbrechwinkel 90° = Werkzeug ohne Kantenbrechflanke (S. 186), ebenso ein Winkel gleich α_n0; ein Winkel unter α_n0 wird durch α_n0 + 10° ersetzt; 85° rechnet STplus, bei 88° bricht es ab (Probeläufe `tool_edge_break_angle_*`) | – | `stplus_max_tool_*`; der Import begrenzt mit Hinweis und liest die drei Steuergrößen (GEN-11) | 3 ✓ |
| Kopfkreis über der Fußlinie des Werkzeugs | wird auf d + 2 m_n (x_E + h_fP0*) abgeschnitten, mit Meldung (S. 19: „der geometrisch ausführbare Kopfkreis“) | DIN ISO 21771:2014-08 §7 kennt h_fP0 nicht | `compute_generation` schneidet ab, Warnung `tip_circle_cut_by_tool` (Nutzerentscheidung 2026-10-03). Spitzer Zahn durch Kantenbrechflanken: typisierter Fehler (GEN-13) | 3 ✓ |
| Kopfkreisdurchmesser ohne Eingabe | d_a = d + 2·m_n·(h_aP* + x) mit h_aP* = 1, ohne Kopfhöhenänderung; danach Verträglichkeitsprüfung und gegebenenfalls Verkleinerung (S. 19) | DIN ISO 21771:2014-08 Gl. (33), S. 34: d_a = d + 2·(x·m_n + h_aP + k·m_n) | Kopfkreis ist Eingabe des Datenvertrags; der Import setzt den STplus-Wert mit Hinweis und merkt ihn vor (`SteImport.preset_tip_diameters`), weil STplus ihn danach noch verkleinern kann. Die Verkleinerung durch das Werkzeug ist nachgebildet (Zeile darüber), die durch Kopfzahndicke und Radpaarung nicht (GEN-16). Die fünf anderen Festlegungen des Kopfkreises (Bild 4.12, S. 25: `BEZ_KOPFDICKE`, `DA_DURCH_WKZ`, `DA_NACH_DIN3960`, `KOPFSPIELFAKTOR`, `K_HOEHENF_VERZ_BEZ_PR`) übersetzt der Import nicht: `NotSupportedError` (GEN-15); neben `KOPFKREISDM` beider Räder wirken sie nicht (Probelauf `tip_circle_given_with_other_definitions`) | 2 ✓, 3 ✓ |
| Kopfspiel, Mindestkopfspiel | Kopfspielfaktor c* als Eingabe (S. 18/19) | DIN ISO 21771:2014-08 §5.2.7 Gl. (60), S. 41 (mit dem erzeugten Fußkreisdurchmesser des Gegenrades) | Funktion `tip_clearance` vorhanden und gegen STplus geprüft; im Ergebnis ab Inkrement 3 | 3 |
| Aufteilung der Profilverschiebungssumme | nach DIN 3992 u. a. (S. 17, 25); mit der Summe und einem Faktor folgt der andere | keine: DIN 3992:1964-03 ist zurückgezogen (liegt im Repo); DIN ISO 21771:2014-08 §5.3 (S. 42) überlässt die Aufteilung den zulässigen Beanspruchungen, den Gleitgeschwindigkeiten oder anderen vorgeschriebenen Maßen | Summe und ein Faktor: der Import berechnet den anderen mit Hinweis (ADR-114); sind Achsabstand und Schrägungswinkel gegeben, benutzt STplus die Summe nicht (x_2 folgt aus dem Achsabstand, Probelauf `profile_shift_sum_with_centre_distance`). Summe ohne Faktor: Erweiterungspunkt, der Import meldet `NotSupportedError`; der Datenvertrag lehnt einen Achsabstand ohne Profilverschiebungsfaktor und ohne Zahnweite ab | 3 ✓ |
| Kopfkantenbruch durch h_K: Tangentialbetrag und Grenzen | Tangentialbetrag 0,7·h_K (S. 19; Steuergröße TANG_BETRAG_ZU_H_KGF 0,3 bis 1,5, S. 225); Restdicke im Normalschnitt s_aK = s_an − 1,4 h_K, mindestens 0,2 s_an; h_K höchstens 0,20 m_n bzw. MAX_KOPFKANTENBRUCH · m_n (Probeläufe `tip_chamfer_*`). Eine Steuergröße ist ein Wert für die Stufe: der erste Wert gilt für beide Räder (Bild 4.231, S. 229; Probeläufe mit beiden Reihenfolgen); ein Wert außerhalb des Einstellbereichs wird nicht angenommen, es bleibt die Vorbelegung (S. 223, Probelauf `control_outside_its_range`); `%` heißt nicht eingegeben | DIN ISO 21771:2014-08 §6.1.2 legt den Kantenbruch durch h_K und s_aK fest, ohne Vorbelegung | Datenvertrag wie die Norm; der Import wendet die STplus-Regel an und vermerkt es (`stplus_tip_chamfer_height`, `stplus_residual_tip_thickness`) | 3 ✓ |
| Kantenbrechwinkel des Werkzeugs | α_n0 + 10° vorbelegt (S. 186, auf der gerenderten Seite gelesen); eine Fußausrundung des Werkzeugs wird durch die Kantenbrechflanke ersetzt | DIN 3960:1987-03 Anhang A.3.1 (Kantenbrechflanke), keine Vorbelegung | der Import setzt den Winkel, wo die Fußhöhe über der Fußformhöhe liegt, mit Hinweis; DIN 3960 A.3.1 mit diesem Winkel trifft den Probelauf (46,3069 / 0,0466 / 0,4069 gegen 46,307 / 0,047 / 0,407) und Beispiel 1 der Anleitung (S. 254 bis 259) | 3 ✓ |
| Bearbeitungszugabe | zwei Eingaben, Summe im Listing (S. 20, 184, 185) | DIN ISO 21771:2014-08 §7.2 | der Datenvertrag führt die Zugabe q des Werkzeugs (Gl. (123)); der Import liest die werkzeuginterne Zugabe in mm (`BEARB_ZUGABE_WKZ`), ihr Faktor (`BEARB_ZUGABE_WKZ_FAKTOR`) ist nicht übersetzt (`NotSupportedError`, GEN-15), die Zugabe der Geometriedaten (`BEARBEITUNGSZUGABE`) wird als nicht abgebildet gemeldet (REG1-03b) | 3 ✓ |
| Unteres Zahnweitenabmaß | fehlt es, gilt A_Wi = A_We (S. 20) | – | der Import setzt es so mit Hinweis; ein unteres ohne oberes Abmaß ist `ParseError` | 3 ✓ |
| Iterationsgrenzen und Steuergrößen (Kap. 4.17.2, S. 223 bis 230) | Formkreise: Zahndickenbögen gleich innerhalb m_n / 10 000 (S. 227); elliptische Werkzeugkopfrundung im Stirnschnitt vorbelegt (S. 227/228); Kreisdifferenz, Schrägungswinkelgrenze, Wälzwinkelschritt, Höchstzahl der Iterationen u. a. | – | in `defaults.yaml` aufbewahrt (62 Vorbelegungen). Der Import wertet MINDESTKOPFSPIEL, MAX_KOPFKANTENBRUCH, TANG_BETRAG_ZU_H_KGF und die drei Steuergrößen der Werkzeuggrenzen aus, lehnt die kreisförmige Werkzeugkopfrundung (ABSCHALTEN_KORRGLIED = 1) ab und nennt jede andere Steuergröße in einem Hinweis. Der Einstellbereich ist ein offenes Intervall. Die Bogengrenze erklärt die Größenordnung der Formkreisgenauigkeit im Vergleich (GEN-06) | 3 ✓ |
| Messzähnezahl k | programmintern, überschreibbar (S. 20) | DIN 21773:2014-08 §7.2 | offen | 4 |
| Messkugel-/Messrollendurchmesser D_M | programmintern, überschreibbar (S. 20) | DIN 21773:2014-08, S. 18: Gl. (26) mit Gl. (27) für schrägverzahnte Räder (Anlage der Messkugel am V-Zylinder); für α_n = 20° näherungsweise Gl. (28), D_M = m_n·D_M*, mit dem Faktor D_M* aus der Netztafel Bild 8. Eine Durchmesserreihe aus einer weiteren Norm verlangt DIN 21773 nicht | offen | 4 |
| Zahndickenabmaße und -toleranzen | Reihe c25 vorbelegt (S. 19) | DIN 3967:1978-08 Tabelle 1 und 2 (gültig) | offen; Eingabefelder vorhanden. Bis dahin erzeugt der Import ein Paar ohne Abmaßeingabe mit der Nennzahndicke (GEN-14) | 5 |
| Achsabstandsabmaße | js 7 vorbelegt (S. 20) | DIN 3964:1980-11 Tabelle 1 (gültig) | offen | 5 |
| Verzahnungsqualität | DIN-Qualität 7 vorbelegt (S. 19); Tabellen DIN 3962/63 und ISO 1328:1975/1995 als XML | DIN ISO 1328-1:2018-03 (Formeln statt Tabellen), DIN ISO 1328-2:2021-09 | offen; Tabellen gegen Formeln ist ein dokumentierter Normunterschied | 5 |
| Werkstoffkennwerte | `wst.dat` (Stahl, Guss), kein Kunststoff | ISO 6336-5:2016, VDI 2736 Blatt 1–2 | nur Datenvertrag | Etappe 2 |
| Schmierstoffdaten | `oel.dat` | ISO/TS 6336-20/-21/-22, VDI 2736 | offen | Etappe 2 |
| Faktoren der Tragfähigkeit (K_A, Z_N, Y_N, Betriebsstunden …) | vorbelegt (S. 35–58) | ISO 6336:2019 | offen | Etappe 2 |

Die Vorbelegungen von STplus sind mit Fundstelle und Probelauf in `data/stplus_program/defaults.yaml` aufbewahrt (ADR-109), gekennzeichnet mit Programmversion und Freigabedatum; `gearcore` wendet keine davon stillschweigend an: der `.ste`-Import wendet sie an und vermerkt jede, der Rechenkern verlangt die Werte (ADR-114).

### Anleitung und Programm im Widerspruch (Stand 2026-10-03)

An sechs Stellen rechnet STplus 11.1F anders, als seine Anleitung sagt. Die Widersprüche sind am
Lehrstuhl bekannt (Nutzerangabe 2026-10-03); `gearcore` folgt dem Programm und hält beides fest
(Nutzerentscheidung, ADR-114).

| Anleitung | Programm 11.1F (Probeläufe) | `gearcore` |
|---|---|---|
| S. 224: h_Ff0* mit 1,1 vorbelegt, h_f0* mit 1,3 | beide 1,300, auch im Listing des Beispiels 1 der Anleitung (S. 259); die Steuergrößen `VB_FUSSFORMHOEHE_HFF0*` und `VB_FUSSHOEHE_HF0*` ändern nichts (`tool_root_presets_of_the_configuration`) | 1,3 und 1,3 |
| S. 186: h_f0 < h_Ff0 wird in h_f0 = h_f0max geändert | h_f0 = h_Ff0 (`tool_root_dedendum_only_low`, `tool_root_dedendum_below_form_height`, kst-E) | h_f0 = h_Ff0 |
| S. 225: größter Kopfkantenbruchfaktor h_KgF* mit 0,02 vorbelegt | ein eingegebener Kantenbruch wird auf 0,20 m_n begrenzt (`tip_chamfer_limits`) | 0,20 m_n |
| S. 224: Die Steuergrößen s_a0* und e_Ff0*, die Werkzeugkopfhöhe und Fußformhöhe begrenzen, sind mit 0,2 und 0,4 vorbelegt | das Programm belegt sie mit 0,12 und 0,11 vor; ausdrücklich eingegeben wirken sie wie beschrieben (Kopfdicke = s_a0*, Lückenweite = e_Ff0*; `tool_tip_land_control*`, `tool_space_control`) | Vorbelegung 0,12 und 0,11; eingegebene Werte werden gelesen |
| S. 224: e_f0* ist eine Werkzeug-Lückenweite, vorbelegt mit 0,06, Einstellbereich 0,01 bis 0,6 | die Lückenweite an der Fußlinie ist 2 e_f0* tan α_n; ohne Eingabe 0,06 tan α_n (e_f0* = 0,03); Werte bis 0,1 wirken nicht (`tool_root_space_control*`) | wie das Programm |
| S. 223, 225: Steuergrößen können „zwischen“ den Grenzen ihres Einstellbereichs variiert werden | die Grenzen selbst werden nicht angenommen, es bleibt die Vorbelegung (`controls_at_the_ends_of_their_ranges`, `tool_controls_at_the_ends_of_their_ranges`) | offenes Intervall |

Seitenangaben: STplus-Programmanleitung 11.1F (gedruckte Seitenzahl). Offen heißt: weder
hinterlegt noch gegen die aktuelle Norm verglichen. Zurückgezogene Normen, auf die sich STplus stützt und die im Repo liegen: DIN 3992:1964-03
(Profilverschiebung) und DIN 58412:1987-11 (Bezugsprofile für Verzahnwerkzeuge der Feinwerktechnik;
die Anleitung nennt sie auf S. 183). Beide sind keine Rechengrundlage von `gearcore`; ihre Werte
können nur als gekennzeichnete alte Voreinstellung dienen. DIN 58400 (Bezugsprofil der
Feinwerktechnik, von DIN 58412 vorausgesetzt) liegt nicht im Repo. Für den Messkugeldurchmesser ist
keine weitere Norm nötig (DIN 21773:2014-08 Gl. (26) bis (28)).

Die Einzelabweichungen mit Zahlenbeispiel entstehen in Inkrement 2–6 und werden in
`expected_differences.yaml` geführt.
