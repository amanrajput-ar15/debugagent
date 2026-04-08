from solution import sort_scores


def test_desc_order():
    assert sort_scores([1, 3, 2]) == [3, 2, 1]
