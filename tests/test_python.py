import unittest


def add_two_numbers(a: int, b: int) -> int:
    return a + b


class TestMultiple:
    def test_sum(self):
        assert add_two_numbers(2, 2) == 4


if __name__ == '__main__':
    unittest.main()
