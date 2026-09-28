"""STplus oracle — run FVA STplus in batch mode or import supplied ``.ste``/``.sta`` pairs as fixtures.

Windows only for ``run`` (needs the local installation); ``import`` and ``discover`` work anywhere.
The installation directory is read-only for this script. STplus opens its runtime companions
(``debug.dbe``, ``DEFAULT.STY``) relative to the working directory, so they are copied into the
scratch directory; contour files are redirected there via ``Pfad_Meldungsausgabe``. Should STplus
nevertheless write into ``bin/``, the run fails loudly instead of adopting foreign files.

    python scripts/stplus_oracle.py discover
    python scripts/stplus_oracle.py import --case kst_e --ste <path> --sta <path> --trust verified
    python scripts/stplus_oracle.py run --case fzg_c --ste <path> [--plot-accuracy 0.005]
    python scripts/stplus_oracle.py run-all            # everything listed in scripts/oracle_cases.yaml

Fixture layout ``src/gearcore/data/stplus/<case>/``: ``input.ste`` (as run), ``report.sta.txt`` (raw
listing; ``*.sta`` is git-ignored repo-wide), ``geometry.json`` (DIN 3960 geometry block + pairing
notes), ``report.json`` (every parsed value), ``interface.sts.txt``/``interface.json`` (STplus
interface file, own runs only), ``contour_wz1.json``/``contour_wz2.json`` (transverse tooth contours,
own runs only), ``meta.json`` (STplus version, trust, provenance, settings).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from gearcore.io.sta import StaReport, load_sta
from gearcore.io.ste import is_number, load_ste, pair_input_from_ste, parse_ste
from gearcore.io.stplus_contour import load_contour
from gearcore.models.inputs import MaterialKind

HERE = Path(__file__).resolve().parent
PKG_ROOT = HERE.parent
REPO_ROOT = PKG_ROOT.parents[1]
FIXTURES = PKG_ROOT / "src" / "gearcore" / "data" / "stplus"
DEFAULT_STPLUS_ROOT = REPO_ROOT / "30_references_and_examples" / "33_STplus" / "STplus11-1F"
REFERENCE_DIRS = (
    REPO_ROOT / "30_references_and_examples" / "33_STplus",
    REPO_ROOT / "30_references_and_examples" / "33_STplus" / "weitere_Konfigurationen",
)
CASES_FILE = HERE / "oracle_cases.yaml"
TRUST_LEVELS = ("verified", "unverified", "generated")
COMPANIONS = ("debug.dbe", "DEFAULT.STY")

PRINT_BLOCK = """$ AUSDRUCKSTEUERUNG
AUSDRUCK_IN_DEUTSCH = ja
LANGAUSDR_GEOMETRIE = ja
LANGAUSDR_TRAGFAEHIGKEIT = ja
AUSDRUCK_DECKBLATT = ja
ECHODRUCK_EINGABEDATEI = ja
AUSDRUCK_ERZEUGUNGSGETR = nein
"""

PLOT_BLOCK = """$ PLOTSTEUERUNG
PLOTFORMAT = A4h A4h
PLOTGENAUIGKEIT = {acc} {acc}
PLOT_TEILKREIS = ja ja
PLOT_VERZAHNUNG_W1 = ja ja
PLOT_VERZAHNUNG_W2 = nein nein
PLOT_FERTIGVERZAHNUNG = nein nein
PLOT_WERKZEUG1 = nein nein
PLOT_WERKZEUG2 = nein nein
PLOT_EINGRIFF = ja
STIRNKOORD_EIN_WKZ = ja
"""

REPLACED_BLOCKS = {"AUSDRUCKSTEUERUNG", "PLOTSTEUERUNG"}
CONTOUR_FORMAT = (
    "zahnkonXwzY.txt: one point per line, `x ; y` in mm (transverse section, scientific "
    "notation); one tooth centred on +y from root circle (left flank) over the tip to root "
    "circle (right flank)"
)


def _stplus_root(explicit: str | None) -> Path:
    env = os.environ.get("GEARCORE_STPLUS_ROOT")
    root = Path(explicit) if explicit else (Path(env) if env else DEFAULT_STPLUS_ROOT)
    if not (root / "bin" / "STplus.exe").is_file():
        raise SystemExit(
            f"STplus.exe not found under {root} (use --stplus-root or GEARCORE_STPLUS_ROOT)"
        )
    return root


def _case_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not slug:
        raise SystemExit(f"invalid case name {name!r}")
    return slug


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("latin-1", errors="replace")).hexdigest()


def _relative(path: Path) -> str:
    return (
        str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        if path.is_relative_to(REPO_ROOT)
        else str(path)
    )


def prepare_ste(text: str, plot_accuracy: float) -> str:
    """Replace the print/plot control blocks by the oracle settings; keep everything else verbatim.

    Returns LF-terminated text; callers write it with ``newline="\\r\\n"`` for STplus.
    """
    out: list[str] = []
    skipping = False
    inserted = False
    for raw in text.splitlines():
        stripped = raw.split("#", 1)[0].strip()
        if stripped.startswith("$"):
            name = stripped[1:].strip().upper()
            if name in REPLACED_BLOCKS:
                skipping = True
                continue
            skipping = False
            if name == "ENDE" and not inserted:
                out.append(PRINT_BLOCK)
                out.append(PLOT_BLOCK.format(acc=plot_accuracy))
                inserted = True
        if skipping:
            continue
        out.append(raw)
    if not inserted:
        raise SystemExit("input has no '$ Ende' block")
    return "\n".join(out) + "\n"


def write_cfg(scratch: Path, root: Path) -> str:
    def win(path: Path) -> str:
        return str(path).replace("/", "\\")

    lines = [
        "Firmenname = FZG",
        "Sachbearbeiter = gearcore oracle",
        f"Eingabedatei = {win(scratch / 'eingabe.ste')}",
        f"Ausgabedatei = {win(scratch / 'ausgabe.sta')}",
        f"Graphikdatei = {win(scratch / 'grafik1.stz')}",
        f"Graphikdatei_2 = {win(scratch / 'grafik2.stz')}",
        "Zuordnungsdatei = qelesed.stq",
        f"Werkzeugdatei_lokal = {win(root / 'wkz' / 'wkz.dat')}",
        f"Werkzeugdatei_global = {win(root / 'global' / 'wkz_glob.dat')}",
        *[f"Werkzeugdatei_{i} = %" for i in range(3, 11)],
        f"Werkstoffdatei_lokal = {win(root / 'wst' / 'WST.dat')}",
        f"Werkstoffdatei_global = {win(root / 'global' / 'wst_glob.dat')}",
        f"Schmierstoffdatei_lokal = {win(root / 'oel' / 'Oel.dat')}",
        f"Schmierstoffdatei_global = {win(root / 'global' / 'oel_glob.dat')}",
        f"Pfad_Maskendateien = {win(root / 'zubeh')}\\",
        f"Schnittstellendatei = {win(scratch / 'ausgabe.sts')}",
        f"STEP_Konfiguration = {win(scratch / 'config.dat')}",
        f"Pfad_Meldungsausgabe = {win(scratch)}\\",
    ]
    text = "\n".join(lines) + "\n"
    # STplus reads CRLF files; Windows text mode would double the CR (IOSTAT 43 on 2026-09-28)
    (scratch / "stplus.cfg").write_text(text, encoding="latin-1", newline="\r\n")
    return text


def _collect_contours(scratch: Path, root: Path, started: float) -> list[Path]:
    """Contour files of this run. Anything new in ``bin/`` means the redirection failed → abort."""
    strays = [p for p in (root / "bin").glob("zahnkon*.txt") if p.stat().st_mtime >= started]
    if strays:
        raise SystemExit(
            "STplus wrote contour files into the installation's bin/ although "
            f"Pfad_Meldungsausgabe was set: {[p.name for p in strays]} — not adopted, please inspect"
        )
    return sorted(scratch.glob("zahnkon*.txt"))


def _values_json(report: StaReport, *, only_geometry: bool) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for value in report.values:
        if only_geometry and not (
            value.section.startswith("Geometrieberechnung")
            or value.section.startswith("Besonderheiten")
        ):
            continue
        key = value.key
        if key in out:
            # repeated key (e.g. A_Ae in the backlash subsection): disambiguate by subsection, then count
            key = f"{key} [{value.subsection or value.section}]"
            counter = 2
            base = key
            while key in out:
                key = f"{base} #{counter}"
                counter += 1
        out[key] = {
            "label": value.label,
            "symbol": value.symbol,
            "numbers": list(value.numbers),
            "tokens": list(value.tokens),
            "unit": value.unit,
            "section": value.section,
            "subsection": value.subsection,
            "line": value.line,
        }
    return out


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def write_fixture(
    case: str,
    *,
    ste_text: str,
    sta_text: str,
    contours: list[Path],
    meta: dict[str, Any],
    sts_text: str | None = None,
) -> Path:
    target = FIXTURES / case
    target.mkdir(parents=True, exist_ok=True)
    (target / "input.ste").write_text(ste_text, encoding="latin-1", newline="\n")
    (target / "report.sta.txt").write_text(sta_text, encoding="latin-1", newline="\n")
    if sts_text is not None:
        # STplus interface file (manual §6.2): same grammar as .ste, all results as KEY = values
        (target / "interface.sts.txt").write_text(sts_text, encoding="latin-1", newline="\n")
        sts = parse_ste(sts_text)
        interface: dict[str, Any] = {}
        for section in sts.sections:
            for entry in section.entries:
                interface[f"{section.name}/{entry.key}"] = {
                    "values": list(entry.values),
                    "numbers": [float(v.replace("D", "E")) for v in entry.values if is_number(v)],
                }
        _write_json(target / "interface.json", interface)
    report = load_sta(target / "report.sta.txt")
    _write_json(target / "geometry.json", _values_json(report, only_geometry=True))
    _write_json(target / "report.json", _values_json(report, only_geometry=False))
    contour_meta: list[dict[str, Any]] = []
    for path in contours:
        match = re.match(r"zahnkon(\d)wz(\d)\.txt$", path.name, flags=re.IGNORECASE)
        if not match:
            continue
        points = load_contour(path)
        columns = len(path.read_text(encoding="latin-1").splitlines()[0].split())
        name = f"contour_wz{match.group(2)}.json"
        _write_json(
            target / name,
            {
                "source_file": path.name,
                "tools": int(match.group(1)),
                "gear": int(match.group(2)),
                "points": points.tolist(),
            },
        )
        contour_meta.append(
            {"file": name, "source": path.name, "points": int(points.shape[0]), "columns": columns}
        )
    meta = {
        **meta,
        "case": case,
        "stplus_version": report.version,
        "ste_sha256": _sha256(ste_text),
        "contours": contour_meta,
        "contour_format": CONTOUR_FORMAT if contour_meta else None,
        "interface_file": "interface.sts.txt" if sts_text is not None else None,
        "sections": list(report.sections),
    }
    # the typed import must succeed or say why — recorded, never hidden
    ste = load_ste(target / "input.ste")
    kinds = {k: MaterialKind(v) for k, v in (meta.get("material_kinds") or {}).items()}
    try:
        imported = pair_input_from_ste(ste, material_kinds=kinds)
        meta["typed_import"] = {
            "ok": True,
            "unmapped_keys": list(imported.unmapped_keys),
            "notes": list(imported.notes),
        }
    except Exception as exc:  # recorded verbatim for the fixture consumer, never swallowed
        meta["typed_import"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    _write_json(target / "meta.json", meta)
    return target


def run_case(
    case: str,
    ste_path: Path,
    *,
    root: Path,
    trust: str,
    plot_accuracy: float,
    material_kinds: dict[str, str] | None,
    notes: str | None,
    ste_text_override: str | None = None,
) -> Path:
    if sys.platform != "win32":
        raise SystemExit("run mode needs Windows (STplus.exe)")
    scratch = Path(tempfile.gettempdir()) / "gearcore_stplus" / case
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    original = (
        ste_text_override
        if ste_text_override is not None
        else ste_path.read_text(encoding="latin-1")
    )
    prepared = prepare_ste(original, plot_accuracy)
    (scratch / "eingabe.ste").write_text(prepared, encoding="latin-1", newline="\r\n")
    cfg_text = write_cfg(scratch, root)
    exe = root / "bin" / "STplus.exe"
    # STplus opens its runtime companions relative to the working directory (first run 2026-09-28:
    # "IMELIB: IOSTAT = 29 ... debug.dbe"); copy them into the scratch dir so bin/ stays untouched.
    for companion in COMPANIONS:
        source = root / "bin" / companion
        if source.is_file():
            shutil.copy2(source, scratch / companion)
    started = dt.datetime.now().astimezone()
    started_ts = started.timestamp()
    proc = subprocess.run(
        [str(exe), "--CFG", str(scratch / "stplus.cfg")],
        cwd=str(scratch),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    sta_file = scratch / "ausgabe.sta"
    if not sta_file.is_file():
        raise SystemExit(
            f"STplus produced no ausgabe.sta (exit {proc.returncode})\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    contours = _collect_contours(scratch, root, started_ts)
    meta: dict[str, Any] = {
        "origin": "run",
        "trust": trust,
        "run_date": started.isoformat(timespec="seconds"),
        "exe": _relative(exe),
        "source_ste": _relative(ste_path),
        "plot_accuracy": plot_accuracy,
        "cfg": cfg_text,
        "exit_code": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "material_kinds": material_kinds or {},
        "notes": notes,
        "scratch": str(scratch),
    }
    sts_file = scratch / "ausgabe.sts"
    return write_fixture(
        case,
        ste_text=prepared,
        sta_text=sta_file.read_text(encoding="latin-1"),
        contours=contours,
        meta=meta,
        sts_text=sts_file.read_text(encoding="latin-1") if sts_file.is_file() else None,
    )


def import_case(
    case: str,
    ste_path: Path,
    sta_path: Path,
    *,
    trust: str,
    material_kinds: dict[str, str] | None,
    notes: str | None,
) -> Path:
    meta: dict[str, Any] = {
        "origin": "supplied",
        "trust": trust,
        "import_date": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_ste": _relative(ste_path),
        "source_sta": _relative(sta_path),
        "material_kinds": material_kinds or {},
        "notes": notes,
    }
    return write_fixture(
        case,
        ste_text=ste_path.read_text(encoding="latin-1"),
        sta_text=sta_path.read_text(encoding="latin-1"),
        contours=[],
        meta=meta,
    )


def discover() -> list[tuple[str, Path, Path]]:
    """``<name>_eingabe.ste`` + ``<name>[-_]ausgabe.sta[.sta]`` pairs in the reference folders."""
    pairs: list[tuple[str, Path, Path]] = []
    for folder in REFERENCE_DIRS:
        if not folder.is_dir():
            continue
        for ste in sorted(folder.glob("*_eingabe.ste")):
            name = ste.name[: -len("_eingabe.ste")]
            candidates = (
                f"{name}_ausgabe.sta",
                f"{name}-ausgabe.sta",
                f"{name}_ausgabe.sta.sta",
                f"{name}-ausgabe.sta.sta",
            )
            for candidate in candidates:
                sta = folder / candidate
                if sta.is_file():
                    pairs.append((name, ste, sta))
                    break
    return pairs


def template_ste(spec: dict[str, Any]) -> str:
    """Minimal geometry-only ``.ste`` for adversarial variants (rack tools, optional edge break)."""
    g1, g2 = spec["pinion"], spec["wheel"]

    def tool_block(name: str, tool: dict[str, Any]) -> str:
        lines = [
            f"$ {name}",
            f"KOPFHOEHENFAKTOR = {tool.get('h_aP0', 1.25)}",
            f"KOPFABRUNDUNGSFAKTOR = {tool.get('rho_aP0', 0.25)}",
            f"WKZ_NORMALMODUL = {spec['m_n']}",
            f"WKZ_EINGRIFFSWINKEL = {spec.get('alpha_n', 20)}",
        ]
        if "h_FfP0" in tool:
            lines.append(f"FUSSFORMHOEHENFAKTOR = {tool['h_FfP0']}")
        if "alpha_K0" in tool:
            lines.append(f"KANTENBRECHWINKEL = {tool['alpha_K0']}")
        return "\n".join(lines) + "\n"

    geo = [
        "$ Anfang",
        "",
        "$ Geometriedaten",
        f"ZAHNBREITE = {g1.get('b', 20)} {g2.get('b', 20)}",
        f"NORMALMODUL = {spec['m_n']}",
        f"EINGRIFFSWINKEL = {spec.get('alpha_n', 20)}",
        f"SCHRAEGUNGSWINKEL = {spec.get('beta', 0)}",
        f"ZAEHNEZAHL = {g1['z']} {g2['z']}",
    ]
    if "a" in spec:
        geo.append(f"ACHSABSTAND = {spec['a']}")
    x1, x2 = g1.get("x"), g2.get("x")
    if x1 is not None and x2 is not None:
        geo.append(f"PROFILVERSCHIEBUNG_N = {x1} {x2}")
    elif x1 is not None:
        geo.append(f"PROFILVERSCHIEBUNG_N = {x1}")
        geo.append("AUFTEILUNG_X1X2 = 0")
    if "d_a" in g1 or "d_a" in g2:
        geo.append(f"KOPFKREISDM = {g1.get('d_a', '%')} {g2.get('d_a', '%')}")
    geo.append("WERKZEUG_VORVERZ. = WKZ_1 WKZ_2")
    return (
        "\n".join(geo)
        + "\n\n"
        + tool_block("WKZ_1", g1.get("tool", {}))
        + "\n"
        + tool_block("WKZ_2", g2.get("tool", {}))
        + "\n$ Ende\n"
    )


def load_cases() -> list[dict[str, Any]]:
    cases = yaml.safe_load(CASES_FILE.read_text(encoding="utf-8"))["cases"]
    return [dict(c) for c in cases]


def run_all(root_arg: str | None, only: str | None) -> None:
    root: Path | None = None
    for spec in load_cases():
        name = _case_slug(spec["name"])
        if only and name != _case_slug(only):
            continue
        trust = spec.get("trust", "generated")
        if trust not in TRUST_LEVELS:
            raise SystemExit(f"{name}: trust must be one of {TRUST_LEVELS}")
        mode = spec["mode"]
        kinds = spec.get("material_kinds")
        notes = spec.get("notes")
        if mode == "import":
            target = import_case(
                name,
                REPO_ROOT / spec["ste"],
                REPO_ROOT / spec["sta"],
                trust=trust,
                material_kinds=kinds,
                notes=notes,
            )
        elif mode == "run":
            root = root or _stplus_root(root_arg)
            override = template_ste(spec["template"]) if "template" in spec else None
            ste_path = REPO_ROOT / spec["ste"] if "ste" in spec else CASES_FILE
            target = run_case(
                name,
                ste_path,
                root=root,
                trust=trust,
                plot_accuracy=float(spec.get("plot_accuracy", 0.005)),
                material_kinds=kinds,
                notes=notes,
                ste_text_override=override,
            )
        else:
            raise SystemExit(f"{name}: unknown mode {mode!r}")
        meta = json.loads((target / "meta.json").read_text(encoding="utf-8"))
        status = "ok" if meta["typed_import"]["ok"] else meta["typed_import"]["error"]
        version = str(meta["stplus_version"])
        print(
            f"{name:<24} {mode:<7} STplus {version:<6} contours {len(meta['contours'])}  "
            f"typed import: {status}"
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("discover", help="list .ste/.sta pairs in the reference folders")
    p_import = sub.add_parser("import", help="import a supplied .ste/.sta pair as a fixture")
    p_import.add_argument("--case", required=True)
    p_import.add_argument("--ste", required=True, type=Path)
    p_import.add_argument("--sta", required=True, type=Path)
    p_import.add_argument("--trust", default="unverified", choices=TRUST_LEVELS)
    p_run = sub.add_parser("run", help="run STplus in batch mode on a .ste and store the fixture")
    p_run.add_argument("--case", required=True)
    p_run.add_argument("--ste", required=True, type=Path)
    p_run.add_argument("--trust", default="generated", choices=TRUST_LEVELS)
    p_run.add_argument("--plot-accuracy", type=float, default=0.005)
    p_run.add_argument("--stplus-root")
    p_all = sub.add_parser("run-all", help="process every case in oracle_cases.yaml")
    p_all.add_argument("--stplus-root")
    p_all.add_argument("--only")
    args = parser.parse_args(argv)

    if args.command == "discover":
        for name, ste, sta in discover():
            print(f"{name:<12} {_relative(ste)}  +  {sta.name}")
        return
    if args.command == "import":
        target = import_case(
            _case_slug(args.case),
            args.ste.resolve(),
            args.sta.resolve(),
            trust=args.trust,
            material_kinds=None,
            notes=None,
        )
        print(target)
        return
    if args.command == "run":
        target = run_case(
            _case_slug(args.case),
            args.ste.resolve(),
            root=_stplus_root(args.stplus_root),
            trust=args.trust,
            plot_accuracy=args.plot_accuracy,
            material_kinds=None,
            notes=None,
        )
        print(target)
        return
    run_all(args.stplus_root, args.only)


if __name__ == "__main__":
    main()
