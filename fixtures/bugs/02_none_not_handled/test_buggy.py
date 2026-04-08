from solution import get_user_name


def test_none_user():
    assert get_user_name(None) == ""
