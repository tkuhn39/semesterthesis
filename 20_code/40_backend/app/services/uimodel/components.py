"""
@module: app.services.uimodel.components
@context: Domain layer — the concrete editor schema of the FVA-Workbench replica.
@role: OUR normative definitions (labels follow the FVA wording where FVA is correct —
       reference: 00_development_documentation/fva_label_reference.json + the screenshot
       set under 30_references_and_examples/31_FVA/Screenshots_Workbench — but slots,
       symbols and couplings follow the norms and our ADRs, never FVA defects).

       Implemented so far (pattern-setting, one tab at a time against its screenshot):
       * Berechnungsauswahl method matrix (drives tab visibility, user decision 2026-07-04)
       * Stirnradstufe → Geometrie (screenshot Stirnradstufe_Geometrie.png)
       * Stirnradstufe → Dynamisches Abwälzen (FEM) (Stirnradstufe_Dynamisches-Abwaelzen.png)
       * Getriebeeinheit → Betriebsdaten (Getriebeeinheit_Betriebsdaten.png)
       * dependency rules (norm-referenced lock/derive couplings)

       Remaining tabs (Toleranzen, Tragfähigkeit, VDI 2736, Werkstoff, Schmierstoff,
       Lastverteilung (FEM), Leistungsfluss, Kräfte und Momente, Steuerparameter,
       Flankenmodifikation, Radkörper) follow the same pattern — add the AttributeDefs,
       compose the TabDef, cross-check field-by-field against the screenshot AND the norm.
"""

from __future__ import annotations

from app.services.uimodel.schema import (
    AttributeDef,
    AttrOption,
    CalcMethod,
    ComponentDef,
    DependencyRule,
    RowRef,
    SectionDef,
    TabDef,
    UiSchema,
)

SCHEMA_VERSION = "0.1.0"


def _opt(value: str, de: str, en: str) -> AttrOption:
    return AttrOption(value=value, label_de=de, label_en=en)


