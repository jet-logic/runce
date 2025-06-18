#!/bin/env python3
from time import sleep
from unittest import TestCase, main
from subprocess import PIPE, run
import re

from runce.utils import check_pid, kill_pid


class TestUtils(TestCase):

    def run_runce(self, *args, stdout_only=False):
        """Helper to run python -m runce with stderr capture"""
        cmd = ["python", "-m", "runce", *args]
        print("RUN:", *cmd)
        result = run(cmd, stdout=PIPE, stderr=PIPE, text=True)
        o = result.stdout + result.stderr
        print(o)
        # if stdout_only:
        #     return result.stdout
        # Combine stdout and stderr for verification
        return o

    def assertRegexInListOnce(self, regex: str, ls: "list[str]"):
        b = [1 for x in ls if re.search(regex, x)]
        self.assertEqual(len(b), 1, f"{regex} in {ls!r}")

    def test_split(self):
        o = self.run_runce(
            "run",
            "--split",
            "--",
            "python",
            "-c" 'from sys import stderr, stdout; stdout.write("123"); stderr.write("456")',
        )
        m = re.search(r"(?mx) (?:\W+|\A) Started: \W+ [^\)]+ \s+ \( [^\)]+ \) \s+ (.+)", o)
        self.assertTrue(m)
        n = m.group(1)
        self.assertTrue(n)
        o = self.run_runce("tail", "--header", "no", "-n", "1k", n)
        # print(n)
        self.assertEqual(o, "123")
        o = self.run_runce("tail", "--err", "--header", "no", "-n", "3b", n)
        self.assertEqual(o, "456")
        self.run_runce("kill", n)
        self.run_runce("clean", n)

    def test_clean(self):
        o = self.run_runce(
            "run",
            "--id",
            "citrus",
            "--",
            "python",
            "tests/echo.py",
            "citrus",
            "out",
            "99",
        )
        m = re.search(r"(?imx) \W+ PID \s* = \s *(\d+) \s*", o)
        print("match", m.group(1), o)
        pid = int(m.group(1))
        # kill_pid(pid)
        o = self.run_runce("clean", "citrus")
        self.assertEqual(o, "")
        o = self.run_runce("kill", "--dry-run", "citrus")
        self.assertRegex(o, r"(?xi) killed .+ \W+ citrus \W+")
        o = self.run_runce("kill", "--remove", "citrus")
        self.assertRegex(o, r"(?xi) killed .+ \W+ citrus \W+")

    def test_kill(self):
        o = self.run_runce("run", "--id", "carrot", "--", "python", "--version")
        m = re.search(r"(?imx) \W+ PID \s* = \s *(\d+) \s*", o)
        # print("PID", m.group(1), o)
        pid = int(m.group(1))
        for i in range(99):
            if not check_pid(pid):
                break
            print("check_pid", pid)
            sleep(1)
        o = self.run_runce("kill", "carrot")
        self.assertRegex(o, r"(?xim) (?:\W+|\A) no \W+ process \W+ .+ \W+ carrot (\W+|\Z)")
        o = self.run_runce("clean", "carrot")

    def test_tail(self):
        o = self.run_runce(
            "run",
            "--id",
            "tomato",
            "--",
            "python",
            "-c",
            "for x in 'ABCD EFGH IJKL MNOP QRST UVWX YZ'.split(): print(x)",
        )
        self.assertRegex(o, r"(?xim) (?:\W+|\A) started: \W+ .+ \W+ tomato \W+")
        sleep(1)
        o = self.run_runce("tail", "-n", "3", "--header", "no", "tomato")
        self.assertRegex(o, r"(?xim) QRST \W+ UVWX \W+ YZ \W+ \Z")

        o = self.run_runce("kill", "--remove", "tomato")
        self.assertRegex(o, r"(?xim) (?:\W+|\A) (?:killed|no\s+process) .+ \W+ tomato \W+")

    def test_cli(self):

        o = self.run_runce("run", "--id", "apple", "--", "python", "tests/echo.py", "apple")

        self.assertRegex(o, r"(?xim) (?:\W+|\A) started: \W+ .+ \W+ apple \W+")

        o = self.run_runce(
            "run",
            "--id",
            "banana",
            "--split",
            "--",
            "python",
            "tests/echo.py",
            "banana",
            "err",
        )
        self.assertRegex(o, r"(?xim) (?:\W+|\A) started: \W+ .+ \W+ banana \W+")

        o = self.run_runce("run", "--id", "pineapple", "--", "python", "tests/echo.py", "pineapple")
        self.assertRegex(o, r"(?xim) (?:\W+|\A) started: \W+ .+ \W+ pineapple \W+")

        a = [x for x in self.run_runce("status").strip().splitlines()]

        self.assertRegexInListOnce(r"(?xi) \W* live \W+ .+ \W+ apple \W+", a)
        self.assertRegexInListOnce(r"(?xi) \W* live \W+ .+ \W+ pineapple \W+", a)
        self.assertRegexInListOnce(r"(?xi) \W* live \W+ .+ \W+ banana \W+", a)

        o = self.run_runce("tail", "--header", "no", "-n", "1k", "pineapple")
        self.assertRegex(o, r"(?xim) \W* pineapple \W+ \d+ \W+")

        o = self.run_runce("tail", "--header", "no", "-n", "16b", "banana")
        self.assertEqual(o, "")
        o = self.run_runce("tail", "--header", "no", "-n", "64b", "banana", "--err")
        self.assertRegex(o, r"(?xim) \W* banana \W+ \d+ \W+")

        o = self.run_runce("run", "--id", "banana", "--", "bash", "-c", "sleep 10")
        self.assertRegex(o, r"(?xim) \W* found \W+ .+ \W+ banana \W+")

        o = self.run_runce("kill", "app")
        self.assertRegex(o, r"(?xim) \W* app \W+ is \W+ ambiguous")

        o = self.run_runce("kill", "apple")
        self.assertRegex(o, r"(?xim) killed .+ \W+ apple \W+")

        a = self.run_runce("kill", "lemon", "banana").strip().splitlines()
        self.assertRegexInListOnce(r"(?xi) (?:\W+|\A) no \s+ record .+ \W+ lemon \W+", a)
        self.assertRegexInListOnce(r"(?xi)(?:\W+|\A) killed .+ \W+ banana \W+", a)

        o = self.run_runce("restart", "banana")

        a = self.run_runce("status").strip().splitlines()
        self.assertRegexInListOnce(r"(?xi) (?:\W+|\A) live \W+ .+ \W+ pineapple \W+", a)
        self.assertRegexInListOnce(r"(?xi) (?:\W+|\A) live \W+ .+ \W+ banana \W+", a)
        self.assertRegexInListOnce(r"(?xi) (?:\W+|\A) done \W+ .+ \W+ apple \W+", a)

        self.assertRegex(
            self.run_runce("clean", "apple"),
            r"(?xim)^ (?:\W+|\A) Cleaning \W+ .+ \W+ apple",
        )
        a = self.run_runce("list").strip().splitlines()
        self.assertRegexInListOnce(r"(?xi) \W+ \d+  \W+ pineapple \W+", a)
        self.assertRegexInListOnce(r"(?xi) \W+ \d+  \W+ banana \W+", a)
        a = self.run_runce("kill", "--remove", "pi", "b").strip().splitlines()
        self.assertRegexInListOnce(r"(?xi) killed .+ \W+ pineapple \W+", a)
        self.assertRegexInListOnce(r"(?xi) killed .+ \W+ banana \W+", a)


if __name__ == "__main__":
    main()
