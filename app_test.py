import unittest
from unittest.mock import patch
from app import shares_input_check, cost_calculator, check
from logic_practice import input_check


class TestInputCheck(unittest.TestCase):
    def test_valid_float_input(self):
        self.assertEqual(shares_input_check((12.34,)), 12.34)

    def test_valid_string_input(self):
        self.assertEqual(shares_input_check("56.78"), 56.78)

    def test_invalid_tuple_input(self):
        self.assertEqual(shares_input_check(("invalid",)), "invalid input")

    def test_invalid_string_input(self):
        self.assertEqual(shares_input_check("invalid"), "invalid input")





if __name__ == '__main__':
    unittest.main()

# 401.77 nflx