# ------------------------------------------------------------------------------------------
# Berechnungsauswahl (screenshot Getriebeeinheit_Berechnungsauswahl.png) — the method matrix
# controls which editor tabs exist. ISO 6336 + VDI 2736 stay always-on: the Stufenvariation
# needs both complete for the analytic flank/root safeties (user decision 2026-07-04).
# ------------------------------------------------------------------------------------------
METHODS: list[CalcMethod] = [
    CalcMethod(
        id="iso_6336_2019",
        label_de="Tragfähigkeit nach ISO 6336 (2019)",
        label_en="Load capacity acc. ISO 6336 (2019)",
        group_de="Stirnradberechnung (Normtragfähigkeit)",
        group_en="Cylindrical gear calculation (standard capacity)",
        implemented=True,
        always_on=True,
        default_on=True,
        enables_tabs=[("cylindrical_mesh", "capacity")],
    ),
    CalcMethod(
        id="iso_6336_2006",
        label_de="Tragfähigkeit nach ISO 6336 (2006)",
        label_en="Load capacity acc. ISO 6336 (2006)",
        group_de="Stirnradberechnung (Normtragfähigkeit)",
        group_en="Cylindrical gear calculation (standard capacity)",
    ),
    CalcMethod(
        id="din_3990_1987",
        label_de="Tragfähigkeit nach DIN 3990 (1987)",
        label_en="Load capacity acc. DIN 3990 (1987)",
        group_de="Stirnradberechnung (Normtragfähigkeit)",
        group_en="Cylindrical gear calculation (standard capacity)",
    ),
    CalcMethod(
        id="agma_2101_d04",
        label_de="Tragfähigkeit nach AGMA 2101 (D04)",
        label_en="Load capacity acc. AGMA 2101 (D04)",
        group_de="Stirnradberechnung (Normtragfähigkeit)",
        group_en="Cylindrical gear calculation (standard capacity)",
    ),
    CalcMethod(
        id="vdi_2736_2014",
        label_de="Tragfähigkeit nach VDI 2736 (2014)",
        label_en="Load capacity acc. VDI 2736 (2014)",
        group_de="Stirnradberechnung (Normtragfähigkeit)",
        group_en="Cylindrical gear calculation (standard capacity)",
        implemented=True,
        always_on=True,
        default_on=True,
        enables_tabs=[("cylindrical_mesh", "vdi2736")],
    ),
    CalcMethod(
        id="fva_30_local",
        label_de="Lokale Beanspruchung (analytisch, FVA 30)",
        label_en="Local stress (analytic, FVA 30)",
        group_de="Stirnradberechnung (lokale Verfahren)",
        group_en="Cylindrical gear calculation (local methods)",
    ),
    CalcMethod(
        id="fva_411_pitting",
        label_de="Lokale Grübchensicherheit (FVA 411)",
        label_en="Local pitting safety (FVA 411)",
        group_de="Stirnradberechnung (lokale Verfahren)",
        group_en="Cylindrical gear calculation (local methods)",
    ),
    CalcMethod(
        id="fva_516_micropitting",
        label_de="Lokale Graufleckensicherheit (ISO 6336-22, FVA 516)",
        label_en="Local micropitting safety (ISO 6336-22, FVA 516)",
        group_de="Stirnradberechnung (lokale Verfahren)",
        group_en="Cylindrical gear calculation (local methods)",
    ),
    CalcMethod(
        id="fva_556_flank_fracture",
        label_de="Lokale Flankenbruchsicherheit (FVA 556)",
        label_en="Local flank fracture safety (FVA 556)",
        group_de="Stirnradberechnung (lokale Verfahren)",
        group_en="Cylindrical gear calculation (local methods)",
    ),
    CalcMethod(
        id="fva_732_root_bem",
        label_de="Lokale Zahnfußspannung (BEM, FVA 732)",
        label_en="Local tooth root stress (BEM, FVA 732)",
        group_de="Stirnradberechnung (lokale Verfahren)",
        group_en="Cylindrical gear calculation (local methods)",
    ),
    CalcMethod(
        id="fva_338_excitation",
        label_de="Verzahnungsanregung (FVA 338)",
        label_en="Gear mesh excitation (FVA 338)",
        group_de="Stirnradberechnung (lokale Verfahren)",
        group_en="Cylindrical gear calculation (local methods)",
    ),
    CalcMethod(
        id="fva_377_fem",
        label_de="Lokale Beanspruchung (FEM, FVA 377)",
        label_en="Local stress (FEM, FVA 377)",
        group_de="Stirnradberechnung (lokale Verfahren)",
        group_en="Cylindrical gear calculation (local methods)",
        enables_tabs=[("cylindrical_mesh", "loaddist_fem")],
    ),
    CalcMethod(
        id="fva_892_transient_fem",
        label_de="Dynamisches Abwälzen (FEM, FVA 892)",
        label_en="Transient FEM rolling (FVA 892)",
        group_de="Stirnradberechnung (lokale Verfahren)",
        group_en="Cylindrical gear calculation (local methods)",
        implemented=True,
        default_on=True,  # the core deliverable of this project
        enables_tabs=[("cylindrical_mesh", "transient_fem")],
    ),
    CalcMethod(
        id="bearing_life",
        label_de="Lagerlebensdauer",
        label_en="Bearing life",
        group_de="Wälzlagerberechnung",
        group_en="Rolling bearing calculation",
    ),
    CalcMethod(
        id="power_loss",
        label_de="Verlustleistung",
        label_en="Power loss",
        group_de="Verlustleistung",
        group_en="Power loss",
    ),
    CalcMethod(
        id="fem_part_deformation",
        label_de="FEM-Bauteilverformung",
        label_en="FEM part deformation",
        group_de="FEM-Bauteilverformung",
        group_en="FEM part deformation",
    ),
    CalcMethod(
        id="eigenmodes",
        label_de="Eigenwerte/Eigenmoden",
        label_en="Eigenvalues/eigenmodes",
        group_de="Dynamik",
        group_en="Dynamics",
    ),
    CalcMethod(
        id="load_spectrum",
        label_de="Lastkollektiv",
        label_en="Load spectrum",
        group_de="Lastkollektiv",
        group_en="Load spectrum",
    ),
]


