"""Evaluation of the measurements of the manufactured gears: Klingelnberg P40 gear measurement
(GINA value and curve files), P40 contour scans and Hommel roughness.

The parsers live in ``gearcore.io`` (``p40``, ``p40_contour``, ``hommel``); the modules here are
pure: they take parsed files and return frozen results, they write nothing and draw nothing
(``scripts/measurements.py`` does both). Norm quantities (profile, helix, pitch and runout
deviations of DIN ISO 1328-1, roughness of ISO/TR 6336-30) come from the quantity registry;
fit statistics (edge radius, axis offset, RMS) are coordinates and carry no registry name, like
``gearcore.contour``.

Modules: ``inventory`` (which files exist for which part, measurement rounds, anomalies),
``gina`` (typed GINA results, tooth tables, tip relief), ``contour_scan`` (axis fit, involute
deviation, tip corners, nominal comparison), ``wear`` (two scans of the same tooth),
``roughness`` (R_a, R_z per flank and group), ``report`` (German tables and labels).
"""
