import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np
from src.pipeline import load_baskets, encode_baskets, mine_rules, direct_metrics, build_network, verify_rules


class BasketTests(unittest.TestCase):
    def setUp(self):
        self.baskets = [frozenset({"a", "b"}), frozenset({"a"}), frozenset({"a"}),
                        frozenset({"b"}), frozenset({"b"})]

    def test_headerless_loader_preserves_first_transaction(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerows([[" A ", "a", "b", ""], [], ["b"]])
            baskets = load_baskets(path)
        self.assertEqual(baskets, [frozenset({"a", "b"}), frozenset({"b"})])

    def test_negative_lift_is_below_independence(self):
        expected = direct_metrics(self.baskets, {"a"}, {"b"})
        self.assertAlmostEqual(expected["support"], .2)
        self.assertAlmostEqual(expected["confidence"], 1 / 3)
        self.assertAlmostEqual(expected["lift"], 5 / 9)
        _, rules = mine_rules(encode_baskets(self.baskets), .1)
        self.assertTrue((rules.lift < 1).all())
        self.assertLess(verify_rules(self.baskets, rules), 1e-12)

    def test_network_filters_negative_associations(self):
        _, rules = mine_rules(encode_baskets(self.baskets), .1)
        self.assertEqual(build_network(rules).number_of_edges(), 0)

    def test_one_item_data_has_no_rules(self):
        _, rules = mine_rules(encode_baskets([frozenset({"a"})]), .1)
        self.assertTrue(rules.empty)

    def test_invalid_inputs_fail(self):
        with self.assertRaises(ValueError):
            encode_baskets([])
        with self.assertRaises(ValueError):
            mine_rules(encode_baskets(self.baskets), 0)
        with self.assertRaises(ValueError):
            direct_metrics(self.baskets, {"a"}, {"a"})


if __name__ == "__main__":
    unittest.main()