# ------------------------------------------------------------------------------------------
# attributes (shared pool; ids are OUR canonical names, bindings hit the frontend store)
# ------------------------------------------------------------------------------------------
ATTRIBUTES: list[AttributeDef] = [
    # --- Stirnradstufe → Geometrie (screenshot: Position auf der Welle / Hauptgeometrie /
    #     Profilerzeugung) --------------------------------------------------------------
    AttributeDef(
        id="u_coordinate_on_shaft",
        label_de="u-Koordinate auf der Welle",
        label_en="u coordinate on the shaft",
        unit="mm",
        per_gear=True,
        bindings=("shaft.u_coordinate_gear1_mm", "shaft.u_coordinate_gear2_mm"),
        info_de="Axiale Lage des Rades auf seiner Welle (Systemrechnung).",
        info_en="Axial position of the gear on its shaft (system calculation).",
    ),
    AttributeDef(
        id="normal_pressure_angle",
        label_de="Normaleingriffswinkel",
        label_en="Normal pressure angle",
        symbol="α_n",
        unit="°",
        precision=5,
        binding="stage.normal_pressure_angle_deg",
        norm_ref="DIN 21771",
    ),
    AttributeDef(
        id="normal_module",
        label_de="Normalmodul",
        label_en="Normal module",
        symbol="m_n",
        unit="mm",
        precision=5,
        binding="stage.normal_module_mm",
        norm_ref="DIN 21771",
        info_de="Modul im Normalschnitt; bestimmt mit z die Radgröße (d = m_t·z).",
        info_en="Module in the normal section; with z it sets the gear size (d = m_t·z).",
    ),
    AttributeDef(
        id="teeth",
        label_de="Zähnezahl",
        label_en="Number of teeth",
        symbol="z",
        kind="int",
        per_gear=True,
        bindings=("stage.teeth_pinion", "stage.teeth_wheel"),
        norm_ref="DIN 21771",
    ),
    AttributeDef(
        id="helix_angle",
        label_de="Schrägungswinkel",
        label_en="Helix angle",
        symbol="β",
        unit="°",
        precision=5,
        binding="stage.helix_angle_deg",
        norm_ref="DIN 21771",
    ),
    AttributeDef(
        id="face_width",
        label_de="Zahnbreite",
        label_en="Face width",
        symbol="b",
        unit="mm",
        precision=3,
        per_gear=True,
        bindings=("stage.face_width_pinion_mm", "stage.face_width_wheel_mm"),
    ),
    AttributeDef(
        id="tooth_end_chamfer",
        label_de="Fase am Zahnende",
        label_en="Chamfer at tooth end",
        symbol="b_F",
        unit="mm",
        per_gear=True,
        bindings=("stage.tooth_end_chamfer_pinion_mm", "stage.tooth_end_chamfer_wheel_mm"),
    ),
    AttributeDef(
        id="center_distance_mode",
        label_de="Achsabstand definieren",
        label_en="Define center distance",
        kind="enum",
        options=[
            _opt(
                "a_and_x",
                "Achsabstand und Profilverschiebung definieren",
                "Define center distance and profile shift",
            ),
            _opt(
                "from_x",
                "Aus den Profilverschiebungen berechnen",
                "Computed from the profile shifts",
            ),
        ],
        binding="geometryUi.center_distance_mode",
        norm_ref="DIN 21771 (inv α_wt = inv α_t + 2·Σx·tan α_n/Σz)",
        info_de="Bestimmt, ob a Eingabe ist (x-Aufteilung folgt) oder aus Σx berechnet wird.",
        info_en="Whether a is an input (x split follows) or derived from Σx.",
    ),
    AttributeDef(
        id="center_distance",
        label_de="Achsabstand",
        label_en="Center distance",
        symbol="a",
        unit="mm",
        precision=3,
        binding="stage.center_distance_mm",
        norm_ref="DIN 21771",
    ),
    AttributeDef(
        id="rotation_about_negative_u",
        label_de="Drehwinkel um die negative u-Achse",
        label_en="Rotation about the negative u axis",
        symbol="φ_u",
        unit="°",
        binding="shaft.rotation_negative_u_deg",
    ),
    AttributeDef(
        id="profile_shift_mode",
        label_de="Aufteilung Profilverschiebung",
        label_en="Allocation of addendum modification",
        kind="enum",
        options=[
            _opt(
                "nominal",
                "Eingabe der Nennprofilverschiebungen",
                "Specification of nominal addendum modification coefficients",
            ),
            _opt("din_3992", "nach DIN 3992", "acc. DIN 3992"),
            _opt("equal_x", "x₁ = x₂", "x₁ = x₂"),
        ],
        binding="geometryUi.profile_shift_mode",
        norm_ref="DIN 3992",
    ),
    AttributeDef(
        id="profile_shift",
        label_de="Nennprofilverschiebungsfaktor",
        label_en="Nominal addendum modification coefficient",
        symbol="x",
        precision=6,
        per_gear=True,
        bindings=("stage.profile_shift_pinion", "stage.profile_shift_wheel"),
        norm_ref="DIN 21771",
    ),
    AttributeDef(
        id="profile_generation_mode",
        label_de="Profilerzeugung",
        label_en="Profile generation",
        kind="enum",
        per_gear=True,
        options=[
            _opt("by_tool", "Durch Werkzeugbezugsprofil", "By tool reference profile"),
            _opt("by_geometry", "Durch Zahngeometrie", "By tooth geometry"),
        ],
        bindings=("geometryUi.profile_generation_gear1", "geometryUi.profile_generation_gear2"),
        info_de=(
            "Unsere Zahnform wird immer über das Werkzeugbezugsprofil erzeugt (validierte "
            "Erzeugungsgeometrie; die FVA-eigene 'Fußrundung über Werkzeug' war fehlerhaft)."
        ),
        info_en=(
            "Our tooth form is always generated via the tool reference profile (validated "
            "generation geometry)."
        ),
    ),
    AttributeDef(
        id="tip_diameter",
        label_de="Kopfkreisdurchmesser",
        label_en="Tip diameter",
        symbol="d_a",
        unit="mm",
        precision=3,
        per_gear=True,
        bindings=("stage.tip_diameter_pinion_mm", "stage.tip_diameter_wheel_mm"),
        norm_ref="DIN 21771",
    ),
    AttributeDef(
        id="tip_edge_break",
        label_de="Kopfkantenbruch (Radialbetrag)",
        label_en="Tip edge break (radial amount)",
        symbol="h_K",
        unit="mm",
        precision=3,
        per_gear=True,
        computed=True,
        bindings=("geometry.tip_edge_break_gear1_mm", "geometry.tip_edge_break_gear2_mm"),
        info_de="Aus dem Werkzeug-Kantenbruchwinkel erzeugt (kst-E: Rad 0.117 mm).",
        info_en="Generated from the tool edge-break angle (kst-E: wheel 0.117 mm).",
    ),
    AttributeDef(
        id="root_diameter",
        label_de="Fußkreisdurchmesser",
        label_en="Root diameter",
        symbol="d_f",
        unit="mm",
        precision=3,
        per_gear=True,
        computed=True,
        bindings=("geometry.root_diameter_gear1_mm", "geometry.root_diameter_gear2_mm"),
        norm_ref="DIN 21771",
    ),
    AttributeDef(
        id="tool_tip_radius_factor",
        label_de="Fußausrundungsradius Bezugsprofil",
        label_en="Root fillet radius of the reference profile",
        symbol="ρ_fP*",
        precision=2,
        binding="stage.tool_tip_radius_factor",
        norm_ref="DIN 867 / ISO 53",
    ),
    # --- Stirnradstufe → Dynamisches Abwälzen (FEM) (screenshot) -----------------------
    AttributeDef(
        id="fem_contour_source",
        label_de="Geometrie für FEM 3d-Lastverteilung",
        label_en="Geometry for FEM 3D load distribution",
        kind="enum",
        per_gear=True,
        options=[
            _opt(
                "generated",
                "Stirnradkontur durch Verzahnungsgeometrie",
                "Cylindrical gear contour from the gearing geometry",
            )
        ],
        bindings=("fem.contour_source_gear1", "fem.contour_source_gear2"),
    ),
    AttributeDef(
        id="fem_modifications_source",
        label_de="Flankenmodifikationen für FEM",
        label_en="Flank modifications for FEM",
        kind="enum",
        per_gear=True,
        options=[_opt("given", "Aus vorgegebenen Modifikationen", "From given modifications")],
        bindings=("fem.mods_source_gear1", "fem.mods_source_gear2"),
    ),
    AttributeDef(
        id="roll_position_mode",
        label_de="Vorgabe der Wälzstellungen",
        label_en="Roll position specification",
        kind="enum",
        options=[
            _opt(
                "linear_count",
                "lineare Verteilung mit Vorgabe der Anzahl",
                "linear distribution with given count",
            )
        ],
        binding="fem.roll_position_mode",
    ),
    AttributeDef(
        id="roll_pitches",
        label_de="Anzahl Teilungen",
        label_en="Number of pitches",
        kind="int",
        binding="fem.roll_pitches",
        info_de="Abgewälzte Zahnteilungen des winkelgeführten Rades (Referenz: 2).",
        info_en="Rolled pitches of the angle-driven gear (reference: 2).",
    ),
    AttributeDef(
        id="roll_positions",
        label_de="Anzahl der Wälzstellungen",
        label_en="Number of roll positions",
        kind="int",
        binding="fem.n_roll_positions",
        info_de="Ausgabe-Frames über den Wälzweg (Referenz-Deck: 30, WS30).",
        info_en="Output frames over the roll path (reference deck: 30, WS30).",
    ),
    AttributeDef(
        id="fem_run_solver",
        label_de="FE-Solver ausführen",
        label_en="Run FE solver",
        kind="bool",
        binding="fem.run_solver",
        info_de="Ohne lokalen Abaqus-Solver bleibt nur der Deck-Export aktiv.",
        info_en="Without a local Abaqus solver only the deck export is active.",
    ),
    AttributeDef(
        id="fem_inp_path",
        label_de="Abaqus inp Datei abspeichern",
        label_en="Save Abaqus inp file",
        kind="action",
        binding="fem.download_deck",
        info_de="Erzeugt das referenzgetreue implizite Abwälz-Deck (.inp) zum Download.",
        info_en="Generates the reference-faithful implicit rolling deck (.inp) for download.",
    ),
    AttributeDef(
        id="fem_result_in_model",
        label_de="FE-Löser Ergebnisdatei im Modell speichern",
        label_en="Store FE solver result file in the model",
        kind="bool",
        binding="fem.result_in_model",
        info_de="Ohne lokalen Abaqus-Solver ohne Wirkung (odb entsteht auf dem Cluster).",
        info_en="No effect without a local Abaqus solver (the odb is produced on the cluster).",
    ),
    AttributeDef(
        id="fem_odb_path",
        label_de="Abaqus odb file für Postprocessing",
        label_en="Abaqus odb file for postprocessing",
        kind="path",
        computed=True,
        binding="fem.odb_path",
        info_de="Wird nach einem Solver-Lauf gesetzt (Schritt 4/5 der Roadmap).",
        info_en="Set after a solver run (roadmap steps 4/5).",
    ),
    AttributeDef(
        id="fem_result_path",
        label_de="Aufbereitete Ergebnisdaten Abwälzen",
        label_en="Postprocessed rolling result data",
        kind="path",
        computed=True,
        binding="fem.result_path",
    ),
    AttributeDef(
        id="fem_auto_smoothing",
        label_de="Automatische Netzglättung",
        label_en="Automatic mesh smoothing",
        kind="bool",
        binding="fem.auto_smoothing",
        info_de="Unser Transplant-Mesher glättet immer auf Jacobi-Güte ≥ Sollvorgabe (ADR-019).",
        info_en="Our transplant mesher always smooths to the target Jacobian quality (ADR-019).",
    ),
    AttributeDef(
        id="fem_expert_stirak",
        label_de="Berechnung mit STIRAK individueller Konfiguration",
        label_en="Calculation with individual STIRAK configuration",
        kind="bool",
        binding="fem.expert_stirak",
        info_de="FVA-Expertenfunktion — im Nachbau ohne Funktion (kein STIRAK-Kernel).",
        info_en="FVA expert switch — inactive in the replica (no STIRAK kernel).",
    ),
    AttributeDef(
        id="meshing_accuracy",
        label_de="Vernetzungsgrad",
        label_en="Meshing accuracy",
        kind="enum",
        options=[
            _opt("converged", "auskonvergiert", "converged"),
            _opt("converged_root", "auskonvergiert (Zahnfuß)", "converged (tooth root)"),
            _opt("converged_flank", "auskonvergiert (Flanke)", "converged (flank)"),
            _opt("user", "benutzerdefiniert", "user defined"),
        ],
        binding="fem.meshing_accuracy",
    ),
    AttributeDef(
        id="fem_modeled_teeth",
        label_de="Anzahl der modellierten Zähne",
        label_en="Number of modelled teeth",
        kind="int",
        computed=True,
        binding="fem.modeled_teeth",
        info_de="Referenz-Topologie: fest 4 Zähne + 2 zahnfreie Schulterteilungen (ADR-019).",
        info_en="Reference topology: fixed 4 teeth + 2 toothless shoulder pitches (ADR-019).",
    ),
    AttributeDef(
        id="fem_free_segments",
        label_de="Anzahl der zahnfreien Segmente",
        label_en="Number of toothless segments",
        kind="int",
        computed=True,
        binding="fem.free_segments",
    ),
    AttributeDef(
        id="fem_angle_limit",
        label_de="Grenzwinkelvorgabe",
        label_en="Angle limit",
        unit="°",
        binding="fem.angle_limit_deg",
        info_de="FVA-Mesher-Qualitätsvorgabe (Default 65°); unser Transplant-Mesher prüft die "
        "Jacobi-Qualität direkt.",
        info_en="FVA mesher quality target (default 65°); our transplant mesher checks the "
        "Jacobian quality directly.",
    ),
    AttributeDef(
        id="fem_jacobi_quality",
        label_de="Sollvorgabe Jacobi-Güte",
        label_en="Target Jacobian quality",
        precision=2,
        binding="fem.jacobi_quality",
        info_de="Minimale skalierte Jacobi-Determinante (Referenz 0.35).",
        info_en="Minimum scaled Jacobian determinant (reference 0.35).",
    ),
    AttributeDef(
        id="fasten_bore",
        label_de="Fesselung an der Bohrung",
        label_en="Fixation at the bore",
        kind="bool",
        binding="fem.fasten_bore",
        norm_ref="Referenz-Deck (gemessen 2026-07-04)",
        info_de="Bohrungsfläche als Teil des *RIGID BODY TIE NSET (jeder Knoten der Fläche).",
        info_en="Bore surface as part of the *RIGID BODY TIE NSET (every node of the face).",
    ),
    AttributeDef(
        id="fasten_cuts",
        label_de="Fesselung im Schnitt",
        label_en="Fixation at the section cuts",
        kind="bool",
        binding="fem.fasten_cuts",
        norm_ref="Referenz-Deck (gemessen 2026-07-04)",
        info_de="Beide radiale Schnittebenen komplett (Bohrung→Fußkreis, alle Breitenlagen).",
        info_en="Both radial cut planes completely (bore→root circle, all width planes).",
    ),
    AttributeDef(
        id="fasten_top",
        label_de="Fesselung oben",
        label_en="Fixation at the top face",
        kind="bool",
        binding="fem.fasten_top",
    ),
    AttributeDef(
        id="fasten_bottom",
        label_de="Fesselung unten",
        label_en="Fixation at the bottom face",
        kind="bool",
        binding="fem.fasten_bottom",
    ),
    AttributeDef(
        id="align_contact",
        label_de="Initiale Flankenanlage (Einflankenkontakt)",
        label_en="Initial single-flank contact alignment",
        kind="bool",
        binding="fem.align_contact",
        norm_ref="Referenz-Deck: ~25 µm Anfangsspalt, Moment schließt",
        info_de="Rad 2 wird spielschließend gedreht, statt mittig mit vollem Flankenspiel "
        "'in der Luft' zu starten.",
        info_en="Gear 2 is rotated to close the backlash instead of floating centred with "
        "the full allowance backlash.",
    ),
    AttributeDef(
        id="torque_gear2",
        label_de="Drehmoment an Rad 2",
        label_en="Torque at gear 2",
        symbol="M₂",
        unit="N·mm",
        binding="fem.torque_gear2_nmm",
        norm_ref="ADR-021 (T_g = M₂·z_g/z₂ am lastführenden Rad)",
    ),
    # --- Getriebeeinheit → Betriebsdaten (screenshot) ----------------------------------
    AttributeDef(
        id="lubricant_name",
        label_de="Schmierstoff",
        label_en="Lubricant",
        kind="enum",
        options=[_opt("iso_vg_100", "ISO-VG-100", "ISO-VG-100")],
        binding="operatingUi.lubricant",
    ),
    AttributeDef(
        id="oil_temperature",
        label_de="Schmierstofftemperatur",
        label_en="Lubricant temperature",
        symbol="θ_oil",
        unit="°C",
        binding="operatingUi.oil_temperature_c",
        norm_ref="VDI 2736-2 (Zahntemperatur-Modell)",
    ),
    AttributeDef(
        id="ambient_temperature",
        label_de="Umgebungstemperatur",
        label_en="Ambient temperature",
        symbol="θ_ambient",
        unit="°C",
        binding="operatingUi.ambient_temperature_c",
    ),
    AttributeDef(
        id="operating_hours",
        label_de="Betriebsdauer",
        label_en="Operating time",
        symbol="L_H",
        unit="h",
        binding="operatingUi.operating_hours",
        info_de="Mit der Drehzahl ergibt sich die Lastwechselzahl N_L der Tragfähigkeit.",
        info_en="With the speed this yields the load-cycle count N_L of the capacity runs.",
    ),
]


