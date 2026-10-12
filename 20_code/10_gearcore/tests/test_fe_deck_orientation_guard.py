"""The guard against a wrongly assigned CONVERSE orientation file: the labels of its
distribution and field variables must be those of the mesh, and against the folder's own
orientation piece every row must agree (a mapping on the same numbering at other node
positions has the same labels and other vectors)."""

import pytest

from gearcore.errors import InputRangeError, ParseError
from gearcore.fe import deck as dk

MESH = """*HEADING
two bricks
*NODE, NSET=ALL
1, 0., 0., 0.
2, 1., 0., 0.
3, 1., 1., 0.
4, 0., 1., 0.
5, 0., 0., 1.
6, 1., 0., 1.
7, 1., 1., 1.
8, 0., 1., 1.
9, 0., 0., 2.
10, 1., 0., 2.
11, 1., 1., 2.
12, 0., 1., 2.
*ELEMENT, TYPE=C3D8I, ELSET=WHEEL
1, 1, 2, 3, 4, 5, 6, 7, 8
2, 5, 6, 7, 8, 9, 10, 11, 12
"""


def _cof(elements: dict[int, str], nodes: tuple[int, ...]) -> str:
    rows = [f" {label}, {vectors}" for label, vectors in elements.items()]
    return "\n".join(
        [
            "*DISTRIBUTION TABLE, NAME=T",
            " COORD3D, COORD3D",
            "*DISTRIBUTION, NAME=D, LOCATION=ELEMENT, TABLE=T",
            " , 1.0, 0.0, 0.0, 0.0, 1.0, 0.0",
            *rows,
            "*ORIENTATION, NAME=O, DEFINITION=COORDINATES",
            " D",
            "*SOLID SECTION, ELSET=CONVERSE_AUTO_SOLID, MATERIAL=M, ORIENTATION=O",
            "*MATERIAL, NAME=M",
            "*INITIAL CONDITIONS, TYPE=FIELD, VARIABLE=1",
            *(f" {n}, 0.6" for n in nodes),
            "*INITIAL CONDITIONS, TYPE=FIELD, VARIABLE=2",
            *(f" {n}, 0.1" for n in nodes),
        ]
    )


ALONG_X = "1.0, 0.0, 0.0, 0.0, 1.0, 0.0"
TILTED = "0.8, 0.6, 0.0, -0.6, 0.8, 0.0"
NODES = tuple(range(1, 13))


def _labels() -> tuple[dict[int, tuple[int, ...]], tuple[int, ...]]:
    return dk.read_element_connectivity(MESH), dk.read_node_labels(MESH)


def test_node_labels_are_read_in_file_order() -> None:
    assert dk.read_node_labels(MESH) == NODES
    with pytest.raises(ParseError):
        dk.read_node_labels("*ELEMENT, TYPE=C3D8\n1, 1, 2, 3, 4, 5, 6, 7, 8\n")


def test_a_fitting_file_passes_and_reports_its_counts() -> None:
    elements, nodes = _labels()
    fit = dk.verify_orientation_file(
        _cof({1: ALONG_X, 2: TILTED}, NODES), element_labels=elements, node_labels=nodes
    )
    assert (fit.elements, fit.nodes, fit.reference) == (2, 12, None)


def test_other_element_labels_are_refused() -> None:
    elements, nodes = _labels()
    extra = r"elements of the mesh 2, of the file 3.*not in the mesh \(first \[3\]\)"
    with pytest.raises(InputRangeError, match=extra):
        dk.verify_orientation_file(
            _cof({1: ALONG_X, 2: TILTED, 3: ALONG_X}, NODES),
            element_labels=elements,
            node_labels=nodes,
            name="pocket.cof",
        )
    missing = r"pocket.cof does not belong.*missing in the file \(first \[2\]\)"
    with pytest.raises(InputRangeError, match=missing):
        dk.verify_orientation_file(
            _cof({1: ALONG_X}, NODES), element_labels=elements, node_labels=nodes, name="pocket.cof"
        )


def test_other_node_labels_are_refused() -> None:
    elements, nodes = _labels()
    with pytest.raises(InputRangeError, match=r"nodes of the mesh 12, of the file 13"):
        dk.verify_orientation_file(
            _cof({1: ALONG_X, 2: TILTED}, NODES + (13,)), element_labels=elements, node_labels=nodes
        )


def test_the_folder_piece_tells_a_mapping_on_other_node_positions_apart() -> None:
    elements, nodes = _labels()
    built_with = _cof({1: ALONG_X, 2: TILTED}, NODES)
    piece = dk.split_orientation_file(built_with).part
    # the same mapping passes against the piece
    fit = dk.verify_orientation_file(
        built_with,
        element_labels=elements,
        node_labels=nodes,
        reference_text=piece,
        reference_name="wheel_orientation_QS_part.inp",
    )
    assert fit.reference == "wheel_orientation_QS_part.inp"
    # a mapping with the same labels and other vectors (other node positions) is refused
    other = _cof({1: ALONG_X, 2: ALONG_X}, NODES)
    differs = r"not the mapping of this folder: 1 of 2 element orientations differ.*first element 2"
    with pytest.raises(InputRangeError, match=differs):
        dk.verify_orientation_file(
            other,
            element_labels=elements,
            node_labels=nodes,
            reference_text=piece,
            reference_name="wheel_orientation_QS_part.inp",
            name="wheel_mesh_QS.cof",
        )


def test_inputs_are_checked() -> None:
    elements, nodes = _labels()
    with pytest.raises(InputRangeError, match="orientation file text"):
        dk.verify_orientation_file("", element_labels=elements, node_labels=nodes)
    with pytest.raises(InputRangeError, match="labels of the mesh are required"):
        dk.verify_orientation_file(
            _cof({1: ALONG_X, 2: TILTED}, NODES), element_labels=[], node_labels=nodes
        )
