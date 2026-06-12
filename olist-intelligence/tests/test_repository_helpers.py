from src.database.dataframe_factory import empty_frame, empty_frame_from
from src.database.repository_errors import zero_on_error


def test_empty_frame_helpers_create_requested_columns():
    assert empty_frame(["a", "b"]).columns.tolist() == ["a", "b"]
    assert empty_frame_from("x", "y").columns.tolist() == ["x", "y"]


def test_zero_on_error_returns_default():
    @zero_on_error({"ok": False})
    def failing():
        raise ValueError("boom")

    assert failing() == {"ok": False}
