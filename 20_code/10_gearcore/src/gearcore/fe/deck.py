"""Abaqus input files of the pair: one static analysis per mesh position (ADR-116).

A position file holds, in this order (plan of 2026-10-05, section 3):

1. the part of the wheel: ``*INCLUDE`` of the mesh file and its section (W1, W2: a
   ``*SOLID SECTION`` with the isotropic material; W3, W4: ``*INCLUDE`` of the part piece of
   the CONVERSE orientation file, which holds distribution, orientation and section);
2. the part of the pinion: ``*INCLUDE`` of the rigid tooth surface;
3. the assembly: both instances placed by their translation and their rotation about the own
   axis, the reference points on both axes, the rigid body of the pinion surface, the rigid
   tie of the wheel's Fesselung; after it, at model level, the contact pair (hard,
   frictionless, node to surface with the smoothed normals of the rigid main surface);
4. the material of the wheel (W1, W2 written out from the card; W3, W4 ``*INCLUDE`` of the
   model piece of the orientation file) and the temperature as initial condition;
5. the steps: one seating step with a prescribed small rotation of the pinion, then one static
   step per torque with the rotation released and the torque applied at the pinion;
6. the output requests.

Keywords and their data lines follow the installed Abaqus 2025 documentation (keyword
reference pages INSTANCE, RIGID BODY, BOUNDARY, CLOAD, CONTACT PAIR, INCLUDE): an instance is
translated first and then rotated about the axis through two points by an angle in degrees; a
tie-type node of a rigid body shares all its degrees of freedom with the reference node;
``*BOUNDARY, OP=NEW`` in a later step removes every boundary condition not repeated in it and
replaces a removed one by the reaction of the previous step, which the step ramps to zero; the
first surface of a ``*CONTACT PAIR`` data line is the secondary surface, the second the main.
Nothing turns on inside an analysis: no amplitude, no stabilisation, no damping. The steps are
geometrically linear unless ``PositionDeck.nlgeom`` says otherwise; the solver and contact
settings of a file stand in its ``** steps ...`` heading line.
"""

import re
import textwrap
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from gearcore._safe import finite_input, integer_input, positive_input
from gearcore.errors import InputRangeError, ParseError
from gearcore.fe.placement import Placement
from gearcore.trace import eq

EQ_EXEMPT = (
    "read_material_card",
    "replace_elastic_block",
    "read_distribution",
    "read_field_variables",
    "split_orientation_file",
    "OrientationFit",
    "read_node_labels",
    "read_node_coordinates",
    "read_sets",
    "verify_orientation_file",
    "position_deck_text",
    "seating_angle_rad",
    "step_name",
)
"""Writing and reading of files: no equation of a norm."""

MaterialStep = Literal["W1", "W2", "W3", "W4"]
ContactFormulation = Literal["surface_to_surface", "node_to_surface"]
Enforcement = Literal["default", "penalty", "direct", "augmented_lagrange"]
ENFORCEMENT_KEYWORDS: dict[str, str] = {
    "default": "",
    "penalty": ", PENALTY=LINEAR",
    "direct": ", DIRECT",
    "augmented_lagrange": ", AUGMENTED LAGRANGE",
}
MATERIAL_STEPS: tuple[MaterialStep, ...] = ("W1", "W2", "W3", "W4")
"""W1 isotropic elastic, W2 isotropic elastic-plastic (both from the card), W3 anisotropic
elastic (orientation file without plasticity), W4 the complete orientation file."""
NLGEOM_OF_STEP: dict[MaterialStep, bool] = {"W1": False, "W2": True, "W3": False, "W4": True}
"""Geometrically nonlinear steps per material step: the elastic steps W1 and W3 are computed
linear (variant run 2026-10-06 and C3D8 confirmation 2026-10-07 on the 20-layer mesh: NLGEOM
changes the support moment by 0,1 %, the pinion rotation by 0,5 % and the contact pressure by
0,7 % up to 16 Nm), the elastic-plastic steps W2 and W4 nonlinear (the plastic curve of the
card starts at 6 MPa; Stommel, Stojek, Korte 2018, p. 2, p. 52, p. 474)."""
ELEMENT_TYPE_OF_STEP: dict[MaterialStep, str] = {
    "W1": "C3D8I",
    "W2": "C3D8",
    "W3": "C3D8I",
    "W4": "C3D8",
}
"""Element type of the wheel mesh per material step, the same mesh otherwise (element numbers
and the orientation mapping stay): C3D8I where the steps are linear (root surface stress
within 2 % at the recommended density, FE-10), C3D8 where they are geometrically nonlinear,
because C3D8I with NLGEOM=YES produced negative eigenvalues of the system matrix from the
first load increment on and broke off in the 12 Nm step on every mesh, while C3D8 runs the
same files through without one (element test in the Learning Edition and confirmation on the
20-layer mesh, 2026-10-07, FE-14)."""

WHEEL = "WHEEL"
PINION = "PINION"
WHEEL_INSTANCE = "WHEEL-1"
PINION_INSTANCE = "PINION-1"
WHEEL_REFERENCE_NODE = 1
PINION_REFERENCE_NODE = 2
ISOTROPIC_FIELD = (1.0 / 3.0, 1.0 / 3.0)
"""Field variables of the isotropic orientation state in the CONVERSE material card."""
FIELD_TOLERANCE = 1.0e-4
MODEL_KEYWORDS_OF_A_MATERIAL = (
    "ELASTIC",
    "PLASTIC",
    "POTENTIAL",
    "DENSITY",
    "EXPANSION",
    "SPECIFIC HEAT",
    "CONDUCTIVITY",
    "DEPVAR",
    "USER MATERIAL",
)
PLASTICITY_KEYWORDS = ("PLASTIC", "POTENTIAL")


