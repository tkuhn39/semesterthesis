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
  Stirnschnitt (Kopfrundung wird zur Ellipse) gehört zur Erzeugung und entsteht mit Inkrement 3.

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

## Tabellenwerte und Vorbelegungen (Stand 2026-09-30)

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

| Wert | STplus 11.1F | aktuelle Norm | Stand in `gearcore` | Inkrement |
|---|---|---|---|---|
| Normaleingriffswinkel | 20° vorbelegt (Anleitung S. 15), aber nur in der Benutzeroberfläche: eine Eingabedatei ohne `EINGRIFFSWINKEL` wird abgelehnt (Probelauf) | DIN 867:1986-02, ISO 53:1998: α_P = 20° | keine Vorbelegung: Pflichteingabe im Datenvertrag und im Import (seit Inkrement 2) | 2 ✓ |
| Schrägungswinkel, Kopfkantenbruch, Protuberanz, Bearbeitungszugabe des Werkzeugs | fehlt die Eingabe, gilt 0 (kein Merkmal) | – | Pflichteingaben im Datenvertrag; der Import setzt 0 mit Hinweis (ADR-111) | 2 ✓ |
| Bezugsprofil des Rades (h_aP, h_fP, c_P, ρ_fP) | über Werkzeugfaktoren | DIN 867:1986-02; ISO 53:1998 Typ A–D | Funktionen `din867_basic_rack`, `iso53_basic_rack`; Grenzen des Fußrundungsradius beider Normen verglichen (gleich) | 1 ✓ |
| Werkzeug-Bezugsprofile I–IV (Kopfhöhe, Kopfrundung, Bearbeitungszugabe) | fest im Programm; ohne Werkzeugeingabe „geeignetes Wälzwerkzeug“ (S. 22) | DIN 3972:1952-02 (gültig) | `din3972_tool`; alle 152 Tabellenwerte gegen die Formeln geprüft, 6 Abweichungen dokumentiert. Kein stilles Standardwerkzeug: das Werkzeug ist Pflichteingabe | 1 ✓ |
| Modulreihe | – | ISO 54:1996 | `check_module` (Hinweis, keine Ablehnung) | 1 ✓ |
| Werkzeugdatenbank | `wkz.dat` (12 Werkzeuge) und `WKZ_GLOB.DAT` (2 Werkzeuge), keine Normtabelle | – | unverändert übernommen, gekennzeichnet „STplus 11.1F (Freigabe 01.12.2025)“ (`gearcore.stplus_program.tool_database`, ADR-109). 6 Datensätze sind gültige Werkzeuge; 6 widersprechen sich (Faktor und Absolutwert), 2 haben keine Kopfrundung: aufbewahrt, aber kein Datenvertrag | 1 ✓ |
| Standardwerkzeug ohne Werkzeugeingabe | Wälzfräser mit h_aP0* = 1,25; ρ_aP0* = 0,25; h_fP0* = h_FfP0* = 1,3 (Probelauf; die Anleitung nennt keine Zahlen, S. 22) | DIN 3972:1952-02 Profil II hat dieselbe Kopfhöhe 1,25·m, die Kopfrundung ist dort je Modul tabelliert | `stplus_default_tool()`, nie stillschweigend | 1 ✓ |
| Kopfkreisdurchmesser ohne Eingabe | d_a = d + 2·m_n·(h_aP* + x), danach Verträglichkeitsprüfung und gegebenenfalls Verkleinerung (S. 19) | DIN ISO 21771:2014-08 Gl. (33), S. 34: d_a = d + 2·(x·m_n + h_aP + k·m_n) | Kopfkreis ist Eingabe; der Nennwert nach Gl. (33) steht über `with_nominal_tip_diameters` als ausdrückliche Wahl bereit. Die Verkleinerung von STplus ist nicht nachgebildet | 2 ✓ |
| Kopfspiel, Mindestkopfspiel | Kopfspielfaktor c* als Eingabe (S. 18/19) | DIN ISO 21771:2014-08 §5.2.7 Gl. (60), S. 41 (mit dem erzeugten Fußkreisdurchmesser des Gegenrades) | Funktion `tip_clearance` vorhanden und gegen STplus geprüft; im Ergebnis ab Inkrement 3 | 3 |
| Aufteilung der Profilverschiebungssumme | nach DIN 3992 u. a. (S. 17, 25) | keine: DIN 3992:1964-03 ist zurückgezogen (liegt im Repo); DIN ISO 21771:2014-08 §5.3 (S. 42) überlässt die Aufteilung den zulässigen Beanspruchungen, den Gleitgeschwindigkeiten oder anderen vorgeschriebenen Maßen | Erweiterungspunkt: der Import meldet `NotSupportedError`, der Datenvertrag lehnt einen Achsabstand ohne Profilverschiebungsfaktor und ohne Zahnweite ab | – |
| Kopfkantenbruch: Tangentialbetrag | 0,7·h_K vorbelegt (S. 19) | zu prüfen (DIN ISO 21771 §7, DIN 3960 A.3.1) | offen | 3 |
| Kantenbrechwinkel des Werkzeugs | α_n0 + 10° vorbelegt (S. 186, nur Textstelle geortet) | zu prüfen | offen (`pending`) | 3 |
| Bearbeitungszugabe | zwei Eingaben, Summe im Listing (S. 20, 184, 185) | DIN ISO 21771:2014-08 §7.2 | Importer liest nur die werkzeuginterne (REG1-03b) | 3 |
| Messzähnezahl k | programmintern, überschreibbar (S. 20) | DIN 21773:2014-08 §7.2 | offen | 4 |
| Messkugel-/Messrollendurchmesser D_M | programmintern, überschreibbar (S. 20) | DIN 21773:2014-08, S. 18: Gl. (26) mit Gl. (27) für schrägverzahnte Räder (Anlage der Messkugel am V-Zylinder); für α_n = 20° näherungsweise Gl. (28), D_M = m_n·D_M*, mit dem Faktor D_M* aus der Netztafel Bild 8. Eine Durchmesserreihe aus einer weiteren Norm verlangt DIN 21773 nicht | offen | 4 |
| Zahndickenabmaße und -toleranzen | Reihe c25 vorbelegt (S. 19) | DIN 3967:1978-08 Tabelle 1 und 2 (gültig) | offen; Eingabefelder vorhanden | 5 |
| Achsabstandsabmaße | js 7 vorbelegt (S. 20) | DIN 3964:1980-11 Tabelle 1 (gültig) | offen | 5 |
| Verzahnungsqualität | DIN-Qualität 7 vorbelegt (S. 19); Tabellen DIN 3962/63 und ISO 1328:1975/1995 als XML | DIN ISO 1328-1:2018-03 (Formeln statt Tabellen), DIN ISO 1328-2:2021-09 | offen; Tabellen gegen Formeln ist ein dokumentierter Normunterschied | 5 |
| Werkstoffkennwerte | `wst.dat` (Stahl, Guss), kein Kunststoff | ISO 6336-5:2016, VDI 2736 Blatt 1–2 | nur Datenvertrag | Etappe 2 |
| Schmierstoffdaten | `oel.dat` | ISO/TS 6336-20/-21/-22, VDI 2736 | offen | Etappe 2 |
| Faktoren der Tragfähigkeit (K_A, Z_N, Y_N, Betriebsstunden …) | vorbelegt (S. 35–58) | ISO 6336:2019 | offen | Etappe 2 |

