import unittest
from typing import List, Dict, Any

from runce.utils import generate_pseudowords, look_multiple, uuid_to_phonetic_words


class TestLookMultiple(unittest.TestCase):
    def setUp(self):
        self.test_data = [
            {"name": "apple", "color": "red"},
            {"name": "banana", "color": "yellow"},
            {"name": "pineapple", "color": "brown"},
            {"name": "grape", "color": "purple"},
            {"name": "kiwi", "color": "green"},
        ]

        # Track callbacks for testing
        self.ambiguous_calls = []
        self.not_found_calls = []

    def ambiguous_callback(self, id: str):
        self.ambiguous_calls.append(id)

    def not_found_callback(self, id: str):
        self.not_found_calls.append(id)

    def test_exact_match_single(self):
        """Test single exact match"""
        results = list(
            look_multiple(
                ["apple"],
                self.test_data,
                self.ambiguous_callback,
                self.not_found_callback,
            )
        )
        self.assertEqual(len(results), 1, results)
        self.assertEqual(results[0]["name"], "apple")
        self.assertEqual(self.ambiguous_calls, [])
        self.assertEqual(self.not_found_calls, [])

    def test_multiple_exact_matches(self):
        """Test multiple exact matches"""
        results = list(
            look_multiple(
                ["apple", "banana"],
                self.test_data,
                self.ambiguous_callback,
                self.not_found_callback,
            )
        )
        self.assertEqual(len(results), 2)
        self.assertEqual({r["name"] for r in results}, {"apple", "banana"})
        self.assertEqual(self.ambiguous_calls, [])
        self.assertEqual(self.not_found_calls, [])

    # def test_partial_match_unambiguous(self):
    #     """Test unambiguous partial match"""
    #     results = list(
    #         look_multiple(
    #             ["app"],
    #             self.test_data,
    #             self.ambiguous_callback,
    #             self.not_found_callback,
    #         )
    #     )
    #     self.assertEqual(len(results), 1)
    #     self.assertEqual(results[0]["name"], "apple")
    #     self.assertEqual(self.ambiguous_calls, [])
    #     self.assertEqual(self.not_found_calls, [])

    def test_partial_match_ambiguous(self):
        """Test ambiguous partial match"""
        results = list(
            look_multiple(
                ["a"],  # Matches apple and banana and pineapple and grape
                self.test_data,
                self.ambiguous_callback,
                self.not_found_callback,
            )
        )
        self.assertEqual(len(results), 0, results)  # No yields for ambiguous matches
        self.assertEqual(self.not_found_calls, [])
        self.assertEqual(self.ambiguous_calls, ["a"])

    def test_not_found(self):
        """Test ID that doesn't exist"""
        results = list(
            look_multiple(
                ["mango"],
                self.test_data,
                self.ambiguous_callback,
                self.not_found_callback,
            )
        )
        self.assertEqual(len(results), 0)
        self.assertEqual(self.ambiguous_calls, [])
        self.assertEqual(self.not_found_calls, ["mango"])

    def test_mixed_cases(self):
        """Test mix of exact, partial, ambiguous and not found"""
        results = list(
            look_multiple(
                ["apple", "ki", "a", "mango"],
                self.test_data,
                self.ambiguous_callback,
                self.not_found_callback,
            )
        )
        # Should yield apple and kiwi (ki is unambiguous partial match)
        self.assertEqual(len(results), 2)
        self.assertEqual({r["name"] for r in results}, {"apple", "kiwi"})
        self.assertEqual(self.ambiguous_calls, ["a"])
        self.assertEqual(self.not_found_calls, ["mango"])

    def test_empty_ids(self):
        """Test empty ID list"""
        results = list(
            look_multiple(
                [], self.test_data, self.ambiguous_callback, self.not_found_callback
            )
        )
        self.assertEqual(len(results), 0)
        self.assertEqual(self.ambiguous_calls, [])
        self.assertEqual(self.not_found_calls, [])

    def test_empty_runs(self):
        """Test empty data list"""
        results = list(
            look_multiple(
                ["apple", "banana"],
                [],
                self.ambiguous_callback,
                self.not_found_callback,
            )
        )
        self.assertEqual(len(results), 0)
        self.assertEqual(self.ambiguous_calls, [])
        self.assertEqual(self.not_found_calls, ["apple", "banana"])

    def test_case_sensitivity(self):
        """Test case sensitivity handling"""
        results = list(
            look_multiple(
                ["Apple", "BANANA"],
                self.test_data,
                self.ambiguous_callback,
                self.not_found_callback,
            )
        )
        self.assertEqual(len(results), 0)  # No matches due to case mismatch
        self.assertEqual(self.ambiguous_calls, [])
        self.assertEqual(self.not_found_calls, ["Apple", "BANANA"])

    def test_duplicate_ids(self):
        """Test duplicate IDs in search list"""
        results = list(
            look_multiple(
                ["apple", "apple", "banana"],
                self.test_data,
                self.ambiguous_callback,
                self.not_found_callback,
            )
        )
        self.assertEqual(len(results), 2)  # Should still only match each item once
        self.assertEqual({r["name"] for r in results}, {"apple", "banana"})
        self.assertEqual(self.ambiguous_calls, [])
        self.assertEqual(self.not_found_calls, [])

    def test_uuid_to_phonetic_words(self):
        print(generate_pseudowords(3, 3))
        print(generate_pseudowords(3, 3))


if __name__ == "__main__":
    unittest.main()
