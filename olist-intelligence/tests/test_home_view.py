from src.views.home_view import _scorecard_markdown


def test_scorecard_markdown_keeps_measured_change_visible():
    rows = [
        {
            "area": "Actual delivery operation",
            "baseline": "6.77% late rate",
            "current_or_target": "No post-intervention delivery period",
            "measured_change": "No actual delivery-time improvement measured",
            "status": "Source baseline only",
        }
    ]

    result = _scorecard_markdown(rows)

    assert "Actual delivery operation" in result
    assert "No actual delivery-time improvement measured" in result
    assert "Source baseline only" in result