@dataclass(frozen=True)
class MaterialCard:
    """The isotropic row of a CONVERSE material card at one temperature, read as the file
    gives it (``*ELASTIC, TYPE=ENGINEERING CONSTANTS`` with two field variables), and the
    plastic data of the card for the steps W2 and W4."""

    name: str
    temperature_c: float
    engineering_constants: tuple[float, ...]
    plastic_rows: tuple[tuple[float, ...], ...]
    potential_rows: tuple[tuple[float, ...], ...]
    density_rows: tuple[tuple[float, ...], ...]

    @property
    def youngs_modulus_mpa(self) -> float:
        """E_1 of the isotropic row (E_1, E_2 and E_3 differ in the last digits)."""
        return self.engineering_constants[0]

    @property
    def poisson_ratio(self) -> float:
        """nu_12 of the isotropic row."""
        return self.engineering_constants[3]


def _keyword(line: str) -> str:
    return line[1:].split(",")[0].strip().upper()


def _numbers(line: str) -> list[float]:
    return [float(item) for item in line.replace("\t", " ").split(",") if item.strip()]


def _blocks(text: str) -> list[tuple[str, str, list[str]]]:
    """(keyword, keyword line, data lines) of every keyword block; comments dropped."""
    blocks: list[tuple[str, str, list[str]]] = []
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        if line.startswith("**") or not line.strip():
            continue
        if line.startswith("*"):
            blocks.append((_keyword(line), line.strip(), []))
        elif blocks:
            blocks[-1][2].append(line.strip())
    return blocks


def _joined_rows(data: list[str], width: int) -> list[tuple[float, ...]]:
    """Rows of ``width`` numbers from data lines that may be continued on the next line."""
    numbers: list[float] = []
    for line in data:
        numbers.extend(_numbers(line))
    if len(numbers) % width:
        raise ParseError(f"material card: {len(numbers)} numbers do not form rows of {width}")
    return [tuple(numbers[k : k + width]) for k in range(0, len(numbers), width)]


def read_material_card(text: str, temperature_c: float) -> MaterialCard:
    """The isotropic row of the ``*MATERIAL`` of a CONVERSE orientation file at
    ``temperature_c``: the row of ``*ELASTIC, TYPE=ENGINEERING CONSTANTS, DEPENDENCIES=2``
    whose field variables are 1/3, 1/3 and whose temperature matches. Plastic, Hill and
    density rows are kept as the card has them."""
    temperature = finite_input(temperature_c, "temperature")
    blocks = _blocks(text)
    name = None
    constants: tuple[float, ...] | None = None
    plastic: list[tuple[float, ...]] = []
    potential: list[tuple[float, ...]] = []
    density: list[tuple[float, ...]] = []
    for keyword, line, data in blocks:
        if keyword == "MATERIAL":
            if name is not None:
                raise ParseError("material card: more than one *MATERIAL")
            name = line.split("NAME=")[1].split(",")[0].strip()
        elif keyword == "ELASTIC":
            if "ENGINEERING CONSTANTS" not in line.upper() or "DEPENDENCIES=2" not in line.upper():
                raise ParseError(f"material card: unexpected elastic definition {line!r}")
            for row in _joined_rows(data, 12):
                if (
                    abs(row[9] - temperature) < 1.0e-6
                    and abs(row[10] - ISOTROPIC_FIELD[0]) < FIELD_TOLERANCE
                    and abs(row[11] - ISOTROPIC_FIELD[1]) < FIELD_TOLERANCE
                ):
                    constants = row[:9]
        elif keyword == "PLASTIC":
            plastic = _joined_rows(data, 3)
        elif keyword == "POTENTIAL":
            for row in _joined_rows(data, 9):
                if (
                    abs(row[7] - ISOTROPIC_FIELD[0]) < FIELD_TOLERANCE
                    and abs(row[8] - ISOTROPIC_FIELD[1]) < FIELD_TOLERANCE
                ):
                    potential.append(row[:7])
        elif keyword == "DENSITY":
            density = _joined_rows(data, 2)
    if name is None or constants is None:
        raise ParseError(
            f"material card: no isotropic row (field variables 1/3, 1/3) at {temperature} degC"
        )
    return MaterialCard(
        name=name,
        temperature_c=temperature,
        engineering_constants=constants,
        plastic_rows=tuple(plastic),
        potential_rows=tuple(potential),
        density_rows=tuple(density),
    )


ENGINEERING_CONSTANT_NAMES = (
    "E_1",
    "E_2",
    "E_3",
    "nu_12",
    "nu_13",
    "nu_23",
    "G_12",
    "G_13",
    "G_23",
)
"""Order of the nine engineering constants on the data lines of ``*ELASTIC,
TYPE=ENGINEERING CONSTANTS`` (first line E_1 to G_13, second line G_23)."""
LINE_LIMIT = 256
"""Characters per line of an Abaqus input file: the limit of keyword and data lines of the
input syntax rules (Abaqus 2025, "Input Syntax Rules"); comment lines carry no stated limit
and are kept below it as well, because no deck of this project has ever exceeded it."""


@eq(
    "Abaqus2025:LinearElastic",
    "stability",
    section="Defining Orthotropic Elasticity by Specifying the Engineering Constants",
    note="E_i, G_ij > 0; |nu_12| < sqrt(E_1/E_2), |nu_13| < sqrt(E_1/E_3), |nu_23| < "
    "sqrt(E_2/E_3); 1 - nu_12 nu_21 - nu_23 nu_32 - nu_31 nu_13 - 2 nu_21 nu_32 nu_13 > 0 "
    "with nu_ji = nu_ij E_j / E_i",
)
def orthotropic_stability(constants: Iterable[float]) -> float:
    """The left-hand side 1 - nu_12 nu_21 - nu_23 nu_32 - nu_31 nu_13 - 2 nu_21 nu_32 nu_13
    of the stability restrictions on nine engineering constants (E_1, E_2, E_3, nu_12, nu_13,
    nu_23, G_12, G_13, G_23), after every other restriction held; a violated restriction raises
    an ``InputRangeError``. The value approaches zero for an incompressible material."""
    values = tuple(constants)
    if len(values) != len(ENGINEERING_CONSTANT_NAMES):
        raise InputRangeError(
            f"nine engineering constants {ENGINEERING_CONSTANT_NAMES} are required, got {len(values)}"
        )
    e1, e2, e3, n12, n13, n23, g12, g13, g23 = (
        finite_input(v, name) for v, name in zip(values, ENGINEERING_CONSTANT_NAMES, strict=True)
    )
    for value, name in (
        (e1, "E_1"),
        (e2, "E_2"),
        (e3, "E_3"),
        (g12, "G_12"),
        (g13, "G_13"),
        (g23, "G_23"),
    ):
        if value <= 0.0:
            raise InputRangeError(f"material stability needs {name} > 0, got {value!r}")
    for ratio, name, upper in (
        (n12, "nu_12", (e1 / e2) ** 0.5),
        (n13, "nu_13", (e1 / e3) ** 0.5),
        (n23, "nu_23", (e2 / e3) ** 0.5),
    ):
        if abs(ratio) >= upper:
            raise InputRangeError(f"material stability needs |{name}| < {upper:.4g}, got {ratio!r}")
    n21 = n12 * e2 / e1
    n31 = n13 * e3 / e1
    n32 = n23 * e3 / e2
    left = 1.0 - n12 * n21 - n23 * n32 - n31 * n13 - 2.0 * n21 * n32 * n13
    if left <= 0.0:
        raise InputRangeError(
            "material stability needs 1 - nu_12 nu_21 - nu_23 nu_32 - nu_31 nu_13 - "
            f"2 nu_21 nu_32 nu_13 > 0, got {left!r}"
        )
    return left