# ------------------------------------------------------------------------------------------
# tabs
# ------------------------------------------------------------------------------------------
def _geometry_tab() -> TabDef:
    """Stirnradstufe → Geometrie (screenshot Stirnradstufe_Geometrie.png, field order)."""
    return TabDef(
        id="geometry",
        title_de="Geometrie",
        title_en="Geometry",
        sections=[
            SectionDef(
                id="shaft_position",
                title_de="Position auf der Welle",
                title_en="Position on the shaft",
                rows=[RowRef(attr="u_coordinate_on_shaft")],
            ),
            SectionDef(
                id="main_geometry",
                title_de="Hauptgeometrie",
                title_en="Main geometry",
                rows=[
                    RowRef(attr="normal_pressure_angle"),
                    RowRef(attr="normal_module"),
                    RowRef(attr="teeth"),
                    RowRef(attr="helix_angle"),
                    RowRef(attr="face_width"),
                    RowRef(attr="tooth_end_chamfer"),
                    RowRef(attr="center_distance_mode"),
                    RowRef(attr="center_distance"),
                    RowRef(attr="rotation_about_negative_u"),
                    RowRef(attr="profile_shift_mode"),
                    RowRef(attr="profile_shift"),
                ],
            ),
            SectionDef(
                id="profile_generation",
                title_de="Profilerzeugung",
                title_en="Profile generation",
                rows=[
                    RowRef(attr="profile_generation_mode"),
                    RowRef(attr="tip_diameter"),
                    RowRef(attr="tip_edge_break"),
                    RowRef(attr="root_diameter"),
                    RowRef(attr="tool_tip_radius_factor"),
                ],
            ),
        ],
    )


