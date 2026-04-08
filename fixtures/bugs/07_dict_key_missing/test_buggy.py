from solution import get_price


def test_missing_price_key():
    assert get_price({"name": "Book"}) == 0
