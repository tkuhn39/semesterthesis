"""Shared fixtures: repository paths, the (optional) local STplus installation, packaged fixtures."""

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

# hypothesis keeps caches (constants, unicode data) in a storage directory: not in the repository
os.environ.setdefault(
    "HYPOTHESIS_STORAGE_DIRECTORY", str(Path(tempfile.gettempdir()) / "gearcore_hypothesis")
)

import pytest  # noqa: E402
from hypothesis import HealthCheck, settings  # noqa: E402

from gearcore.data import data_path, stplus_case_dirs  # noqa: E402

# no example database: a test run writes nothing into the repository
settings.register_profile("dev", max_examples=50, deadline=None, database=None)
settings.register_profile(
    "ci",
    max_examples=300,
    deadline=None,
    database=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STPLUS_ROOT = REPO_ROOT / "30_references_and_examples" / "33_STplus" / "STplus11-1F"
DEFAULT_MEASUREMENTS_ROOT = REPO_ROOT / "70_input" / "71_Messungen"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def stplus_root() -> Path:
    """Local STplus installation; tests using it skip with a visible reason when it is absent."""
    root = Path(os.environ.get("GEARCORE_STPLUS_ROOT", DEFAULT_STPLUS_ROOT))
    if not (root / "bin" / "STplus.exe").is_file():
        pytest.skip(f"local STplus installation not found at {root} (reference-only test)")
    return root


@pytest.fixture(scope="session")
def measurements_root() -> Path:
    """The user's measurement folder (P40, contour scans, roughness); tests using it skip with a
    visible reason where it is absent (it is versioned, but only in this repository)."""
    root = Path(os.environ.get("GEARCORE_MEASUREMENTS_ROOT", DEFAULT_MEASUREMENTS_ROOT))
    if not (root / "GINA").is_dir():
        pytest.skip(f"measurement folder not found at {root} (reference-only test)")
    return root


@pytest.fixture(scope="session")
def fixture_case_dirs() -> list[Path]:
    return stplus_case_dirs()


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrise ``case_dir`` over the packaged STplus fixture cases (visible ids)."""
    if "case_dir" in metafunc.fixturenames:
        dirs = stplus_case_dirs()
        metafunc.parametrize("case_dir", dirs, ids=[d.name for d in dirs])


@pytest.fixture
def sources_path() -> Path:
    return data_path("sources.yaml")


@pytest.fixture
def tmp_text_file(tmp_path: Path) -> Iterator[Path]:
    yield tmp_path / "file.txt"