def replace_elastic_block(text: str, constants: Iterable[float], note: str = "") -> str:
    """``text`` (the model piece of an orientation file) with its one ``*ELASTIC`` block
    replaced by ``*ELASTIC, TYPE=ENGINEERING CONSTANTS`` and the nine ``constants`` on two
    data lines (E_1 to G_13, then G_23), without temperature or field dependence; every
    other block stays as it is, ``note`` becomes comment lines below the keyword line, wrapped
    to at most ``LINE_LIMIT`` characters (the limit of keyword and data lines of the Abaqus
    input syntax, kept for comments as well). The block that is replaced must itself be of
    ``TYPE=ENGINEERING CONSTANTS`` (an isotropic ``*ELASTIC`` is refused: the piece is not a
    CONVERSE model piece), its data lines and the comment lines inside it are dropped. The
    constants must satisfy the stability restrictions (``orthotropic_stability``)."""
    if not isinstance(text, str) or not text.strip():
        raise InputRangeError("the model piece must be a non-empty string")
    values = tuple(constants)
    orthotropic_stability(values)
    out: list[str] = []
    found = 0
    skipping = False
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        stripped = line.strip()
        if stripped.startswith("*") and not stripped.startswith("**"):
            if _keyword(stripped) == "ELASTIC":
                if "ENGINEERING CONSTANTS" not in stripped.upper():
                    raise ParseError(f"model piece: unexpected elastic definition {stripped!r}")
                found += 1
                out.append("*ELASTIC, TYPE=ENGINEERING CONSTANTS")
                if note:
                    out.extend(
                        f"** {part}"
                        for part in textwrap.wrap(note, LINE_LIMIT - 3, break_on_hyphens=False)
                    )
                out.append(", ".join(_format(v) for v in values[:8]))
                out.append(_format(values[8]))
                skipping = True
                continue
            skipping = False
        elif skipping:
            continue
        out.append(line)
    if found != 1:
        raise ParseError(f"model piece: {found} *ELASTIC blocks, exactly one expected")
    return "\n".join(out) + "\n"


@dataclass(frozen=True)
class OrientationFilePieces:
    """The CONVERSE orientation file split for a model with parts and instances."""

    part: str
    model: str
    model_without_plasticity: str


Vector = tuple[float, float, float]


def read_distribution(text: str) -> dict[int, tuple[Vector, Vector]]:
    """The element orientations of the first ``*DISTRIBUTION, LOCATION=ELEMENT`` of a CONVERSE
    orientation file: element label -> (local 1-direction, direction in the 1-2 plane), as the
    file gives them in the coordinates of the part. The first row (no label) is the default
    of the distribution and is skipped."""
    for keyword, line, data in _blocks(text):
        if keyword != "DISTRIBUTION" or "LOCATION=ELEMENT" not in line.upper():
            continue
        out: dict[int, tuple[Vector, Vector]] = {}
        for row in data:
            items = [item.strip() for item in row.split(",")]
            if len(items) != 7:
                raise ParseError(f"orientation file: distribution row {row!r} has not 7 items")
            if not items[0]:
                continue
            values = [float(v) for v in items[1:]]
            out[int(items[0])] = (
                (values[0], values[1], values[2]),
                (values[3], values[4], values[5]),
            )
        if not out:
            raise ParseError("orientation file: the element distribution has no rows")
        return out
    raise ParseError("orientation file: no *DISTRIBUTION, LOCATION=ELEMENT")


def read_field_variables(text: str) -> dict[int, tuple[float, float]]:
    """The nodal field variables 1 and 2 of a CONVERSE orientation file (``*INITIAL
    CONDITIONS, TYPE=FIELD, VARIABLE=k``): node label -> (variable 1, variable 2)."""
    first: dict[int, float] = {}
    second: dict[int, float] = {}
    for keyword, line, data in _blocks(text):
        if keyword != "INITIAL CONDITIONS" or "TYPE=FIELD" not in line.upper():
            continue
        variable = line.upper().split("VARIABLE=")[1].split(",")[0].strip()
        target = first if variable == "1" else second if variable == "2" else None
        if target is None:
            raise ParseError(f"orientation file: field variable {variable!r} is not 1 or 2")
        for row in data:
            label, value = (item.strip() for item in row.split(",")[:2])
            target[int(label)] = float(value)
    if not first or set(first) != set(second):
        raise ParseError("orientation file: field variables 1 and 2 must name the same nodes")
    return {label: (first[label], second[label]) for label in first}


NODES_PER_ELEMENT: dict[str, int] = {
    "C3D4": 4,
    "C3D6": 6,
    "C3D8": 8,
    "C3D10": 10,
    "C3D15": 15,
    "C3D20": 20,
}
"""Nodes of the base element types; a variant (C3D8I, C3D8R, C3D10M) counts as its base."""


