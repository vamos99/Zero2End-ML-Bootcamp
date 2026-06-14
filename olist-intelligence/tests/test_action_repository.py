from unittest.mock import patch

from src.database.action_repository import _to_python_number, get_recent_actions


class ScalarLike:
    def item(self):
        return 12.5


def test_to_python_number_converts_scalar_like_value():
    assert _to_python_number(ScalarLike()) == 12.5


def test_to_python_number_keeps_plain_value():
    assert _to_python_number(7) == 7


def test_recent_actions_clamps_limit_before_query():
    with patch("src.database.action_repository.pd.read_sql") as read_sql:
        get_recent_actions(limit=500)

    assert read_sql.call_args.kwargs["params"]["limit"] == 100
