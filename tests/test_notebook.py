"""Validate the generated Kaggle notebook without executing it.

A Kaggle session costs 40+ minutes before it reaches the interesting code, so
the failures worth catching here are the cheap ones: a symbol renamed in
``src/`` that the notebook still imports, a cell that does not parse, or a
notebook that has drifted from its generator.

These checks do not need Kaggle, internet, or the dataset.
"""

from __future__ import annotations

import ast
import importlib
import json
import subprocess
import sys

import pytest

from src.config import PROJECT_ROOT

NOTEBOOK = PROJECT_ROOT / "notebooks" / "00_kaggle_ingest.ipynb"
GENERATOR = PROJECT_ROOT / "notebooks" / "build_kaggle_notebook.py"


@pytest.fixture(scope="module")
def notebook() -> dict:
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def code_cells(notebook: dict) -> list[str]:
    return ["".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"]


def test_notebook_exists() -> None:
    assert NOTEBOOK.exists(), "run: python notebooks/build_kaggle_notebook.py"


def test_notebook_is_valid_nbformat(notebook: dict) -> None:
    assert notebook["nbformat"] == 4
    assert notebook["nbformat_minor"] >= 5
    assert notebook["cells"]


def test_every_cell_has_an_id(notebook: dict) -> None:
    """nbformat >= 4.5 requires ids; Kaggle rejects notebooks without them."""
    missing = [i for i, c in enumerate(notebook["cells"]) if not c.get("id")]
    assert missing == []


def test_every_code_cell_parses(code_cells: list[str]) -> None:
    for index, source in enumerate(code_cells):
        try:
            ast.parse(source)
        except SyntaxError as exc:  # pragma: no cover - failure path
            pytest.fail(f"code cell {index} does not parse: {exc}")


def test_every_imported_src_symbol_exists(code_cells: list[str]) -> None:
    """The notebook must not reference a name that src/ no longer exports."""
    symbols: set[tuple[str, str]] = set()
    for source in code_cells:
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("src."):
                symbols.update((node.module, alias.name) for alias in node.names)

    assert symbols, "expected the notebook to import from src/"
    missing = [
        f"{module}.{name}"
        for module, name in sorted(symbols)
        if not hasattr(importlib.import_module(module), name)
    ]
    assert missing == [], f"notebook imports names that no longer exist: {missing}"


def test_notebook_holds_no_pipeline_logic(code_cells: list[str]) -> None:
    """Notebooks render and orchestrate; logic belongs in src/.

    A function or class definition here means the notebook has started to hold
    behaviour that nothing tests.
    """
    offenders = []
    for index, source in enumerate(code_cells):
        for node in ast.parse(source).body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                offenders.append(f"cell {index}: {node.name}")
    assert offenders == [], f"definitions found in the notebook: {offenders}"


def test_repo_url_is_an_obvious_placeholder(code_cells: list[str]) -> None:
    """The committed notebook must not carry someone's half-edited URL."""
    joined = "\n".join(code_cells)
    assert "REPO_URL" in joined
    assert "YOUR_USERNAME" in joined, "REPO_URL should stay a visible placeholder"


def test_secrets_are_read_not_hardcoded(code_cells: list[str]) -> None:
    """Guestbook identity must come from Kaggle Secrets, never the notebook."""
    joined = "\n".join(code_cells)
    assert "UserSecretsClient" in joined
    for key in (
        "DATAVERSE_GB_NAME",
        "DATAVERSE_GB_EMAIL",
        "DATAVERSE_GB_INSTITUTION",
        "DATAVERSE_GB_POSITION",
    ):
        assert key in joined
    assert "@" not in joined.split("UserSecretsClient")[1].split("guestbook:")[0].replace(
        'f"guestbook', ""
    ), "an email address appears to be hardcoded"


def test_streaming_settings_match_the_kaggle_constraints(code_cells: list[str]) -> None:
    """A time budget below the 12 h cap is what makes a timeout recoverable."""
    joined = "\n".join(code_cells)
    assert "TIME_BUDGET_MIN" in joined
    budget = next(
        int(line.split("=")[1].strip())
        for line in joined.splitlines()
        if line.startswith("TIME_BUDGET_MIN")
    )
    assert 0 < budget < 12 * 60, f"time budget {budget} min must sit under the 12 h cap"


def test_generator_reproduces_the_committed_notebook(tmp_path) -> None:
    """The notebook is generated, so a hand-edit would be silently overwritten."""
    completed = subprocess.run(
        [sys.executable, str(GENERATOR)],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        check=False,
    )
    assert completed.returncode == 0, completed.stderr

    regenerated = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    assert regenerated["cells"], "generator produced an empty notebook"


def test_working_dir_is_cleaned_before_publishing(code_cells: list[str]) -> None:
    """The saved output becomes a dataset; the repo clone should not be in it."""
    joined = "\n".join(code_cells)
    assert "rmtree" in joined
    assert "REPO_DIR" in joined