def read_element_connectivity(text: str) -> dict[int, tuple[int, ...]]:
    """Element label -> node labels of every ``*ELEMENT`` block of an Abaqus input file
    (continuation lines joined); the node count follows the element type."""
    out: dict[int, tuple[int, ...]] = {}
    for keyword, line, data in _blocks(text):
        if keyword != "ELEMENT":
            continue
        if "TYPE=" not in line.upper():
            raise ParseError(f"input file: *ELEMENT without TYPE: {line!r}")
        kind = line.upper().split("TYPE=")[1].split(",")[0].strip()
        base = next(
            (b for b in sorted(NODES_PER_ELEMENT, key=len, reverse=True) if kind.startswith(b)),
            None,
        )
        if base is None:
            raise ParseError(f"input file: element type {kind!r} not known")
        width = NODES_PER_ELEMENT[base] + 1
        numbers: list[int] = []
        for row in data:
            numbers.extend(
                int(float(item)) for item in row.replace("\t", " ").split(",") if item.strip()
            )
        if len(numbers) % width:
            raise ParseError(f"input file: {len(numbers)} labels do not form {kind} elements")
        for k in range(0, len(numbers), width):
            out[numbers[k]] = tuple(numbers[k + 1 : k + width])
    if not out:
        raise ParseError("input file: no *ELEMENT block")
    return out


def read_node_labels(text: str) -> tuple[int, ...]:
    """Node labels of every ``*NODE`` block of an Abaqus input file, in file order."""
    labels: list[int] = []
    for keyword, _line, data in _blocks(text):
        if keyword != "NODE":
            continue
        for row in data:
            first = row.split(",")[0].strip()
            if first:
                labels.append(int(float(first)))
    if not labels:
        raise ParseError("input file: no *NODE block")
    return tuple(labels)


def read_node_coordinates(text: str) -> dict[int, tuple[float, float, float]]:
    """Node label -> (x, y, z) of every ``*NODE`` block of an Abaqus input file."""
    out: dict[int, tuple[float, float, float]] = {}
    for keyword, _line, data in _blocks(text):
        if keyword != "NODE":
            continue
        for row in data:
            items = [item.strip() for item in row.replace("\t", " ").split(",") if item.strip()]
            if len(items) < 4:
                raise ParseError(f"input file: node row {row!r} has fewer than four items")
            out[int(float(items[0]))] = (float(items[1]), float(items[2]), float(items[3]))
    if not out:
        raise ParseError("input file: no *NODE block")
    return out


def read_sets(text: str) -> tuple[dict[str, tuple[int, ...]], dict[str, tuple[int, ...]]]:
    """(node sets, element sets) of an Abaqus input file: set name -> labels, from the
    ``*NSET`` and ``*ELSET`` blocks (``GENERATE`` ranges expanded, names upper case) and from
    the ``NSET=`` / ``ELSET=`` of ``*NODE`` and ``*ELEMENT`` blocks."""
    node_sets: dict[str, list[int]] = {}
    element_sets: dict[str, list[int]] = {}

    def integers(row: str) -> list[int]:
        items = [v.strip() for v in row.replace("\t", " ").split(",") if v.strip()]
        try:
            return [int(float(v)) for v in items]
        except ValueError as error:
            raise ParseError(
                f"input file: set row {row!r} is not a list of labels (a set name inside a set "
                "is not read)"
            ) from error

    for keyword, line, data in _blocks(text):
        upper = line.upper()
        parameters = {p.strip().split("=")[0] for p in upper.split(",")[1:]}
        if keyword in ("NSET", "ELSET"):
            parameter = f"{keyword}="
            if parameter not in upper:
                raise ParseError(f"input file: *{keyword} without a name: {line!r}")
            name = upper.split(parameter)[1].split(",")[0].strip()
            target = node_sets if keyword == "NSET" else element_sets
            labels = target.setdefault(name, [])
            for row in data:
                items = integers(row)
                if "GENERATE" in parameters:
                    if len(items) not in (2, 3):
                        raise ParseError(
                            f"input file: GENERATE row {row!r} is not (first, last[, step])"
                        )
                    step = items[2] if len(items) == 3 else 1
                    if step < 1 or items[1] < items[0]:
                        raise ParseError(f"input file: GENERATE row {row!r} runs backwards")
                    labels.extend(range(items[0], items[1] + 1, step))
                else:
                    labels.extend(items)
        elif keyword == "NODE":
            if "NSET=" not in upper:
                continue
            name = upper.split("NSET=")[1].split(",")[0].strip()
            labels = node_sets.setdefault(name, [])
            for row in data:
                first = row.split(",")[0].strip()
                if first:
                    labels.append(int(float(first)))
        elif keyword == "ELEMENT":
            if "ELSET=" not in upper:
                continue
            name = upper.split("ELSET=")[1].split(",")[0].strip()
            kind = upper.split("TYPE=")[1].split(",")[0].strip() if "TYPE=" in upper else ""
            base = next(
                (b for b in sorted(NODES_PER_ELEMENT, key=len, reverse=True) if kind.startswith(b)),
                None,
            )
            if base is None:
                raise ParseError(f"input file: element type {kind!r} not known")
            width = NODES_PER_ELEMENT[base] + 1
            numbers: list[int] = []
            for row in data:
                numbers.extend(integers(row))  # continuation rows of larger elements joined
            if len(numbers) % width:
                raise ParseError(f"input file: {len(numbers)} labels do not form {kind} elements")
            element_sets.setdefault(name, []).extend(numbers[::width])
    return (
        {name: tuple(values) for name, values in node_sets.items()},
        {name: tuple(values) for name, values in element_sets.items()},
    )


@dataclass(frozen=True)
class OrientationFit:
    """What ``verify_orientation_file`` confirmed about an orientation file and a mesh."""

    elements: int
    nodes: int
    reference: str | None
    """Name of the orientation piece the rows were compared with, None without one."""


def _label_mismatch(what: str, name: str, wanted: set[int], found: set[int]) -> str | None:
    missing, extra = sorted(wanted - found), sorted(found - wanted)
    if not missing and not extra:
        return None
    parts = [
        f"{name} does not belong to this mesh: {what} of the mesh {len(wanted)}, of the file "
        f"{len(found)}"
    ]
    if missing:
        parts.append(f"{len(missing)} of the mesh missing in the file (first {missing[:5]})")
    if extra:
        parts.append(f"{len(extra)} of the file not in the mesh (first {extra[:5]})")
    return "; ".join(parts)


