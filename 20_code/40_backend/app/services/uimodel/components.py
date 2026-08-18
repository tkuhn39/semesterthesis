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
    # --- tool reference profile per gear (kst-E ground truth: h_aP0* 1.1/1.25, the 45°
    # Kantenbrechwinkel exists ONLY on the wheel tool) — gear-2 fields empty = like gear 1
    AttributeDef(
        id="tool_addendum_factor",
        label_de="Kopfhöhenfaktor Werkzeug",
        label_en="Tool addendum factor",
        symbol="h_aP0*",
        precision=3,
        per_gear=True,
        bindings=("stage.tool_addendum_factor", "stage.tool_addendum_factor_gear2"),
        norm_ref="DIN 867 / ISO 53",
        info_de="Je Rad ein eigenes Bezugsprofil; Rad-2-Feld leer = wie Rad 1.",
        info_en="One reference profile per gear; empty gear-2 field = same as gear 1.",
    ),
    AttributeDef(
        id="tool_tip_radius_factor",
        label_de="Fußausrundungsradius Bezugsprofil",
        label_en="Root fillet radius of the reference profile",
        symbol="ρ_fP*",
        precision=2,
        per_gear=True,
        bindings=("stage.tool_tip_radius_factor", "stage.tool_tip_radius_factor_gear2"),
        norm_ref="DIN 867 / ISO 53",
    ),
    AttributeDef(
        id="tool_dedendum_factor",
        label_de="Fußhöhenfaktor Werkzeug",
        label_en="Tool dedendum factor",
        symbol="h_fP0*",
        precision=3,
        per_gear=True,
        nullable=True,
        bindings=("stage.tool_dedendum_factor", "stage.tool_dedendum_factor_gear2"),
        norm_ref="DIN 867 / ISO 53",
    ),
    AttributeDef(
        id="tool_root_form_height_factor",
        label_de="Fußformhöhenfaktor Werkzeug",
        label_en="Tool root form height factor",
        symbol="h_FfP0*",
        precision=4,
        per_gear=True,
        nullable=True,
        bindings=(
            "stage.tool_root_form_height_factor",
            "stage.tool_root_form_height_factor_gear2",
        ),
        info_de="h_FfP0* < h_fP0* aktiviert die Kantenbruchflanke des Werkzeugs "
        "(erzeugt den Kopfkantenbruch h_K).",
        info_en="h_FfP0* < h_fP0* activates the tool edge-break flank "
        "(generates the tip edge break h_K).",
    ),
    AttributeDef(
        id="tool_edge_break_angle",
        label_de="Kantenbrechwinkel Werkzeug",
        label_en="Tool edge-break angle",
        symbol="α_Kn0",
        unit="°",
        precision=1,
        per_gear=True,
        nullable=True,
        bindings=("stage.tool_edge_break_angle_deg", "stage.tool_edge_break_angle_deg_gear2"),
        info_de="kst-E: nur das Rad-Werkzeug bricht die Kopfkante (45°, h_K = 0.117 mm).",
        info_en="kst-E: only the wheel tool breaks the tip edge (45°, h_K = 0.117 mm).",
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
        id="fem_rigid_shell",
        label_de="Ideal steife Außenhülle",
        label_en="Ideally stiff outer shell",
        kind="bool",
        per_gear=True,
        bindings=("fem.rigid_shell_gear1", "fem.rigid_shell_gear2"),
        norm_ref="R3D4-Mantelfläche (Starrkörper um den Rotationsknoten)",
        info_de=(
            "Ersetzt den vollen Solid des Rades durch seine Mantelfläche (Zahnkontur, "
            "Schnittflächen, Bohrung; Stirnseiten offen) als Starrkörper — massive "
            "Elementreduktion, sinnvoll für die Stahlseite einer Stahl-Kunststoff-Paarung. "
            "Die Kunststoffseite (Kontakt-Slave) muss verformbar bleiben."
        ),
        info_en=(
            "Replaces the gear's solid by its lateral surface (tooth contour, cut faces, "
            "bore; open end faces) as a rigid body — massive element reduction for the "
            "steel side of a mixed pairing. The plastic contact slave stays deformable."
        ),
    ),
    AttributeDef(
        id="fem_deck_mode",
        label_de="Berechnungsmodus",
        label_en="Calculation mode",
        kind="enum",
        options=[
            _opt(
                "series",
                "Positions-Serie (ein INP je Wälzstellung)",
                "Position series (one INP per roll position)",
            ),
            _opt(
                "single",
                "Ein Deck (quasi-statische Durchfahrt)",
                "Single deck (quasi-static sweep)",
            ),
        ],
        binding="fem.deck_mode",
        norm_ref="pfadunabhängig: Marlow-Hyperelastizität + reibungsfreier Kontakt",
        info_de=(
            "Serie (Default): je Wälzstellung eine unabhängige statische Rechnung — "
            "ergebnisgleich (pfadunabhängiges Modell), robust gegen Konvergenzabbrüche, "
            "parallelisierbar. Ein-Deck: Referenzmodus mit Momentzyklus je Position "
            "(durchgängige Animation)."
        ),
        info_en=(
            "Series (default): one independent static solve per roll position — same "
            "results (path-independent model), robust, parallelisable. Single deck: "
            "reference mode with the per-position torque cycle."
        ),
    ),
    AttributeDef(
        id="fem_inp_path",
        label_de="Abaqus inp Datei abspeichern",
        label_en="Save Abaqus inp file",
        kind="action",
        binding="fem.download_deck",
        info_de=(
            "Erzeugt den Abwälz-Lastfall zum Download — je nach Berechnungsmodus das "
            "Einzel-Deck (.inp) oder die Positions-Serie (.zip mit pair_common.inp, "
            "pos_NNN.inp, manifest.json und Run-Skripten)."
        ),
        info_en=(
            "Generates the rolling load case for download — the single deck (.inp) or "
            "the position series (.zip with shared mesh, per-position files, manifest "
            "and run scripts), per the calculation mode."
        ),
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
        computed=True,  # SSOT: derives from the Leistungsfluss Antrieb load (FVA behaviour)
        binding="fem.torque_gear2_nmm",
        norm_ref="ADR-021 (T_g = M₂·z_g/z₂ am lastführenden Rad)",
        info_de="Kommt aus dem Leistungsfluss (Antriebsmoment) — keine eigene Eingabe im "
        "Abwälz-Reiter, damit der Lastfall systemweit konsistent bleibt.",
        info_en="Derived from the power flow (input torque) — no separate input here so the "
        "load case stays consistent system-wide.",
    ),
    # --- Stirnradstufe → Tragfähigkeit (screenshot Stirnradstufe_Tragfaehigkeit.png) ----
    AttributeDef(
        id="cap_web_mode",
        label_de="Bezogene Stegbreite",
        label_en="Related web width",
        symbol="b_s / b",
        kind="enum",
        per_gear=True,
        options=[_opt("solid", "Vollscheibenrad", "Solid disc gear")],
        bindings=("operating.web_mode_gear1", "operating.web_mode_gear2"),
        norm_ref="ISO 6336-3 (Y_B)",
    ),
    AttributeDef(
        id="cap_rim_mode",
        label_de="Relative Kranzdicke",
        label_en="Related rim thickness",
        symbol="s_R / m_n",
        kind="enum",
        per_gear=True,
        options=[_opt("solid", "Vollscheibenrad", "Solid disc gear")],
        bindings=("operating.rim_mode_gear1", "operating.rim_mode_gear2"),
        norm_ref="ISO 6336-3 (Y_B)",
    ),
    AttributeDef(
        id="cap_roughness_auto",
        label_de="Rauheiten automatisch umrechnen",
        label_en="Convert roughness automatically",
        kind="bool",
        binding="operating.roughness_auto",
        info_de="R_a ↔ R_z Umrechnung (R_z ≈ 6·R_a) — gilt für beide Räder.",
        info_en="R_a ↔ R_z conversion (R_z ≈ 6·R_a) — applies to both gears.",
    ),
    AttributeDef(
        id="cap_ra_flank",
        label_de="Arithmetischer Mittenrauwert Flanke",
        label_en="Arithmetic mean roughness, flank",
        symbol="R_aH",
        unit="µm",
        precision=1,
        binding="operating.flank_roughness_ra_um",
    ),
    AttributeDef(
        id="cap_rz_flank",
        label_de="Gemittelte Rautiefe Flanke",
        label_en="Mean roughness depth, flank",
        symbol="R_zH",
        unit="µm",
        precision=1,
        binding="operating.flank_roughness_rz_um",
        norm_ref="ISO 6336-2 (Z_R)",
    ),
    AttributeDef(
        id="cap_ra_root",
        label_de="Arithmetischer Mittenrauwert Fuß",
        label_en="Arithmetic mean roughness, root",
        symbol="R_aF",
        unit="µm",
        precision=1,
        binding="operating.root_roughness_ra_um",
    ),
    AttributeDef(
        id="cap_rz_root",
        label_de="Gemittelte Rautiefe Fuß",
        label_en="Mean roughness depth, root",
        symbol="R_zF",
        unit="µm",
        precision=1,
        binding="operating.root_roughness_rz_um",
        norm_ref="ISO 6336-3 (Y_RrelT)",
    ),
    AttributeDef(
        id="cap_tip_relief",
        label_de="Kopfrücknahme",
        label_en="Tip relief",
        symbol="C_a",
        unit="µm",
        precision=1,
        binding="operating.tip_relief_ca_um",
        norm_ref="ISO 6336-1 (K_v, Anregung)",
    ),
    AttributeDef(
        id="cap_mesh_stiffness_mode",
        label_de="Eingriffsfedersteifigkeit im Gesamtsystem",
        label_en="Mesh stiffness in the system run",
        symbol="c_γ",
        kind="enum",
        options=[_opt("iso6336", "Nach ISO 6336", "Acc. ISO 6336")],
        binding="operating.mesh_stiffness_mode",
        norm_ref="ISO 6336-1 §9",
    ),
    AttributeDef(
        id="cap_application_factor",
        label_de="Anwendungsfaktor",
        label_en="Application factor",
        symbol="K_A",
        precision=2,
        binding="operating.application_factor",
        norm_ref="ISO 6336-1 / VDI 2736",
    ),
    # --- Stirnradstufe → Toleranzen (screenshot Stirnradstufe_Toleranz.png) ------------
    AttributeDef(
        id="tol_awe",
        label_de="Oberes Zahnweitenabmaß",
        label_en="Upper tooth-width allowance",
        symbol="A_We",
        unit="µm",
        precision=1,
        per_gear=True,
        bindings=("tol.awe1_um", "tol.awe2_um"),
        norm_ref="DIN 3967",
        info_de="Mittelwert (A_We+A_Wi)/2 fließt als A̅_We in Erzeugung (x_E) UND ins "
        "Abwälz-Deck (Flankenspiel → spielschließende Drehung).",
        info_en="The mean flows into the generation (x_E) AND the rolling deck (backlash "
        "→ closing rotation).",
    ),
    AttributeDef(
        id="tol_awi",
        label_de="Unteres Zahnweitenabmaß",
        label_en="Lower tooth-width allowance",
        symbol="A_Wi",
        unit="µm",
        precision=1,
        per_gear=True,
        bindings=("tol.awi1_um", "tol.awi2_um"),
        norm_ref="DIN 3967",
    ),
    AttributeDef(
        id="tol_aw_factor",
        label_de="Zahnweitenabmaßfaktor",
        label_en="Tooth-width allowance factor",
        symbol="A_W/A_s",
        kind="enum",
        options=[_opt("0.94", "0.94", "0.94")],
        binding="tol.aw_factor_mode",
    ),
    AttributeDef(
        id="tol_aw_selection",
        label_de="Auswahl des Zahnweitenabmaßes",
        label_en="Tooth-width allowance selection",
        kind="enum",
        options=[
            _opt("mean", "Mit mittlerem Zahnweitenabmaß", "With the mean allowance"),
            _opt("upper", "Mit oberem Zahnweitenabmaß", "With the upper allowance"),
            _opt("lower", "Mit unterem Zahnweitenabmaß", "With the lower allowance"),
        ],
        binding="tol.aw_selection",
    ),
    AttributeDef(
        id="tol_a_upper",
        label_de="Oberes Achsabstandsabmaß",
        label_en="Upper centre-distance allowance",
        symbol="A_Ae",
        unit="µm",
        precision=1,
        binding="tol.a_upper_um",
        norm_ref="DIN 3964",
    ),
    AttributeDef(
        id="tol_a_lower",
        label_de="Unteres Achsabstandsabmaß",
        label_en="Lower centre-distance allowance",
        symbol="A_Ai",
        unit="µm",
        precision=1,
        binding="tol.a_lower_um",
        norm_ref="DIN 3964",
    ),
    AttributeDef(
        id="tol_quality_standard",
        label_de="Verzahnungsqualität",
        label_en="Gear quality standard",
        kind="enum",
        options=[
            _opt("din_3962_1978", "DIN 3962 (1978)", "DIN 3962 (1978)"),
            _opt("iso_1328_2013", "ISO 1328 (2013)", "ISO 1328 (2013)"),
        ],
        binding="tol.quality_standard",
    ),
    AttributeDef(
        id="tol_grade",
        label_de="Verzahnungsqualität DIN 3962",
        label_en="Quality grade DIN 3962",
        symbol="A",
        kind="int",
        per_gear=True,
        bindings=("tol.grade1", "tol.grade2"),
        norm_ref="DIN 3962 / ISO 1328-1",
        info_de="Die Qualität speist die Flankenabweichungen (f_pb, f_fα) der Dynamik.",
        info_en="The grade feeds the flank deviations (f_pb, f_fα) of the dynamics run.",
    ),
    AttributeDef(
        id="tol_custom_diameter",
        label_de="Benutzerdefinierter Durchmesser",
        label_en="Custom diameter",
        kind="bool",
        per_gear=True,
        bindings=("tol.custom_diameter1", "tol.custom_diameter2"),
    ),
    # --- Stirnradstufe → Werkstoff (screenshot Stirnradstufe_Werkstoff.png) -------------
    AttributeDef(
        id="mat_name",
        label_de="Werkstoff",
        label_en="Material",
        kind="enum",
        per_gear=True,
        options=[
            _opt("20MnCr5", "20MnCr5", "20MnCr5"),
            _opt("Stanyl_TW200F6_cond_80", "Stanyl_TW200F6_cond_80", "Stanyl_TW200F6_cond_80"),
        ],
        bindings=("materials.gear1_name", "materials.gear2_name"),
        info_de="Katalogwerkstoffe (app.services.materials.CATALOG) — erweiterbar.",
        info_en="Catalog materials (app.services.materials.CATALOG) — extensible.",
    ),
    AttributeDef(
        id="mat_kind",
        label_de="Werkstoffart",
        label_en="Material kind",
        kind="enum",
        per_gear=True,
        options=[_opt("steel", "Stahl", "Steel"), _opt("plastic", "Kunststoff", "Plastic")],
        bindings=("materials.gear1_kind", "materials.gear2_kind"),
        norm_ref="Norm-Dispatch: Stahl → ISO 6336, Kunststoff → VDI 2736",
        info_de="DIE Weiche des Systems: bestimmt Norm, Deck-Materialkarte, Rigid-Shell- "
        "und Kontakt-Slave-Rolle je Rad.",
        info_en="THE system dispatch: sets the norm, deck material card, rigid-shell and "
        "contact-slave role per gear.",
    ),
    AttributeDef(
        id="mat_root_group",
        label_de="Werkstoffgruppe (ISO 6336-3)",
        label_en="Material group (ISO 6336-3)",
        kind="enum",
        per_gear=True,
        options=[
            _opt("case_hardened", "Einsatzgehärtet (Eh, IF)", "Case hardened (Eh, IF)"),
            _opt("through_hardened", "Vergütet (V, GTS, GGG perl.)", "Through hardened (V)"),
            _opt("normalized", "Normalisiert (St)", "Normalized (St)"),
            _opt("nitrided", "Nitriert (NT, NV)", "Nitrided (NT, NV)"),
            _opt("cast_iron", "Gusseisen (GG, GGG ferr.)", "Cast iron (GG)"),
        ],
        bindings=("materials.gear1_root_group", "materials.gear2_root_group"),
        norm_ref="ISO 6336-3:2019 Tab. 4/5 (ρ′, Y_RrelT, Y_X)",
        info_de="Bestimmt Gleitschichtdicke ρ′ (Y_δrelT), Y_RrelT-Kurve und Y_X-Gruppe "
        "des ISO-6336-Zweigs (nur Stahlräder; Audit NRM-07).",
        info_en="Sets the slip-layer ρ′ (Y_δrelT), the Y_RrelT curve and the Y_X group "
        "of the ISO 6336 branch (steel gears only; audit NRM-07).",
    ),
    AttributeDef(
        id="mat_softer_hb",
        label_de="Härte des weicheren Rades",
        label_en="Hardness of the softer gear",
        symbol="HB",
        unit="HB",
        precision=0,
        nullable=True,  # empty field → null → Z_W = 1 (matches the info text)
        binding="materials.softer_gear_hardness_hb",
        norm_ref="ISO 6336-2:2019 §9 (Z_W)",
        info_de="Für den Werkstoffpaarungsfaktor Z_W (130 ≤ HB ≤ 470); leer → Z_W = 1.",
        info_en="For the work-hardening factor Z_W (130 ≤ HB ≤ 470); empty → Z_W = 1.",
    ),
    *[
        AttributeDef(
            id=f"mat_steel_{key}",
            label_de=f"{de} (Stahl)",
            label_en=f"{en} (steel)",
            symbol=sym,
            unit=unit,
            precision=prec,
            binding=f"materials.steel_{key}",
        )
        for key, de, en, sym, unit, prec in (
            ("modulus_mpa", "Elastizitätsmodul", "Young's modulus", "E", "N/mm²", 0),
            ("poisson", "Querkontraktionszahl", "Poisson ratio", "ν", None, 2),
            (
                "sigma_hlim_mpa",
                "Dauerfestigkeit Flanke",
                "Flank endurance limit",
                "σ_Hlim",
                "N/mm²",
                1,
            ),
            ("sigma_flim_mpa", "Dauerfestigkeit Fuß", "Root endurance limit", "σ_Flim", "N/mm²", 1),
            ("density_kg_dm3", "Dichte", "Density", "ρ", "kg/dm³", 2),
        )
    ],
    *[
        AttributeDef(
            id=f"mat_plastic_{key}",
            label_de=f"{de} (Kunststoff)",
            label_en=f"{en} (plastic)",
            symbol=sym,
            unit=unit,
            precision=prec,
            binding=f"materials.plastic_{key}",
        )
        for key, de, en, sym, unit, prec in (
            ("modulus_mpa", "Elastizitätsmodul", "Young's modulus", "E", "N/mm²", 0),
            ("poisson", "Querkontraktionszahl", "Poisson ratio", "ν", None, 2),
            ("sigma_hlim_mpa", "Zeitwälzfestigkeit", "Flank strength", "σ_HlimN", "N/mm²", 1),
            ("sigma_flim_mpa", "Zeitschwellfestigkeit", "Root strength", "σ_FlimN", "N/mm²", 1),
            ("density_kg_dm3", "Dichte", "Density", "ρ", "kg/dm³", 2),
            ("yield_strength_mpa", "Dehngrenze", "Yield strength", "R_p0.2", "MPa", 1),
            (
                "allowable_temperature_c",
                "Zulässige Temperatur",
                "Allowable temperature",
                "ϑ_zul",
                "°C",
                1,
            ),
        )
    ],
    # --- Stirnradstufe → Schmierstoff (screenshot Stirnradstufe_Schmirstoff.png) --------
    AttributeDef(
        id="lub_density",
        label_de="Dichte bei 15 °C",
        label_en="Density at 15 °C",
        symbol="ρ",
        unit="kg/dm³",
        precision=2,
        binding="operating.lubricant_density_15c_kg_dm3",
    ),
    AttributeDef(
        id="lub_visc40",
        label_de="Nennviskosität bei 40 °C",
        label_en="Nominal viscosity at 40 °C",
        symbol="ν_40",
        unit="mm²/s",
        precision=1,
        binding="operating.lubricant_viscosity_40_mm2s",
        norm_ref="ISO 6336-2 (Z_L)",
    ),
    AttributeDef(
        id="lub_visc100",
        label_de="Nennviskosität bei 100 °C",
        label_en="Nominal viscosity at 100 °C",
        symbol="ν_100",
        unit="mm²/s",
        precision=1,
        binding="operating.lubricant_viscosity_100_mm2s",
    ),
    # --- Stirnradstufe → VDI 2736 (2014) (screenshot Stirnradstufe_VDI-2736.png) --------
    AttributeDef(
        id="vdi_lubrication_kind",
        label_de="Schmierungsart",
        label_en="Lubrication kind",
        kind="enum",
        options=[
            _opt("oil_circulation", "Ölumlauf", "Oil circulation"),
            _opt("grease", "Fett", "Grease"),
            _opt("dry", "Trockenlauf", "Dry running"),
        ],
        binding="operating.lubrication_kind",
        norm_ref="VDI 2736-2 (Zahntemperatur)",
    ),
    AttributeDef(
        id="vdi_ambient_mode",
        label_de="Umgebungstemperatur",
        label_en="Ambient temperature",
        symbol="ϑ_0",
        kind="enum",
        options=[
            _opt("equals_oil", "entspricht Öltemperatur", "equals oil temperature"),
            _opt("value", "Nutzereingabe", "User input"),
        ],
        binding="operating.ambient_mode",
    ),
    AttributeDef(
        id="vdi_duty_cycle",
        label_de="Relative Einschaltdauer bezogen auf 10 min",
        label_en="Relative duty cycle (per 10 min)",
        symbol="ED",
        precision=3,
        binding="operating.duty_cycle",
        norm_ref="VDI 2736-2",
    ),
    AttributeDef(
        id="vdi_housing_type",
        label_de="Bauart des Getriebegehäuses",
        label_en="Housing type",
        kind="enum",
        options=[
            _opt("closed", "Geschlossenes Gehäuse", "Closed housing"),
            _opt("open", "Offenes Gehäuse", "Open housing"),
        ],
        binding="operating.housing_type",
    ),
    AttributeDef(
        id="vdi_housing_surface",
        label_de="Wärmeabführende Oberfläche des Gehäuses",
        label_en="Heat-dissipating housing surface",
        symbol="A_G",
        unit="m²",
        precision=3,
        binding="operating.housing_surface_m2",
        norm_ref="VDI 2736-2 (Zahntemperatur)",
    ),
    AttributeDef(
        id="vdi_friction_mode",
        label_de="Reibbeiwert",
        label_en="Friction coefficient",
        symbol="µ",
        kind="enum",
        options=[
            _opt("vdi_2736_2014", "nach VDI 2736:2014", "acc. VDI 2736:2014"),
            _opt("value", "Nutzereingabe", "User input"),
        ],
        binding="operating.friction_mode",
    ),
    AttributeDef(
        id="vdi_friction_value",
        label_de="Reibbeiwert (Wert)",
        label_en="Friction coefficient (value)",
        symbol="µ",
        precision=3,
        binding="operating.friction_coefficient",
    ),
    AttributeDef(
        id="vdi_heat_transfer",
        label_de="Wärmeübergangsbeiwert (Fuß/Flanke)",
        label_en="Heat-transfer coefficient (root/flank)",
        symbol="k_ϑ",
        kind="enum",
        options=[_opt("vdi_2736_table3", "nach VDI 2736 Tabelle 3", "acc. VDI 2736 table 3")],
        binding="operating.heat_transfer_mode",
    ),
    AttributeDef(
        id="vdi_tooth_loss",
        label_de="Zahnverlustgrad",
        label_en="Tooth loss factor",
        symbol="H_v",
        kind="enum",
        options=[_opt("wimmer", "nach Wimmer", "acc. Wimmer")],
        binding="operating.tooth_loss_mode",
    ),
    AttributeDef(
        id="vdi_root_min_safety",
        label_de="Mindestsicherheit Zahnfuß",
        label_en="Minimum root safety",
        symbol="S_Fmin",
        precision=2,
        binding="operating.root_minimum_safety",
        norm_ref="VDI 2736-2 (S_Fmin ≥ 2.0 empfohlen)",
    ),
    AttributeDef(
        id="vdi_flank_min_safety",
        label_de="Mindestsicherheit Zahnflanke",
        label_en="Minimum flank safety",
        symbol="S_Hmin",
        precision=2,
        binding="operating.flank_minimum_safety",
        norm_ref="VDI 2736-2 (S_Hmin ≥ 1.4 empfohlen)",
    ),
    AttributeDef(
        id="vdi_wear_allowable",
        label_de="Zulässiger linearer Verschleiß",
        label_en="Allowable linear wear",
        symbol="W_zul",
        kind="enum",
        options=[_opt("0.1_mn", "0.1 · m_n", "0.1 · m_n")],
        binding="operating.allowable_wear_mode",
        norm_ref="VDI 2736-2 §7",
    ),
    AttributeDef(
        id="vdi_wear_coefficient",
        label_de="Verschleißkoeffizient",
        label_en="Wear coefficient",
        symbol="k_W",
        unit="10⁻⁶ mm³/(N·m)",
        precision=3,
        binding="operating.wear_coefficient_e6",
        norm_ref="VDI 2736-2 Tabelle 7",
    ),
    AttributeDef(
        id="vdi_deformation_condition",
        label_de="Umgebungsbedingung (Verformung)",
        label_en="Ambient condition (deformation)",
        kind="enum",
        options=[_opt("dry", "Trocken", "Dry"), _opt("humid", "Feucht", "Humid")],
        binding="operating.deformation_condition",
        norm_ref="VDI 2736-2 §8 (λ)",
    ),
    AttributeDef(
        id="vdi_static_overload",
        label_de="Statischer Überlastfaktor",
        label_en="Static overload factor",
        symbol="K_A,stat",
        kind="enum",
        options=[
            _opt("none", "Keine statische Berechnung", "No static analysis"),
            _opt("value", "Nutzereingabe", "User input"),
        ],
        binding="operating.static_mode",
        norm_ref="VDI 2736-2 §5.3 (Spitzenlasten)",
    ),
    # --- Stirnradstufe → Lastverteilung (FEM, FVA 377) ----------------------------------
    AttributeDef(
        id="ld_position_mode",
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
        binding="loaddist.position_mode",
    ),
    AttributeDef(
        id="ld_positions",
        label_de="Anzahl der Wälzstellungen",
        label_en="Number of roll positions",
        kind="int",
        binding="loaddist.n_positions",
    ),
    AttributeDef(
        id="ld_stress_eval",
        label_de="Spannungsauswertung",
        label_en="Stress evaluation",
        kind="enum",
        options=[
            _opt("tangential", "Tangentialspannungen", "Tangential stresses"),
            _opt("principal", "Hauptspannungen", "Principal stresses"),
        ],
        binding="loaddist.stress_eval",
        norm_ref="FVA 377 / eigene FE-Auswertung",
    ),
    AttributeDef(
        id="ld_save_influence",
        label_de="Einflusszahlen im Modell speichern",
        label_en="Store influence numbers in the model",
        kind="bool",
        binding="loaddist.save_influence",
    ),
    AttributeDef(
        id="ld_auto_overroll",
        label_de="Automatische Überrollung durchführen",
        label_en="Automatic overroll",
        kind="bool",
        binding="loaddist.auto_overroll",
    ),
    AttributeDef(
        id="ld_meshing_accuracy",
        label_de="Vernetzungsgrad",
        label_en="Meshing accuracy",
        kind="enum",
        options=[
            _opt("coarse", "Grob", "Coarse"),
            _opt("medium", "Mittel", "Medium"),
            _opt("fine", "Fein", "Fine"),
        ],
        binding="loaddist.meshing_accuracy",
    ),
    AttributeDef(
        id="ld_run_meshing",
        label_de="FEM-Vernetzung Visualisierung",
        label_en="FEM meshing visualisation",
        kind="action",
        binding="loaddist.run_meshing",
        info_de="Erzeugt das 2D-Sektornetz (Transplant-Mesher) und zeigt es an.",
        info_en="Generates and displays the 2D sector mesh (transplant mesher).",
    ),
    # --- Flankenmodifikation [34] (screenshots Flankenmodifikation_*.png) ---------------
    AttributeDef(
        id="corr_length_mode",
        label_de="Längenangaben der Modifikationen",
        label_en="Length specifications",
        kind="enum",
        options=[
            _opt("diameter_mm", "in mm des Durchmessers", "in mm of the diameter"),
            _opt("roll_length", "als Wälzlänge", "as roll length"),
        ],
        binding="correction.length_mode",
        norm_ref="ISO 21771 §6",
    ),
    AttributeDef(
        id="corr_width_mode",
        label_de="Breitenangaben der Modifikationen",
        label_en="Width specifications",
        kind="enum",
        options=[_opt("mm", "in mm", "in mm")],
        binding="correction.width_mode",
    ),
    AttributeDef(
        id="corr_flank_mode",
        label_de="Flanke",
        label_en="Flank",
        kind="enum",
        options=[
            _opt("both_equal", "beide Flanken gleich", "both flanks equal"),
            _opt("separate", "links/rechts getrennt", "left/right separate"),
        ],
        binding="correction.flank_mode",
        info_de="Flanken-Symmetrie-Politik: gespiegelt nur bei identischen Daten "
        "(datengetriebene Prüfung, nie angenommen).",
        info_en="Flank symmetry policy: mirrored only for identical data.",
    ),
    AttributeDef(
        id="corr_non_additive",
        label_de="Nicht-additive Modifikationen zulassen",
        label_en="Allow non-additive modifications",
        kind="bool",
        binding="correction.non_additive",
    ),
    AttributeDef(
        id="corr_scope",
        label_de="Vorgabe Definitionsbereich",
        label_en="Definition range",
        kind="enum",
        options=[_opt("full_field", "Ganzes Eingriffsfeld", "Full field of action")],
        binding="correction.scope_mode",
    ),
    *[
        AttributeDef(
            id=f"corr_{key}_{suffix}",
            label_de=de,
            label_en=en,
            symbol=sym,
            unit=unit,
            kind=kind,  # type: ignore[arg-type]
            options=(
                [
                    _opt("linear", "linear", "linear"),
                    _opt("circular", "kreisbogenförmig", "circular arc"),
                    _opt("symmetric_arc", "Symmetrisch ein Kreisbogen", "Symmetric arc"),
                    _opt(
                        "start_width",
                        "Am Beginn der Zahnbreite (kleinere u-Koordinate)",
                        "At the face-width start (smaller u)",
                    ),
                ]
                if kind == "enum"
                else None
            ),
            binding=f"correction.{key}_{suffix}",
            norm_ref="ISO 21771 §6",
        )
        for key, base_de, base_en, sym in (
            (
                "helix_slope",
                "Winkelmodifikation (Flankenlinie)",
                "helix slope modification",
                "C_Hβ",
            ),
            ("helix_crown", "Balligkeit (Flankenlinie)", "helix crowning", "C_β"),
            ("end_relief_left", "Endrücknahme links", "end relief left", "C_βI"),
            ("end_relief_right", "Endrücknahme rechts", "end relief right", "C_βII"),
            (
                "profile_slope",
                "Winkelmodifikation (Stirnprofil)",
                "profile slope modification",
                "C_Hα",
            ),
            ("profile_crown", "Balligkeit (Stirnprofil)", "profile crowning", "C_α"),
            ("tip_relief", "Kopfrücknahme", "tip relief", "C_αa"),
            ("root_relief", "Fußrücknahme", "root relief", "C_αf"),
            ("tri_tip", "Dreieckförmige Endrücknahme am Kopf", "triangular tip end relief", "C_Ea"),
            (
                "tri_root",
                "Dreieckförmige Endrücknahme am Fuß",
                "triangular root end relief",
                "C_Ef",
            ),
            ("twist", "Verschränkung", "twist", "S_α"),
            ("waviness", "Periodische Flankenwelligkeit", "periodic flank waviness", "C_sin"),
        )
        for suffix, de, en, unit, kind in (
            ("on", f"{base_de} berücksichtigen", f"Consider {base_en}", None, "bool"),
            ("form", f"Form der {base_de}", f"Form of the {base_en}", None, "enum"),
            ("um", f"Betrag der {base_de}", f"Amount of the {base_en}", "µm", "float"),
        )
        if not (key in ("profile_slope", "twist", "waviness") and suffix == "form")
    ],
    AttributeDef(
        id="corr_end_relief_left_len",
        label_de="Länge der Endrücknahme links",
        label_en="End relief length left",
        symbol="l_CI",
        unit="mm",
        binding="correction.end_relief_left_len_mm",
    ),
    AttributeDef(
        id="corr_end_relief_right_len",
        label_de="Länge der Endrücknahme rechts",
        label_en="End relief length right",
        symbol="l_CII",
        unit="mm",
        binding="correction.end_relief_right_len_mm",
    ),
    AttributeDef(
        id="corr_tip_relief_dca",
        label_de="Beginn der Kopfrücknahme (Durchmesser)",
        label_en="Tip relief start diameter",
        symbol="d_Ca",
        unit="mm",
        precision=3,
        binding="correction.tip_relief_dca_mm",
        norm_ref="ISO 21771 §6 (kst-E: 51.946)",
    ),
    AttributeDef(
        id="corr_waviness_len",
        label_de="Wellenlänge der periodischen Flankenwelligkeit",
        label_en="Waviness wavelength",
        symbol="λ_sin",
        unit="mm",
        precision=3,
        binding="correction.waviness_length_mm",
    ),
    # --- Radkörper Stirnrad [40] (screenshot Radkoerper_Allgemein.png) ------------------
    AttributeDef(
        id="wb_material",
        label_de="Werkstoff",
        label_en="Material",
        kind="enum",
        options=[
            _opt("Stanyl_TW200F6_cond_80", "Stanyl_TW200F6_cond_80", "Stanyl_TW200F6_cond_80")
        ],
        binding="materials.gear2_name",  # SSOT: same material as the plastic wheel
    ),
    AttributeDef(
        id="wb_design_mode",
        label_de="Radkörpergestaltung",
        label_en="Wheel-body design",
        kind="enum",
        options=[
            _opt(
                "none_reference",
                "ohne Radkörper (Referenz-Deck, Fesselung am Kranz)",
                "without wheel body (reference deck, rim fixation)",
            ),
            _opt(
                "elastic_cad",
                "elast. Radkörper aus CAD-Datei",
                "elastic wheel body from a CAD file",
            ),
        ],
        binding="wheelBody.design_mode",
        info_de="Das validierte Abwälz-Deck ist die 'ohne Radkörper'-Variante; die "
        "CAD-Anbindung (STP + Tie, C3D10) folgt (Roadmap Workstream C).",
        info_en="The validated rolling deck is the 'without wheel body' variant; the CAD "
        "tie-in (STP, C3D10) follows.",
    ),
    AttributeDef(
        id="wb_angular_position",
        label_de="Winkellagenmodifikation",
        label_en="Angular position modification",
        unit="°",
        precision=1,
        binding="wheelBody.angular_position_deg",
    ),
    AttributeDef(
        id="wb_cad_name",
        label_de="CAD-Körper Name",
        label_en="CAD body name",
        kind="path",
        binding="wheelBody.cad_name",
    ),
    AttributeDef(
        id="wb_cut_diameter",
        label_de="CAD-Radkörper Zuschnittdurchmesser",
        label_en="CAD wheel-body cut diameter",
        unit="mm",
        precision=1,
        binding="wheelBody.cut_diameter_mm",
    ),
    AttributeDef(
        id="wb_stiffness_mode",
        label_de="Anbindesteifigkeit Verzahnungshebelarm in Gesamtsystemberechnung",
        label_en="Coupling stiffness in the system run",
        kind="enum",
        options=[_opt("ideal_stiff", "ideal steif", "ideally stiff")],
        binding="wheelBody.stiffness_mode",
    ),
    # --- Getriebeeinheit → Leistungsfluss (screenshot Getriebeeinheit_Leisutungsfluss) --
    AttributeDef(
        id="pf_n_configurations",
        label_de="Anzahl der Konfigurationen",
        label_en="Number of configurations",
        kind="int",
        binding="powerflow.n_configurations",
    ),
    AttributeDef(
        id="pf_active_configuration",
        label_de="Aktuelle Konfiguration",
        label_en="Active configuration",
        kind="enum",
        options=[_opt("1", "1. Konfig.", "1st config.")],
        binding="powerflow.active_configuration",
    ),
    AttributeDef(
        id="pf_operating_hours",
        label_de="Betriebsdauer",
        label_en="Operating time",
        symbol="h",
        unit="h",
        binding="operatingUi.operating_hours",  # SSOT: same value as the Betriebsdaten tab
    ),
    AttributeDef(
        id="pf_load_switchable",
        label_de="Belastung ist schaltbar",
        label_en="Load is switchable",
        kind="bool",
        per_gear=True,
        bindings=("powerflow.load1_switchable", "powerflow.load2_switchable"),
    ),
    AttributeDef(
        id="pf_speed_shaft1",
        label_de="Drehzahl Welle 1",
        label_en="Speed shaft 1",
        symbol="n",
        unit="1/min",
        precision=2,
        binding="powerflow.speed_shaft1_min1",
        norm_ref="Kinematik",
    ),
    AttributeDef(
        id="pf_speed_shaft2",
        label_de="Drehzahl Welle 2",
        label_en="Speed shaft 2",
        symbol="n",
        unit="1/min",
        precision=2,
        computed=True,
        binding="powerflow.speed_shaft2_min1",
        norm_ref="n₂ = −n₁·z₁/z₂ (Außenverzahnung)",
        info_de="Berechnet aus der Übersetzung — Eingabe nur an Welle 1.",
        info_en="Derived from the ratio — input only at shaft 1.",
    ),
    AttributeDef(
        id="pf_direction",
        label_de="Drehrichtung Welle 1",
        label_en="Rotation sense shaft 1",
        kind="enum",
        options=[
            _opt("cw", "rechtslaufend", "clockwise"),
            _opt("ccw", "linkslaufend", "counter-clockwise"),
        ],
        binding="powerflow.direction_shaft1",
        norm_ref="Prüfstand-Draufsicht (ADR-021)",
        info_de=(
            "Drehsinn des Antriebs — bestimmt die Vorzeichen von Moment und Wälzrichtung "
            "im Abwälz-Deck (rechtslaufend = validierter Referenzfall: Momentenrad dreht "
            "im Uhrzeigersinn)."
        ),
        info_en=(
            "Drive rotation sense — sets the torque/roll signs of the rolling deck "
            "(clockwise = the validated reference case)."
        ),
    ),
    AttributeDef(
        id="pf_load_type",
        label_de="Typ",
        label_en="Type",
        kind="enum",
        per_gear=True,
        options=[_opt("antrieb", "Antrieb", "Input"), _opt("abtrieb", "Abtrieb", "Output")],
        bindings=("powerflow.load1_type", "powerflow.load2_type"),
        info_de="Antrieb: Drehmoment ist Eingabe, Leistung folgt; Abtrieb: beides berechnet.",
        info_en="Input: torque is entered, power follows; output: both derived.",
    ),
    AttributeDef(
        id="pf_power",
        label_de="Leistung",
        label_en="Power",
        symbol="P",
        unit="kW",
        precision=4,
        per_gear=True,
        computed=True,
        bindings=("powerflow.power_load1_kw", "powerflow.power_load2_kw"),
        norm_ref="P = 2π·n/60 · T",
    ),
    AttributeDef(
        id="pf_torque",
        label_de="Drehmoment",
        label_en="Torque",
        symbol="T",
        unit="N·m",
        precision=4,
        per_gear=True,
        nullable=True,
        bindings=("powerflow.torque_shaft1_nm", "powerflow.torque_shaft2_nm"),
        locked_ifs=("powerflow.torque_shaft1_locked", "powerflow.torque_shaft2_locked"),
        norm_ref="T₁ = T₂·z₁/z₂ (verlustfrei)",
        info_de=(
            "DER Lastfall des Systems — Eingabe an Welle 1 ODER Welle 2; die andere "
            "Seite wird über die Übersetzung berechnet und gesperrt. Feld leeren = "
            "Reset (beide Felder frei). Treibt Tragfähigkeit, Stufenvariation, "
            "Dynamik UND das Abwälz-Deck (M₂)."
        ),
        info_en=(
            "THE system load case — enter at shaft 1 OR shaft 2; the other side is "
            "derived via the ratio and locked. Clearing the field resets both. Drives "
            "capacity, variation, dynamics AND the rolling deck (M₂)."
        ),
    ),
    AttributeDef(
        id="pf_u_coordinate",
        label_de="u-Koordinate auf der Welle",
        label_en="u coordinate on the shaft",
        unit="mm",
        precision=3,
        per_gear=True,
        bindings=("powerflow.u_load1_mm", "powerflow.u_load2_mm"),
    ),
    # --- Getriebeeinheit → Kräfte und Momente (per load; FVA defaults 0) ---------------
    *[
        AttributeDef(
            id=f"force_{key}",
            label_de=de,
            label_en=en,
            symbol=sym,
            unit=unit,
            per_gear=True,
            bindings=(f"forces.load1_{key}", f"forces.load2_{key}"),
            info_de="Zusatzlast der Systemrechnung — im Nachbau mitgeführt, noch ohne Löser.",
            info_en="System-run extra load — carried in the replica, solver pending.",
        )
        for key, de, en, sym, unit in (
            ("f_u", "Axiale Kraft", "Axial force", "F_u", "N"),
            ("f_v", "Einzelkraft in v-Richtung", "Point force in v", "F_v", "N"),
            ("f_w", "Einzelkraft in w-Richtung", "Point force in w", "F_w", "N"),
            ("f_r", "Radialkraft", "Radial force", "F_r", "N"),
            ("phi_r", "Winkel der Radialkraft", "Radial force angle", "φ_r", "°"),
            ("f_u_sc", "Skalierbare axiale Kraft", "Scalable axial force", "F_u,sc", "N"),
            (
                "f_v_sc",
                "Skalierbare Einzelkraft in v-Richtung",
                "Scalable force in v",
                "F_v,sc",
                "N",
            ),
            (
                "f_w_sc",
                "Skalierbare Einzelkraft in w-Richtung",
                "Scalable force in w",
                "F_w,sc",
                "N",
            ),
            ("f_r_sc", "Skalierbare Radialkraft", "Scalable radial force", "F_r,sc", "N"),
            (
                "phi_r_sc",
                "Winkel der skalierbaren Radialkraft",
                "Scalable radial force angle",
                "φ_r,sc",
                "°",
            ),
            ("m_v", "Biegemoment um die v-Achse", "Bending moment about v", "M_v", "N·m"),
            ("m_w", "Biegemoment um die w-Achse", "Bending moment about w", "M_w", "N·m"),
            (
                "m_v_sc",
                "Skalierbares Biegemoment um die v-Achse",
                "Scalable bending moment about v",
                "M_v,sc",
                "N·m",
            ),
            (
                "m_w_sc",
                "Skalierbares Biegemoment um die w-Achse",
                "Scalable bending moment about w",
                "M_w,sc",
                "N·m",
            ),
        )
    ],
    # --- Getriebeeinheit → Steuerparameter (screenshot Getriebeeinheit_Steuerparameter) -
    AttributeDef(
        id="ctl_log_io",
        label_de="Aktiviere Logging der Ein- und Ausgabeparameter der Gesamtsystemberechnung",
        label_en="Log the system-run input/output parameters",
        kind="bool",
        binding="control.log_io",
    ),
    AttributeDef(
        id="ctl_nominal_torques",
        label_de="Nominelle Drehmomente für Berechnungen verwenden",
        label_en="Use nominal torques for the calculations",
        kind="bool",
        binding="control.nominal_torques",
    ),
    AttributeDef(
        id="ctl_load_dependent_a",
        label_de="Lastabhängige Achsabstandsveränderung",
        label_en="Load-dependent centre-distance change",
        kind="bool",
        binding="control.load_dependent_center_distance",
    ),
    AttributeDef(
        id="ctl_backlash_mode",
        label_de="Flankenspiel im mech. Gesamtsystem berücksichtigen",
        label_en="Consider backlash in the mechanical system",
        kind="enum",
        options=[
            _opt("ignore", "Nicht berücksichtigen", "Not considered"),
            _opt("consider", "Berücksichtigen", "Considered"),
        ],
        binding="control.backlash_mode",
    ),
    AttributeDef(
        id="ctl_linear_solver",
        label_de="Linearer Gleichungslöser",
        label_en="Linear equation solver",
        kind="enum",
        options=[_opt("native", "NumPy/SciPy (nativ)", "NumPy/SciPy (native)")],
        binding="control.linear_solver",
        info_de="FVA nutzt hier Matlab — der Nachbau rechnet nativ in Python.",
        info_en="FVA uses Matlab here — the replica computes natively in Python.",
    ),
    AttributeDef(
        id="ctl_convergence",
        label_de="Konvergenztoleranz im Gesamtsystem",
        label_en="System convergence tolerance",
        kind="enum",
        options=[_opt("default", "Default", "Default")],
        binding="control.convergence_tolerance",
    ),
    AttributeDef(
        id="ctl_max_iterations",
        label_de="Maximale Iterationszahl für Gesamtsystemberechnung",
        label_en="Maximum system-run iterations",
        kind="int",
        binding="control.max_iterations",
    ),
    AttributeDef(
        id="ctl_bearing_method",
        label_de="Methode der Wälzlagerberechnung",
        label_en="Rolling-bearing method",
        kind="enum",
        options=[_opt("fva_909", "FVA 909", "FVA 909")],
        binding="control.bearing_method",
        info_de="Lagerrechnung ist im Nachbau nicht implementiert (Berechnungsauswahl grau).",
        info_en="Bearing analysis is not implemented in the replica.",
    ),
    AttributeDef(
        id="ctl_width_load_points",
        label_de="Stützstellen für die Lastverteilung entlang der Zahnbreite",
        label_en="Face-width load-distribution points",
        kind="int",
        binding="control.width_load_points",
    ),
    AttributeDef(
        id="ctl_width_correction",
        label_de="Breitenkorrekturvorschlag für gleichmäßige Lastverteilung",
        label_en="Width-correction proposal for uniform load",
        kind="bool",
        binding="control.width_correction_proposal",
    ),
    AttributeDef(
        id="ctl_point_forces",
        label_de="Verzahnungslasten als Einzelkräfte berücksichtigen",
        label_en="Mesh loads as point forces",
        kind="bool",
        binding="control.loads_as_point_forces",
    ),
    AttributeDef(
        id="ctl_idler_tiltable",
        label_de="Zwischen- und Planetenräder sind kippweich gelagert",
        label_en="Idler/planet gears tiltable",
        kind="bool",
        binding="control.idler_tiltable",
    ),
    AttributeDef(
        id="ctl_deviation_multiplier",
        label_de="Multiplikationsfaktor für Verzahnungsabweichung",
        label_en="Deviation multiplication factor",
        precision=1,
        binding="control.deviation_multiplier",
    ),
    AttributeDef(
        id="ctl_mesh_positions",
        label_de="Anzahl der Eingriffsstellungen",
        label_en="Number of mesh positions",
        kind="enum",
        options=[_opt("24", "24", "24"), _opt("12", "12", "12"), _opt("48", "48", "48")],
        binding="control.n_mesh_positions",
    ),
    AttributeDef(
        id="ctl_fourier",
        label_de="Anzahl der Fourierkoeffizienten",
        label_en="Number of Fourier coefficients",
        kind="int",
        binding="control.n_fourier",
    ),
    AttributeDef(
        id="ctl_te_norm",
        label_de="Drehwegfehler zur Normierung der Soundausgabe",
        label_en="Transmission error for sound normalisation",
        unit="µm",
        precision=1,
        binding="control.transmission_error_norm_um",
    ),
    AttributeDef(
        id="ctl_pre_post",
        label_de="Vor- und nachzeitigen Eingriff berücksichtigen",
        label_en="Consider pre-/post-engagement",
        kind="bool",
        binding="control.pre_post_engagement",
    ),
    AttributeDef(
        id="ctl_dyn_stiffness",
        label_de="Berechnung dynamische Verzahnungssteifigkeit",
        label_en="Dynamic mesh-stiffness computation",
        kind="bool",
        binding="control.dynamic_stiffness",
    ),
    AttributeDef(
        id="ctl_mod_criterion",
        label_de="Kriterium für Flankenmodifikationen aus der 3d-Lastverteilung",
        label_en="Criterion for modifications from the 3D load distribution",
        kind="enum",
        options=[_opt("linear_pressure", "Linearer Pressungsanstieg", "Linear pressure rise")],
        binding="control.flank_mod_criterion",
    ),
    AttributeDef(
        id="ctl_min_contact_line",
        label_de="Minimale relative Berührlinienlänge",
        label_en="Minimum relative contact-line length",
        unit="%",
        precision=1,
        binding="control.min_contact_line_pct",
    ),
    AttributeDef(
        id="op_gravity_enabled",
        label_de="Schwerkraft berücksichtigen",
        label_en="Consider gravity",
        kind="bool",
        binding="operatingUi.gravity_enabled",
    ),
    AttributeDef(
        id="op_gravity_u",
        label_de="Richtungsvektor für Schwerkraft (u)",
        label_en="Gravity direction (u)",
        precision=1,
        binding="operatingUi.gravity_u",
    ),
    AttributeDef(
        id="op_gravity_v",
        label_de="Richtungsvektor für Schwerkraft (v)",
        label_en="Gravity direction (v)",
        precision=1,
        binding="operatingUi.gravity_v",
    ),
    AttributeDef(
        id="op_gravity_w",
        label_de="Richtungsvektor für Schwerkraft (w)",
        label_en="Gravity direction (w)",
        precision=1,
        binding="operatingUi.gravity_w",
    ),
    AttributeDef(
        id="op_gravity_g",
        label_de="Erdbeschleunigung",
        label_en="Gravitational acceleration",
        unit="m/s²",
        precision=2,
        binding="operatingUi.gravity_m_s2",
    ),
    AttributeDef(
        id="op_centrifugal",
        label_de="Fliehkraft berücksichtigen",
        label_en="Consider centrifugal force",
        kind="bool",
        binding="operatingUi.centrifugal_enabled",
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
                    RowRef(attr="tool_addendum_factor"),
                    RowRef(attr="tool_tip_radius_factor"),
                    RowRef(attr="tool_dedendum_factor"),
                    RowRef(attr="tool_root_form_height_factor"),
                    RowRef(attr="tool_edge_break_angle"),
                ],
            ),
        ],
    )


