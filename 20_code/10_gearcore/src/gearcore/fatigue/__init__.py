"""Design check of the plastic wheel after Stommel, Stojek and Korte (2018), chapter 6.

The simplified strength check of the book (``Vereinfachte Vorgehensweise zum Festigkeitsnachweis
thermoplastischer Kunststoffbauteile``) is a utilisation check per FE node: an equivalent stress
interpolated between von Mises and the normal stress hypothesis by the control variable q,
the degree of multiaxiality h after Hencky that scales the permissible strain between the bounds
of the reduction factor A of the material class, a static utilisation a_stat (section 6.2) and a
cyclic utilisation a_B,V (section 6.3) from a Goodman mean stress factor K_M with four overload
cases and a synthetic Basquin line between the static strength at N = 1 and the alternating
strength σ_W = A_W K at N_G = 10^7. The method prescribes a linear elastic, isotropic model of
the component even for short-fibre materials (section 6.2.1, p. 344), so the material step W1 of
the FE model is its basis; it knows no damage accumulation and no statistics. It has not been
applied to gears before (ADR-118).

Modules: ``stommel`` (one traced function per equation of chapter 6), ``materials`` (the class
tables of the book, the stress-strain curves of the material at room and at service temperature,
the K-value, the strain limits and the strengths they give), ``check`` (the history of a node
over the mesh cycle, assembled from the stress files of the positions, and the node-wise static
and cyclic check). The reader of the stress files is ``gearcore.fe.stress``; the scripts draw and
write (``scripts/fe_fatigue.py``). The anisotropic evaluation of W3/W4 is the own extension of
the thesis and lives apart from the published method (track E7, not implemented here).
"""