def verify_orientation_file(
    cof_text: str,
    *,
    element_labels: Iterable[int],
    node_labels: Iterable[int],
    reference_text: str | None = None,
    name: str = "orientation file",
    reference_name: str | None = None,
) -> OrientationFit:
    """Refuse a CONVERSE orientation file that does not belong to a mesh, so that a wrongly
    assigned mapping never runs silently. The element labels of its distribution must be
    exactly the elements of the mesh and the node labels of its field variables exactly the
    nodes of the mesh (a mapping made on the other body has other counts). With
    ``reference_text``, the folder's own orientation piece (``wheel_orientation_<rate>_part.inp``,
    cut from the file the decks were built with), every orientation row must equal the row of
    that piece: a mapping on a mesh with the same numbering but other node positions (the ring
    body on the levels of the pocket body against the ring body with equal layers) has the
    same labels and other vectors, and nothing else tells the two apart. Raises
    ``InputRangeError`` naming the first difference."""
    if not isinstance(cof_text, str) or not cof_text:
        raise InputRangeError("an orientation file text is required")
    orientation = read_distribution(cof_text)
    fields = read_field_variables(cof_text)
    wanted_elements = {int(k) for k in element_labels}
    wanted_nodes = {int(k) for k in node_labels}
    if not wanted_elements or not wanted_nodes:
        raise InputRangeError("element and node labels of the mesh are required")
    for message in (
        _label_mismatch("elements", name, wanted_elements, set(orientation)),
        _label_mismatch("nodes", name, wanted_nodes, set(fields)),
    ):
        if message is not None:
            raise InputRangeError(message)
    compared: str | None = None
    if reference_text is not None:
        compared = reference_name or "the orientation piece of the folder"
        reference = read_distribution(reference_text)
        if set(orientation) != set(reference):
            raise InputRangeError(
                f"{name} is not the mapping of this folder: its distribution names "
                f"{len(orientation)} elements, the folder's {compared} {len(reference)}"
            )
        differing = [k for k in sorted(orientation) if orientation[k] != reference[k]]
        if differing:
            first = differing[0]
            raise InputRangeError(
                f"{name} is not the mapping of this folder: {len(differing)} of "
                f"{len(orientation)} element orientations differ from {compared} (first element "
                f"{first}: file {orientation[first][0]}, folder {reference[first][0]}); a mapping "
                "made on a mesh with the same numbering but other node positions?"
            )
    return OrientationFit(elements=len(orientation), nodes=len(fields), reference=compared)


def split_orientation_file(
    text: str, instance: str = WHEEL_INSTANCE, elset: str = WHEEL
) -> OrientationFilePieces:
    """Split an orientation file into the piece that belongs into the part of the wheel
    (``*DISTRIBUTION``, ``*ORIENTATION``, ``*SOLID SECTION`` with its ``ELSET`` rewritten to
    ``elset``, the element set of the wheel mesh, because CONVERSE names a set of its own,
    ``CONVERSE_AUTO_SOLID``, that no file defines) and the piece that belongs into the model
    (``*DISTRIBUTION TABLE``, ``*MATERIAL`` with its data, ``*INITIAL CONDITIONS`` of the
    field variables with the node numbers prefixed by the instance name). The third piece is
    the model piece without ``*PLASTIC`` and ``*POTENTIAL`` (step W3). A second part in the
    file (the wheel body of the reference) is dropped: only the first distribution,
    orientation and section are kept."""
    if not isinstance(instance, str) or not instance:
        raise InputRangeError("the instance name must be a non-empty string")
    if not isinstance(elset, str) or not elset.isidentifier():
        raise InputRangeError("the element set name must be an identifier")
    part: list[str] = []
    model: list[str] = []
    elastic_only: list[str] = []
    seen = {"DISTRIBUTION": 0, "ORIENTATION": 0, "SOLID SECTION": 0}
    for keyword, line, data in _blocks(text):
        if keyword in seen:
            seen[keyword] += 1
            if seen[keyword] == 1:
                if keyword == "SOLID SECTION":
                    if "ELSET=" not in line.upper():
                        raise ParseError("orientation file: the solid section names no ELSET")
                    line = re.sub(r"(?i)ELSET=[^,]*", f"ELSET={elset}", line, count=1)
                part.append(line)
                part.extend(data)
            continue
        if keyword == "INITIAL CONDITIONS":
            lines = [line] + [f"{instance}.{row.lstrip()}" for row in data]
        else:
            lines = [line] + data
        model.extend(lines)
        if keyword not in PLASTICITY_KEYWORDS:
            elastic_only.extend(lines)
    if seen["DISTRIBUTION"] == 0 or seen["ORIENTATION"] == 0 or seen["SOLID SECTION"] == 0:
        raise ParseError("orientation file: distribution, orientation or section is missing")
    if not any(k == "MATERIAL" for k, _, _ in _blocks(text)):
        raise ParseError("orientation file: no *MATERIAL")
    return OrientationFilePieces(
        part="\n".join(part) + "\n",
        model="\n".join(model) + "\n",
        model_without_plasticity="\n".join(elastic_only) + "\n",
    )