def _tolerances_tab() -> TabDef:
    """Stirnradstufe → Toleranzen (screenshot Stirnradstufe_Toleranz.png)."""
    return TabDef(
        id="tolerances",
        title_de="Toleranzen",
        title_en="Tolerances",
        sections=[
            SectionDef(
                id="tooth_width_allowances",
                title_de="Zahnweitenabmaße",
                title_en="Tooth-width allowances",
                rows=[
                    RowRef(attr="tol_awe"),
                    RowRef(attr="tol_awi"),
                    RowRef(attr="tol_aw_factor"),
                    RowRef(attr="tol_aw_selection"),
                ],
                info_de="Das mittlere Zahnweitenabmaß fließt in die Erzeugung (x_E) und "
                "bestimmt das Flankenspiel des Abwälz-Decks (spielschließende Drehung).",
                info_en="The mean allowance feeds the generation (x_E) and sets the rolling "
                "deck backlash (closing rotation).",
            ),
            SectionDef(
                id="centre_distance_allowances",
                title_de="Achsabstandsabmaße",
                title_en="Centre-distance allowances",
                rows=[RowRef(attr="tol_a_upper"), RowRef(attr="tol_a_lower")],
            ),
            SectionDef(
                id="quality",
                title_de="Verzahnungsqualität",
                title_en="Gear quality",
                rows=[RowRef(attr="tol_quality_standard"), RowRef(attr="tol_grade")],
            ),
            SectionDef(
                id="tooth_plot",
                title_de="Anzeige eines benutzerdefinierten Durchmessers im Zahnplot",
                title_en="Custom diameter in the tooth plot",
                rows=[RowRef(attr="tol_custom_diameter")],
            ),
        ],
    )


