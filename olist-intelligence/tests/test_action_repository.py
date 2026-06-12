from src.database.action_repository import _to_python_number


class ScalarLike:
    def item(self):
        return 12.5


def test_to_python_number_converts_scalar_like_value():
    assert _to_python_number(ScalarLike()) == 12.5


def test_to_python_number_keeps_plain_value():
    assert _to_python_number(7) == 7
