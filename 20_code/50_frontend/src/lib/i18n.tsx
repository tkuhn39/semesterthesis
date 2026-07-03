"use client";

// Minimal i18n (plan v2 workstream D): every new view uses keys from day one; the locale
// switch lives in the workbench header. German is the default, English complete for handover.

import { createContext, useContext, useState, type ReactNode } from "react";

export type Locale = "de" | "en";

const DICT: Record<string, { de: string; en: string }> = {
  "app.title": { de: "Zahnfuß-Workbench", en: "Tooth Root Workbench" },
  "app.subtitle": {
    de: "FE-Zahnfußspannung · Kunststoff-Stirnräder",
    en: "FE tooth-root stress · plastic spur gears",
  },
  "tree.model": { de: "Modell", en: "Model" },
  "tree.stage": { de: "Stirnradstufe [kst-E]", en: "Cylindrical stage [kst-E]" },
  "tree.geometry": { de: "Geometrie", en: "Geometry" },
  "tree.capacity": { de: "Tragfähigkeit", en: "Load capacity" },
  "tree.dynamics": { de: "Dynamikfaktoren", en: "Dynamic factors" },
  "tree.variation": { de: "Stufenvariation", en: "Stage variation" },
  "tree.pinion": { de: "Stahlritzel [z=51]", en: "Steel pinion [z=51]" },
  "tree.wheel": { de: "Kunststoffrad [z=52]", en: "Plastic wheel [z=52]" },
  "tree.toothform": { de: "Zahnform", en: "Tooth form" },
  "tree.mesh": { de: "FE-Mesh", en: "FE mesh" },
  "tree.calcs": { de: "Berechnungen", en: "Calculations" },
  "tree.deck": { de: "FE-Abwälzmodell (Deck)", en: "FE rolling model (deck)" },
  "tree.overview": { de: "Übersicht", en: "Overview" },
  "quick.title": { de: "Ergebnis-Schnellansicht", en: "Quick results" },
  "quick.empty": {
    de: "Berechnung ausführen, um Ergebnisse zu sehen.",
    en: "Run a calculation to see results.",
  },
  "msg.title": { de: "Meldungen", en: "Messages" },
  "msg.ready": { de: "Bereit.", en: "Ready." },
  "msg.backendOffline": { de: "Backend offline", en: "backend offline" },
  "common.run": { de: "Berechnen", en: "Compute" },
  "common.running": { de: "Berechnet…", en: "Computing…" },
  "common.download": { de: "Herunterladen", en: "Download" },
  "common.value": { de: "Wert", en: "Value" },
  "common.attribute": { de: "Attribut", en: "Attribute" },
  "common.unit": { de: "Einheit", en: "Unit" },
  "common.pinion": { de: "Ritzel", en: "Pinion" },
  "common.wheel": { de: "Rad", en: "Wheel" },
  "geo.main": { de: "Hauptgeometrie", en: "Main geometry" },
  "geo.mesh": { de: "Eingriff & Überdeckung", en: "Mesh & contact ratios" },
  "geo.diameters": { de: "Durchmesser", en: "Diameters" },
  "mesh.params": { de: "Vernetzung", en: "Meshing" },
  "mesh.density": { de: "Netzfeinheit", en: "Mesh density" },
  "mesh.densityRoot": { de: "Feinheit Zahnfuß", en: "Root density" },
  "mesh.densityFlank": { de: "Feinheit Zahnflanke", en: "Flank density" },
  "mesh.fillet": { de: "Zahnfußgeometrie", en: "Root fillet geometry" },
  "mesh.fillet.standard": { de: "Standard (Norm, ρ_F)", en: "Standard (norm, ρ_F)" },
  "mesh.fillet.elliptic": { de: "Elliptisch", en: "Elliptic" },
  "mesh.fillet.bezier": { de: "Bézier (Voith)", en: "Bézier (Voith)" },
  "mesh.fillet.bionic": { de: "Bionisch (Zugdreiecke)", en: "Bionic (tension triangles)" },
  "mesh.generate": { de: "Mesh erzeugen", en: "Generate mesh" },
  "mesh.stats": { de: "Mesh-Qualität", en: "Mesh quality" },
  "mesh.minJ": { de: "min. Jacobi-Güte", en: "min scaled Jacobian" },
  "mesh.below": { de: "Zellen < 0.35", en: "cells < 0.35" },
  "mesh.hexes": { de: "Hexaeder", en: "hexahedra" },
  "mesh.nodes": { de: "Knoten", en: "nodes" },
  "mesh.layers": { de: "Schichten über Zahnbreite", en: "face-width layers" },
  "mesh.convergence": { de: "Konvergenz-Schnelltest", en: "Convergence quick check" },
  "mesh.convergence.run": { de: "Konvergenz prüfen", en: "Check convergence" },
  "mesh.convergence.root": { de: "Zahnfuß", en: "Tooth root" },
  "mesh.convergence.flank": { de: "Zahnflanke", en: "Tooth flank" },
  "mesh.convergence.level": { de: "konvergiert ab Stufe", en: "converged at level" },
  "mesh.filletCompare": { de: "Fußkurven-Vergleich (2D-FE)", en: "Fillet ranking (2D FE)" },
  "mesh.filletCompare.run": { de: "Strategien vergleichen", en: "Compare strategies" },
  "mesh.clearance": { de: "Freigang", en: "clearance" },
  "deck.title": { de: "Implizites Abwälzmodell", en: "Implicit rolling model" },
  "deck.torque": { de: "Moment an Rad 2", en: "Torque at gear 2" },
  "deck.rollPositions": { de: "Wälzstellungen", en: "Roll positions" },
  "deck.steelShell": {
    de: "Stahlseite ideal steif (Rigid-Shell)",
    en: "Steel side ideally stiff (rigid shell)",
  },
  "deck.download": { de: "Deck (.inp) erzeugen", en: "Build deck (.inp)" },
  "toothform.title": { de: "Zahnform (erzeugte Kontur)", en: "Tooth form (as-cut contour)" },
  "variation.overlay": { de: "Varianten-Vergleich", en: "Variant comparison" },
  "variation.matrix": { de: "Material-Matrix", en: "Material matrix" },
  "tree.design": { de: "Auslegung", en: "Design" },
  "tree.pair": { de: "Paar & FE-Abwälzmodell", en: "Pair & FE rolling model" },
  "design.source": { de: "Quelle", en: "Source" },
  "design.preset": { de: "FZG-Preset laden …", en: "Load FZG preset …" },
  "design.uploadSte": { de: ".ste importieren", en: "Import .ste" },
  "design.orEdit": { de: "oder unten frei editieren", en: "or edit freely below" },
  "design.tool": { de: "Werkzeug-Bezugsprofil", en: "Tool reference profile" },
  "design.toolPreset": { de: "Profil wählen (DIN 3972 / ISO 53) …", en: "Choose profile (DIN 3972 / ISO 53) …" },
  "design.micro": { de: "Mikrogeometrie (ISO 21771 §6)", en: "Micro-geometry (ISO 21771 §6)" },
  "design.microNote": {
    de: "Wird mitgeführt und prüft die Flankensymmetrie; mechanisch wirksam ab Lastverteilung/3D-Kontakt.",
    en: "Carried through and checked for flank symmetry; mechanically active from load distribution/3D contact.",
  },
  "design.microActive": { de: "Mikrogeometrie aktiv — Spiegelsymmetrie ggf. aufgehoben", en: "Micro-geometry active — mirror symmetry may be dropped" },
  "design.apply": { de: "Stufe übernehmen", en: "Apply stage" },
  "design.tolerances": { de: "Toleranzen (ISO 1328-1)", en: "Tolerances (ISO 1328-1)" },
  "design.grade": { de: "Qualität", en: "Grade" },
  "cap.operating": { de: "Betriebsdaten", en: "Operating data" },
  "cap.quality": { de: "Verzahnungsqualität", en: "Gear quality" },
  "cap.static": { de: "Statische Spitzenlast (VDI 2736)", en: "Static peak load (VDI 2736)" },
  "cap.materials": { de: "Werkstoffe", en: "Materials" },
  "pair.stageLabel": { de: "Stufe", en: "Stage" },
  "pair.generate": { de: "Paar erzeugen", en: "Generate pair" },
  "pair.roll": { de: "Abwälzen (kinematisch gekoppelt)", en: "Roll (kinematically coupled)" },
  "pair.legend": { de: "Koordinatensysteme (Rot_Node_Rad1/2)", en: "Coordinate systems (Rot_Node_Rad1/2)" },
  "pair.legendLocked": { de: "DOF 1–5 gesperrt (Ring + Streben)", en: "DOF 1–5 locked (ring + struts)" },
  "pair.legendDriven": {
    de: "DOF 6 frei — grün: winkelgetriebenes Rad (Treppenkurve, Kunststoffseite)",
    en: "DOF 6 free — green: angle-driven gear (staircase, plastic side)",
  },
  "pair.legendTorque": {
    de: "DOF 6 frei — gelb: momentbelastetes Rad (aus M₂ umgerechnet)",
    en: "DOF 6 free — amber: torque-loaded gear (converted from M₂)",
  },
  "pair.gear1": { de: "Rad 1", en: "Gear 1" },
  "pair.gear2": { de: "Rad 2", en: "Gear 2" },
  "pair.axial": { de: "Axiale Lage", en: "Axial position" },
  "pair.axialOffset": { de: "Axialversatz", en: "Axial offset" },
  "pair.axialNote": {
    de: "Ansicht wie am Kleingetriebeprüfstand: links Rad 1, rechts Rad 2 (STE-Reihenfolge). Beide Räder sind symmetrisch um ihre Mittelebene extrudiert (Rot_Nodes in Radmitte, z = 0) und wälzen standardmäßig mittig aufeinander ab; der Versatz verschiebt jedes Rad entlang seiner Drehachse.",
    en: "View like the small-gear test rig: gear 1 left, gear 2 right (STE order). Both gears extrude symmetric about their mid-plane (rotation nodes at mid-width, z = 0) and roll centred on each other by default; the offset displaces each gear along its rotation axis.",
  },
  "mesh.fillet.trochoid": { de: "Werkzeug-Trochoide (DIN 3960)", en: "Tool trochoid (DIN 3960)" },
  "mesh.fillet.manufacturing": {
    de: "Optimierte Fußkurve: nur Spritzguss/Erodieren — geschnittene Räder brauchen werkzeugkonforme Füße (DIN 3972/Protuberanz).",
    en: "Optimized fillet: molded/WEDM only — cut gears need tool-conform roots (DIN 3972/protuberance).",
  },
  "mesh.preset.reference": { de: "Referenzdichte (FVA)", en: "Reference density (FVA)" },
  "mesh.preset.convRoot": { de: "Konvergenz Fuß (Fuß ×2)", en: "Root convergence (root ×2)" },
  "mesh.preset.convFlank": { de: "Konvergenz Flanke (Flanke ×2)", en: "Flank convergence (flank ×2)" },
  "mesh.preset.fine": { de: "Fein (×2/×2)", en: "Fine (×2/×2)" },
  "mesh.preset.custom": { de: "Benutzerdefiniert", en: "Custom" },
  "mesh.sweep": { de: "Fußkurven-Optimierung (Sweep)", en: "Fillet optimization (sweep)" },
  "mesh.sweep.best": { de: "Empfehlung", en: "Recommendation" },
  "tree.glossary": { de: "Legende & Parameter", en: "Legend & parameters" },
  "glossary.search": { de: "Suchen (Symbol, Name, Beschreibung) …", en: "Search (symbol, name, description) …" },
  "glossary.all": { de: "Alle", en: "All" },
  "glossary.allNorms": { de: "Alle Normen", en: "All norms" },
  "glossary.entries": { de: "Einträge", en: "entries" },
  "glossary.noMatch": { de: "Keine Treffer — Filter anpassen.", en: "No matches — adjust the filters." },
  "glossary.seeAlso": { de: "Siehe auch", en: "See also" },
  "glossary.filterNorm": { de: "Nach dieser Norm filtern", en: "Filter by this norm" },
  "glossary.jump": { de: "Zum Parameter springen", en: "Jump to parameter" },
};

const LocaleCtx = createContext<{ locale: Locale; setLocale: (l: Locale) => void }>({
  locale: "de",
  setLocale: () => {},
});

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>("de");
  return <LocaleCtx.Provider value={{ locale, setLocale }}>{children}</LocaleCtx.Provider>;
}

export function useLocale() {
  return useContext(LocaleCtx);
}

export function useT(): (key: string) => string {
  const { locale } = useContext(LocaleCtx);
  return (key: string) => DICT[key]?.[locale] ?? key;
}
