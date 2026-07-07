"""
@module: app.api.fem_results
@context: API layer — upload/parse of the Abaqus postprocessing dump + the path-of-contact
          transformation for the 3-D stress/strain viewer (phase G, user goal 2026-07-06).
@role: ``POST /api/fem/results`` takes the ``fem_results.json`` produced by the bundled
       ``abaqus_fem_postprocessing.py`` (the browser reads the file client-side, like the
       .ste import) together with THE shared ``StageParams`` and returns viewer-ready data:
       every flank node's radius is unwrapped onto the LINE OF ACTION as
       ``xi(r) = ±(sqrt(r² − r_b²) − r_w·sin α_wt)`` relative to the pitch point C — gear 1
       positive towards E (its tip), gear 2 negative towards A (its tip) — using the SAME
       :class:`GearStage` quantities as the Zahneingriff plot (single source of truth). The
       A/B/C/D/E markers and the extended usable range (d_Nf … d_Na, i.e. beyond A/E for
       pre-/post-engagement of the compliant plastic pair) come along as axis annotations.
"""

from __future__ import annotations

import math
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.stage_params import StageParams
from app.services.geometry.tooth_form import ToothProfile

router = APIRouter(prefix="/api/fem", tags=["fem-results"])

_TAG = re.compile(r"^G([12])T(\d{3})F([12])$")


class FemResultsRequest(BaseModel):
    """The postprocessing dump (client-side file read) + the stage for the unwrapping."""

    stage: StageParams = Field(default_factory=StageParams)
    results: dict


class FlankFrameData(BaseModel):
    """One flank set at one measurement frame, viewer-ready (structure of arrays)."""

    xi: list[float]  # path-of-contact coordinate relative to C [mm] (gear-signed)
    z: list[float]  # axial coordinate over the face width [mm]
    s_mises: list[float]
    s_maxp: list[float]
    s_minp: list[float]
    e_mises: list[float]
    e_maxp: list[float]
    cpress: list[float]
    u: list[float]
    max_mises: float
    max_cpress: float
    # grid reconstruction hint: nodes are sorted (z, r); n_z · n_xi == len(xi) for the
    # structured flank band, letting the viewer draw a surface instead of a point cloud
    n_z: int
    n_xi: int


class FrameOut(BaseModel):
    index: int
    phi_driven_rad: float | None = None
    flanks: dict[str, FlankFrameData]


class LineOfActionMarkers(BaseModel):
    """ξ positions of the ISO 21771 points on the path of contact (C = 0)."""

    a: float
    b: float
    c: float
    d: float
    e: float
    # extended usable range beyond A/E (root/tip form circles — pre-/post-engagement)
    xi_min: float  # from gear 2's usable tip / gear 1's root form circle
    xi_max: float  # from gear 1's usable tip / gear 2's root form circle
    transverse_base_pitch_mm: float


class FemResultsResponse(BaseModel):
    mode: str
    n_frames: int
    flank_tags: list[str]  # every G{g}T{ttt}F{f} present, sorted
    markers: LineOfActionMarkers
    frames: list[FrameOut]


def _unwrap(stage_r_b: float, r_w_sin: float, sign: float, radius: float) -> float:
    """ξ(r) = sign · (sqrt(r² − r_b²) − r_w·sin α_wt); r below the base circle clamps to T."""
    tangent = math.sqrt(max(radius * radius - stage_r_b * stage_r_b, 0.0))
    return sign * (tangent - r_w_sin)


