import unittest

from server import evaluate


class CalculatorTests(unittest.TestCase):
    def test_basic_and_precedence(self):
        self.assertEqual(evaluate("1+2*3"), 7)
        self.assertEqual(evaluate("(1+2)*3"), 9)

    def test_decimal_and_unary(self):
        self.assertEqual(evaluate("1.5+2.25"), 3.75)
        self.assertEqual(evaluate("-5+8"), 3)
        self.assertEqual(evaluate("3*-2"), -6)

    def test_square_root(self):
        self.assertEqual(evaluate("√(9)"), 3)
        self.assertEqual(evaluate("√9+1"), 4)

    def test_invalid_and_zero_division(self):
        with self.assertRaises(ValueError):
            evaluate("1/0")
        with self.assertRaises(ValueError):
            evaluate("2+abc")
        with self.assertRaises(ValueError):
            evaluate("√(-1)")


if __name__ == "__main__":
    unittest.main()
