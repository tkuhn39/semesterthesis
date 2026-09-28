# Normenlandkarte Stirnräder (gerad- und schrägverzahnt, Außenverzahnung)

Stand 2026-09-28, verifiziert aus den Norm-PDFs in `00_literatur/05_normen_und_richtlinien/`.
Pflege: bei jeder Änderung der Berechnungsbasis (ADR) aktualisieren. Gleichungsebene der Unterschiede:
`norm_differences.md` (generiert aus `expected_differences.yaml`).

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

Die Einzelabweichungen mit Zahlenbeispiel entstehen in Inkrement 2–6 und werden in
`expected_differences.yaml` geführt.
