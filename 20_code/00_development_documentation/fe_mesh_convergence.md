# Netzparameter und Netzkonvergenz des Radsektors (Stand 2026-10-06)

Deutsch, weil der Text in die Semesterarbeit übernommen werden soll. Zahlen aus
`80_output/fe/kst_e/convergence/convergence.md` und `verification.md` (Erzeugung siehe unten);
Bilder dort: `load_case.png`, `fillet_stress.png`, `convergence_root_stress.png`,
`convergence_tip_displacement.png`, `convergence_strain_energy.png`.

## 1 Was am Netz einstellbar ist

Das Netz des Kunststoffrads entsteht aus der Vorlage (Mittelschnitt des FVA-Referenznetzes von
kst-E, ADR-116 Punkt 7) und der erzeugten Zahnkontur. Einstellbar sind, in den Worten des
FVA-Vernetzungsdialogs:

| Größe im FVA-Dialog | Parameter in gearcore (`build_fe_decks.py mesh`) | Grundnetz (2026-10-05) |
|---|---|---|
| Anzahl der modellierten Zähne | `--teeth` | 5 |
| Anzahl der zahnfreien Segmente | fest: ein zahnloses Segment je Ende (Fesselung an den Schnittebenen wie im Referenznetz); Spalten darin `--shoulder-columns` | 2 (je 4 Spalten) |
| Elemente über die Zahnhöhe | `--over-tooth-height` (Fußformpunkt bis Kopfformpunkt) und `--at-tip-edge-break` (Kopfkantenbruch) | 18 + 2 je Flanke |
| Elemente am Zahnfuß | `--at-tooth-root` (je Zahnlücke, Fußformpunkt bis Fußformpunkt, gerade Zahl) | 80 |
| Elemente über die Zahndicke | `--over-tooth-thickness` (gerade Zahl) | 10 am Kopfkreis |
| Fußschichten normal zur Oberfläche | `--root-layers` (zugleich die äußeren Kopfspalten je Seite; der Rest der Zahndicke sind die mittleren Spalten) | 3 |
| Elemente über die gemeinsame Zahnbreite | `--layers` | 80 Schichten (0,1875 mm) |
| Kranzdicke | `--rings` (Ringe) und `--bore-radius` (Bohrung; Voreinstellung 12 Ringe der Vorlage = 18,10 mm) | 12 Ringe |

Die Anzahlen sind frei wählbar (ganze Zahlen ab 1, Zahndicke und Zahnfuß gerade). Dazu wird die
Blockstruktur der Vorlage ausgelesen: Das Netz des FVA-Referenzschnitts besteht je Zahnhälfte aus
einem Fußband (40 × 3), einem Dom unter dem Zahn (40 × 2), zwei Kopfblöcken (18 × 3 und 18 × 2),
zwei Kantenbruchblöcken (2 × 3 und 2 × 2) und dem Kranz (12 × 2), das zahnlose Segment aus einem
Block 15 × 4; alle Blockseiten gehören zu sieben Klassen paralleler Seiten, die genau die Zahlen
der Tabelle sind (`gearcore.fe.resample`). Jeder Block wird als Gitter der neuen Größe neu
aufgebaut; die Knoten einer Seite liegen bei denselben relativen Bogenlängen wie in der Vorlage
(interpoliert, damit dünne Schichten verhältnismäßig dünn bleiben), das Innere wird im Indexraum
der Vorlage interpoliert. Mit den Zahlen der Vorlage entsteht die Vorlage selbst (Test); die
Zähne bleiben kongruent und spiegelsymmetrisch, die Formpunkte bleiben Knoten. Der geschriebene
Netzbericht nennt die wirksamen Zahlen. Für Konvergenzreihen gibt es daneben ganzzahlige
Faktoren auf die Vorlage (`gearcore.fe.refine`, Sehnenteilung), die das Skript der Studie nutzt.

## 2 Vorgehen der Konvergenzstudie

Grundlage im Buch von Stommel, Stojek, Korte (FEM zur Berechnung von Kunststoff- und
Elastomerbauteilen, 2. Aufl., Hanser 2018), ohne Formeln, als Vorgehensregeln: Abschnitt 7.7.1
Elementeigenschaften, S. 424: einer unzureichenden Diskretisierung begegnet die h-Methode, das
Netz wird lokal oder global verfeinert, bis die Spannungsunterschiede zwischen angrenzenden
Elementen hinreichend klein sind; S. 427 f.: Hourglassing bei reduziert integrierten Elementen
und die Pflicht zur Energiebilanz. Abschnitt 7.7.3 Strukturelemente, S. 433: vor der endgültigen
Auswertung eine Konvergenzstudie an einem kleinen Modell unter vergleichbarer Last, mit
verschiedenen Elementtypen, im Idealfall gegen eine analytische Lösung, sonst gegen ein
Kontinuumsmodell als Referenz (dort für Strukturelemente formuliert; hier auf die
Elementformulierungen des Kontinuums übertragen). Abschnitt 8.2.2 Vernetzung, S. 465: die
Elementgröße so groß wie möglich wählen, um Rechenzeit zu sparen, nach oben begrenzt durch
Geometriedetails und Beanspruchungsgradienten; das ist der Grundsatz der Empfehlung in
Abschnitt 5b. Die Studie läuft hier auf dem Stirnschnitt des
Radsektors (ebener Dehnungszustand), weil das Volumennetz ein reines Auszugsnetz dieses Schnitts
ist: was in der Zahnebene konvergiert, konvergiert im Volumennetz ebenso. Die Zahl der Schichten
über die Breite prüft die Studie nicht (Abschnitt 6).

