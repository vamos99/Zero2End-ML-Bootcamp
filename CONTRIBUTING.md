# Contributing

Thank you for considering a contribution to Zero2End ML Bootcamp.

This repository is maintained as a practical open-source reference for analytics engineering, machine learning workflow design, and maintainable data applications using the Olist dataset.

## Scope

Useful contributions include:

- documentation improvements;
- setup and reproducibility fixes;
- data contract and validation improvements;
- dashboard or API contract fixes;
- focused tests;
- issue triage and validation notes.

Please avoid large rewrites without an issue first. The project is a learning and reference project, not a production SaaS platform.

## Local setup

Main implementation files are under `olist-intelligence/`.

```bash
cd olist-intelligence
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v --tb=short
```

Some commands require local Olist data files. Local data and generated database files should stay out of Git.

## Pull requests

A pull request should include:

- what changed;
- why it changed;
- validation commands;
- screenshots only for UI changes;
- known limitations.

Keep changes small and reviewable. Separate documentation, refactor, feature, and validation work when possible.

## AI-assisted work

AI assistants may be used for planning, documentation drafting, test suggestions, refactoring support, and review assistance. All changes must still be understood, checked, and approved by a human maintainer before merging.
