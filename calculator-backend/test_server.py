import unittest

from server import Handler, evaluate


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

    def test_scientific_extensions(self):
        self.assertEqual(evaluate("2^3"), 8)
        self.assertEqual(evaluate("sin(30)"), 0.5)
        self.assertEqual(evaluate("log(100)"), 2)
        self.assertEqual(evaluate("5!"), 120)
        self.assertEqual(evaluate("50%"), 0.5)

    def test_invalid_and_zero_division(self):
        with self.assertRaises(ValueError):
            evaluate("1/0")
        with self.assertRaises(ValueError):
            evaluate("2+abc")
        with self.assertRaises(ValueError):
            evaluate("√(-1)")

    def test_base_and_unit_conversion(self):
        self.assertEqual(Handler.convert_base({"value": "FF", "fromBase": 16, "toBase": 10}), "255")
        self.assertEqual(Handler.convert_base({"value": "1010", "fromBase": 2, "toBase": 16}), "A")
        self.assertEqual(Handler.convert_unit({"category": "length", "value": 1, "fromUnit": "km", "toUnit": "m"}), 1000)
        self.assertEqual(Handler.convert_unit({"category": "temperature", "value": 0, "fromUnit": "C", "toUnit": "F"}), 32)


if __name__ == "__main__":
    unittest.main()