- **Löser:** eigener ebener Löser (`gearcore.fe.plane_solver`), Vierknotenelement mit 2 × 2
  Gaußpunkten und dem volumetrischen Dehnungsanteil im Elementmittelpunkt. Das ist die
  Formulierung der voll integrierten Elemente erster Ordnung von Abaqus (CPE4, C3D8: „selectively
  reduced integration (reduced integration on the volumetric terms)“, Abaqus 2025 Dokumentation,
  Solid (continuum) elements). Spannungen an den Knoten wie in Abaqus: von den Gaußpunkten auf die
  Ecken extrapoliert und über die anliegenden Elemente gemittelt.
- **Last:** Punkt B des Rades, der äußere Einzeleingriffspunkt (die ganze Last auf einem Zahn mit
  dem längsten Hebelarm; dort bewertet ISO 6336-3 nach Methode B — Seite im Kapitel nachtragen),
  16 Nm am Rad. Kraft in Eingriffsrichtung F_bt = T_2 / r_b2 = 654,9 N, je mm Zahnbreite
  F' = 43,66 N/mm. Sie wirkt als Hertzsche Pressungsverteilung p(s) = p_0 √(1 − (s/b_H)²) über den
  Bogen |s| ≤ b_H der Flanke um den Berührpunkt (b_H = 0,322 mm, p_0 = 86,4 MPa, starres
  Stahlritzel gegen E* = E/(1 − ν²) des Rades), normal zur Oberfläche, als konsistente Knotenlasten
  je Oberflächenkante. Quelle der Linienberührung nach Hertz: Niemann, Winter, Höhn, Stahl,
  Maschinenelemente 1, 5. Aufl., Springer Vieweg 2019, Tab. 13.1 (S. 372: p_H = √(K·E'/π) mit
  K = F_N/(D_1·l_eff), halbe Druckbreite b = 2·D_1·p_H/E'), Gl. (13.5) (S. 376:
  1/E' = ½·((1 − ν₁²)/E₁ + (1 − ν₂²)/E₂)) und Gl. (13.6) (S. 376: R = R₁R₂/(R₁ + R₂)); mit starrem
  Gegenkörper wird E' = 2E/(1 − ν²), und b entspricht b_H oben. Für Kunststoffräder rechnet
  VDI 2736 Blatt 2:2014-06 die Flankenpressung ebenso nach Hertz, Gl. (14) mit dem
  Elastizitätsfaktor Z_E nach Gl. (15) (S. 15), mit dem Elastizitätsmodul des Kunststoffs bei
  Betriebstemperatur; deshalb E = 2282 MPa bei 80 °C. Dasselbe tun Erhard und Strickle,
  Maschinenelemente aus thermoplastischen Kunststoffen, Band 2, VDI-Verlag 1978, Abschnitt
  6.6.2.3, Gl. (6-23), S. 168: Hertzsche Pressung für Kunststoffräder mit dem Materialfaktor Z_M
  der Paarung Stahl/Kunststoff in Abhängigkeit von der Flankentemperatur (Bild 6-29, S. 170);
  Abschnitt 6.6.2.4, S. 173: der Modul hängt außer von der Temperatur von der
  Verformungsgeschwindigkeit ab, normalerweise wird der dynamisch gemessene Modul eingesetzt,
  und Kriechen unter Stillstandslast vergrößert die Verformung. Eine eigene Formel für die
  Breite der Berührfläche von Kunststoffrädern geben beide Quellen nicht; die Studie bildet sie
  deshalb nach der Hertzschen Linienberührung mit dem Modul bei Betriebstemperatur (Grenze
  FE-12). Die Halbbreite bestimmt hier nur die Breite der Lastverteilung; die Empfindlichkeit
  in Abschnitt 4 zeigt, dass sie die Absolutwerte um einige Prozent, das Konvergenzverhalten
  aber nicht ändert.
  Für die Kopfverschiebung geben Erhard und Strickle mit Gl. (6-27), S. 173, eine Näherung
  (f_k = 3F_U/(2b cos α₀)·φ·(ψ₁/E₁ + ψ₂/E₂)); sie taugt als Plausibilitätsvergleich für die
  Verschiebung aus der FE-Rechnung, nicht für die Netzstudie.
- **Fesselung:** Bohrung und beide Schnittebenen fest, wie im Deck.
- **Werkstoff:** isotrop, E = 2282 MPa, ν = 0,30 (isotrope Zeile der Werkstoffkarte bei 80 °C,
  Plan O1).
- **Bewertet:** größte Hauptspannung σ1 an der Fußoberfläche der belasteten Flanke
  (Knotenmittel; Fußformpunkt bis Lückenmitte), Verschiebung des Kopfmittenknotens und der
  belasteten Kopfecke, Formänderungsenergie U des Sektors (globales Maß, konvergiert beim
  Verschiebungsansatz monoton).
- **Reihen:** gleichmäßig h, h/2, h/3, h/4 und jede Richtung des Dialogs für sich (Zahnhöhe ×2,
  ×3; Zahnfuß ×2, ×3; Zahndicke ×2, ×3, ×4). Änderung zur vorigen Stufe und Richardson-
  Extrapolation f(h) = f_0 + C hᵖ über die letzten drei Stufen (für die Empfehlung ein Ausgleich
  über alle Stufen). Grundlage des Fehlermodells: die A-priori-Abschätzung der
  Verschiebungsmethode bei Bathe, Finite Element Procedures, Prentice-Hall 1996, Abschnitt 4.3.5,
  Gl. (4.101) und (4.102), S. 247: der Fehler der Lösung ist durch c·hᵏ beschränkt, k die Ordnung
  des vollständigen Polynoms des Elements (k = 1 beim Vierknotenelement, deshalb erste Ordnung
  für Spannungen an der Oberfläche, höhere für Verschiebungen); Abschnitt 4.3.6, S. 254: die
  Spannungssprünge zwischen Elementen nehmen mit der Verfeinerung ab, mit einer Rate, die die
  Elementordnung bestimmt. Die Extrapolation auf h → 0 aus einer Netzfolge ist das Verfahren von
  Richardson, bei Dahmen und Reusken, Numerik für Ingenieure und Naturwissenschaftler, 3. Aufl.,
  Springer 2022, Abschnitt 10.4, S. 528, als allgemeines Konzept: eine Näherung N(h) mit der
  asymptotischen Entwicklung N(h) = J + c₁hᵠ + c₂h²ᵠ + … + R(h), Gl. (10.35), wird auf h = 0
  extrapoliert, Gl. (10.36). Hier wird die Entwicklung nach dem ersten Glied abgebrochen und der
  Exponent aus den Stufen mitbestimmt (f₀ = J, C = c₁, p = q).
- **Prüfung des Lösers:** der Sektor mit einem Zahn (859 Knoten, unter der Grenze der Learning
  Edition) als ebenes Deck mit CPE4, CPE4R und CPE4I in Abaqus 2025 LE, gleiche Lasten und
  Fesselung. Mit CPE4 stimmen Verschiebungen aller Knoten und Spannungen an allen
  Integrationspunkten mit dem eigenen Löser auf die Druckgenauigkeit der `.dat`-Datei überein
  (≤ 7 · 10⁻⁵ relativ). Ein Vierknotenelement mit voller Integration (Lehrbuch) weicht dagegen um
  2 % in der Verschiebung und 15 % in der Fußspannung ab; so wurde die Formulierung gefunden.

## 3 Ergebnisse (kst-E, Rad, 5 Zähne + 2 zahnlose Segmente, 12 Kranzringe)

| Reihe | Stufe | Knoten je Schicht | Zahnhöhe | Zahnfuß | Zahndicke | σ1,max Fuß in MPa | u Kopfmitte in µm | u Kopfecke in µm | U in N mm je mm |
|---|---|---|---|---|---|---|---|---|---|
| Grundnetz | 1 | 3 719 | 20 | 80 | 10 | 125,42 | 203,80 | 203,85 | 3,5776 |
| gleichmäßig | 2 | 14 157 | 40 | 160 | 20 | 135,11 | 203,61 | 204,04 | 3,5790 |
| gleichmäßig | 3 | 31 315 | 60 | 240 | 30 | 138,89 | 203,65 | 204,12 | 3,5810 |
| gleichmäßig | 4 | 55 193 | 80 | 320 | 40 | 140,89 | 203,69 | 204,18 | 3,5825 |
| Zahnhöhe | 2 | 4 819 | 40 | 80 | 10 | 125,37 | 203,69 | 204,05 | 3,5768 |
| Zahnhöhe | 3 | 5 919 | 60 | 80 | 10 | 125,38 | 203,70 | 204,10 | 3,5777 |
| Zahnfuß | 2 | 5 919 | 20 | 160 | 10 | 125,46 | 203,97 | 204,02 | 3,5805 |
| Zahnfuß | 3 | 8 119 | 20 | 240 | 10 | 125,46 | 204,00 | 204,05 | 3,5810 |
| Zahndicke | 2 | 7 021 | 20 | 80 | 20 | 135,13 | 203,49 | 203,57 | 3,5758 |
| Zahndicke | 3 | 10 323 | 20 | 80 | 30 | 138,91 | 203,47 | 203,55 | 3,5761 |
| Zahndicke | 4 | 13 625 | 20 | 80 | 40 | 140,91 | 203,47 | 203,55 | 3,5763 |

Extrapolation (gleichmäßige Reihe): σ1,max konvergiert mit der Ordnung p = 0,84 gegen 148,2 MPa;
die Stufen liegen −15,4 %, −8,9 %, −6,3 % und −4,9 % darunter. Die Reihe Zahndicke liefert
dasselbe (p = 0,85, Grenzwert 148,1 MPa). Die Kopfverschiebung ändert sich in keiner Reihe um mehr
als 0,2 %, die Formänderungsenergie um höchstens 0,14 %.

Dieselben Reihen mit dem Element mit inkompatiblen Moden (Gegenstück von C3D8I; eigener Löser,
`--formulation incompatible_modes`):

| Reihe | Stufe | Knoten je Schicht | σ1,max Fuß in MPa | u Kopfmitte in µm | u Kopfecke in µm |
|---|---|---|---|---|---|
| Grundnetz | 1 | 3 719 | 141,61 | 201,99 | 202,25 |
| gleichmäßig | 2 / 3 / 4 | 14 157 / 31 315 / 55 193 | 147,54 / 148,50 / 148,63 | 203,15 / 203,44 / 203,57 | 203,54 / 203,91 / 204,06 |
| Zahnhöhe | 2 / 3 | 4 819 / 5 919 | 141,58 / 141,59 | 201,86 / 201,87 | 202,20 / 202,24 |
| Zahnfuß | 2 / 3 | 5 919 / 8 119 | 141,76 / 141,86 | 202,18 / 202,22 | 202,32 / 202,36 |
| Zahndicke | 2 / 3 / 4 | 7 021 / 10 323 / 13 625 | 147,61 / 148,50 / 148,61 | 203,07 / 203,33 / 203,42 | 203,46 / 203,72 / 203,82 |

Extrapolation (Reihe Zahndicke): σ1,max konvergiert schnell (p = 4,7) gegen 148,65 MPa; die Stufen
liegen −4,7 %, −0,7 %, −0,1 % und −0,03 % darunter. Die Kopfverschiebung konvergiert gegen
203,6 µm (p = 1,8); Grundnetz −0,8 %, Zahndicke ×2 −0,2 %. Die gleichmäßige Reihe gibt denselben
Grenzwert (148,68 MPa).

Prüfung in der Learning Edition (Sektor mit einem Zahn, Grundnetzdichte):

| Element | u Kopfmitte in µm | σ1,max Fuß (Knotenmittel) in MPa | σ1,max Fuß (Gaußpunkte) in MPa | Formänderungsenergie in N mm | Hourglass-Energie in N mm |
|---|---|---|---|---|---|
| CPE4 | 192,155 | 125,16 | 120,36 | 3,3528 | – |
| eigener Löser, selektiv reduziert | 192,155 | 125,17 | 120,36 | 3,3528 | – |
| CPE4R | 194,46 | 114,19 | 114,23 | 3,3949 | 3,9 · 10⁻⁴ (0,01 %) |
| CPE4I | 190,061 | 141,80 | 129,07 | 3,3207 | – |
| eigener Löser, inkompatible Moden | 190,060 | 141,81 | 129,07 | 3,3207 | – |

CPE4 und der eigene Löser stimmen auf die Druckgenauigkeit überein (Verschiebungen aller Knoten
und Spannungen aller Integrationspunkte ≤ 7 · 10⁻⁵); CPE4I und das Element mit inkompatiblen
Moden auf 1,3 · 10⁻⁵ in der Verschiebung und 0,6 % in den Spannungen an den Gaußpunkten (Abaqus
leitet sein Element nach Simo und Rifai her, die Kopfverschiebung und die Fußspannung am Knoten
stimmen auf 0,01 %). (Die Werte des Einzahnsektors sind wegen der nahen Fesselung nicht gleich
denen des Fünfzahnsektors; verglichen wird je Zeile.)

Empfindlichkeit des Grundnetzes gegen das Lastmodell: halbe Breite der Pressungsverteilung
σ1 = 131,8 MPa und u = 211,3 µm, doppelte Breite 118,1 MPa und 189,2 µm (die breite Verteilung
wird am Kopfformkreis abgeschnitten und verschiebt den Lastschwerpunkt nach innen); Punkt D
statt B 86,9 MPa und 102,2 µm. Das Lastmodell verschiebt also die Absolutwerte um etwa 5 %, das
Konvergenzverhalten der Reihen nicht.

## 4 Deutung

1. **Kopfverschiebung:** Das Grundnetz ist konvergiert (Abweichung unter 0,2 % über alle Reihen,
   alle drei Elementformulierungen innerhalb von 1,2 %). Für die Verschiebung am Zahnkopf genügt
   die Dichte der Vorlage.
2. **Fußspannung an der Oberfläche:** Die Dichte der Vorlage reicht für die Oberflächenspannung
   nicht. Sie konvergiert nur mit erster Ordnung und liegt mit der Formulierung von C3D8 um 15 %
   unter dem extrapolierten Grenzwert. Entscheidend ist allein die Richtung normal zur
   Fußoberfläche (Sehnen der Zahndicke): ×2 bringt −8,8 %, ×4 noch −4,9 %. Zahnhöhe und
   Fußrundung entlang der Oberfläche sind mit der Vorlage konvergiert (unter 0,1 %). Grund: das
   Element hält den volumetrischen Dehnungsanteil je Element konstant; an einer Kerboberfläche
   hat gerade der hydrostatische Anteil (σ_rr = 0 an der Oberfläche, steil ansteigend nach innen)
   einen starken Gradienten, den die dünnen Oberflächenelemente (erste Schicht 0,02 mm bei
   ρ_F ≈ 0,38 mm) mit dieser Formulierung nur mit dem Fehler der Elementgröße wiedergeben.
3. **Elementtyp:** Die Formulierung wiegt so schwer wie die Dichte. Mit reduzierter Integration
   (CPE4R, dem ebenen Gegenstück von C3D8R aus dem Referenzdeck) liegt der Knotenwert 9 % unter
   CPE4, also rund 23 % unter dem Grenzwert; die Hourglass-Energie ist mit 0,01 % der
   Formänderungsenergie unkritisch (Energiebilanz nach Stommel u. a., S. 428). Mit
   inkompatiblen Moden (CPE4I, Gegenstück von C3D8I) liegt der Knotenwert im Grundnetz 4,7 %
   unter dem Grenzwert, mit Zahndicke ×2 noch 0,7 %, und die Konvergenz ist schnell (p ≈ 4,7).
   Die archivierte Arbeit (ADR-018 dort) war ebenfalls bei C3D8I für den Fuß gelandet.
4. **Grenzwert:** Drei Formulierungen weisen auf denselben Grenzwert: volle Integration des
   Lehrbuchs 147 bis 152 MPa auf den Stufen 1 bis 4, selektiv reduziert extrapoliert 148,2 MPa,
   inkompatible Moden extrapoliert 148,7 MPa. Die Hauptspannung an der Fußoberfläche des Rades
   bei 16 Nm beträgt mit diesem Lastmodell also 148 bis 149 MPa.

## 5 Entscheidungsvorlage für das Einfrieren des Radnetzes

Die Dichte und der Elementtyp sind die Entscheidung des Verfassers (Grenze FE-10). Die Zahlen
oben stützen drei Wege (Abweichungen gegen den Grenzwert 148,7 MPa und 203,6 µm):

| Weg | Elementtyp des Rades | Zahndicke-Faktor | Knoten je Schicht (5 + 2 Zähne) | Knoten bei 80 Schichten | σ1 an der Fußoberfläche | Kopfverschiebung |
|---|---|---|---|---|---|---|
| A (wie Referenz) | C3D8R | 1 | 3 719 | 301 239 | etwa −23 % | −0,2 % |
| B | C3D8I | 1 | 3 719 | 301 239 | −4,7 % | −0,8 % |
| C | C3D8I | 2 | 7 021 | 568 701 | −0,7 % | −0,2 % |

Empfehlung aus den Zahlen: Weg C, wenn die Rechenzeit des Pilotlaufs es zulässt (etwa 1,9-fache
Knotenzahl gegenüber dem Grundnetz, dazu die inneren Freiheitsgrade von C3D8I), sonst Weg B mit
dem bekannten Abschlag von 5 % auf die Oberflächenspannung. C3D8I kostet je Element 13 innere
Freiheitsgrade (kondensiert), also längere Rechenzeit als C3D8R, dafür keine Hourglass-Steuerung;
die Kontaktformulierung ist davon unberührt. Zahnhöhe und Fußrundung bleiben bei der Dichte der
Vorlage.

## 5b Empfehlung je Verzahnung

`python scripts/fe_mesh_convergence.py recommend --case <Fall> --tolerance-stress 0,02
--tolerance-displacement 0,01 [--max-nodes-per-layer N]` rechnet für eine Verzahnung die Leiter
der Zahndicke und Fußschichten (10/3, 14/4, 20/6, 26/8, 32/10, 40/12; Zahnhöhe, Zahnfuß und Kranz
bleiben bei der Vorlage, weil die Studie sie als konvergiert zeigt) mit dem Element mit
inkompatiblen Moden, gleicht f = f₀ + C·hᵖ über alle Stufen aus und nennt das gröbste Netz, dessen
σ1 an der Fußoberfläche und Kopfverschiebung innerhalb der Toleranzen zum Grenzwert liegen und das
das Knotenbudget einhält. Für kst-E:

| Zahndicke | Fußschichten | Knoten je Schicht | Knoten bei 80 Schichten | σ1 Fuß in MPa | Fehler | u Kopf in µm | Fehler |
|---|---|---|---|---|---|---|---|
| 10 | 3 | 3 719 | 301 239 | 141,61 | −4,75 % | 201,99 | −0,74 % |
| 14 | 4 | 5 063 | 410 103 | 145,97 | −1,82 % | 202,75 | −0,37 % |
| 20 | 6 | 7 021 | 568 701 | 147,61 | −0,72 % | 203,07 | −0,21 % |
| 26 | 8 | 8 979 | 727 299 | 148,43 | −0,17 % | 203,33 | −0,08 % |
| 32 | 10 | 10 937 | 885 897 | 148,61 | −0,05 % | 203,40 | −0,05 % |
| 40 | 12 | 13 625 | 1 103 625 | 148,60 | −0,05 % | 203,43 | −0,03 % |

Grenzwerte: σ1 = 148,68 MPa (Ordnung 3,2), u = 203,50 µm (Ordnung 2,1). Mit 2 % / 1 % Toleranz
fällt die Wahl auf Zahndicke 14 mit 4 Fußschichten, mit 1 % / 0,5 % auf Zahndicke 20 mit
6 Fußschichten. Die Toleranzen sind die Wahl des Anwenders; die Tabelle zeigt, was jede Stufe
kostet und bringt.

In einer zweiten Phase werden die übrigen Anzahlen eine nach der anderen von der Vorlage aus
vergröbert, solange beide Größen innerhalb der Toleranzen zu den Grenzwerten bleiben (Zahnhöhe
12, 9, 6; Kopfkantenbruch 1; Zahnfuß 60, 40, 20; Kranzringe 8, 6, 4; Spalten im zahnfreien Segment
3, 2). Für die Zahnhöhe gilt zusätzlich eine Untergrenze aus dem Kontakt: mindestens drei Elemente
je Hertzscher Halbbreite entlang der aktiven Flanke (kst-E: 19; die Vorlage hat 18 und wird
deshalb nicht vergröbert), weil
Fußspannung und Kopfverschiebung die Flankenteilung kaum spüren, der Kontaktdruck des Ritzels sie
aber braucht. Ergebnis für kst-E bei 2 % / 1 %:

| Größe | Wert | Knoten je Schicht | σ1 Fehler | u Fehler | angenommen |
|---|---|---|---|---|---|
| Zahnhöhe | 12 | – | – | – | nein (Untergrenze 19) |
| Kopfkantenbruch | 1 | 4 988 | −1,7 % | −0,3 % | ja |
| Zahnfuß | 60 | 4 238 | −1,9 % | −0,3 % | ja |
| Zahnfuß | 40 | 3 488 | −2,2 % | −0,4 % | nein |
| Kranzringe | 8 / 6 / 4 | 4 082 / 4 004 / 3 926 | −1,9 / −1,9 / −2,0 % | −0,4 / −0,4 / −0,5 % | ja |
| Spalten zahnfreies Segment | 3 / 2 | 3 908 / 3 890 | −2,0 % | −0,5 % | ja |

Empfehlung für kst-E: Zahnhöhe 18 + 1, Zahnfuß 60, Zahndicke 14, Fußschichten 4, Kranzringe 4,
Spalten im zahnfreien Segment 2, Element C3D8I: 3 890 Knoten je Schicht, 315 000 Knoten bei
80 Schichten, also etwa so viele wie das gestrige Netz (301 000), aber mit −1,9 % statt −23 %
(C3D8R) oder −4,7 % (C3D8I am gestrigen Netz) an der Fußoberfläche. Der Elementtyp wird dem
Anwender mit der Empfehlung genannt.

## 5a Decks für die Abaqus-Vollversion

`python scripts/fe_mesh_convergence.py decks --case kst_e` schreibt nach
`80_output/fe/kst_e/full_licence/` die ebenen Decks (Grundnetz, Zahndicke ×2/×3/×4, gleichmäßig
×2, je CPE4R/CPE4/CPE4I) und die Volumendecks (Grundnetz mit 20, 40 und 80 Schichten, je
C3D8R/C3D8I; Lasten des ebenen Lastfalls über die Breite verteilt), dazu `run_all.bat`,
`manifest.json` und eine Anleitung (`README.md`). Nach dem Rechnen auf der Vollversion werden die
`.dat`-Dateien zurückkopiert; `compare` stellt die Abaqus-Werte neben die des eigenen Lösers und
wertet die Schichtzahl aus (Radmitte, Stirnfläche).

**Ergebnis des Laufs auf der Vollversion (2026-10-06, alle 21 Decks durchgelaufen):** Die ebenen
Decks bestätigen den eigenen Löser auf allen Stufen (CPE4 gleich auf alle gedruckten Stellen,
CPE4I auf 0,01 MPa und 0,01 µm) und ergänzen die Reihe mit CPE4R, dem ebenen Gegenstück von
C3D8R:

| Zahndicke | CPE4R | CPE4 | CPE4I |
|---|---|---|---|
| ×1 | 114,85 | 125,42 | 141,60 |
| ×2 | 127,94 | 135,13 | 147,61 |
| ×3 | 133,57 | 138,91 | 148,50 |
| ×4 | 136,69 | 140,90 | 148,62 |
| Grenzwert (Ordnung) | 150,5 (0,7) | 148,1 (0,85) | 148,7 (4,6) |

σ1,max an der Fußoberfläche in MPa; die Hourglass-Energie von CPE4R bleibt unter 0,04 % der
Formänderungsenergie. Die Volumendecks (Grundnetz, Lasten des ebenen Lastfalls über die Breite
verteilt) zeigen die Schichtzahl:

| Schichten | Element | Knoten | u Kopf Radmitte in µm | σ1 Fuß Radmitte in MPa | σ1 Fuß größte Schicht | σ1 Fuß Stirnfläche | Rechenzeit |
|---|---|---|---|---|---|---|---|
| 20 | C3D8I | 78 099 | 204,87 | 143,49 | 147,20 | 108,34 | 7 s |
| 40 | C3D8I | 152 479 | 204,93 | 143,53 | 147,25 | 101,57 | – |
| 80 | C3D8I | 301 239 | 204,95 | 143,55 | 147,28 | 96,80 | 28 s |
| 20 | C3D8R | 78 099 | 209,04 | 116,39 | 119,39 | 95,63 | – |
| 80 | C3D8R | 301 239 | 209,09 | 116,38 | 119,31 | 83,84 | – |

Zwischen 20 und 80 Schichten ändern sich Kopfverschiebung und Fußspannung in der Radmitte und im
Maximum über die Schichten um weniger als 0,05 %: Für diese Größen reichen 20 Schichten. Nur der
Wert unmittelbar an der Stirnfläche fällt mit feinerer Teilung weiter (108 → 97 MPa); er ist der
Wert am freien Rand und keine Zielgröße der Auswertung. Der Vergleich mit dem ebenen Modell
(C3D8I, Radmitte 143,5 MPa und 204,9 µm gegen 141,6 MPa und 202,0 µm) zeigt, dass der ebene
Dehnungszustand das Rad um 1,4 % zu steif nimmt; für die Netzstudie ist das ohne Belang, für
Absolutwerte zählt das Volumenmodell.

## 5c Elementtyp und geometrische Nichtlinearität (2026-10-07)

Die Stellungsdateien des Paars (ADR-116, Schritt S5) brachen mit NLGEOM=YES in jedem Lauf am
feinen Netz (Pilot 1, drei Varianten der Kontaktformulierung) und am Grobmodell der Learning
Edition im 12-Nm-Schritt ab, mit der Warnung negativer Eigenwerte der Systemmatrix ab dem
ersten Lastinkrement (1,6 Nm am Ritzel), wachsend mit der Last, vor jeder Kontaktänderung und
bei allen drei Kontaktformulierungen gleich. Der Elementtest am Grobmodell (1 Zahn, 2 Schichten,
Knoten-zu-Fläche, sonst identisch; `80_output/fe/kst_e/le_tests/element_nlgeom`) trennt die
Ursache:

| Element | NLGEOM=NO | NLGEOM=YES |
|---|---|---|
| C3D8I | alle Schritte, 0 Warnungen | alle Schritte, 29 Warnungen ab 8 Nm, Inkrement 1 |
| C3D8 | alle Schritte, 0 Warnungen | alle Schritte, 0 Warnungen |
| C3D8R | alle Schritte, 0 Warnungen | alle Schritte, 0 Warnungen |

Die negativen Eigenwerte entstehen allein aus den inkompatiblen Moden von C3D8I in der
geometrisch nichtlinearen Formulierung; das Elementhandbuch von Abaqus 2025 beschränkt diese
Elemente auf kleine Druckdehnungen („Using incompatible mode elements in large-strain
applications"). Folgen für die Elementwahl: Die isotrop elastische Stufe W1 wird geometrisch
linear gerechnet (NLGEOM=YES ändert Stützmoment, Ritzeldrehung und Pressung bei 8 Nm um
höchstens 0,6 %), dort bleibt C3D8I mit −1,9 % an der Fußoberfläche die genaueste Wahl. Die
elastisch-plastischen Stufen W2 bis W4 brauchen NLGEOM=YES (Stommel, Stojek, Korte 2018, S. 2,
S. 52, S. 474) und damit ein Netz ohne C3D8I. Die Leiter mit der Formulierung von C3D8
(`recommend --formulation selectively_reduced`, 20 Schichten) konvergiert an der Fußoberfläche
nur mit Ordnung 0,81:

| Zahndicke | Fußschichten | Knoten je Schicht | Knoten Volumen (20 Schichten) | σ1,max Fuß in MPa | Fehler |
|---|---|---|---|---|---|
| 10 | 3 | 3 719 | 78 099 | 125,42 | −15,4 % |
| 14 | 4 | 5 063 | 106 323 | 130,46 | −12,0 % |
| 20 | 6 | 7 021 | 147 441 | 135,14 | −8,8 % |
| 26 | 8 | 8 979 | 188 559 | 137,94 | −6,9 % |
| 32 | 10 | 10 937 | 229 677 | 139,71 | −5,7 % |
| 40 | 12 | 13 625 | 286 125 | 140,91 | −4,9 % |

Grenzwert 148,23 MPa; die Kopfverschiebung liegt auf jeder Stufe innerhalb 0,2 %. Keine Stufe
erreicht 2 %. Zur Entscheidung des Anwenders (FE-10) stehen: C3D8I für die linearen W1-Läufe und
C3D8 mit dem dokumentierten Abschlag für W2 bis W4 auf demselben Netz (der Elementtyp ist eine
Zeile der Netzdatei, Elementnummern und die Zuordnung der Faserorientierung bleiben), oder ein
feinerer Fuß für alle Stufen.

Bestätigung am feinen Netz (`pilot_20layers_c3d8_variants`, Vollversion, 2026-10-07): das
Pilotnetz (20 Schichten, 81 690 Knoten) mit C3D8 statt C3D8I rechnet linear wie mit NLGEOM=YES
alle vier Schritte in je 6 Inkrementen ohne negativen Eigenwert durch (140 s und 161 s gegen
173 s für C3D8I linear). Die globalen Größen der Stellungsdatei hängen weder von der
geometrischen Nichtlinearität noch vom Elementtyp merklich ab:

| Lauf | RM3 Rad 8 / 12 / 16 Nm in N mm | Ritzeldrehung 16 Nm in rad | CPRESS max 8 / 12 / 16 Nm in MPa |
|---|---|---|---|
| C3D8I, linear | −7 911 / −11 834 / −15 798 | 3,467e-3 | 59,0 / 67,8 / 74,9 |
| C3D8, linear | −7 911 / −11 832 / −15 796 | 3,472e-3 | 59,6 / 68,0 / 74,9 |
| C3D8, NLGEOM=YES | −7 915 / −11 845 / −15 814 | 3,487e-3 | 59,5 / 67,5 / 74,4 |

Regel seit 2026-10-07 (`deck.NLGEOM_OF_STEP`, `deck.ELEMENT_TYPE_OF_STEP`): W1 und W3
geometrisch linear mit C3D8I, W2 und W4 geometrisch nichtlinear mit C3D8 auf demselben Netz.
Fußspannungen einer C3D8-Stufe sind mit einer C3D8I-Stufe nur auf gleichem Elementtyp oder
gegen den extrapolierten Grenzwert vergleichbar (Abschlag etwa 10 % bei 14 / 4). Offen bleibt
die Dichte (FE-10).

## 6 Grenzen der Studie

- Ebener Dehnungszustand, isotrop linear elastisch, Pressungsverteilung statt Kontaktiteration;
  mit der Faserorientierung (Stufen W3, W4) ändert sich die Steifigkeit, nicht die Konvergenz
  des Netzes.
- Die Schichtzahl über die Zahnbreite ist auf der Vollversion geprüft (Abschnitt 5a): 20, 40
  und 80 Schichten unterscheiden sich in Kopfverschiebung und Fußspannung um weniger als
  0,05 %; Empfehlung für den Stapel 40 Schichten (0,375 mm, Seitenverhältnis der dünnsten
  Fußschicht etwa 19), 20 für schnelle Prüfläufe, 80 nur wenn die Kontaktverteilung über die
  Breite ausgewertet werden soll.
- Die Leiter der Empfehlung ändert nur Zahndicke und Fußschichten; wer Zahnhöhe oder Zahnfuß
  gröber als die Vorlage wählt, prüft das mit `study` oder eigenen Stufen nach.
- Die Hertzsche Halbbreite wird mit dem Modul bei Betriebstemperatur gebildet, wie VDI 2736
  Blatt 2 Gl. (15) und Erhard/Strickle Gl. (6-23) es für die Flankenpressung tun; sie formt nur
  die Lastverteilung der Studie.
- Die Quellen der Hertzschen Linienberührung (Maschinenelemente 1) und des Buchs von Stommel
  u. a. sind im Quellenregister eingetragen und warten auf die Bestätigung des Verfassers; bis
  dahin zitiert der Code sie nur in den Docstrings.

## 7 Erzeugung

```
python scripts/fe_mesh_convergence.py study  --case kst_e --levels 4
python scripts/fe_mesh_convergence.py study  --case kst_e --levels 4 --formulation incompatible_modes
python scripts/fe_mesh_convergence.py verify --case kst_e
python scripts/fe_mesh_convergence.py decks  --case kst_e
python scripts/fe_mesh_convergence.py compare --case kst_e
python scripts/fe_mesh_convergence.py recommend --case kst_e --tolerance-stress 0.02 --tolerance-displacement 0.01
python scripts/fe_mesh_convergence.py recommend --case kst_e --formulation selectively_reduced --layers 20
python scripts/build_fe_decks.py mesh --case kst_e --teeth 5 --layers 80 --over-tooth-thickness 14 --root-layers 4
python scripts/build_fe_decks.py decks --layers 20 --element-type C3D8 --over-tooth-height 18 --at-tip-edge-break 1 --at-tooth-root 60 --over-tooth-thickness 14 --root-layers 4 --rings 4 --shoulder-columns 2 --positions pilot --variants n2s nlgeom_n2s --out 80_output/fe/kst_e/pilot_20layers_c3d8_variants
```

Der Elementtest in der Learning Edition (Abschnitt 5c) ruft `decks(...)` je Elementtyp mit den
Zahlen von `LE_COUNTS` (1 Zahn, 2 Schichten, Sitzbogen 0,01 mm, Sehnen 0,4 mm) und den Varianten
`n2s`, `nlgeom_n2s` auf und startet `abq2025le.bat job=<Name> interactive ask_delete=OFF` je
Datei; die Zählung der Warnungen `NEGATIVE EIGENVALUES` in der `.msg` steht in
`80_output/fe/kst_e/le_tests/element_nlgeom/ELEMENT_TEST.md`.

Ausgabe unter `80_output/fe/kst_e/convergence/` (nicht versioniert): `convergence.md`,
`convergence.csv`, die Bilder, `verification.md`, die Learning-Edition-Decks `le_cpe4*.inp` mit
ihren `.dat`-Dateien.
