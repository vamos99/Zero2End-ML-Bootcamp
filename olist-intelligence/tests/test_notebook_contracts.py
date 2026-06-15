from pathlib import Path

from scripts.validate_notebooks import validate_notebooks


def test_source_notebooks_follow_reproducibility_contract():
    notebook_dir = Path(__file__).resolve().parents[1] / "notebooks"

    assert validate_notebooks(notebook_dir) == []