def _capacity_tab() -> TabDef:
    """Stirnradstufe → Tragfähigkeit (screenshot Stirnradstufe_Tragfaehigkeit.png)."""
    return TabDef(
        id="capacity_inputs",
        title_de="Tragfähigkeit",
        title_en="Load capacity",
        sections=[
            SectionDef(
                id="general",
                title_de="Allgemeine Eingaben zur Tragfähigkeit",
                title_en="General capacity inputs",
                rows=[
                    RowRef(attr="cap_web_mode"),
                    RowRef(attr="cap_rim_mode"),
                    RowRef(attr="cap_roughness_auto"),
                    RowRef(attr="cap_ra_flank"),
                    RowRef(attr="cap_rz_flank"),
                    RowRef(attr="cap_ra_root"),
                    RowRef(attr="cap_rz_root"),
                    RowRef(attr="cap_tip_relief"),
                    RowRef(attr="cap_application_factor"),
                ],
            ),
            SectionDef(
                id="system_parameters",
                title_de="Berechnungsparameter für Gesamtsystem",
                title_en="System-run parameters",
                rows=[RowRef(attr="cap_mesh_stiffness_mode")],
            ),
        ],
    )


def _material_tab() -> TabDef:
    """Stirnradstufe → Werkstoff (screenshot Stirnradstufe_Werkstoff.png)."""
    steel_keys = ["modulus_mpa", "poisson", "sigma_hlim_mpa", "sigma_flim_mpa", "density_kg_dm3"]
    plastic_keys = [
        "modulus_mpa",
        "poisson",
        "sigma_hlim_mpa",
        "sigma_flim_mpa",
        "density_kg_dm3",
        "yield_strength_mpa",
        "allowable_temperature_c",
    ]
    return TabDef(
        id="material",
        title_de="Werkstoff",
        title_en="Material",
        sections=[
            SectionDef(
                id="selection",
                title_de="Allgemeine Werkstoffdaten",
                title_en="General material data",
                rows=[RowRef(attr="mat_name"), RowRef(attr="mat_kind")],
                info_de="Die Werkstoffart ist DIE Weiche: Stahl → ISO 6336, Kunststoff → "
                "VDI 2736 (je Rad); Deck-Materialkarte und Kontaktrollen folgen.",
                info_en="The material kind is THE dispatch: steel → ISO 6336, plastic → "
                "VDI 2736 (per gear); deck cards and contact roles follow.",
            ),
            SectionDef(
                id="steel",
                title_de="Kennwerte Stahl (ISO 6336)",
                title_en="Steel properties (ISO 6336)",
                rows=[
                    *[RowRef(attr=f"mat_steel_{k}") for k in steel_keys],
                    # ISO 6336-3 group + Z_W hardness (audit NRM-07 — rows added
                    # 2026-08-18; the attributes alone were unreachable in the UI)
                    RowRef(attr="mat_root_group"),
                    RowRef(attr="mat_softer_hb"),
                ],
            ),
            SectionDef(
                id="plastic",
                title_de="Kennwerte Kunststoff (VDI 2736)",
                title_en="Plastic properties (VDI 2736)",
                rows=[RowRef(attr=f"mat_plastic_{k}") for k in plastic_keys],
            ),
        ],
    )