def _transient_fem_tab() -> TabDef:
    """Stirnradstufe → Dynamisches Abwälzen (FEM) (screenshot, FVA 892)."""
    return TabDef(
        id="transient_fem",
        title_de="Dynamisches Abwälzen (FEM)",
        title_en="Transient FEM rolling",
        visible_if_method="fva_892_transient_fem",
        sections=[
            SectionDef(
                id="tooth_contour",
                title_de="Zahnkontur",
                title_en="Tooth contour",
                rows=[
                    RowRef(attr="fem_contour_source"),
                    RowRef(attr="fem_modifications_source"),
                ],
            ),
            SectionDef(
                id="parameters",
                title_de="Berechnungsparameter Dynamisches Abwälzen (FEM)",
                title_en="Parameters of the transient FEM rolling",
                rows=[
                    RowRef(attr="roll_position_mode"),
                    RowRef(attr="roll_pitches"),
                    RowRef(attr="roll_positions"),
                    RowRef(attr="torque_gear2"),
                    RowRef(attr="align_contact"),
                    RowRef(attr="fem_result_in_model"),
                    RowRef(attr="fem_run_solver"),
                    RowRef(attr="fem_inp_path"),
                    RowRef(attr="fem_odb_path"),
                    RowRef(attr="fem_result_path"),
                ],
            ),
            SectionDef(
                id="meshing",
                title_de="Vernetzung Dynamisches Abwälzen (FEM)",
                title_en="Meshing of the transient FEM rolling",
                rows=[
                    RowRef(attr="meshing_accuracy"),
                    RowRef(attr="fem_modeled_teeth"),
                    RowRef(attr="fem_free_segments"),
                    RowRef(attr="fem_angle_limit"),
                    RowRef(attr="fem_jacobi_quality"),
                    RowRef(attr="fem_auto_smoothing"),
                ],
            ),
            SectionDef(
                id="fastening",
                title_de="Fesselung",
                title_en="Fixation",
                rows=[
                    RowRef(attr="fasten_bore"),
                    RowRef(attr="fasten_cuts"),
                    RowRef(attr="fasten_top"),
                    RowRef(attr="fasten_bottom"),
                ],
                info_de="Default = Referenz-Deck: Bohrung + beide Schnittebenen, jeweils jeder "
                "einzelne Knoten der Fläche (gemessen am Original-INP).",
                info_en="Default = reference deck: bore + both cut planes, every single node "
                "of those faces (measured on the original INP).",
            ),
            SectionDef(
                id="expert",
                title_de="Individuelle Konfiguration für die FE-Stirnradberechnung "
                "(Expertenfunktion)",
                title_en="Individual configuration for the FE calculation (expert function)",
                rows=[RowRef(attr="fem_expert_stirak")],
            ),
        ],
    )