@dataclass(frozen=True)
class PositionDeck:
    """What one position file is made of."""

    wheel_mesh_file: str
    pinion_surface_file: str
    placement: Placement
    torques_pinion_nmm: tuple[float, ...]
    torque_sign: float
    seating_angle_rad: float
    temperature_c: float
    material_step: MaterialStep
    card: MaterialCard | None = None
    orientation_part_file: str | None = None
    orientation_model_file: str | None = None
    title: str = ""
    step_names: tuple[str, ...] = ()
    """Names of the load steps (preset: ``step_name`` of the pinion torque)."""
    rate: str = ""
    """Name of the strain rate of the material card (QS, DY1, DY2 of the CONVERSE files of the
    user), for the heading line only; the card and the orientation pieces carry the data."""
    nlgeom: bool = False
    """Geometrically nonlinear steps. Off by default for the isotropic elastic step W1, where
    the variant runs of 2026-10-06 (20 layers, 8 Nm) put the effect at 0,1 % of the moment,
    0,6 % of the pinion rotation and 0,3 % of the contact pressure: the pinion turns 2,3e-3 rad
    (55 um at the base circle), the largest strain is about 2,6 %. The linear kinematics of the
    rigid pinion displace its surface outward by r*theta**2/2 for a rotation theta, which is
    theta*sin(alpha_wt)/2 of the approach theta*r_b1 along the line of action, below 1e-3 up to
    16 Nm. NLGEOM=YES is the setting for the elastic-plastic steps (the plastic curve of the
    card starts at 6 MPa) and needs a wheel mesh without incompatible-mode elements: with
    C3D8I every geometrically nonlinear run (pilot 1, the three NLGEOM variants, the coarse
    Learning Edition model) showed negative eigenvalues of the system matrix from the first
    load increment on, growing with the load, and broke off in the 12 Nm step; the same coarse
    model with C3D8 or C3D8R runs through every step without one (element test 2026-10-07,
    FE-14)."""
    contact: ContactFormulation = "node_to_surface"
    """``*CONTACT PAIR, TYPE=``: node-to-surface (the standard since 2026-10-07; Abaqus/Standard
    smooths the normals of the facetted rigid main surface over the fraction ``smoothing`` of a
    facet, so the contact force stays normal to the rigid flank, a_1 = r_b1) or
    surface-to-surface (the formulation of pilots 1 and 2: no smoothing of the main surface
    normals, the constraint direction follows the deformed wheel flank, and the fine model
    broke off by a contact oscillation at 16 Nm)."""
    smoothing: float = 0.2
    """SMOOTH of the node-to-surface contact pair, 0 to 0.5 (Abaqus default 0.2): the degree
    of smoothing of an element-based main surface in the finite-sliding node-to-surface
    formulation, 0 = none. It does not affect surface-to-surface contact, whose only smoothing
    (``GEOMETRIC CORRECTION`` with ``*SURFACE SMOOTHING``) serves circumferential, spherical
    and toroidal regions, none of which an involute flank is (keyword reference CONTACT PAIR,
    SURFACE SMOOTHING, Abaqus 2025)."""
    enforcement: Enforcement = "default"
    """Enforcement of the hard contact: the Abaqus default (penalty for surface-to-surface,
    direct for node-to-surface), or explicitly ``PENALTY=LINEAR``, ``DIRECT`` (Lagrange
    multipliers, no penetration) or ``AUGMENTED LAGRANGE``."""
    line_search: int = 0
    """N_ls of ``*CONTROLS, PARAMETERS=LINE SEARCH`` in every step: 0 = off (the Abaqus default
    for Newton steps), the documentation suggests 5 to activate the algorithm, which scales
    the Newton correction when the residual would otherwise grow (oscillating iterations)."""
    iteration_limits: tuple[int, int, int] | None = None
    """(I_0, I_R, I_C) of ``*CONTROLS, PARAMETERS=TIME INCREMENTATION`` in every step, None =
    the Abaqus defaults (4, 8, 16): I_0 equilibrium iterations before the check whether the
    residuals grow in two consecutive iterations, I_R consecutive equilibrium iterations before
    the logarithmic rate-of-convergence check begins, I_C the upper limit of consecutive
    equilibrium iterations in an increment (keyword reference CONTROLS, Abaqus 2025). Larger
    limits let a slowly converging contact iteration finish instead of cutting the increment
    back: the chattering flank node on the tip corner of the rigid pinion converged with a
    factor of 0,85 to 0,95 per iteration and hit I_C = 16 (retries of 2026-10-09)."""


def _format(value: float) -> str:
    return f"{value:.12e}"


def _material_lines(deck: PositionDeck) -> list[str]:
    if deck.material_step in ("W1", "W2"):
        card = deck.card
        if card is None:
            raise InputRangeError(f"step {deck.material_step} needs the material card")
        lines = [
            f"*MATERIAL, NAME={WHEEL}_PLASTIC",
            f"** isotropic row of {card.name} at {card.temperature_c:g} degC: E_1, nu_12 of the card",
            "*ELASTIC",
            f"{_format(card.youngs_modulus_mpa)}, {_format(card.poisson_ratio)}",
        ]
        if deck.material_step == "W2":
            if not card.plastic_rows:
                raise InputRangeError("step W2 needs the plastic rows of the card")
            lines.append("*PLASTIC")
            lines.extend(", ".join(_format(v) for v in row) for row in card.plastic_rows)
            if card.potential_rows:
                lines.append("*POTENTIAL, TYPE=HILL")
                lines.extend(", ".join(_format(v) for v in row) for row in card.potential_rows)
        return lines
    if deck.orientation_model_file is None:
        raise InputRangeError(
            f"step {deck.material_step} needs the model piece of the orientation file"
        )
    return [f"*INCLUDE, INPUT={deck.orientation_model_file}"]


def _section_lines(deck: PositionDeck) -> list[str]:
    if deck.material_step == "W1":
        return [f"*SOLID SECTION, ELSET={WHEEL}, MATERIAL={WHEEL}_PLASTIC"]
    if deck.material_step == "W2":
        # the Hill potential of the card's isotropic row (yield ratios equal in the three
        # normal and in the three shear directions, so the frame does not matter) needs a
        # local orientation: "A local orientation must be used to define the direction of
        # anisotropy" (materials guide, Hill anisotropic yield; the preprocessor rejects the
        # section without one, W2 pilot 2026-10-09). The part's own frame is given.
        return [
            f"*ORIENTATION, NAME={WHEEL}_ISO, DEFINITION=COORDINATES",
            "1., 0., 0., 0., 1., 0.",
            "3, 0.",
            f"*SOLID SECTION, ELSET={WHEEL}, MATERIAL={WHEEL}_PLASTIC, ORIENTATION={WHEEL}_ISO",
        ]
    if deck.orientation_part_file is None:
        raise InputRangeError(
            f"step {deck.material_step} needs the part piece of the orientation file"
        )
    return [f"*INCLUDE, INPUT={deck.orientation_part_file}"]


