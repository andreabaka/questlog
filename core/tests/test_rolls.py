from django.test import TestCase
from core.utils import roll_exploding_d10


class ExplodingD10Tests(TestCase):

    def test_rolls_are_between_1_and_10(self):
        result = roll_exploding_d10()
        rolls = result["rolls"]

        self.assertTrue(len(rolls) >= 1)
        for r in rolls:
            self.assertGreaterEqual(r, 1)
            self.assertLessEqual(r, 10)

    def test_total_equals_sum_of_rolls(self):
        result = roll_exploding_d10()
        self.assertEqual(result["total"], sum(result["rolls"]))