def _operating_data_tab() -> TabDef:
    """Getriebeeinheit → Betriebsdaten (screenshot Getriebeeinheit_Betriebsdaten.png)."""
    return TabDef(
        id="operating_data",
        title_de="Betriebsdaten",
        title_en="Operating data",
        sections=[
            SectionDef(
                id="lubricant",
                title_de="Schmierstoff",
                title_en="Lubricant",
                rows=[
                    RowRef(attr="lubricant_name"),
                    RowRef(attr="oil_temperature"),
                    RowRef(attr="ambient_temperature"),
                ],
            ),
            SectionDef(
                id="operation",
                title_de="Betriebsdaten",
                title_en="Operating data",
                rows=[RowRef(attr="operating_hours")],
            ),
        ],
    )


# ------------------------------------------------------------------------------------------
# dependency rules (norm-referenced; each one is a glossary entry)
# ------------------------------------------------------------------------------------------
RULES: list[DependencyRule] = [
    DependencyRule(
        id="center_distance_input_mode",
        when="geometryUi.center_distance_mode",
        when_value="from_x",
        effect="compute",
        targets=["stage.center_distance_mm"],
        description_de=(
            "a wird aus Σx berechnet: inv α_wt = inv α_t + 2·(x₁+x₂)·tan α_n/(z₁+z₂), "
            "a = a_d·cos α_t/cos α_wt — das Achsabstandsfeld ist dann berechnet/gesperrt."
        ),
        description_en=(
            "a is derived from Σx via inv α_wt; the center-distance field turns computed/locked."
        ),
        norm_ref="DIN 21771",
    ),
    DependencyRule(
        id="fix_center_distance_locks_partners",
        when="variation.fix_center_distance",
        when_value=True,
        effect="lock",
        targets=["variation.z1", "variation.z2", "variation.x2"],
        description_de=(
            "Achsabstand fixieren: z₁, z₂ gesperrt und x₂ kompensiert x₁ (Σx fest), da "
            "a = m_t·(z₁+z₂)/2·cos α_t/cos α_wt jede dieser Größen enthält."
        ),
        description_en=(
            "Fixing a locks z₁/z₂ and derives x₂ from x₁ (Σx fixed) — a depends on all of them."
        ),
        norm_ref="DIN 21771 / DIN 3992",
    ),
    DependencyRule(
        id="material_dispatches_norm",
        when="materials.gear_kind",
        effect="compute",
        targets=["capacity.method_gear1", "capacity.method_gear2"],
        description_de=(
            "Der Werkstoff bestimmt die Norm je Rad: Stahl → ISO 6336, Kunststoff → "
            "VDI 2736 — nie nach Rolle, nie gemischt. Folgen: aktive Festigkeitsfelder, "
            "VDI-Reiter-Seiten, Deck-Materialkarte, Rigid-Shell (Stahlseite), "
            "Kontakt-Slave (Kunststoffseite)."
        ),
        description_en=(
            "The material dispatches the norm per gear (steel → ISO 6336, plastic → "
            "VDI 2736); strength fields, VDI tab sides, deck material card, rigid shell "
            "and contact slave follow."
        ),
        norm_ref="ISO 6336:2019 / VDI 2736:2014",
    ),
    DependencyRule(
        id="meshing_accuracy_user_unlocks_counts",
        when="fem.meshing_accuracy",
        when_value="user",
        effect="show",
        targets=[
            "fem.elements_tooth_height",
            "fem.elements_root",
            "fem.elements_thickness",
            "fem.elements_width",
        ],
        description_de=(
            "Vernetzungsgrad 'benutzerdefiniert' schaltet die manuellen Elementanzahlen "
            "frei (FVA-Vernetzer-Dialog: Nutzereingabe)."
        ),
        description_en=(
            "Meshing accuracy 'user defined' unlocks the manual element counts (FVA mesher "
            "dialog: user input)."
        ),
    ),
    DependencyRule(
        id="method_tabs_visibility",
        when="calc.fva_892_transient_fem",
        when_value=True,
        effect="show",
        targets=["tabs.cylindrical_mesh.transient_fem"],
        description_de=(
            "Die Berechnungsauswahl steuert die Reiter: ein Verfahren blendet seine "
            "Eingabereiter ein (FVA 892 → 'Dynamisches Abwälzen (FEM)'); abgewählte "
            "Verfahren verstecken den Reiter, der Zustand bleibt erhalten."
        ),
        description_en=(
            "The calculation selection drives the tabs: a method reveals its input tabs "
            "(FVA 892 → transient FEM); deselecting hides the tab, state is preserved."
        ),
    ),
]


def build_ui_schema() -> UiSchema:
    """Assemble the schema served at ``/api/ui-schema``."""
    components = [
        ComponentDef(
            id="gear_unit",
            label_de="Getriebeeinheit",
            label_en="Gear unit",
            tabs=[_operating_data_tab()],
        ),
        ComponentDef(
            id="cylindrical_mesh",
            label_de="Stirnradstufe",
            label_en="Cylindrical gear stage",
            tabs=[_geometry_tab(), _transient_fem_tab()],
        ),
    ]
    return UiSchema(
        version=SCHEMA_VERSION,
        components=components,
        attributes={a.id: a for a in ATTRIBUTES},
        rules=RULES,
        methods=METHODS,
    )