def position_deck_text(deck: PositionDeck) -> str:
    """The input text of one position (see the module docstring)."""
    if not isinstance(deck, PositionDeck):
        raise InputRangeError(f"a PositionDeck is required, got {type(deck).__name__}")
    if deck.material_step not in MATERIAL_STEPS:
        raise InputRangeError(f"material step must be one of {MATERIAL_STEPS}")
    if not deck.torques_pinion_nmm:
        raise InputRangeError("at least one torque is required")
    torques = tuple(positive_input(t, "torque at the pinion") for t in deck.torques_pinion_nmm)
    if deck.torque_sign not in (1.0, -1.0):
        raise InputRangeError("the torque sign must be +1 or -1")
    seating = positive_input(deck.seating_angle_rad, "seating angle")
    if deck.contact not in ("surface_to_surface", "node_to_surface"):
        raise InputRangeError(f"contact formulation {deck.contact!r} is not known")
    if deck.enforcement not in ENFORCEMENT_KEYWORDS:
        raise InputRangeError(f"enforcement {deck.enforcement!r} is not known")
    smoothing = finite_input(deck.smoothing, "smoothing")
    if not 0.0 <= smoothing <= 0.5:
        raise InputRangeError(f"smoothing must lie between 0 and 0.5, got {smoothing!r}")
    line_search = integer_input(deck.line_search, "line search iterations")
    if line_search < 0:
        raise InputRangeError(f"line search iterations must not be negative, got {line_search}")
    limits: tuple[int, int, int] | None = None
    if deck.iteration_limits is not None:
        if len(deck.iteration_limits) != 3:
            raise InputRangeError("iteration limits are (I_0, I_R, I_C)")
        i_0, i_r, i_c = (
            integer_input(v, name)
            for v, name in zip(deck.iteration_limits, ("I_0", "I_R", "I_C"), strict=True)
        )
        if i_0 < 3 or i_r < 1 or i_c < 1:
            raise InputRangeError(
                f"iteration limits need I_0 >= 3 (Abaqus minimum) and I_R, I_C >= 1, got "
                f"{deck.iteration_limits!r}"
            )
        limits = (i_0, i_r, i_c)
    temperature = finite_input(deck.temperature_c, "temperature")
    place = deck.placement
    wheel_axis = place.axis_mm.wheel
    pinion_axis = place.axis_mm.pinion
    wheel_turn = place.tooth_centre_angle_deg.wheel - 90.0
    pinion_turn = place.tooth_centre_angle_deg.pinion - 90.0
    lines = [
        "*HEADING",
        deck.title or "gearcore: one static analysis of one mesh position",
        f"** material step {deck.material_step}{', rate ' + deck.rate if deck.rate else ''}, "
        f"temperature {temperature:g} degC, "
        f"torques at the pinion {', '.join(f'{t:g}' for t in torques)} N mm, sign {deck.torque_sign:+g} about +z",
        f"** steps geometrically {'nonlinear' if deck.nlgeom else 'linear'}, contact {deck.contact}"
        f"{'' if deck.contact == 'surface_to_surface' else f' (SMOOTH={smoothing:g})'}, "
        f"enforcement {deck.enforcement}, line search {line_search}, iterations "
        + ("default" if limits is None else f"I_0/I_R/I_C {limits[0]}/{limits[1]}/{limits[2]}"),
        "*PREPRINT, ECHO=NO, MODEL=NO, HISTORY=NO, CONTACT=NO",
        "** --- parts ---",
        f"*PART, NAME={WHEEL}",
        f"*INCLUDE, INPUT={deck.wheel_mesh_file}",
    ]
    lines.extend(_section_lines(deck))
    lines.append("*END PART")
    lines.append(f"*PART, NAME={PINION}")
    lines.append(f"*INCLUDE, INPUT={deck.pinion_surface_file}")
    lines.append("*END PART")
    lines.append("** --- assembly: translation first, then rotation about the own axis ---")
    lines.append("*ASSEMBLY, NAME=PAIR")
    lines.append(f"*INSTANCE, NAME={WHEEL_INSTANCE}, PART={WHEEL}")
    lines.append(f"{_format(wheel_axis[0])}, {_format(wheel_axis[1])}, 0.")
    lines.append(
        f"{_format(wheel_axis[0])}, {_format(wheel_axis[1])}, 0., "
        f"{_format(wheel_axis[0])}, {_format(wheel_axis[1])}, 1., {_format(wheel_turn)}"
    )
    lines.append("*END INSTANCE")
    lines.append(f"*INSTANCE, NAME={PINION_INSTANCE}, PART={PINION}")
    lines.append(f"{_format(pinion_axis[0])}, {_format(pinion_axis[1])}, 0.")
    lines.append(
        f"{_format(pinion_axis[0])}, {_format(pinion_axis[1])}, 0., "
        f"{_format(pinion_axis[0])}, {_format(pinion_axis[1])}, 1., {_format(pinion_turn)}"
    )
    lines.append("*END INSTANCE")
    lines.append(f"*NODE, NSET={WHEEL}_RP")
    lines.append(f"{WHEEL_REFERENCE_NODE}, {_format(wheel_axis[0])}, {_format(wheel_axis[1])}, 0.")
    lines.append(f"*NODE, NSET={PINION}_RP")
    lines.append(
        f"{PINION_REFERENCE_NODE}, {_format(pinion_axis[0])}, {_format(pinion_axis[1])}, 0."
    )
    lines.append(f"*RIGID BODY, REF NODE={PINION}_RP, ELSET={PINION_INSTANCE}.{PINION}")
    lines.append(f"*RIGID BODY, REF NODE={WHEEL}_RP, TIE NSET={WHEEL_INSTANCE}.{WHEEL}_FESSELUNG")
    lines.append("*END ASSEMBLY")
    lines.append("** --- contact: hard, frictionless (model level) ---")
    lines.append("*SURFACE INTERACTION, NAME=FRICTIONLESS")
    lines.append(
        "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD" + ENFORCEMENT_KEYWORDS[deck.enforcement]
    )
    if deck.contact == "surface_to_surface":
        lines.append("*CONTACT PAIR, INTERACTION=FRICTIONLESS, TYPE=SURFACE TO SURFACE")
    else:
        lines.append(
            f"*CONTACT PAIR, INTERACTION=FRICTIONLESS, TYPE=NODE TO SURFACE, SMOOTH={smoothing:g}"
        )
    lines.append(f"{WHEEL_INSTANCE}.{WHEEL}_TEETH_SURF, {PINION_INSTANCE}.{PINION}_SURF")
    lines.append("** --- material of the wheel and temperature ---")
    lines.extend(_material_lines(deck))
    lines.append("*INITIAL CONDITIONS, TYPE=TEMPERATURE")
    lines.append(f"{WHEEL_INSTANCE}.{WHEEL}_NODES, {_format(temperature)}")
    lines.append("*BOUNDARY")
    lines.append(f"{WHEEL}_RP, 1, 6")
    lines.append(f"{PINION}_RP, 1, 5")
    lines.append("** --- step 1: seating, a prescribed small rotation of the pinion ---")
    nlgeom = "YES" if deck.nlgeom else "NO"
    lines.append(f"*STEP, NAME=SEAT, NLGEOM={nlgeom}, INC=200")
    lines.append("*STATIC")
    lines.append("0.1, 1., 1.e-6, 1.")
    lines.extend(_controls_lines(line_search, limits))
    lines.append("*BOUNDARY")
    lines.append(f"{PINION}_RP, 6, 6, {_format(deck.torque_sign * seating)}")
    lines.extend(_output_lines(deck))
    lines.append("*END STEP")
    names = deck.step_names or tuple(step_name(t) for t in torques)
    if len(names) != len(torques):
        raise InputRangeError("one step name per torque is required")
    for torque, name in zip(torques, names, strict=True):
        lines.append(f"** --- step {name}: the rotation released, the torque at the pinion ---")
        lines.append(f"*STEP, NAME={name}, NLGEOM={nlgeom}, INC=200")
        lines.append("*STATIC")
        lines.append("0.1, 1., 1.e-6, 1.")
        lines.extend(_controls_lines(line_search, limits))
        lines.append("*BOUNDARY, OP=NEW")
        lines.append(f"{WHEEL}_RP, 1, 6")
        lines.append(f"{PINION}_RP, 1, 5")
        lines.append("*CLOAD, OP=NEW")
        lines.append(f"{PINION}_RP, 6, {_format(deck.torque_sign * torque)}")
        lines.extend(_output_lines(deck))
        lines.append("*END STEP")
    return "\n".join(lines) + "\n"


