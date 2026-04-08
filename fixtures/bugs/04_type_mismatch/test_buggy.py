from solution import add_tax


def test_string_number_input():
    assert add_tax("100", 0.1) == 110.0
