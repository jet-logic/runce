#!/bin/env python3
import unittest

from runce.utils import filesizepu


class TestFilesizep(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(filesizepu("1b"), (1, "b"))
        self.assertEqual(filesizepu("1024b"), (1024, "b"))

    def test_kilobytes(self):
        self.assertEqual(filesizepu("1k"), (1024, "k"))
        self.assertEqual(filesizepu("2K"), (2048, "k"))
        self.assertEqual(filesizepu("1.5k"), (1536, "k"))
        self.assertEqual(filesizepu("2Kb"), (2048, "k"))

    # def test_megabytes(self):
    #     self.assertEqual(filesizepu("1m"), 1048576)
    #     self.assertEqual(filesizepu("2M"), 2097152)

    # def test_gigabytes(self):
    #     self.assertEqual(filesizepu("1g"), 1073741824)
    #     self.assertEqual(filesizepu("3G"), 3221225472)
    #     self.assertEqual(filesizepu("1GB"), 1073741824)

    # def test_terabytes(self):
    #     self.assertEqual(filesizepu("1t"), 1099511627776)

    # def test_petabytes(self):
    #     self.assertEqual(filesizepu("1p"), 1125899906842624)

    # def test_exabytes(self):
    #     self.assertEqual(filesizepu("1e"), 1152921504606846976)

    def test_zettabytes(self):
        self.assertEqual(filesizepu("1z"), (1180591620717411303424, "z"))

    # def test_yottabytes(self):
    #     self.assertEqual(filesizepu("1y"), 1208925819614629174706176)

    def test_no_unit(self):
        self.assertEqual(filesizepu("1024"), (1024.0, ""))
        self.assertEqual(
            filesizepu("1208925819614629174706176"), (1208925819614629174706176, "")
        )

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            filesizepu("abc")
        with self.assertRaises(ValueError):
            filesizepu("k")
        with self.assertRaises(ValueError):
            filesizepu("1x")  # invalid unit
        with self.assertRaises(ValueError):
            filesizepu("1BB")
        with self.assertRaises(ValueError):
            filesizepu("9xb")
        with self.assertRaises(ValueError):
            filesizepu("3.14")

    def test_case_insensitive(self):
        # self.assertEqual(filesizepu("1K"), 1024)
        # self.assertEqual(filesizepu("1kB"), 1024)
        # self.assertEqual(filesizepu("1Kb"), 1024)
        # self.assertEqual(filesizepu("1KB"), 1024)
        self.assertEqual(filesizepu("2 KB"), (1024 * 2, "k"))


if __name__ == "__main__":
    unittest.main()
