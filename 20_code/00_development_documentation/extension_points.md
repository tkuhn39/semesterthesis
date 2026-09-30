# Extension points (prepared, not implemented in stage 1)

Each item below is represented in the contracts today and raises `NotSupportedError` with a clear
message; a test asserts that behaviour so nothing is silently wrong. Adding the feature means removing
the guard and implementing the branch against its primary source.

| Extension | Contract hook today | Primary source for the future branch | Notes |
|---|---|---|---|
| Internal gears (Hohlräder) | `GearInput.kind = GearKind.INTERNAL`; `.ste` `ZAEHNEZAHL < 0` is parsed and mapped | DIN ISO 21771:2014 (internal-gear equations throughout §4–§7), DIN 21773:2014 §7.3 (Messlückenzahl), DIN 3960:1987 | sign conventions differ per norm; needed for planetary ring gears |
| Rack as a mating element (Zahnstange, z → ∞) | not a `GearInput`; a future `RackInput` | DIN ISO 21771:2014 §5 (limit case), STplus manual §5.3 | different from rack-type **tools**, which are the stage-1 core |
| Planetary stage | sun/planet already work as an external pair; ring gear needs internal branch | DIN ISO 21771:2014; DIN 3990-11 Annex B example | STplus manual §5.2 |
| Shaper cutter / profile tools | `ToolProfile.kind = ToolKind.SHAPER / PROFILE`; `.ste` `SR_*` / `PW_*` keys are parsed and kept | DIN 3960:1987 §3.6 (Schneidrad), DIN 1829; FVA 604 I (Flankengenerator) | envelope of a circular tool instead of a rack |
| Second tool / machining allowance | `GearInput.finishing_tool`, `ToolProfile.machining_allowance_mm`, `.ste` `WERKZEUG_FERTIGVERZ.`, `BEARBEITUNGSZUGABE` | DIN ISO 21771:2014 §7.2; DIN 3960:1987 Annex A; STplus manual §4.2 | pre-/finish-machined states (Vor-/Fertigverzahnung) |
| Protuberance flank | `ToolProfile.protuberance_mm`, `protuberance_angle_deg` | DIN 3960:1987 A.3.3; DIN ISO 21771:2014 §7.1 | root relief / Fußfreischnitt |
| Non-circular tool tip (elliptic/free) | `.ste` `PW_KOPFART`, `PW_KOPF_XY`, `PW_KOPF_POLAR` parsed | STplus manual §4.16.2.4; Dong et al. 2020 (Bézier tip) | reuses the general envelope sampler |
| Tool referenced by name from the STplus tool database | `gearcore.stplus_program.tool_database()`, `stplus_tool(name)`; the `.ste` importer requires the tool block in the file | STplus manual p. 21 (tool files 1 to 10, local before global); ADR-109 | the importer would look the name up in the packaged databases; records that are no valid contract stay rejected |
| Load capacity, materials, fillet variants, FE | separate stages (see roadmap) | ISO 6336:2019 family, VDI 2736, patents/papers in `00_literatur` | contracts (`MaterialKind`, `MaterialRecord`) exist from stage 1 |
