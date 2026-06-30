import argparse
import json
from pathlib import Path


FORBIDDEN_TEXT = {
    "/Users/": "absolute local path",
    "ADDED BY ASSISTANT": "assistant-generated marker",
    "OTOMATİK EKLENDİ": "assistant-generated marker",
    "Production-ready API": "unverified production-readiness claim",
    "Proje başarıyla tamamlandı": "unverified completion claim",
    "Proje tamamlandı!": "unverified completion claim",
    "Churn AUC | **0.85**": "hard-coded model metric",
    "Potansiyel ROI | **~460K": "hard-coded ROI claim",
    "RMSE 7.6 gün": "hard-coded model metric",
    "ROI Tahmini:": "hard-coded ROI claim",
}

DIRECT_CHURN_LEAKAGE = "df['is_churn'] = (df['recency']"
REQUIRED_BY_NOTEBOOK = {
    "2_logistics_engine.ipynb": {
        "temporal_train_test_split": "strict temporal holdout helper",
    },
    "3_customer_sentinel.ipynb": {
        "has_usable_class_balance": "class-balance training gate",
    },
    "4_growth_engine.ipynb": {
        "segmentation_model.pkl": "correct segmentation artifact name",
    },
    "5_final_evaluation.ipynb": {
        "build_summary": "shared measured-results summary builder",
        "evidence_rows": "source baseline / benchmark / scenario evidence table",
        "outcome_scorecard": "plain-language before/current/result scorecard",
    },
    "6_executive_pipeline.ipynb": {
        "build_summary": "shared measured-results summary builder",
        "evidence_rows": "source baseline / benchmark / scenario evidence table",
        "outcome_scorecard": "plain-language before/current/result scorecard",
    },
}


def validate_notebook(path: Path) -> list[str]:
    errors = []
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: invalid notebook JSON: {exc}"]

    if not isinstance(notebook, dict) or not isinstance(notebook.get("cells"), list):
        return [f"{path}: notebook must be an object containing a cells list"]

    full_text = ""
    for index, cell in enumerate(notebook["cells"]):
        source = "".join(cell.get("source", []))
        full_text += source
        if cell.get("cell_type") != "code":
            continue

        if cell.get("execution_count") is not None:
            errors.append(f"{path}: code cell {index} has a stored execution count")
        if cell.get("outputs"):
            errors.append(f"{path}: code cell {index} has stored outputs")

    for pattern, description in FORBIDDEN_TEXT.items():
        if pattern in full_text:
            errors.append(f"{path}: contains {description}: {pattern}")

    if path.name == "3_customer_sentinel.ipynb" and DIRECT_CHURN_LEAKAGE in full_text:
        errors.append(f"{path}: churn label is derived directly from the recency feature")

    for pattern, description in REQUIRED_BY_NOTEBOOK.get(path.name, {}).items():
        if pattern not in full_text:
            errors.append(f"{path}: missing {description}: {pattern}")

    return errors


def validate_notebooks(notebook_dir: Path) -> list[str]:
    paths = sorted(notebook_dir.glob("*.ipynb"))
    if not paths:
        return [f"{notebook_dir}: no notebooks found"]

    return [error for path in paths for error in validate_notebook(path)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate source notebook contracts.")
    parser.add_argument(
        "--notebook-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "notebooks",
    )
    args = parser.parse_args()

    errors = validate_notebooks(args.notebook_dir)
    if errors:
        print("\n".join(errors))
        return 1

    print(f"Notebook validation passed: {args.notebook_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