@router.post("/results", response_model=FemResultsResponse)
def fem_results(req: FemResultsRequest) -> FemResultsResponse:
    """Transform the Abaqus dump into path-of-contact viewer data (GearStage SSOT)."""
    data = req.results
    if data.get("schema") != "zahnfuss.fem_results/1":
        raise HTTPException(422, "not a fem_results.json dump (schema zahnfuss.fem_results/1)")
    frames_in = data.get("frames")
    if not isinstance(frames_in, list) or not frames_in:
        raise HTTPException(422, "dump carries no measurement frames")

    stage = req.stage.stage()
    usable = stage.usable_tip_diameter_mm
    if usable is None:
        raise HTTPException(422, "stage carries no generation data (usable tip circles)")
    alpha_wt = math.radians(stage.working_pressure_angle_deg)
    rb = [d / 2.0 for d in stage.base_diameter_mm]
    rw = [d / 2.0 for d in stage.working_pitch_diameter_mm]
    rw_sin = [r * math.sin(alpha_wt) for r in rw]
    # gear sign on the ξ axis: gear 1 unwraps towards E (+), gear 2 towards A (−) —
    # matches line_of_action_points (E = gear-1 tip, A = gear-2 tip)
    sign = {1: 1.0, 2: -1.0}

    # A/B/C/D/E from the same terms as GearStage.path_of_contact_mm (ISO 21771 eq. 77)
    xi_e = _unwrap(rb[0], rw_sin[0], 1.0, usable[0] / 2.0)
    xi_a = _unwrap(rb[1], rw_sin[1], -1.0, usable[1] / 2.0)
    p_et = stage.transverse_base_pitch_mm
    # extended range d_Nf … d_Na: the root form circles come from the validated
    # tooth-profile chain (same d_Ff the mesher and the contour preview use)
    d_ff = (ToothProfile.from_stage(stage, 0).d_Ff, ToothProfile.from_stage(stage, 1).d_Ff)
    xi_min = min(xi_a, _unwrap(rb[0], rw_sin[0], 1.0, d_ff[0] / 2.0))
    xi_max = max(xi_e, _unwrap(rb[1], rw_sin[1], -1.0, d_ff[1] / 2.0))
    markers = LineOfActionMarkers(
        a=round(xi_a, 4),
        b=round(xi_e - p_et, 4),
        c=0.0,
        d=round(xi_a + p_et, 4),
        e=round(xi_e, 4),
        xi_min=round(xi_min, 4),
        xi_max=round(xi_max, 4),
        transverse_base_pitch_mm=round(p_et, 4),
    )

    tags: set[str] = set()
    frames_out: list[FrameOut] = []
    for frame in frames_in:
        flanks_out: dict[str, FlankFrameData] = {}
        for tag, nodes in (frame.get("flanks") or {}).items():
            m = _TAG.match(tag)
            if m is None or not nodes:
                continue
            gear = int(m.group(1))
            g = gear - 1
            xi = [round(_unwrap(rb[g], rw_sin[g], sign[gear], float(nd["r"])), 4) for nd in nodes]
            z = [float(nd["z"]) for nd in nodes]
            n_z = len(set(z))
            n_xi = len(nodes) // n_z if n_z and len(nodes) % n_z == 0 else 0
            mises = [float(nd.get("s_mises", 0.0)) for nd in nodes]
            cpress = [float(nd.get("cpress", 0.0)) for nd in nodes]
            flanks_out[tag] = FlankFrameData(
                xi=xi,
                z=z,
                s_mises=mises,
                s_maxp=[float(nd.get("s_maxp", 0.0)) for nd in nodes],
                s_minp=[float(nd.get("s_minp", 0.0)) for nd in nodes],
                e_mises=[float(nd.get("e_mises", 0.0)) for nd in nodes],
                e_maxp=[float(nd.get("e_maxp", 0.0)) for nd in nodes],
                cpress=cpress,
                u=[float(nd.get("u", 0.0)) for nd in nodes],
                max_mises=round(max(mises), 4),
                max_cpress=round(max(cpress), 4),
                n_z=n_z,
                n_xi=n_xi,
            )
            tags.add(tag)
        frames_out.append(
            FrameOut(
                index=int(frame.get("index", len(frames_out) + 1)),
                phi_driven_rad=frame.get("phi_driven_rad"),
                flanks=flanks_out,
            )
        )

    if not tags:
        raise HTTPException(422, "dump carries no G{g}T{ttt}F{f} flank data")
    return FemResultsResponse(
        mode=str(data.get("mode", "unknown")),
        n_frames=len(frames_out),
        flank_tags=sorted(tags),
        markers=markers,
        frames=frames_out,
    )