Die Vorbelegungen von STplus sind mit Fundstelle und Probelauf in `data/stplus_program/defaults.yaml` aufbewahrt (ADR-109), gekennzeichnet mit Programmversion und Freigabedatum; `gearcore` wendet keine davon stillschweigend an.

Seitenangaben: STplus-Programmanleitung 11.1F (gedruckte Seitenzahl). Offen heißt: weder
hinterlegt noch gegen die aktuelle Norm verglichen. Zurückgezogene Normen, auf die sich STplus stützt und die im Repo liegen: DIN 3992:1964-03
(Profilverschiebung) und DIN 58412:1987-11 (Bezugsprofile für Verzahnwerkzeuge der Feinwerktechnik;
die Anleitung nennt sie auf S. 183). Beide sind keine Rechengrundlage von `gearcore`; ihre Werte
können nur als gekennzeichnete alte Voreinstellung dienen. DIN 58400 (Bezugsprofil der
Feinwerktechnik, von DIN 58412 vorausgesetzt) liegt nicht im Repo. Für den Messkugeldurchmesser ist
keine weitere Norm nötig (DIN 21773:2014-08 Gl. (26) bis (28)).

Die Einzelabweichungen mit Zahlenbeispiel entstehen in Inkrement 2–6 und werden in
`expected_differences.yaml` geführt.
