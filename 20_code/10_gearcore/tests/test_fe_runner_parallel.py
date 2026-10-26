"""The runner of a deck folder (``run_all.ps1`` of ``build_fe_decks.py``): several jobs at a
time with ``-Parallel``, the skip of completed positions and the extraction kept."""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_fe_decks.py"


def _runner_text() -> str:
    spec = importlib.util.spec_from_file_location("build_fe_decks_for_runner", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    text: str = module._runner_text()
    return text


def test_runner_queues_jobs_and_keeps_the_skip_and_the_extraction() -> None:
    text = _runner_text()
    assert 'param([string]$Launcher = "abaqus", [int]$Cpus = 4, [int]$Parallel = 1)' in text
    assert "Start-Job -Name $job" in text
    assert "Wait-Job -Any -Timeout 30" in text
    assert "-ge $Parallel" in text  # the queue waits while $Parallel jobs run
    assert text.count('Select-String -Path $sta -Pattern "COMPLETED SUCCESSFULLY" -Quiet') == 2
    assert "already completed" in text
    assert '"cpus=$cores" "interactive" "ask_delete=OFF"' in text
    # a solved position whose fields are missing or cut short is extracted again, not solved
    assert (
        '$extracted = (Test-Path "${job}_fields.json") -and (Test-Path "${job}_stress.npz")' in text
    )
    assert "if ($solved -and ($extracted -or -not $extractable)) {" in text
    assert "extract $job again (solved before" in text
    assert "if (-not $solved) {" in text
    assert "$Cpus, $solved | Out-Null" in text
    # the extraction runs inside the background job, so the queue never blocks on it
    block = text.split("Start-Job -Name $job -ScriptBlock {")[1].split("} -ArgumentList")[0]
    assert '& $launcher "python" "extract_odb.py" "$name"' in block
    assert (
        "extract_odb.py"
        not in text.split("function Complete-Position")[1].split("function Complete-Finished")[0]
    )
    assert (
        "Complete-Finished" in text.split("foreach ($deck")[1]
    )  # finished jobs collected in the loop
    assert text.rstrip().endswith("Complete-Finished")  # and once more after the last job


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