def _lubricant_tab() -> TabDef:
    """Stirnradstufe → Schmierstoff (screenshot Stirnradstufe_Schmirstoff.png)."""
    return TabDef(
        id="lubricant",
        title_de="Schmierstoff",
        title_en="Lubricant",
        sections=[
            SectionDef(
                id="selection",
                title_de="Schmierstoff",
                title_en="Lubricant",
                rows=[RowRef(attr="lubricant_name"), RowRef(attr="oil_temperature")],
            ),
            SectionDef(
                id="properties",
                title_de="Schmierstoffangaben",
                title_en="Lubricant data",
                rows=[
                    RowRef(attr="lub_density"),
                    RowRef(attr="lub_visc40"),
                    RowRef(attr="lub_visc100"),
                ],
            ),
        ],
    )


def _vdi2736_tab() -> TabDef:
    """Stirnradstufe → VDI 2736 (2014) (screenshot Stirnradstufe_VDI-2736.png)."""
    return TabDef(
        id="vdi2736",
        title_de="VDI 2736 (2014)",
        title_en="VDI 2736 (2014)",
        visible_if_method="vdi_2736_2014",
        sections=[
            SectionDef(
                id="lubrication",
                title_de="VDI 2736 - Schmierungsart",
                title_en="VDI 2736 - lubrication kind",
                rows=[RowRef(attr="vdi_lubrication_kind")],
            ),
            SectionDef(
                id="temperature",
                title_de="VDI 2736 - Zahntemperatur",
                title_en="VDI 2736 - tooth temperature",
                rows=[
                    RowRef(attr="vdi_ambient_mode"),
                    RowRef(attr="oil_temperature"),
                    RowRef(attr="vdi_duty_cycle"),
                    RowRef(attr="vdi_housing_type"),
                    RowRef(attr="vdi_housing_surface"),
                    RowRef(attr="vdi_friction_mode"),
                    RowRef(attr="vdi_friction_value", visible_if="operating.friction_is_user"),
                    RowRef(attr="vdi_heat_transfer"),
                    RowRef(attr="vdi_tooth_loss"),
                ],
            ),
            SectionDef(
                id="root",
                title_de="VDI 2736 - Fußtragfähigkeit",
                title_en="VDI 2736 - root capacity",
                rows=[RowRef(attr="cap_application_factor"), RowRef(attr="vdi_root_min_safety")],
            ),
            SectionDef(
                id="flank",
                title_de="VDI 2736 - Flankentragfähigkeit",
                title_en="VDI 2736 - flank capacity",
                rows=[RowRef(attr="vdi_flank_min_safety")],
            ),
            SectionDef(
                id="wear",
                title_de="VDI 2736 - Verschleißtragfähigkeit",
                title_en="VDI 2736 - wear capacity",
                rows=[RowRef(attr="vdi_wear_allowable"), RowRef(attr="vdi_wear_coefficient")],
            ),
            SectionDef(
                id="deformation",
                title_de="VDI 2736 - Verformung",
                title_en="VDI 2736 - deformation",
                rows=[RowRef(attr="vdi_deformation_condition")],
            ),
            SectionDef(
                id="peak_loads",
                title_de="VDI 2736 - Spitzenlasten",
                title_en="VDI 2736 - peak loads",
                rows=[RowRef(attr="vdi_static_overload")],
            ),
        ],
    )