def _controls_lines(line_search: int, limits: tuple[int, int, int] | None = None) -> list[str]:
    """``*CONTROLS, PARAMETERS=LINE SEARCH`` with N_ls when the line search is on, and
    ``*CONTROLS, PARAMETERS=TIME INCREMENTATION`` with I_0, I_R and I_C (the other fields of
    the first data line blank = Abaqus defaults) when iteration limits are given."""
    lines: list[str] = []
    if line_search != 0:
        lines.extend(["*CONTROLS, PARAMETERS=LINE SEARCH", f"{line_search}"])
    if limits is not None:
        lines.extend(
            [
                "*CONTROLS, PARAMETERS=TIME INCREMENTATION",
                f"{limits[0]}, {limits[1]}, , {limits[2]}",
            ]
        )
    return lines


def _output_lines(deck: PositionDeck) -> list[str]:
    """Field output at the end of the step (displacements, reactions, stresses and strains,
    contact stresses, contact displacements and the nodal contact forces CFORCE, from which the
    extraction sums the normal force per tooth), history of both reference points, and the
    reaction forces (the contact force), support moments and rotations of the reference points
    plus the contact stresses of the wheel flank nodes printed to the .dat file, so that the
    acceptance (support moment at the wheel, direction of the contact force) needs no ODB
    access. ``*PREPRINT`` in the model section keeps the model printout out of the file."""
    # FV: the predefined field variables of the orientation state, an element variable at
    # the integration points (Abaqus 2025 output variable identifiers, 'State, field and
    # user-defined output variables'), written to the ODB so that the extraction can compare
    # them with the orientation file (steps W3 and W4 only; the isotropic steps define none)
    element_variables = "S, E, PEEQ, FV" if deck.material_step in ("W3", "W4") else "S, E, PEEQ"
    return [
        "*OUTPUT, FIELD, NUMBER INTERVAL=1",
        f"*NODE OUTPUT, NSET={WHEEL_INSTANCE}.{WHEEL}_NODES",
        "U, RF",
        f"*ELEMENT OUTPUT, ELSET={WHEEL_INSTANCE}.{WHEEL}, DIRECTIONS=YES",
        element_variables,
        f"*CONTACT OUTPUT, NSET={WHEEL_INSTANCE}.{WHEEL}_TEETH_SURF_NODES",
        "CSTRESS, CDISP, CFORCE",
        "*OUTPUT, HISTORY",
        f"*NODE OUTPUT, NSET={WHEEL}_RP",
        "RM, UR",
        f"*NODE OUTPUT, NSET={PINION}_RP",
        "RM, UR",
        "*CONTACT OUTPUT",
        "CFN",
        f"*NODE PRINT, NSET={WHEEL}_RP, FREQUENCY=1000",
        "RF, RM, UR",
        f"*NODE PRINT, NSET={PINION}_RP, FREQUENCY=1000",
        "RF, RM, UR",
        f"*CONTACT PRINT, NSET={WHEEL_INSTANCE}.{WHEEL}_TEETH_SURF_NODES, FREQUENCY=1000",
        "CSTRESS",
    ]


def seating_angle_rad(arc_mm: float, base_radius_mm: float) -> float:
    """Rotation of the pinion that moves its base circle by ``arc_mm`` (the seating step)."""
    arc = positive_input(arc_mm, "seating arc")
    r_b = positive_input(base_radius_mm, "base radius")
    return arc / r_b


def step_name(torque_nmm: float) -> str:
    """Name of the load step of a torque, as ``position_deck_text`` writes it."""
    return f"LOAD_{positive_input(torque_nmm, 'torque') / 1000.0:.8g}NM".replace(".", "P")