def _loaddist_fem_tab() -> TabDef:
    """Stirnradstufe → Lastverteilung (FEM, FVA 377) (screenshot)."""
    return TabDef(
        id="loaddist_fem",
        title_de="Lastverteilung (FEM)",
        title_en="Load distribution (FEM)",
        visible_if_method="fva_377_fem",
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
                title_de="Berechnungsparameter",
                title_en="Parameters",
                info_de="Der FVA-377-Löser (3D-Lastverteilung) ist im Nachbau noch nicht "
                "implementiert — Vernetzung und Fesselung sind funktional.",
                info_en="The FVA-377 solver is not implemented in the replica yet — meshing "
                "and fixation are functional.",
                rows=[
                    RowRef(attr="ld_position_mode"),
                    RowRef(attr="ld_positions"),
                    RowRef(attr="ld_stress_eval"),
                    RowRef(attr="ld_save_influence"),
                    RowRef(attr="ld_auto_overroll"),
                ],
            ),
            SectionDef(
                id="meshing",
                title_de="Vernetzung",
                title_en="Meshing",
                rows=[
                    RowRef(attr="ld_meshing_accuracy"),
                    RowRef(attr="ld_run_meshing"),
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
                info_de="Gleiche Fesselung wie das Abwälz-Deck (gemeinsame Einstellung).",
                info_en="Same fixation as the rolling deck (shared setting).",
            ),
            SectionDef(
                id="expert",
                title_de="Individuelle Konfiguration für die FE-Stirnradberechnung "
                "(Expertenfunktion)",
                title_en="Individual FE configuration (expert function)",
                rows=[RowRef(attr="fem_expert_stirak")],
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
                    RowRef(attr="fem_rigid_shell"),
                    RowRef(attr="fem_deck_mode"),
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


def _mod_block(key: str, extra: list[RowRef] | None = None) -> list[RowRef]:
    """on / form / amount rows of one modification (+ optional extra rows)."""
    rows = [RowRef(attr=f"corr_{key}_on")]
    rows.append(RowRef(attr=f"corr_{key}_form", visible_if=f"correction.{key}_on"))
    rows.append(RowRef(attr=f"corr_{key}_um", visible_if=f"correction.{key}_on"))
    return rows + (extra or [])


def _correction_tabs() -> list[TabDef]:
    """Flankenmodifikation [34] — the five FVA editor tabs (screenshots)."""
    general = TabDef(
        id="general",
        title_de="Allgemeine Angaben",
        title_en="General",
        sections=[
            SectionDef(
                id="general",
                title_de="Allgemeine Angaben",
                title_en="General",
                rows=[
                    RowRef(attr="corr_length_mode"),
                    RowRef(attr="corr_width_mode"),
                    RowRef(attr="corr_flank_mode"),
                    RowRef(attr="corr_non_additive"),
                    RowRef(attr="corr_scope"),
                ],
                info_de="Die Beträge, die unser Mikrogeometrie-Modell trägt (C_Hβ, C_β, "
                "C_βI/II, C_α, C_αa, C_αf), fließen in die Stage — weitere Formen werden "
                "mitgeführt (Mechanik folgt mit der Lastverteilung).",
                info_en="Amounts our micro-geometry model carries flow into the stage; "
                "further forms are carried (mechanics follows with the load distribution).",
            ),
        ],
    )
    helix = TabDef(
        id="helix",
        title_de="Flankenlinie",
        title_en="Helix",
        sections=[
            SectionDef(
                id="slope",
                title_de="Winkelmodifikation",
                title_en="Slope modification",
                rows=_mod_block("helix_slope"),
            ),
            SectionDef(
                id="crown",
                title_de="Balligkeit",
                title_en="Crowning",
                rows=_mod_block("helix_crown"),
            ),
            SectionDef(
                id="end_left",
                title_de="Endrücknahme links",
                title_en="End relief left",
                rows=_mod_block(
                    "end_relief_left",
                    [
                        RowRef(
                            attr="corr_end_relief_left_len",
                            visible_if="correction.end_relief_left_on",
                        )
                    ],
                ),
            ),
            SectionDef(
                id="end_right",
                title_de="Endrücknahme rechts",
                title_en="End relief right",
                rows=_mod_block(
                    "end_relief_right",
                    [
                        RowRef(
                            attr="corr_end_relief_right_len",
                            visible_if="correction.end_relief_right_on",
                        )
                    ],
                ),
            ),
        ],
    )
    profile = TabDef(
        id="profile",
        title_de="Stirnprofil",
        title_en="Profile",
        sections=[
            SectionDef(
                id="slope",
                title_de="Winkelmodifikation",
                title_en="Slope modification",
                rows=[
                    RowRef(attr="corr_profile_slope_on"),
                    RowRef(attr="corr_profile_slope_um", visible_if="correction.profile_slope_on"),
                ],
            ),
            SectionDef(
                id="crown",
                title_de="Balligkeit",
                title_en="Crowning",
                rows=_mod_block("profile_crown"),
            ),
            SectionDef(
                id="tip",
                title_de="Kopfrücknahme",
                title_en="Tip relief",
                rows=_mod_block(
                    "tip_relief",
                    [RowRef(attr="corr_tip_relief_dca", visible_if="correction.tip_relief_on")],
                ),
                info_de="kst-E: C_αa = 8 µm ab d_Ca = 51.946 mm (Referenz).",
                info_en="kst-E: C_αa = 8 µm from d_Ca = 51.946 mm (reference).",
            ),
            SectionDef(
                id="root",
                title_de="Fußrücknahme",
                title_en="Root relief",
                rows=_mod_block("root_relief"),
            ),
        ],
    )
    further = TabDef(
        id="further",
        title_de="Weitere Formen",
        title_en="Further forms",
        sections=[
            SectionDef(
                id="tri_tip",
                title_de="Dreieckförmige Endrücknahme am Kopf",
                title_en="Triangular tip end relief",
                rows=_mod_block("tri_tip"),
            ),
            SectionDef(
                id="tri_root",
                title_de="Dreieckförmige Endrücknahme am Fuß",
                title_en="Triangular root end relief",
                rows=_mod_block("tri_root"),
            ),
            SectionDef(
                id="twist",
                title_de="Verschränkung",
                title_en="Twist",
                rows=[
                    RowRef(attr="corr_twist_on"),
                    RowRef(attr="corr_twist_um", visible_if="correction.twist_on"),
                ],
            ),
            SectionDef(
                id="waviness",
                title_de="Periodische Flankenwelligkeit",
                title_en="Periodic flank waviness",
                rows=[
                    RowRef(attr="corr_waviness_on"),
                    RowRef(attr="corr_waviness_um", visible_if="correction.waviness_on"),
                    RowRef(attr="corr_waviness_len", visible_if="correction.waviness_on"),
                ],
            ),
        ],
    )
    matrix = TabDef(
        id="matrix",
        title_de="Matrix",
        title_en="Matrix",
        sections=[
            SectionDef(
                id="matrix",
                title_de="Eingaben einer Modifikationsmatrix",
                title_en="Modification matrix input",
                rows=[],
                info_de="Der Matrixeditor (Breiten-/Höhenstützpunkte, Import, Invertieren, "
                "Spiegeln) folgt mit der 3D-Lastverteilung.",
                info_en="The matrix editor follows with the 3D load distribution.",
            ),
        ],
    )
    return [general, helix, profile, further, matrix]


def _wheel_body_tab() -> TabDef:
    """Radkörper Stirnrad [40] (screenshot Radkoerper_Allgemein.png)."""
    return TabDef(
        id="wheel_body",
        title_de="Radkörper",
        title_en="Wheel body",
        sections=[
            SectionDef(
                id="material",
                title_de="Werkstoffdaten",
                title_en="Material data",
                rows=[RowRef(attr="wb_material")],
            ),
            SectionDef(
                id="design",
                title_de="Radkörpergestaltung",
                title_en="Wheel-body design",
                rows=[RowRef(attr="wb_design_mode")],
            ),
            SectionDef(
                id="mounting",
                title_de="Einbaulage",
                title_en="Mounting position",
                rows=[RowRef(attr="wb_angular_position")],
            ),
            SectionDef(
                id="fem_binding",
                title_de="Schrittweise FEM-Anbindung durchführen (nur einmal notwendig)",
                title_en="Step-wise FEM tie-in (only once)",
                visible_if="wheelBody.design_is_cad",
                rows=[
                    RowRef(attr="wb_cad_name"),
                    RowRef(attr="wb_cut_diameter"),
                    RowRef(attr="wb_stiffness_mode"),
                ],
                info_de="Schritte 1–5 (Positionierung, FEM-Vernetzung, Netzqualität, "
                "FE-Ankoppelknoten, Steifigkeitsberechnung) folgen mit der "
                "CAD-Radkörper-Anbindung.",
                info_en="Steps 1–5 follow with the CAD wheel-body tie-in.",
            ),
        ],
    )


def _powerflow_tab() -> TabDef:
    """Getriebeeinheit → Leistungsfluss (screenshot Getriebeeinheit_Leisutungsfluss.png)."""
    return TabDef(
        id="powerflow",
        title_de="Leistungsfluss",
        title_en="Power flow",
        sections=[
            SectionDef(
                id="switch_matrix",
                title_de="Schaltmatrix",
                title_en="Switching matrix",
                rows=[
                    RowRef(attr="pf_n_configurations"),
                    RowRef(attr="pf_active_configuration"),
                    RowRef(attr="pf_operating_hours"),
                    RowRef(attr="pf_load_switchable"),
                ],
            ),
            SectionDef(
                id="io_loads",
                title_de="Ein- und Ausgangsbelastungen",
                title_en="Input and output loads",
                info_de="Antrieb und Abtrieb schließen sich gegenseitig aus (Umschalten "
                "wechselt die Gegenseite mit). Drehmoment an Welle 1 ODER Welle 2 "
                "eingeben — die andere Seite wird über z₁/z₂ berechnet und gesperrt; "
                "Feld leeren setzt beide zurück.",
                info_en="Input and output are mutually exclusive (flipping one flips the "
                "other). Enter the torque at shaft 1 OR shaft 2 — the other side is "
                "derived via z₁/z₂ and locked; clearing the field resets both.",
                rows=[
                    RowRef(attr="pf_speed_shaft1"),
                    RowRef(attr="pf_speed_shaft2"),
                    RowRef(attr="pf_direction"),
                    RowRef(attr="pf_load_type"),
                    RowRef(attr="pf_power"),
                    RowRef(attr="pf_torque"),
                    RowRef(attr="pf_u_coordinate"),
                ],
            ),
        ],
    )


def _forces_tab() -> TabDef:
    """Getriebeeinheit → Kräfte und Momente (screenshot, per-load pair columns)."""
    force_rows = ["f_u", "f_v", "f_w", "f_r", "phi_r"]
    scalable_rows = ["f_u_sc", "f_v_sc", "f_w_sc", "f_r_sc", "phi_r_sc"]
    return TabDef(
        id="forces",
        title_de="Kräfte und Momente",
        title_en="Forces and moments",
        sections=[
            SectionDef(
                id="position",
                title_de="Position auf der Welle",
                title_en="Position on the shaft",
                rows=[RowRef(attr="pf_u_coordinate")],
            ),
            SectionDef(
                id="switchability",
                title_de="Schaltbarkeit",
                title_en="Switchability",
                rows=[RowRef(attr="pf_load_switchable")],
            ),
            SectionDef(
                id="torques",
                title_de="Drehmomente/Leistungen",
                title_en="Torques/powers",
                info_de="Die Übersicht zu allen Drehmomenten, Leistungen und Drehzahlen "
                "befindet sich im Editor „Leistungsfluss“ unter der Getriebeeinheit.",
                info_en="The full torque/power/speed overview lives in the power-flow editor.",
                rows=[
                    RowRef(attr="pf_load_type"),
                    RowRef(attr="pf_power"),
                    RowRef(attr="pf_torque"),
                ],
            ),
            SectionDef(
                id="point_forces",
                title_de="Einzelkräfte",
                title_en="Point forces",
                rows=[RowRef(attr=f"force_{k}") for k in force_rows],
            ),
            SectionDef(
                id="scalable_forces",
                title_de="Skalierbare Einzelkräfte",
                title_en="Scalable point forces",
                rows=[RowRef(attr=f"force_{k}") for k in scalable_rows],
            ),
            SectionDef(
                id="bending",
                title_de="Biegemomente",
                title_en="Bending moments",
                rows=[RowRef(attr="force_m_v"), RowRef(attr="force_m_w")],
            ),
            SectionDef(
                id="scalable_bending",
                title_de="Skalierbare Biegemomente",
                title_en="Scalable bending moments",
                rows=[RowRef(attr="force_m_v_sc"), RowRef(attr="force_m_w_sc")],
            ),
        ],
    )


def _control_tab() -> TabDef:
    """Getriebeeinheit → Steuerparameter (screenshot Getriebeeinheit_Steuerparameter.png)."""
    return TabDef(
        id="control",
        title_de="Steuerparameter",
        title_en="Control parameters",
        sections=[
            SectionDef(
                id="system",
                title_de="Berechnungsparameter für Gesamtsystem",
                title_en="System-run parameters",
                info_de="Diese Schalter steuern den FVA-Gesamtsystemlöser; der Nachbau führt "
                "sie mit, gerechnet wird nativ (ISO 6336/VDI 2736 + FE-Deck).",
                info_en="These switches steer the FVA system solver; the replica carries "
                "them, computation is native (ISO 6336/VDI 2736 + FE deck).",
                rows=[
                    RowRef(attr="ctl_log_io"),
                    RowRef(attr="ctl_nominal_torques"),
                    RowRef(attr="ctl_load_dependent_a"),
                    RowRef(attr="ctl_backlash_mode"),
                    RowRef(attr="ctl_linear_solver"),
                    RowRef(attr="ctl_convergence"),
                    RowRef(attr="ctl_max_iterations"),
                ],
            ),
            SectionDef(
                id="bearing",
                title_de="Wälzlagerberechnung",
                title_en="Rolling-bearing analysis",
                rows=[RowRef(attr="ctl_bearing_method")],
            ),
            SectionDef(
                id="load_distribution",
                title_de="Analytische Lastverteilungsberechnung (Stirnräder)",
                title_en="Analytic load distribution (cylindrical gears)",
                rows=[
                    RowRef(attr="ctl_width_load_points"),
                    RowRef(attr="ctl_width_correction"),
                    RowRef(attr="ctl_point_forces"),
                    RowRef(attr="ctl_idler_tiltable"),
                    RowRef(attr="ctl_deviation_multiplier"),
                    RowRef(attr="ctl_mesh_positions"),
                    RowRef(attr="ctl_fourier"),
                    RowRef(attr="ctl_te_norm"),
                    RowRef(attr="ctl_pre_post"),
                    RowRef(attr="ctl_dyn_stiffness"),
                    RowRef(attr="ctl_mod_criterion"),
                    RowRef(attr="ctl_min_contact_line"),
                ],
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
            SectionDef(
                id="gravity",
                title_de="Schwerkraft",
                title_en="Gravity",
                rows=[
                    RowRef(attr="op_gravity_enabled"),
                    RowRef(attr="op_gravity_u"),
                    RowRef(attr="op_gravity_v"),
                    RowRef(attr="op_gravity_w"),
                    RowRef(attr="op_gravity_g"),
                ],
            ),
            SectionDef(
                id="centrifugal",
                title_de="Fliehkraft",
                title_en="Centrifugal force",
                rows=[RowRef(attr="op_centrifugal")],
            ),
        ],
    )


# ------------------------------------------------------------------------------------------
# dependency rules (norm-referenced; each one is a glossary entry)
# ------------------------------------------------------------------------------------------
RULES: list[DependencyRule] = [
    DependencyRule(
        id="load_types_mutually_exclusive",
        when="powerflow.load1_type",
        effect="compute",
        targets=["powerflow.load2_type"],
        description_de=(
            "Antrieb und Abtrieb schließen sich gegenseitig aus: Umschalten des Typs "
            "einer Welle stellt die Gegenseite automatisch auf das Komplement (eine "
            "Welle treibt, die andere wird getrieben)."
        ),
        description_en=(
            "Input and output are mutually exclusive: flipping one shaft's type sets "
            "the other shaft to the complement (one drives, one is driven)."
        ),
        norm_ref="Leistungsbilanz",
    ),
    DependencyRule(
        id="torque_single_input_converts",
        when="powerflow.torque_shaft1_locked",
        effect="lock",
        targets=["powerflow.torque_shaft1_nm", "powerflow.torque_shaft2_nm"],
        description_de=(
            "EIN Drehmoment für das System: Eingabe an Welle 1 ODER Welle 2; die "
            "Gegenseite wird verlustfrei über die Übersetzung berechnet "
            "(T₁ = T₂·z₁/z₂) und gesperrt. Feld leeren setzt beide zurück. Dieser "
            "eine Wert speist Tragfähigkeit, Stufenvariation, Dynamik und das "
            "Abwälz-Deck (M₂)."
        ),
        description_en=(
            "ONE system torque: entered at shaft 1 OR shaft 2; the other side is "
            "derived loss-free via the ratio (T₁ = T₂·z₁/z₂) and locked. Clearing "
            "resets both. This single value feeds capacity, variation, dynamics and "
            "the rolling deck (M₂)."
        ),
        norm_ref="Leistungsbilanz (verlustfrei)",
    ),
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
            # FVA tab order: Berechnungsauswahl (frontend matrix) · Leistungsfluss ·
            # Kräfte und Momente · Betriebsdaten · Steuerparameter
            tabs=[_powerflow_tab(), _forces_tab(), _operating_data_tab(), _control_tab()],
        ),
        ComponentDef(
            id="cylindrical_mesh",
            label_de="Stirnradstufe",
            label_en="Cylindrical gear stage",
            # FVA tab order: Geometrie · Toleranzen · Tragfähigkeit · VDI 2736 (2014) ·
            # Werkstoff · Schmierstoff · Lastverteilung (FEM) · Dynamisches Abwälzen (FEM)
            tabs=[
                _geometry_tab(),
                _tolerances_tab(),
                _capacity_tab(),
                _vdi2736_tab(),
                _material_tab(),
                _lubricant_tab(),
                _loaddist_fem_tab(),
                _transient_fem_tab(),
            ],
        ),
        ComponentDef(
            id="gear_correction",
            label_de="Flankenmodifikation",
            label_en="Flank modification",
            tabs=_correction_tabs(),
        ),
        ComponentDef(
            id="wheel_body_cylindrical_gear",
            label_de="Radkörper Stirnrad",
            label_en="Cylindrical gear wheel body",
            tabs=[_wheel_body_tab()],
        ),
    ]
    return UiSchema(
        version=SCHEMA_VERSION,
        components=components,
        attributes={a.id: a for a in ATTRIBUTES},
        rules=RULES,
        methods=METHODS,
    )
